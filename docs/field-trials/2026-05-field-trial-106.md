# Field Trial 106: Idempotency Key パターン

## テーマ

`Idempotency-Key` ヘッダーを使って POST リクエストを冪等にするパターンを検証する。
`nene2.cache.TtlCache` の実用例として組み込む。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft106-idempotency/` に以下を実装:

- `TtlCache[dict[str, Any]]` を `app.state.idempotency_cache` として lifespan で初期化
- `POST /orders` で `Idempotency-Key` ヘッダーをチェック
- 既存キャッシュがあれば `X-Idempotency-Replayed: true` ヘッダーと共にキャッシュから返す
- キャッシュなければ UseCase を実行してキャッシュに保存
- 7 テスト通過

## テスト結果

全 7 テスト通過。

## Friction Points

### FP1: Idempotency Key 同一キー + 異なるボディの扱いが未定義

**状況**: Stripe などの実装では、同じ `Idempotency-Key` で異なるリクエストボディを送ると `422 Unprocessable Entity` を返す。現在の実装ではキャッシュされた最初のレスポンスを無条件に返すため、ボディが変わっても同じレスポンスが返る。

**影響**: 中。金融系 API では重要だが、一般的な API では省略可。

### FP2: Idempotency Key ユーティリティがない

**状況**: `TtlCache` を使って実装できたが、`get_idempotency_cache()` Depends パターンや `X-Idempotency-Replayed` ヘッダーの付与は完全に自前実装。Stripe / Square などで標準化されたパターンであるため、nene2 に軽量ユーティリティがあると便利。

**影響**: 低。`TtlCache` + ハンドラーコードで完結可能。

## まとめ

`TtlCache` の実用例として Idempotency Key パターンはスムーズに実装できた。摩擦は小さい。
docs として how-to を追加する。
