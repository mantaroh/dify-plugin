"""HelloWorld ツールプラグイン."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

_MANIFEST_PATH = Path(__file__).with_name("manifest.json")
with _MANIFEST_PATH.open("r", encoding="utf-8") as fp:
    manifest: Dict[str, Any] = json.load(fp)


class ValidationError(Exception):
    """入力値が期待した形式ではない場合に送出される例外。"""


_SUPPORTED_LANGUAGES = {
    "ja": "こんにちは、{name}!",
    "en": "Hello, {name}!",
}


def _normalize_name(value: Optional[Any]) -> str:
    if value is None:
        return "World"
    if not isinstance(value, str):
        raise ValidationError("name は文字列で指定してください。")
    normalized = value.strip()
    return normalized or "World"


def _normalize_language(value: Optional[Any]) -> str:
    if value is None:
        return "ja"
    if not isinstance(value, str):
        raise ValidationError("language は文字列で指定してください。")
    language = value.lower()
    if language not in _SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(_SUPPORTED_LANGUAGES))
        raise ValidationError(f"language は {supported} のいずれかを指定してください。")
    return language


def say_hello_tool(
    *, inputs: Optional[Mapping[str, Any]] = None, logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """HelloWorld チュートリアルのツール実装."""

    logger = logger or logging.getLogger(__name__)
    payload = dict(inputs or {})

    logger.debug("[hello_world] sayHello invoked", extra={"inputs": payload})

    name = _normalize_name(payload.get("name"))
    language = _normalize_language(payload.get("language"))

    template = _SUPPORTED_LANGUAGES[language]
    message = template.format(name=name)

    logger.info(
        "[hello_world] sayHello completed",
        extra={"message": message, "language": language, "name": name},
    )

    return {
        "message": message,
        "raw": {
            "language": language,
            "name": name,
        },
    }


tools = {
    "sayHello": say_hello_tool,
}

errors = {
    "ValidationError": ValidationError,
}

__all__ = [
    "manifest",
    "tools",
    "errors",
    "say_hello_tool",
    "ValidationError",
]
