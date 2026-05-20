# Field Trial 93: Dependency Override パターン

**日付**: 2026-05-20
**テーマ**: `app.dependency_overrides` を使ったテスト時 DI 切り替えパターン
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

FastAPI の `app.dependency_overrides` を使ったテスト時の DI 切り替えを検証する。
nene2 の `UseCaseProtocol` / `Repository` パターン、`PaginationDep`、認証 `Depends` との組み合わせを確認する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft93-dependency-override/` に以下を実装:

- `app.py` — `ItemRepository`（インメモリ）+ CRUD エンドポイント + 認証 `Depends`
- 9 テスト（全 PASS）

---

## 確認できた良好な動作

### リポジトリのオーバーライド

テスト専用の `ItemRepository` インスタンスを fixture で作り、`dependency_overrides` に差し込むことで、テスト間の状態を完全に分離できる。

```python
@pytest.fixture()
def test_repo() -> ItemRepository:
    return ItemRepository()

@pytest.fixture()
def client(test_repo: ItemRepository) -> TestClient:
    app.dependency_overrides[get_repo] = lambda: test_repo
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
```

### 認証 Depends のオーバーライド

`get_current_user` を差し替えることで、認証なしのテスト環境を簡単に構築できる。

```python
fake_user = CurrentUser(user_id=99, username="test_user")
app.dependency_overrides[get_current_user] = lambda: fake_user
```

---

## 摩擦点

### F93-1: `dependency_overrides.clear()` の忘れはテスト汚染の原因

`app.dependency_overrides` は `app` オブジェクトに紐付いたグローバルな辞書。
`clear()` 忘れは後続テストに影響する。

```python
# ❌ clear() を忘れるとテスト汚染
app.dependency_overrides[get_repo] = lambda: test_repo
r = client.get("/items")
# clear() なし → 次のテストも test_repo を使う

# ✅ fixture の yield + finally で確実にクリア
@pytest.fixture()
def client(test_repo: ItemRepository) -> TestClient:
    app.dependency_overrides[get_repo] = lambda: test_repo
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()  # ← これが必須
```

**推奨**: `conftest.py` に `autouse=True` の fixture を置いてセッション/テストごとに自動クリアする。

```python
@pytest.fixture(autouse=True)
def clear_overrides() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.clear()
```

### F93-2: `Annotated[T, Depends(f)]` のオーバーライドキーは `f`（ファクトリ関数）

`PaginationDep = Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]` のような型エイリアスの場合、`dependency_overrides` のキーは `PaginationDep`（Annotated 型）ではなく `PaginationQueryParser`（Depends に渡したクラス）になる。

```python
# ❌ 失敗: Annotated 型はキーとして機能しない
from nene2.http import PaginationDep
app.dependency_overrides[PaginationDep] = fixed_pagination  # 効かない

# ✅ 成功: Depends の引数（ファクトリ関数またはクラス）がキー
from nene2.http import PaginationQueryParser
app.dependency_overrides[PaginationQueryParser] = fixed_pagination
```

この挙動は FastAPI のドキュメントには明示されていないが、`Annotated` を用いた `Depends` では依存関数（クラス）がキーになる。

### F93-3: グローバル `app` インスタンスへのオーバーライドはスレッドセーフでない

`app.dependency_overrides` はグローバル辞書のため、並列テスト実行（`pytest-xdist`）環境では競合が発生する。
`pytest-xdist` と組み合わせる場合は、テストごとに別の `FastAPI()` インスタンスを生成するか、ワーカーを分離する必要がある。

---

## 結論

`dependency_overrides` は nene2 パターンと問題なく組み合わせられる。
主な摩擦は `clear()` の管理と `Annotated Depends` のキー仕様の把握。
コード修正は不要で、fixture の設計と使い方の理解で対応できる。
