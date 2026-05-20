# Field Trial 42: get_request_id() Depends + configure_problem_details() 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.5 時点
**テーマ**: `get_request_id()` を FastAPI `Depends` で注入しレスポンスに含めるパターン、および `configure_problem_details()` のプロジェクト全体設定

---

## 概要

`nene2.middleware.get_request_id()` を `Annotated[str, Depends(get_request_id)]` 構文で
ハンドラーに注入し、レスポンスボディに `request_id` を含めるパターンを実装した。
`configure_problem_details()` でプロジェクト全体の Problem Details base_url を設定し、
カスタム例外を `SimpleDomainHandler` でマッピングする構成も確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft42-request-id-depends/` に以下を作成:

- **`app.py`** — `get_request_id()` Depends 注入・`configure_problem_details()` 設定・`SimpleDomainHandler` でカスタム例外マッピング
- **`test_app.py`** — 正常系・404・Problem Details base_url・request_id 相関 (9 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 13 件全通過 ✅

---

## 摩擦点

### FP42-1: RequestIdMiddleware なしで get_request_id() を呼ぶと空文字が返る

**分類**: 注意喚起（ドキュメントに記載済み）

`get_request_id()` は `contextvars` を参照する。
テスト関数から直接呼ぶ場合や `RequestIdMiddleware` を経由しない場合は `""` を返す。
`TestClient` 経由でリクエストを送れば正しく UUID が返る。

```python
# RequestIdMiddleware なしで直接呼ぶ → ""
from nene2.middleware import get_request_id
assert get_request_id() == ""

# TestClient 経由で呼ぶ → UUID v4
r = client.get("/debug/request-id")
assert len(r.json()["request_id"]) == 36
```

**判断**: ドキュメントに記載済みの動作。TestClient 経由で使うことを徹底すれば問題ない。

---

### FP42-2: configure_problem_details() のグローバル状態がテスト間で共有される

**分類**: 軽微な摩擦（設計上の制約・テスト時の注意点）

`configure_problem_details()` はモジュールレベルのグローバル変数 `_configured_base_url` を変更する。
異なる `base_url` で複数の `create_app()` を呼ぶと最後の設定が残り、
テスト間で state が漏れる。

```python
create_app(base_url="https://first.example.com/problems/")
# _configured_base_url == "https://first.example.com/problems/"

create_app(base_url="https://second.example.com/problems/")
# _configured_base_url == "https://second.example.com/problems/"
# ← first の設定は上書きされている
```

**対処**: テスト間で隔離が必要な場合、`nene2.http.problem_details._configured_base_url = None`
で手動リセットするか、全テストで同一の base_url を使う。
運用環境では起動時に一度だけ呼ぶ設計なので実害はない。

**判断**: アプリ起動時一度だけ呼ぶ設計であり仕様通り。テスト向けに `reset_problem_details()` 関数を追加する価値があるかもしれない。

---

### FP42-3: SimpleDomainHandler のエラーレスポンスに request_id が自動付与されない

**分類**: 設計上の制約（許容範囲・パターン提示）

`ErrorHandlerMiddleware` + `SimpleDomainHandler` が生成する 404 レスポンスには
`request_id` フィールドが自動追加されない。
`X-Request-Id` ヘッダーは `RequestIdMiddleware` が付与するが、
レスポンスボディへの `request_id` 付与はアプリ側で明示的に行う必要がある。

エラーレスポンスに `request_id` を含めたい場合は、`problem_details_response()` を
直接呼ぶ exception handler を登録するか、`SimpleDomainHandler` を継承して
`request_id` を `extra` に追加するカスタム実装が必要。

**判断**: `ErrorHandlerMiddleware` はドメインレイヤーに依存しない設計のため、
`request_id` のような HTTP 横断概念を自動付与しないのは正しい。
クライアントが `X-Request-Id` ヘッダーを参照すれば相関できる。

---

### FP42-4: Annotated[str, Depends(get_request_id)] 構文は問題なく動作する

**分類**: 摩擦なし（良い設計の確認）

Python 3.12+ 推奨の `Annotated` 構文で `get_request_id()` を注入できる。
FastAPI の型推論も正しく動作し、`str` 型として扱われる。

```python
from typing import Annotated
from fastapi import Depends
from nene2.middleware import get_request_id

async def handler(
    request_id: Annotated[str, Depends(get_request_id)],
) -> JSONResponse:
    return JSONResponse({"request_id": request_id})
```

**判断**: FT25 で実装した `get_request_id()` は `Annotated` + `Depends` パターンと完全に互換。

---

## フレームワーク変更

なし（全て設計通りの挙動）

以下のドキュメント追記を検討:
- `docs/how-to/` に `get_request_id()` Depends パターンの how-to ガイドを追加

---

## 関連

- `nene2.middleware.get_request_id` (FT25, v1.8.1)
- `nene2.middleware.RequestIdMiddleware`
- `nene2.http.configure_problem_details` (FT19, v1.8.0)
- `nene2.middleware.SimpleDomainHandler` (FT21, v1.8.0)
- FT19 (configure_problem_details 実装, v1.8.0)
- FT21 (SimpleDomainHandler 実装, v1.8.0)
- FT25 (get_request_id 実装, v1.8.1)
