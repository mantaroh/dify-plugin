"""GitHub Workflow Exporter プラグイン.

公開済みの Dify ワークフロー DSL を GitHub にコミットするアクションを提供します。
"""
from __future__ import annotations

import base64
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_BRANCH = "main"
DEFAULT_BASE_PATH = "dify/workflows"
DEFAULT_EXTENSION = ".json"
DEFAULT_COMMIT_TEMPLATE = "chore: sync Dify workflow {workflowId}"


class ValidationError(Exception):
    """入力や設定が不足している場合に送出される例外。"""


class GitHubAPIError(Exception):
    """GitHub API 呼び出し時のエラー。"""

    def __init__(self, message: str, status: Optional[int] = None, body: Any | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class PluginSettings:
    token: str
    repository_owner: str
    repository_name: str
    branch: str = DEFAULT_BRANCH
    base_path: str = DEFAULT_BASE_PATH
    file_extension: str = DEFAULT_EXTENSION
    commit_message_template: str = DEFAULT_COMMIT_TEMPLATE
    author_name: Optional[str] = None
    author_email: Optional[str] = None

    @classmethod
    def from_context(cls, context: Mapping[str, Any] | None) -> "PluginSettings":
        context = context or {}
        auth = context.get("auth", {}) if isinstance(context, Mapping) else {}
        secrets = context.get("secrets", {}) if isinstance(context, Mapping) else {}
        settings = context.get("settings", {}) if isinstance(context, Mapping) else {}
        credentials = context.get("credentials", {}) if isinstance(context, Mapping) else {}

        token = cls._select_first_nonempty(
            [
                secrets.get("githubToken"),
                auth.get("githubToken"),
                credentials.get("githubToken"),
            ]
        )
        if not token:
            raise ValidationError("GitHub Access Token (githubToken) が設定されていません。")

        repository_owner = str(settings.get("repositoryOwner", "")).strip()
        repository_name = str(settings.get("repositoryName", "")).strip()
        if not repository_owner or not repository_name:
            raise ValidationError("repositoryOwner / repositoryName を設定してください。")

        branch = str(settings.get("branch", DEFAULT_BRANCH)).strip() or DEFAULT_BRANCH
        base_path = cls._normalize_path(str(settings.get("basePath", DEFAULT_BASE_PATH)).strip() or DEFAULT_BASE_PATH)
        file_extension = str(settings.get("fileExtension", DEFAULT_EXTENSION)).strip() or DEFAULT_EXTENSION
        commit_message_template = (
            str(settings.get("commitMessageTemplate", DEFAULT_COMMIT_TEMPLATE)).strip() or DEFAULT_COMMIT_TEMPLATE
        )
        author_name = cls._optional_str(settings.get("authorName"))
        author_email = cls._optional_str(settings.get("authorEmail"))

        return cls(
            token=token,
            repository_owner=repository_owner,
            repository_name=repository_name,
            branch=branch,
            base_path=base_path,
            file_extension=file_extension,
            commit_message_template=commit_message_template,
            author_name=author_name,
            author_email=author_email,
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if not value:
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _select_first_nonempty(values: list[Any]) -> Optional[str]:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _normalize_path(path: str) -> str:
        path = path.replace("\\", "/")
        return path.strip("/")


class GitHubContentClient:
    """GitHub Contents API を扱う軽量クライアント。"""

    def __init__(self, *, settings: PluginSettings) -> None:
        self.settings = settings

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "dify-github-workflow-exporter",
        }

    def _build_url(self, path: str, *, branch: str) -> str:
        encoded_path = urllib.parse.quote(path)
        return (
            f"{GITHUB_API_BASE}/repos/{self.settings.repository_owner}/"
            f"{self.settings.repository_name}/contents/{encoded_path}?ref={urllib.parse.quote(branch)}"
        )

    def _request(self, url: str, *, method: str, body: Optional[bytes] = None) -> Dict[str, Any]:
        request = urllib.request.Request(url, method=method, headers=self._headers(), data=body)
        try:
            with urllib.request.urlopen(request) as response:  # type: ignore[arg-type]
                text = response.read().decode("utf-8")
                payload = json.loads(text) if text else {}
                return {"status": response.status, "data": payload}
        except urllib.error.HTTPError as exc:
            status = exc.code
            error_body = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(error_body)
            except json.JSONDecodeError:
                payload = {"message": error_body}
            raise GitHubAPIError(payload.get("message", "GitHub API error"), status=status, body=payload) from exc

    def get_existing_sha(self, *, path: str, branch: str) -> Optional[str]:
        url = self._build_url(path, branch=branch)
        try:
            response = self._request(url, method="GET")
        except GitHubAPIError as exc:  # noqa: PERF203 - 明示的に 404 を扱う
            if exc.status == 404:
                return None
            raise
        return response["data"].get("sha")

    def put_content(
        self,
        *,
        path: str,
        content_text: str,
        commit_message: str,
        branch: str,
        author_name: Optional[str],
        author_email: Optional[str],
    ) -> Dict[str, Any]:
        url = self._build_url(path, branch=branch)
        sha = self.get_existing_sha(path=path, branch=branch)

        payload: MutableMapping[str, Any] = {
            "message": commit_message,
            "content": base64.b64encode(content_text.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        if author_name or author_email:
            author_block: Dict[str, str] = {}
            if author_name:
                author_block["name"] = author_name
            if author_email:
                author_block["email"] = author_email
            payload["author"] = author_block
            payload["committer"] = author_block

        body = json.dumps(payload).encode("utf-8")
        response = self._request(url, method="PUT", body=body)
        return response["data"]


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "workflow"


def build_target_path(
    *,
    base_path: str,
    workflow_id: str,
    workflow_name: Optional[str],
    version: Optional[str],
    file_extension: str,
    explicit_path: Optional[str] = None,
) -> str:
    if explicit_path:
        normalized = explicit_path.replace("\\", "/").strip("/")
        return normalized or f"{base_path}/{workflow_id}{file_extension}"

    base_path = base_path.strip("/")
    name_or_id = slugify(workflow_name) if workflow_name else slugify(workflow_id)
    suffix = f"-v{version}" if version else ""
    return f"{base_path}/{name_or_id}{suffix}{file_extension}"


def normalize_dsl(dsl: Any) -> str:
    if isinstance(dsl, (dict, list)):
        return json.dumps(dsl, ensure_ascii=False, indent=2)
    return str(dsl)


def render_commit_message(
    *,
    template: str,
    workflow_id: str,
    workflow_name: Optional[str],
    version: Optional[str],
    fallback: Optional[str] = None,
) -> str:
    base_message = fallback or DEFAULT_COMMIT_TEMPLATE
    try:
        return template.format(workflowId=workflow_id, workflowName=workflow_name or "", version=version or "")
    except Exception:  # noqa: BLE001 - フォーマット失敗時はフォールバック
        logger.warning("commit message template failed; using fallback")
        return base_message.format(workflowId=workflow_id, workflowName=workflow_name or "", version=version or "")


def execute(inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Action entrypoint called by Dify."""

    published = bool(inputs.get("published"))
    workflow_id = str(inputs.get("workflowId", "")).strip()
    if not workflow_id:
        raise ValidationError("workflowId は必須です。")

    workflow_name = inputs.get("workflowName")
    version = inputs.get("version")
    explicit_path = inputs.get("path")
    commit_message_override = inputs.get("commitMessage")
    branch_override = inputs.get("branch")

    settings = PluginSettings.from_context(context)
    branch = str(branch_override or settings.branch).strip() or settings.branch

    path = build_target_path(
        base_path=settings.base_path,
        workflow_id=workflow_id,
        workflow_name=str(workflow_name) if workflow_name else None,
        version=str(version) if version else None,
        file_extension=settings.file_extension,
        explicit_path=str(explicit_path) if explicit_path else None,
    )

    result: Dict[str, Any] = {
        "committed": False,
        "path": path,
        "branch": branch,
    }

    if not published:
        result["message"] = "published フラグが false のためコミットをスキップしました。"
        return result

    workflow_dsl = inputs.get("workflowDsl")
    if workflow_dsl is None:
        raise ValidationError("workflowDsl が指定されていません。")

    content_text = normalize_dsl(workflow_dsl)
    commit_message = commit_message_override or render_commit_message(
        template=settings.commit_message_template,
        workflow_id=workflow_id,
        workflow_name=str(workflow_name) if workflow_name else None,
        version=str(version) if version else None,
    )

    client = GitHubContentClient(settings=settings)
    response = client.put_content(
        path=path,
        content_text=content_text,
        commit_message=commit_message,
        branch=branch,
        author_name=settings.author_name,
        author_email=settings.author_email,
    )

    file_info = response.get("content", {})
    commit_info = response.get("commit", {})

    result.update(
        {
            "committed": True,
            "commitSha": commit_info.get("sha"),
            "url": file_info.get("html_url"),
            "message": "GitHub へコミットしました。",
        }
    )
    return result


__all__ = [
    "execute",
    "ValidationError",
    "GitHubAPIError",
    "PluginSettings",
    "GitHubContentClient",
    "build_target_path",
    "normalize_dsl",
    "render_commit_message",
]
