# Field Trial 53: ApiKeyAuthMiddleware 実運用検証

**Date**: 2026-05-20
**Theme**: `ApiKeyAuthMiddleware` の実運用パターン検証
**Version under test**: v1.8.12
**FT App**: `/home/xi/docker/nene2-python-FT/ft53-api-key-auth/`

---

## 概要

`ApiKeyAuthMiddleware` + `LocalTokenVerifier(set)` の組み合わせを複数 API キー対応の
サービスで実運用した。`exclude_paths` と `RequestIdMiddleware` との組み合わせも検証。

---

## 実装内容

```python
verifier = LocalTokenVerifier({"key-dev-001", "key-dev-002"})
app.add_middleware(
    ApiKeyAuthMiddleware,
    verifier=verifier,
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc"],
)
```

---

## テスト結果

9 tests, all passed.

---

## 摩擦ポイント

### FP53-1: `ApiKeyAuthMiddleware` のヘッダー名が `X-Api-Key` に固定されている

**状況**: サービスによっては `X-Service-Token` や `X-Internal-Key` など
異なるヘッダー名を使いたい場合がある。

**修正**: `header_name: str = "X-Api-Key"` パラメータを追加 (#286)。

```python
app.add_middleware(
    ApiKeyAuthMiddleware,
    verifier=verifier,
    header_name="X-Service-Token",  # カスタムヘッダー名
)
```

エラーメッセージにも `header_name` が反映される:
```
"A valid X-Service-Token header is required."
```

**補足**: HTTP ヘッダーは RFC 7230 で大文字小文字無視であるため、
`X-API-KEY` / `X-Api-Key` などの大文字小文字の違いは問題にならない。

---

## フレームワーク変更

### `ApiKeyAuthMiddleware` — `header_name` パラメータを追加 (#286)

```python
# デフォルト動作（後方互換）
ApiKeyAuthMiddleware(verifier=verifier)  # X-Api-Key を使用

# カスタムヘッダー名
ApiKeyAuthMiddleware(verifier=verifier, header_name="X-Service-Token")
```

---

## 結論

`ApiKeyAuthMiddleware` は `LocalTokenVerifier(set)` との組み合わせで
複数 API キーを管理する用途で問題なく動作する。
`header_name` パラメータの追加で柔軟性が向上した。
