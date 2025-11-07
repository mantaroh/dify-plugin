## Dify Plugins

このプロジェクトは Dify の自作プラグイン集をまとめたものです。
基本的なプラグインの開発は公式ガイドのプラグイン開発者ガイドラインに従います。

https://docs.dify.ai/plugin-dev-ja/0312-contributor-covenant-code-of-conduct

## 技術スタック

- node.js v23 以上

## プラグインのパッケージング

CI で配布できる Zip アーカイブを生成するには、次のコマンドを実行します。

```bash
npm run package -- <pluginName>
```

例: Chartwork プラグインをパッケージ化する場合は `npm run package -- chartwork` を実行します。複数のプラグインをまとめて配布したい場合は `npm run package -- --all` を利用してください。生成されたアーカイブは `dist/` ディレクトリに出力されます。

## GitHub Actions での配布

`main` ブランチへの push や `v*` タグの push、もしくは手動実行 (`workflow_dispatch`) をトリガーとして GitHub Actions が `npm run package -- --all` を実行し、`dist/` 以下に生成された Zip ファイルを成果物としてアップロードします。手動実行時は入力欄にスペース区切りのプラグイン名を指定すると、そのプラグインのみをパッケージ化できます。

