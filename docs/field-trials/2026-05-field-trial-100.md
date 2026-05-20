# Field Trial 100: In-memory TTL レスポンスキャッシュ

## テーマ

重い処理の結果を TTL 付きインメモリキャッシュに格納し、重複リクエストにキャッシュから応答するパターンを nene2 上で実装する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft100-response-cache/` に以下を実装:

- `TtlCache` データクラス（TTL 付き辞書）
- FastAPI lifespan でキャッシュを初期化・破棄
- `Depends(get_cache)` でハンドラーに注入
- キャッシュヒット/ミス判定、TTL 失効テスト

## テスト結果

全 7 テスト通過。

## Friction Points

### FP1: nene2 に TTL キャッシュユーティリティがない

**状況**: キャッシュは Web API の基本パターンだが、nene2 に `TtlCache` のようなユーティリティが存在しない。`TtlCache` を毎回自前実装する必要がある。

**影響**: 開発者がスレッドセーフでないキャッシュを実装してしまうリスク。また asyncio 環境での並行アクセスの考慮が漏れやすい（Python GIL により dict 操作自体はアトミックだが、get-then-set パターンは競合する）。

**期待する API**:
```python
from nene2.cache import TtlCache

cache = TtlCache(ttl_seconds=60.0)
cache.set("key", value)
value = cache.get("key")  # None if expired
```

### FP2: lifespan + グローバル変数パターンに型エラーが出る

**状況**: キャッシュを lifespan で初期化してグローバル変数に格納するパターンで、`async def lifespan(app: FastAPI)` の型注釈に `type: ignore[type-arg]` が必要。

```python
_cache: TtlCache | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg] が必要
    global _cache
    _cache = TtlCache(ttl_seconds=60.0)
    yield
```

`app.state` を使うパターンの方がよりクリーンだが、`app.state` の型付けも `app.state.cache` のアクセスで `Any` になる。

### FP3: `app.state` でのキャッシュ管理がドキュメント化されていない

**状況**: `lifespan-and-app-state.md` では `app.state.db` の例はあるが、キャッシュを `app.state` に格納するパターン（`request.app.state.cache`）の説明がない。

**影響**: グローバル変数を使う開発者が多く、テスト時のリセットが困難になる。

## まとめ

キャッシュユーティリティ追加は中程度の価値あり（FP1）。FP2・FP3 はドキュメント摩擦。
今回は FP1 を `nene2.cache` モジュールとして実装し、Issue を起票する。
