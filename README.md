## Dify Plugins

このプロジェクトは Dify の自作プラグイン集をまとめたものです。
基本的なプラグインの開発は公式ガイドのプラグイン開発者ガイドラインに従います。

https://docs.dify.ai/plugin-dev-ja/0312-contributor-covenant-code-of-conduct

## 技術スタック

- node.js v23 以上

## プラグインのパッケージング

リポジトリルートに配置している Dify CLI 互換スクリプト `./dify` を利用してプラグインを Zip 化します。

```bash
./dify plugin package <plugin ディレクトリへのパス>
```

例: Chatwork プラグインをパッケージ化する場合は `./dify plugin package ./src/chatwork` を実行します。複数のプラグインをまとめて配布したい場合は `./dify plugin package --all` を利用してください。生成されたアーカイブは `dist/` ディレクトリに出力されます。

## GitHub Actions での配布

`main` ブランチへの push や `v*` タグの push、もしくは手動実行 (`workflow_dispatch`) をトリガーとして GitHub Actions が `./dify plugin package --all` を実行し、`dist/` 以下に生成された Zip ファイルを成果物としてアップロードします。手動実行時は入力欄にスペース区切りのパスを指定すると、そのプラグインのみをパッケージ化できます。`v*` タグから実行した場合は生成した Zip を GitHub Release に添付するため、ローカルの Dify 環境へ配布する際はリリースページからダウンロードできます。

