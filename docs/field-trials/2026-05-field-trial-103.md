# Field Trial 103: カスタムミドルウェアで認証情報をリクエストスコープに格納

## テーマ

JWT ミドルウェアで検証後の認証情報（`AuthUser`）を `request.state` に格納し、ハンドラーで `Depends()` を通じて取得するパターンを検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft103-request-state-auth/` に以下を実装:

- `JwtAuthMiddleware` — JWT を検証して `request.state.user` に `AuthUser` を格納
- `get_current_user()` — `request.state.user` から `AuthUser` を取得する Depends ファクトリ
- `require_admin()` — `admin` ロールチェック依存
- `EXCLUDE_PATHS` で `/health` をスキップ

## テスト結果

全 7 テスト通過。`InsecureKeyLengthWarning` はテスト用の短いシークレットによるもの（想定内）。

## Friction Points

### FP1: `request.state.user` アクセスに `type: ignore[attr-defined]` が必要

**状況**: `request.state` は `starlette.datastructures.State` で動的属性を持つ。ミドルウェアで `request.state.user = AuthUser(...)` と設定しても、Depends ファクトリで `request.state.user` を参照する際に mypy が `attr-defined` エラーを出す。

```python
def get_current_user(request: Request) -> AuthUser:
    user: AuthUser = request.state.user  # type: ignore[attr-defined]  # reason: middleware で確実に設定済み
    return user
```

これは `app.state` でも同様（FT100 で確認済み）。

**影響**: 低。`type: ignore` + `reason` コメントで対処可能。

### FP2: `BearerTokenMiddleware` のトークン文字列が `request.state` に格納されない

**状況**: nene2 の `BearerTokenMiddleware` は JWT/API キーの検証後にトークン文字列を返す（`make_require_auth()` Depends 経由）が、検証済みのペイロードやユーザー情報を `request.state` に自動格納する機能がない。

カスタム JWT ミドルウェアで対応したが、`BearerTokenMiddleware` + `request.state` の統合パターンがない。

**影響**: 中。`BearerTokenMiddleware` を使いたいが `request.state` にユーザー情報を格納したい場合、自前ミドルウェアを書き直す必要がある。

## まとめ

FP1 は既知の Starlette 制約（low）。FP2 は nene2 の認証統合に関する中程度の摩擦。
docs として「request.state を使った認証情報伝播パターン」を how-to に追加する。
