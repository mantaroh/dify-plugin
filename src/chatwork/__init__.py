"""Chatwork Room Messenger プラグイン (Python 実装)."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

_manifest_path = Path(__file__).with_name("manifest.json")
with _manifest_path.open("r", encoding="utf-8") as f:
    manifest: Dict[str, Any] = json.load(f)

DEFAULT_BASE_URL = "https://api.chatwork.com/v2"


@dataclass
class ChatworkSettings:
    """チャットワークアクションで利用する設定値を表現するデータクラス。"""

    api_token: str
    base_url: str = DEFAULT_BASE_URL
    default_room_id: Optional[str] = None
    account_id: Optional[str] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ChatworkSettings":
        api_token = str(data.get("apiToken", "")).strip()
        if not api_token:
            raise ValidationError("Chatwork API トークン (apiToken) が設定されていません。")

        base_url = str(data.get("baseUrl", DEFAULT_BASE_URL)).strip() or DEFAULT_BASE_URL
        default_room_id = data.get("defaultRoomId")
        if isinstance(default_room_id, str):
            default_room_id = default_room_id.strip() or None

        account_id = data.get("accountId")
        if isinstance(account_id, str):
            account_id = account_id.strip() or None

        return cls(
            api_token=api_token,
            base_url=base_url.rstrip("/"),
            default_room_id=default_room_id,
            account_id=account_id,
        )


class ValidationError(Exception):
    """入力値が不正な場合に送出される例外。"""


class AuthenticationError(Exception):
    """認証が失敗した場合に送出される例外。"""

    def __init__(self, message: str, status: int, response_body: Any) -> None:
        super().__init__(message)
        self.status = status
        self.response_body = response_body


class ChatworkAPIError(Exception):
    """Chatwork API へのアクセスでエラーが発生した場合に送出される例外。"""

    def __init__(self, message: str, status: Optional[int], response_body: Any) -> None:
        super().__init__(message)
        self.status = status
        self.response_body = response_body


@dataclass
class _Response:
    status: int
    text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class ChatworkClient:
    """Chatwork API を呼び出すためのクライアント。"""

    def __init__(
        self,
        *,
        api_token: str,
        base_url: Optional[str] = None,
        request_impl: Optional[Callable[..., _Response]] = None,
    ) -> None:
        if not api_token:
            raise ValidationError("Chatwork API トークン (apiToken) が設定されていません。")

        self.api_token = api_token
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._request_impl = request_impl or self._default_request_impl

    def _default_request_impl(
        self, url: str, *, method: str, headers: Mapping[str, str], body: bytes
    ) -> _Response:
        request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urllib.request.urlopen(request) as response:  # type: ignore[call-arg]
                status = response.status
                text_bytes = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            text_bytes = exc.read()
        except urllib.error.URLError as exc:  # pragma: no cover - ネットワーク障害
            raise ChatworkAPIError(
                f"Chatwork API への接続に失敗しました: {exc.reason}",
                None,
                None,
            ) from exc

        text = text_bytes.decode("utf-8", errors="replace") if isinstance(text_bytes, bytes) else str(text_bytes)
        return _Response(status=status, text=text)

    def build_headers(self) -> Dict[str, str]:
        return {
            "X-ChatWorkToken": self.api_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def post_room_message(self, room_id: str, body_params: Mapping[str, str]) -> Dict[str, Any]:
        if not room_id:
            raise ValidationError("roomId が指定されていません。設定の defaultRoomId を確認してください。")

        url = f"{self.base_url}/rooms/{urllib.parse.quote(room_id)}/messages"
        encoded_body = urllib.parse.urlencode(body_params).encode("utf-8")

        response = self._request_impl(
            url,
            method="POST",
            headers=self.build_headers(),
            body=encoded_body,
        )

        try:
            payload = json.loads(response.text) if response.text else {}
        except json.JSONDecodeError as exc:
            raise ChatworkAPIError(
                f"Chatwork API のレスポンスを JSON として解釈できませんでした: {exc.msg}",
                response.status,
                response.text,
            ) from exc

        if response.status == 401:
            raise AuthenticationError("Chatwork API トークンが不正です。", response.status, payload)

        if not response.ok:
            raise ChatworkAPIError(
                f"Chatwork API へのリクエストが失敗しました (status={response.status})",
                response.status,
                payload,
            )

        return payload


def build_message_payload(
    *, message: Optional[str], self_mention: bool, link_urls: bool, account_id: Optional[str]
) -> Dict[str, str]:
    if not message:
        raise ValidationError("message は必須です。")

    body = message.strip()

    if link_urls:
        body = f"+{body}"

    if self_mention and account_id:
        body = f"[To:{account_id}] {body}"

    return {"body": body}


def _normalize_room_id(value: Any) -> str:
    if value is None:
        raise ValidationError("roomId が指定されていません。設定の defaultRoomId を確認してください。")

    if isinstance(value, (int, float)):
        value = str(int(value))

    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized

    raise ValidationError("roomId が指定されていません。設定の defaultRoomId を確認してください。")


def post_room_message_action(
    *,
    settings: Optional[Mapping[str, Any]] = None,
    inputs: Optional[Mapping[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
    request_impl: Optional[Callable[..., _Response]] = None,
) -> Dict[str, Any]:
    raw_settings = dict(settings or {})
    inputs = dict(inputs or {})
    logger = logger or logging.getLogger(__name__)

    config = ChatworkSettings.from_mapping(raw_settings)

    room_id_value = inputs.get("roomId") or config.default_room_id
    room_id = _normalize_room_id(room_id_value)

    message = inputs.get("message")
    self_mention = bool(inputs.get("selfMention", False))
    link_urls = bool(inputs.get("linkUrls", False))

    logger.debug(
        "[chatwork] postRoomMessage - preparing request",
        extra={
            "roomId": room_id,
            "messageLength": len(message) if isinstance(message, str) else None,
            "selfMention": self_mention,
            "linkUrls": link_urls,
        },
    )

    client = ChatworkClient(
        api_token=config.api_token,
        base_url=config.base_url,
        request_impl=request_impl,
    )
    payload = build_message_payload(
        message=message,
        self_mention=self_mention,
        link_urls=link_urls,
        account_id=config.account_id,
    )

    result = client.post_room_message(room_id, payload)

    normalized = {
        "messageId": result.get("message_id") or result.get("messageId"),
        "roomId": room_id,
        "postedAt": _normalize_timestamp(result),
        "raw": result,
    }

    logger.debug(
        "[chatwork] postRoomMessage - completed",
        extra={
            "messageId": normalized["messageId"],
            "roomId": normalized["roomId"],
        },
    )

    return normalized


def _normalize_timestamp(result: Mapping[str, Any]) -> Optional[str]:
    send_time = result.get("send_time") or result.get("postedAt")

    if isinstance(send_time, (int, float)):
        dt = datetime.utcfromtimestamp(float(send_time)).replace(microsecond=0)
        return dt.isoformat() + "Z"

    if isinstance(send_time, str):
        return send_time

    return None


actions = {
    "postRoomMessage": post_room_message_action,
}

errors = {
    "ValidationError": ValidationError,
    "AuthenticationError": AuthenticationError,
    "ChatworkAPIError": ChatworkAPIError,
}

utils = {
    "ChatworkClient": ChatworkClient,
    "buildMessagePayload": build_message_payload,
    "ChatworkSettings": ChatworkSettings,
}

__all__ = [
    "manifest",
    "actions",
    "errors",
    "utils",
    "ChatworkClient",
    "ChatworkSettings",
    "ValidationError",
    "AuthenticationError",
    "ChatworkAPIError",
    "build_message_payload",
    "post_room_message_action",
]
