# GitHub Workflow Exporter プラグイン仕様

## 概要
セルフホストの Dify で編集しているワークフローを、公開タイミングで GitHub リポジトリへ DSL として保存するアクションプラグインです。Dify 側の自動保存イベントではコミットせず、公開イベント (publish) 時のみコミットします。認証・リポジトリ情報・コミット署名者などはプラグイン設定で指定し、ワークフローの DSL とメタ情報を使って保存先パスやコミットメッセージを組み立てます。

## 想定ユースケース
- ワークフロー公開時に DSL を GitHub でバージョン管理する
- 本番適用前のワークフロー変更差分を Pull Request ベースでレビューする
- ワークフロー ID/名前/バージョンを含むパスへ書き出し、履歴を自動追跡する

## 設定項目 (config)
- **GitHub Access Token (githubToken)**: リポジトリへの push 権限を持つ PAT。必須。
- **Repository Owner (repositoryOwner)**: 対象リポジトリのオーナー。必須。
- **Repository Name (repositoryName)**: 対象リポジトリ名。必須。
- **Branch (branch)**: コミット先ブランチ。省略時は `main`。
- **Base Path (basePath)**: DSL を保存するディレクトリプレフィックス。省略時は `dify/workflows`。
- **File Extension (fileExtension)**: 書き出すファイル拡張子。省略時は `.json`。
- **Commit Message Template (commitMessageTemplate)**: `{workflowId}` `{workflowName}` `{version}` を利用できるテンプレート。省略時は `chore: sync Dify workflow {workflowId}`。
- **Author Name / Email (authorName / authorEmail)**: コミット署名者。省略時は GitHub がトークンのデフォルトに従う。

## アクション: `commitWorkflowDsl`
### 入力
| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `published` | boolean | はい | `true` の場合のみ GitHub へコミットします。自動保存では `false` を渡してスキップします。 |
| `workflowId` | string | はい | Dify ワークフローの ID。 |
| `workflowName` | string | いいえ | ワークフロー名。ファイル名やコミットメッセージに利用。 |
| `workflowDsl` | object/string | はい | 保存対象の DSL。オブジェクトの場合は JSON 整形して保存します。 |
| `version` | string | いいえ | 公開バージョン (例: `v2`)。ファイル名やコミットメッセージに利用。 |
| `path` | string | いいえ | 保存先パスを個別指定する場合に利用。省略時は `basePath` 配下にワークフロー名/ID から生成。 |
| `commitMessage` | string | いいえ | コミットメッセージを個別指定。テンプレートより優先。 |
| `branch` | string | いいえ | 呼び出しごとに上書きするブランチ名。 |

### 出力
- `committed`: `true` または `false`。publish イベント以外では `false`。
- `path`: コミットした (もしくは予定だった) パス。
- `branch`: コミット先ブランチ。
- `commitSha`: 成功時のコミット SHA。
- `url`: GitHub 上のファイル URL。
- `message`: スキップ理由や完了メッセージ。

## 仕様メモ
- `published` が `true` でない場合は GitHub API を呼び出さずにスキップします。
- `path` を省略した場合、`{basePath}/{slugified-workflow-name-or-id}{version?}{fileExtension}` という形式で生成します。`version` があれば `-v{version}` をサフィックスに付与します。
- `workflowDsl` が辞書/リストの場合はインデント付き JSON (UTF-8) に変換して保存します。
- GitHub API には `/repos/{owner}/{repo}/contents/{path}` (PUT) を利用し、既存ファイルがあれば `sha` を付与して上書きします。
- `authorName` / `authorEmail` が設定されている場合は `author` と `committer` の両方に反映します。
