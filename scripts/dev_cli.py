#!/usr/bin/env python3
"""
Minimal dev CLI for the Dify Tool plugin.

Commands:
  - validate: basic checks for manifest.yaml
  - invoke:   run src.execute.execute with JSON input
  - pack:     create a distributable ZIP in dist/

Note: This is a lightweight helper. Adjust to match latest Dify spec.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_manifest() -> int:
    manifest = ROOT / "manifest.yaml"
    if not manifest.exists():
        print("manifest.yaml not found", file=sys.stderr)
        return 1

    content = read_text(manifest)

    required_keys = ["name:", "version:", "type:", "runtime:"]
    missing = [k for k in required_keys if k not in content]
    if missing:
        print(f"manifest.yaml missing keys: {', '.join(missing)}", file=sys.stderr)
        return 1

    # Extract version for later use
    m = re.search(r"^version:\s*\"?([0-9A-Za-z\.-]+)\"?\s*$", content, re.MULTILINE)
    if not m:
        print("manifest.yaml: version not parseable", file=sys.stderr)
        return 1

    print("manifest.yaml looks OK")
    return 0


def invoke_tool(json_input: str | None, stdin: bool) -> int:
    # Resolve inputs
    if stdin:
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON from stdin: {e}", file=sys.stderr)
            return 1
    else:
        if not json_input:
            print("--input is required when not using --stdin", file=sys.stderr)
            return 1
        try:
            payload = json.loads(json_input)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            return 1

    # Lazy import of tool entry
    sys.path.insert(0, str((ROOT / "").resolve()))
    try:
        from src.execute import execute  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"Failed to import tool entry: {e}", file=sys.stderr)
        return 1

    try:
        result = execute(payload, context={})
    except Exception as e:
        print(f"Tool execution error: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


def get_version_from_manifest() -> str:
    content = read_text(ROOT / "manifest.yaml")
    m = re.search(r"^version:\s*\"?([0-9A-Za-z\.-]+)\"?\s*$", content, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def pack_dist() -> int:
    code = validate_manifest()
    if code != 0:
        return code

    version = get_version_from_manifest()
    dist_dir = ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    out_zip = dist_dir / f"starter-tool-plugin-{version}.zip"

    include_paths = [
        ROOT / "manifest.yaml",
        ROOT / "README.md",
        ROOT / "src",
    ]

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include_paths:
            if path.is_dir():
                for p in path.rglob("*"):
                    if p.is_file():
                        zf.write(p, p.relative_to(ROOT))
            elif path.is_file():
                zf.write(path, path.relative_to(ROOT))

    print(f"Packed -> {out_zip}")
    return 0


def package_with_dify_cli() -> int:
    exe = shutil.which("dify")
    if not exe:
        print("dify CLI が見つかりません。公式 CLI をインストールしてください。", file=sys.stderr)
        print("参考: https://docs.dify.ai/plugin-dev-ja/0322-release-by-file", file=sys.stderr)
        return 1

    # 事前に manifest を軽く検証
    if validate_manifest() != 0:
        return 1

    try:
        # `dify plugin package .` をそのまま実行
        proc = subprocess.run([exe, "plugin", "package", str(ROOT)], check=False)
        return proc.returncode
    except Exception as e:  # pragma: no cover
        print(f"dify CLI 実行中にエラー: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Dev CLI for Dify Tool plugin")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="Validate manifest.yaml")

    p_invoke = sub.add_parser("invoke", help="Invoke local tool entry")
    p_invoke.add_argument("--input", help="JSON string input")
    p_invoke.add_argument("--stdin", action="store_true", help="Read input JSON from stdin")

    sub.add_parser("pack", help="Create a distributable zip in dist/ (fallback)")
    sub.add_parser("package", help="Use official dify CLI to package")

    args = parser.parse_args()

    if args.cmd == "validate":
        return validate_manifest()
    if args.cmd == "invoke":
        return invoke_tool(args.input, args.stdin)
    if args.cmd == "pack":
        return pack_dist()
    if args.cmd == "package":
        return package_with_dify_cli()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
