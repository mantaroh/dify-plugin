"""Tests for the Chatwork Room Messenger plugin."""
from __future__ import annotations

import json
import urllib.parse

import pytest

from src.chatwork import (
    AuthenticationError,
    ChatworkAPIError,
    ChatworkClient,
    ChatworkSettings,
    ValidationError,
    build_message_payload,
    post_room_message_action,
)


class DummyResponse:
    """Simple response stub emulating `_Response`."""

    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@pytest.fixture
def success_response():
    def _factory(payload: dict[str, object]) -> DummyResponse:
        return DummyResponse(status=200, text=json.dumps(payload))

    return _factory


def test_build_message_payload_with_options() -> None:
    payload = build_message_payload(
        message="Hello Chatwork",
        self_mention=True,
        link_urls=True,
        account_id="999",
    )

    assert payload["body"] == "[To:999] +Hello Chatwork"


def test_build_message_payload_requires_message() -> None:
    with pytest.raises(ValidationError):
        build_message_payload(message=None, self_mention=False, link_urls=False, account_id=None)


def test_chatwork_client_requires_token() -> None:
    with pytest.raises(ValidationError):
        ChatworkClient(api_token="")


def test_chatwork_settings_from_mapping() -> None:
    config = ChatworkSettings.from_mapping(
        {"apiToken": " tok ", "baseUrl": "https://example.com/api/", "defaultRoomId": " 42 "}
    )

    assert config.api_token == "tok"
    assert config.base_url == "https://example.com/api"
    assert config.default_room_id == "42"


def test_post_room_message_action_success(success_response) -> None:
    captured = {}

    def fake_request(url: str, *, method: str, headers, body: bytes):
        captured["url"] = url
        captured["method"] = method
        captured["headers"] = headers
        captured["body"] = body
        return success_response({"message_id": "mid-1", "send_time": 1_700_000_000})

    result = post_room_message_action(
        settings={
            "apiToken": "token-123",
            "defaultRoomId": "room-42",
            "accountId": "321",
        },
        inputs={
            "message": "Hello",
            "selfMention": True,
            "linkUrls": True,
        },
        request_impl=fake_request,
    )

    assert result["messageId"] == "mid-1"
    assert result["roomId"] == "room-42"
    assert result["postedAt"] == "2023-11-14T22:13:20Z"

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/rooms/room-42/messages")
    assert captured["headers"]["X-ChatWorkToken"] == "token-123"

    sent_body = urllib.parse.parse_qs(captured["body"].decode("utf-8"))
    assert sent_body == {"body": ["[To:321] +Hello"]}


def test_post_room_message_action_requires_room_id(success_response) -> None:
    def fake_request(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("request_impl must not be invoked when validation fails")

    with pytest.raises(ValidationError):
        post_room_message_action(
            settings={"apiToken": "token"},
            inputs={"message": "hi"},
            request_impl=fake_request,
        )


def test_post_room_message_action_default_room(success_response) -> None:
    called = {}

    def fake_request(url: str, *, method: str, headers, body: bytes):
        called["room"] = url
        return success_response({"messageId": "123"})

    post_room_message_action(
        settings={"apiToken": "token", "defaultRoomId": "999"},
        inputs={"message": "ping"},
        request_impl=fake_request,
    )

    assert called["room"].endswith("/rooms/999/messages")


def test_post_room_message_action_custom_base_url(success_response) -> None:
    captured = {}

    def fake_request(url: str, *, method: str, headers, body: bytes):
        captured["url"] = url
        return success_response({"messageId": "1"})

    post_room_message_action(
        settings={
            "apiToken": "token",
            "defaultRoomId": "room-1",
            "baseUrl": "https://chatwork.example.com/api/",
        },
        inputs={"message": "ping"},
        request_impl=fake_request,
    )

    assert captured["url"].startswith("https://chatwork.example.com/api/rooms/room-1/messages")


def test_post_room_message_action_authentication_error() -> None:
    def fake_request(*args, **kwargs):
        return DummyResponse(status=401, text=json.dumps({"error": "Unauthorized"}))

    with pytest.raises(AuthenticationError):
        post_room_message_action(
            settings={"apiToken": "token", "defaultRoomId": "room"},
            inputs={"message": "hi"},
            request_impl=fake_request,
        )


def test_post_room_message_action_http_error() -> None:
    def fake_request(*args, **kwargs):
        return DummyResponse(status=500, text=json.dumps({"error": "server"}))

    with pytest.raises(ChatworkAPIError):
        post_room_message_action(
            settings={"apiToken": "token", "defaultRoomId": "room"},
            inputs={"message": "hi"},
            request_impl=fake_request,
        )
