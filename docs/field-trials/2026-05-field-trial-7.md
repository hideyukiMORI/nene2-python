# Field Trial 7 — bookmark: PyPI publish フロー DX 検証

## Date

2026-05-20

## Baseline

- nene2-python v1.0.0（**PyPI 経由** `uv add nene2-python`）
- Python 3.14（uv managed）
- プロジェクト: **bookmark** — ブックマーク管理 JSON API
- エンティティ: `Bookmark`（id, title, url, description）
- 5 エンドポイント: CRUD（List / Get / Create / Update / Delete）
- InMemory リポジトリのみ（SQLite なし）
- **目標**: `pip install nene2-python` → ゼロ設定で動く API を構築できるか

## Goal

1. PyPI 公開フローの DX 検証（TestPyPI → PyPI 本番）
2. `uv add nene2-python`（PyPI 経由）でのインストールが正常に機能するか確認
3. 公開パッケージだけを使ってブックマーク API を構築する E2E DX 検証

---

## Steps Taken

### 1. PyPI 公開フロー

#### TestPyPI

- GitHub Actions OIDC（Trusted Publishing）を設定
- `uv publish --trusted-publishing always` を使用
- `pypa/gh-action-pypi-publish@release/v1` は Docker コンテナ内で実行されるため、
  GitHub Actions の Docker ネットワークで DNS 解決が失敗する問題が発生
  → `uv publish` をランナー直接実行に切り替えて解決

#### PyPI 本番

- TestPyPI 確認後、同一ワークフローで本番 PyPI へ publish
- GitHub Release を自動生成（`gh release create`）

### 2. プロジェクト初期化

```bash
uv init --name bookmark --no-workspace
uv add nene2-python   # PyPI から v1.0.0 をインストール
```

追加設定不要。`nene2-python` が FastAPI・Pydantic・SQLAlchemy・structlog をすべて束ねているため、
依存関係の解決は `uv add nene2-python` 一行で完了。

### 3. ドメイン層の実装

Clean Architecture の4層（entity / exceptions / repository / use_case）を独立して記述：

```python
# entity.py
@dataclass(frozen=True, slots=True)
class Bookmark:
    id: int
    title: str
    url: str
    description: str
```

`nene2` からインポートが必要なのは exceptions のみ：
```python
from nene2.http import problem_details_response
from nene2.middleware.domain_exception import DomainExceptionHandlerProtocol
```

UseCase・Repository・Entity は nene2 に依存しないため、フレームワーク非依存のビジネスロジックとして成立。

### 4. HTTP 層の実装

`handler.py` で `nene2.http`・`nene2.validation` を使用：

```python
from nene2.http import PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationError, ValidationException
```

パターンは example/note/handler.py と完全に同じ。5分で移植可能。

### 5. アプリケーションファクトリ

`app.py` でミドルウェアをスタックして完成：

```python
from nene2.config import AppSettings
from nene2.middleware import (
    ErrorHandlerMiddleware, RequestIdMiddleware,
    RequestLoggingMiddleware, RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
```

ミドルウェア登録は innermost-first 順で明示的（ドキュメントにコメントあり）。

### 6. 動作確認

```bash
uv run uvicorn app:app --port 8090
```

```
POST /bookmarks  {"title":"GitHub","url":"https://github.com","description":"Code hosting"}
→ 201  {"id":1,"title":"GitHub","url":"https://github.com","description":"Code hosting"}

GET  /bookmarks?limit=10&offset=0
→ 200  {"items":[...],"limit":10,"offset":0,"total":2}

GET  /bookmarks/1
→ 200  {"id":1,...}

PUT  /bookmarks/1  {"title":"GitHub Updated","url":"https://github.com","description":"World's largest code host"}
→ 200  {"id":1,"title":"GitHub Updated",...}

DELETE /bookmarks/2
→ 204

GET  /bookmarks/99
→ 404  {"type":"https://nene2.dev/problems/not-found","title":"Not Found","status":404,"detail":"Bookmark 99 not found."}

POST /bookmarks  {"title":"   ","url":"https://example.com","description":""}
→ 422  {"type":"https://nene2.dev/problems/validation-failed","errors":[{"field":"title","message":"Title must not be empty.","code":"required"}]}
```

全エンドポイントが期待通りに動作。Problem Details（RFC 9457）レスポンスも正常。

---

## Friction Points

### FT7-1: Docker DNS 問題（`pypa/gh-action-pypi-publish`）

- **摩擦**: `pypa/gh-action-pypi-publish@release/v1` を使用すると、Docker コンテナ内で
  `upload.test.pypi.org` の DNS 解決に失敗する
- **深刻度**: HIGH（公開ブロック）
- **解決策**: `uv publish --trusted-publishing always` をランナー直接実行に切り替え
- **所要時間**: ワークフロー修正・デバッグで約 1 時間

### FT7-2: `[tool.uv] dev-dependencies` → `[dependency-groups]` 変更

- **摩擦**: `uv init` が生成した `pyproject.toml` に旧形式の `[tool.uv] dev-dependencies` が含まれる場合がある（uv バージョン依存）
- **深刻度**: LOW（警告のみ）
- **解決策**: `[dependency-groups] dev` 形式に更新

### FT7-3: `InMemoryRepository` を毎回自前実装

- **摩擦**: テスト用 InMemory Repository をドメインごとにゼロから書く必要がある
- **深刻度**: LOW（パターンが明確なため機械的に書ける）
- **検討**: `GenericInMemoryRepository[T]` のような汎用実装をフレームワークに含めるか検討余地あり

---

## Summary

| ID     | 摩擦                                      | 深刻度 | 種別          | Follow-up |
|--------|-------------------------------------------|--------|---------------|-----------|
| FT7-1  | Docker DNS で pypa action が失敗          | HIGH   | インフラ      | 解決済み（uv publish に切り替え） |
| FT7-2  | dev-dependencies フォーマット警告         | LOW    | DX            | 解決済み（PR #154） |
| FT7-3  | InMemory Repository を毎回書く            | LOW    | フレームワーク | 検討余地あり |

FT7 の主目的（PyPI 公開 → インストール → 動く API 構築）は達成。
`uv add nene2-python` の一行でフレームワーク全体が入り、
Clean Architecture パターンをゼロから構築するのに要した時間は **30分以内**（ドメイン4ファイル + handler + app）。

**PyPI publish パイプライン（TestPyPI → PyPI → GitHub Release）は確立済み。**
FT8 候補：MySQL/PostgreSQL アダプターの実地検証、または親子リソース（nested REST）DX 検証。
