#!/usr/bin/env python3
"""Utility script to download and install the official Dify Plugin CLI.

This script fetches the latest (or a specified) release artifact from the
`langgenius/dify-plugin-cli` repository and installs the `dify` executable into
an installation directory (default: ``~/.local/bin``).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "langgenius/dify-plugin-cli"


class InstallError(RuntimeError):
    """Raised when the CLI cannot be installed."""


def fetch_release_metadata(version: str) -> dict:
    if version == "latest":
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{REPO}/releases/tags/{version}"

    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request) as response:  # noqa: S310 - trusted GitHub URL
        return json.load(response)


def select_linux_asset(release: dict) -> tuple[str, str]:
    assets = release.get("assets", [])
    candidates: list[tuple[str, str]] = []
    for asset in assets:
        name = asset.get("name", "")
        url = asset.get("browser_download_url")
        if not name or not url:
            continue
        lower = name.lower()
        if "linux" not in lower:
            continue
        if lower.endswith((".tar.gz", ".tgz", ".zip")):
            candidates.append((url, name))
    if not candidates:
        raise InstallError("Linux 向けの CLI アセットが見つかりませんでした")
    return candidates[0]


def extract_archive(archive_path: Path, extract_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_dir)
        return

    # Handle .tar.gz / .tgz and other tar formats
    with tarfile.open(archive_path, mode="r:*") as tf:
        tf.extractall(extract_dir)


def locate_binary(root: Path) -> Path:
    for path in root.rglob("*"):
        if path.is_file() and path.name == "dify":
            return path
    raise InstallError("展開したアーカイブ内に dify 実行ファイルが見つかりませんでした")


def install_binary(binary: Path, install_dir: Path) -> Path:
    install_dir.mkdir(parents=True, exist_ok=True)
    destination = install_dir / "dify"
    shutil.copy2(binary, destination)
    current_mode = destination.stat().st_mode
    destination.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return destination


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the Dify Plugin CLI")
    parser.add_argument(
        "--version",
        default="latest",
        help="Release tag to install (default: latest)",
    )
    parser.add_argument(
        "--install-dir",
        default=os.path.join(Path.home(), ".local", "bin"),
        help="Installation directory for the dify executable",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    install_dir = Path(args.install_dir).expanduser().resolve()

    try:
        release = fetch_release_metadata(args.version)
        download_url, asset_name = select_linux_asset(release)
    except Exception as exc:  # pragma: no cover - network errors are non-deterministic
        raise SystemExit(f"CLI リリース情報の取得に失敗しました: {exc}") from exc

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        archive_path = tmpdir / asset_name
        try:
            with urllib.request.urlopen(download_url) as response, archive_path.open("wb") as fp:  # noqa: S310 - trusted GitHub URL
                shutil.copyfileobj(response, fp)
        except Exception as exc:  # pragma: no cover - network errors are non-deterministic
            raise SystemExit(f"CLI アセットのダウンロードに失敗しました: {exc}") from exc

        extract_dir = tmpdir / "extracted"
        extract_dir.mkdir()
        try:
            extract_archive(archive_path, extract_dir)
        except Exception as exc:
            raise SystemExit(f"CLI アセットの展開に失敗しました: {exc}") from exc

        try:
            binary = locate_binary(extract_dir)
        except InstallError as exc:
            raise SystemExit(str(exc)) from exc

        try:
            destination = install_binary(binary, install_dir)
        except Exception as exc:
            raise SystemExit(f"CLI のインストールに失敗しました: {exc}") from exc

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
