# FT84: 認証 Depends ユーティリティ — CurrentUser / require_auth パターン検証

**日付**: 2026-05-20  
**テーマ**: nene2.auth に認証 Depends ユーティリティがない摩擦点と make_require_auth 設計検証  
**バージョン**: v1.8.28  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft84-auth-depends/`

---

## 概要

`LocalTokenVerifier` と `TokenVerifierProtocol` は実装されているが、
FastAPI の Depends パターンに接続するユーティリティがない。
ユーザーは `HTTPBearer` → `verify()` → 未認証 401 を毎プロジェクトで手組みする必要がある。
`make_require_auth(verifier)` ファクトリーを追加することで解消できる。

---

## 発見した問題

### 問題1: 認証 Depends を毎回手組みする必要がある

```python
# 現状: プロジェクトごとに以下のコードを書く必要がある (50+ 行のボイラープレート)

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nene2.auth import LocalTokenVerifier

security = HTTPBearer(auto_error=False)
_verifier = LocalTokenVerifier.from_env("BEARER_TOKENS")

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    if credentials is None:
        return None
    if not _verifier.verify(credentials.credentials):
        return None
    return credentials.credentials

def require_auth(user: str | None = Depends(get_current_user)) -> str:
    if user is None:
        raise HTTPException(status_code=401)
    return user

# ハンドラーで使う
@app.post("/items")
def create(body: ItemBody, user: str = Depends(require_auth)) -> JSONResponse: ...
```

### 問題2: 任意認証パターンが冗長

```python
# 未認証でも通るが user を取得したいパターン
def optional_auth(user: str | None = Depends(get_current_user)) -> str | None:
    return user  # None = 未認証、str = ユーザーID

@app.get("/feed")
def get_feed(user: str | None = Depends(optional_auth)) -> JSONResponse:
    if user:
        return JSONResponse({"personalized": True})
    return JSONResponse({"personalized": False})
```

### 問題3: TokenVerifierProtocol を Depends で直接使えない

```python
# こういう書き方をしたくなるが Depends は callable を期待する
@app.post("/items")
def create(
    body: ItemBody,
    token: Annotated[str, Depends(LocalTokenVerifier.from_env("TOKENS"))],  # ← 機能しない
) -> JSONResponse: ...
```

---

## テスト結果（全12件パス）

```
test_public_endpoint_no_auth                     PASSED
test_create_item_with_valid_token                PASSED
test_create_item_without_token_returns_401       PASSED
test_create_item_with_invalid_token_returns_401  PASSED
test_get_me_returns_user_info                    PASSED
test_delete_item_authenticated                   PASSED
test_delete_item_unauthenticated_returns_401     PASSED
test_request_id_present_on_401                  PASSED  # nene2 ミドルウェアと共存
test_security_headers_present_on_401            PASSED  # nene2 ミドルウェアと共存
test_friction_boilerplate_for_auth_depends       PASSED  # 摩擦記録
test_friction_optional_auth_pattern_verbose      PASSED  # 摩擦記録
test_friction_verifier_not_injectable_as_depends PASSED  # 摩擦記録
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F84-1 | 認証 Depends ボイラープレートを毎プロジェクトで手組みする必要がある | 中 |
| F84-2 | 任意認証（Optional User）パターンが冗長 | 低 |
| F84-3 | `TokenVerifierProtocol` を Depends で直接使えない | 低 |

---

## 使用感（主観評価）

### 直感性 ★★☆☆☆

「nene2 でトークン認証を追加する」という操作に必要なステップが多すぎる。
`BearerTokenMiddleware` は全経路に認証を入れるには便利だが、
「このエンドポイントだけ認証を要求」パターンに Depends ユーティリティがない。
FastAPI の HTTPBearer を使う方法は FastAPI のドキュメントを参照しなければわからない。

### 実害の深刻さ ★★★☆☆

認証は多くのプロジェクトで必要。毎回 50 行のボイラープレートを書くのは
DRY 原則に反する。バグが入りやすく、テスト漏れにもつながる。

### 修正のしやすさ ★★★★★

`make_require_auth(verifier)` 関数を `nene2.auth` に追加するだけ:

```python
def make_require_auth(verifier: TokenVerifierProtocol) -> Callable[..., str]:
    security = HTTPBearer(auto_error=False)
    def get_current_user(credentials: ... = Depends(security)) -> str | None:
        if credentials is None or not verifier.verify(credentials.credentials):
            return None
        return credentials.credentials
    def require_auth(user: str | None = Depends(get_current_user)) -> str:
        if user is None:
            raise HTTPException(status_code=401)
        return user
    return require_auth
```

### 総合コメント

nene2 の認証機能は「ミドルウェアで全経路を保護する」ユースケースは
`BearerTokenMiddleware` でカバーされている。
不足しているのは「特定エンドポイントのみ認証を要求する」ユースケース。
`make_require_auth()` を追加することで「nene2 だけで完結」できる。

---

## 推奨アクション

1. **Issue #358**: `nene2.auth` に `make_require_auth(verifier)` ファクトリーを追加
   — `require_auth = make_require_auth(LocalTokenVerifier.from_env("TOKENS"))` パターンを実現
