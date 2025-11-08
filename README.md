# Dify ツールプラグイン（スターター）

このリポジトリは、Dify の Tool プラグインを作成するための最小構成の雛形です。

同梱物
- `manifest.yaml`：プラグインのメタ情報と実行エントリ（Dify の最新仕様に合わせて調整してください）
- `src/execute.py`：最小のエントリポイント `execute(inputs, context)` の実装
- `scripts/dev_cli.py`：開発用の簡易 CLI（`validate` / `invoke` / `pack`）
- `Makefile`：よく使うコマンドのショートカット

クイックスタート
- 検証: `python scripts/dev_cli.py validate` もしくは `make validate`
- 実行: `python scripts/dev_cli.py invoke --input '{"text":"hello"}'` もしくは `make invoke`
- パッケージ（公式CLI推奨）: `dify plugin package .` もしくは `make package`
  - 参考: https://docs.dify.ai/plugin-dev-ja/0322-release-by-file
- フォールバックZip作成: `python scripts/dev_cli.py pack` もしくは `make pack`（成果物は `dist/*.zip`）

構成の説明
- `manifest.yaml`
  - プラグイン名、表示名、説明、作者、バージョン、タイプ（`tool`）などを定義します。
  - `runtime.entry` はローカル実行に使うエントリ（例: `src/execute.py:execute`）。公開時は公式ドキュメントの形式に合わせてください。
- `src/execute.py`
  - `execute(inputs, context) -> dict` を実装します。
  - 返り値は `{ "type": "text", "text": "..." }` などの辞書形式を想定しています（実際の仕様に合わせて変更してください）。
- `scripts/dev_cli.py`
  - `validate`: `manifest.yaml` の簡易チェック
  - `invoke`: ローカルで `execute` を JSON 入力で実行
  - `pack`: `manifest.yaml`/`README.md`/`src/` を ZIP 化して `dist/` に出力

開発メモ
- 推奨 Python バージョンは `3.9+`。
- 仮想環境の利用を推奨します（例: `python -m venv .venv && source .venv/bin/activate`）。
- 依存が増える場合は `pyproject.toml` の `dependencies` に追加してください。

注意事項
- `manifest.yaml` のスキーマは将来的に変わる可能性があります。公開前に必ず公式ドキュメントへ合わせてください。
 - 配布は基本的に公式の `dify plugin package` コマンドで行うことを推奨します。
