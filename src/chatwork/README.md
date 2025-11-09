# Chatwork Room Messenger プラグイン仕様

## 概要
Chatwork Room Messenger プラグインは、API トークンで認証された Chatwork API を利用して、指定されたルームにメッセージを投稿します。Dify のエージェントやワークフローから利用し、通知やレポートの自動投稿に活用できます。

## 対応 API
- Chatwork REST API v2
  - `POST /rooms/{room_id}/messages`

## 認証
- **方式**: カスタム HTTP ヘッダー認証
- **設定項目**:
- `apiToken` (必須): Chatwork API トークン。`X-ChatWorkToken` ヘッダーに付与します。
- `baseUrl` (任意): Chatwork API のベース URL。省略時は `https://api.chatwork.com/v2` を利用します。

## プラグイン設定
| キー | 型 | 必須 | 説明 |
| ---- | -- | ---- | ---- |
| `defaultRoomId` | string | 任意 | 指定した場合、このルーム ID がアクションで roomId を省略した際のデフォルトになります。 |
| `baseUrl` | string | 任意 | Chatwork API のベース URL。オンプレミス環境などを利用する際に上書きします。 |
| `accountId` | string | 任意 | `selfMention` オプションを利用する際に付与するチャットワークのアカウント ID。 |

## アクション: `postRoomMessage`
| パラメータ | 型 | 必須 | 説明 |
| ---------- | -- | ---- | ---- |
| `roomId` | string | 任意 | メッセージを送信する Chatwork ルームの ID。未指定時は `defaultRoomId` を利用します。 |
| `message` | string | 必須 | 送信するメッセージ本文。テキスト形式で送信されます。 |
| `selfMention` | boolean | 任意 | `true` の場合、メッセージ先頭に `[To:account_id]` を付与します。account_id は API トークン所有者のものを利用します。 |
| `linkUrls` | boolean | 任意 | `true` の場合、メッセージ内の URL を自動リンクするため `+` プレフィックスを付与します。 |

### 成功時レスポンス
```json
{
  "messageId": "1234567890",
  "roomId": "987654321",
  "postedAt": "2024-04-30T12:34:56.000Z"
}
```

### エラー仕様
- 認証エラー: 401 応答を捕捉し、`AuthenticationError` として扱います。
- パラメータ不足: 必須フィールドが欠けている場合は即座に `ValidationError` を投げます。
- その他 HTTP エラー: レスポンス本文を添えて `ChatworkAPIError` を投げます。

## ログ出力
- 送信前後に、roomId とメッセージ長をデバッグログとして出力します。
- エラー時にはステータスコードとレスポンス本文を警告ログとして出力します。

## テスト方針
- 単体テスト: HTTP レスポンスのモックを利用して、正常系・認証エラー・その他エラーのハンドリングを検証します。
- 結合テスト: 実際の Chatwork テストルームを用意し、API トークンでの送信を確認します (CI ではモックのみ実施)。
