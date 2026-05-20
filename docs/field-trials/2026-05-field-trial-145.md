# Field Trial 145: weakref モジュール

## テーマ

`weakref.ref`, `weakref.WeakValueDictionary`, `weakref.WeakSet`,
`weakref.finalize` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft145-weakref/` に以下を実装:

- `create_weak_ref()` / `is_alive()` — 弱参照の作成・生存確認
- `SessionCache` — `WeakValueDictionary` を使ったセッションキャッシュ（GC で自動削除）
- `ObserverRegistry` — `WeakSet` を使ったオブザーバー登録（GC で自動解除）
- `register_cleanup()` — `weakref.finalize` でオブジェクト破棄コールバック登録
- HTTP エンドポイント（セッション CRUD + GC 確認）
- 16 テスト通過（摩擦ゼロ）

## テスト結果

初回から 16 テスト全通過。

## Friction Points

なし。

## 観察

### O1: `weakref.ref()` で弱参照を作成し、呼び出しで値を取得する

```python
obj = MyClass()
ref = weakref.ref(obj)

# オブジェクト生存中
assert ref() is obj       # 呼び出してデリファレンス
assert ref() is not None  # 生存確認

del obj
gc.collect()

# GC 後
assert ref() is None      # デッドリファレンス
```

`ref()` で生存していれば元のオブジェクト、GC 後は `None` を返す。

### O2: `WeakValueDictionary` は参照がなくなった値を自動削除する

```python
cache: weakref.WeakValueDictionary[str, Session] = weakref.WeakValueDictionary()
session = Session("s1", "alice")
cache["s1"] = session

del session
gc.collect()
assert "s1" not in cache  # 自動削除
```

通常の dict とは異なり、値への強参照がなくなると自動的にエントリが削除される。
キャッシュ・セッション管理・メモリリーク防止に有効。

### O3: `WeakSet` はメンバーへの強参照がなくなると自動的にセットから除外される

```python
observers: weakref.WeakSet[Session] = weakref.WeakSet()
obs = Session("obs", "user")
observers.add(obs)

del obs
gc.collect()
assert len(observers) == 0  # 自動除外
```

オブザーバーパターン・プラグインシステムで、参照を管理せずに登録解除できる。

### O4: `weakref.finalize` はオブジェクト破棄時にコールバックを呼ぶ

```python
def cleanup_callback() -> None:
    print("object was garbage collected!")

obj = MyObject()
weakref.finalize(obj, cleanup_callback)

del obj
gc.collect()
# → "object was garbage collected!" が出力される
```

`__del__` より安全（GC サイクル中に呼ばれることが保証される）。

### O5: 弱参照には `__hash__` と `__eq__` の実装が必要（デフォルトの object で十分）

弱参照可能なオブジェクトは GC によって管理される通常の Python オブジェクトであれば何でもよい。
`int`, `str` 等の組み込みイミュータブル型では弱参照を作れない（`TypeError`）。
カスタムクラスはデフォルトで弱参照可能。

## まとめ

FT145 は摩擦ゼロ。weakref API は直感的で、
`WeakValueDictionary` によるキャッシュと `WeakSet` によるオブザーバー管理を
FastAPI と組み合わせてメモリ効率の良い設計を確認した。
