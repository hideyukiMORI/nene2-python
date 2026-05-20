# Field Trial 144: logging 高度機能

## テーマ

`logging.Handler`, `logging.Formatter`, `logging.Filter`,
ロガー階層、構造化ログ (`extra` フィールド) を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft144-logging-advanced/` に以下を実装:

- `InMemoryHandler` — `logging.Handler` サブクラス、ログをメモリに蓄積（テスト用）
- `JsonFormatter` — JSON 形式のログフォーマッター
- `LevelRangeFilter` — ログレベル範囲フィルター
- `KeywordFilter` — メッセージキーワードフィルター
- `create_logger_hierarchy()` — `ft144` → `ft144.module_a` → `ft144.module_a.service` の階層
- `capture_logs()` / `capture_logs_as_json()` — テスト用ログキャプチャユーティリティ
- 19 テスト通過（摩擦2件あり）

## テスト結果

初回: 9失敗 → 修正後: 19テスト全通過。

## Friction Points

### FP1: `@dataclass` で `logging.Handler` を継承すると `super().__init__()` が呼ばれない

`@dataclass` デコレータは `__init__` を自動生成するが、親クラスの `__init__()` は
呼び出さない。`logging.Handler.__init__()` が実行されないため
`self.level` 属性が未設定となり `AttributeError` が発生した。

**対処**: `__post_init__` で `super().__init__()` を明示的に呼び出す。

```python
@dataclass(eq=False)
class InMemoryHandler(logging.Handler):
    records: list[logging.LogRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__()  # logging.Handler.__init__() を呼ぶ
```

### FP2: mutable `@dataclass` で `logging.Handler` を継承すると `WeakSet` への追加が失敗する

FP1 の修正として `__post_init__` を追加したが、今度は別のエラーが発生した:

```
TypeError: cannot use 'weakref.ReferenceType' as a set element (unhashable type: 'InMemoryHandler')
```

`logging.Handler.__init__()` は内部で `WeakSet` にインスタンスを追加するが、
mutable な `@dataclass`（`frozen=False`）は `__hash__ = None` を設定するため
ハッシュ不可能になる。

**対処**: `@dataclass(eq=False)` を使い、`__eq__` と `__hash__` を上書きしないようにする。

```python
@dataclass(eq=False)  # __hash__ を None にしない
class InMemoryHandler(logging.Handler):
    ...
```

`eq=False` にすると `@dataclass` は `__eq__` も `__hash__` も生成しないため、
`object` の `__hash__` が維持される。

## 観察

### O1: `logging.Handler` のサブクラスは `emit()` を実装するだけでよい

```python
class InMemoryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
```

`logging.Handler.handle()` がフィルタリングとフォーマットを担当し、
`emit()` は実際の出力処理のみ実装すればよい。

### O2: `logging.Formatter.format()` をオーバーライドして任意フォーマットを実現できる

```python
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }, ensure_ascii=False)
```

`record.getMessage()` は `msg % args` の評価済みメッセージを返す。

### O3: ロガーの親子関係は名前のドット区切りで自動的に構成される

```python
parent = logging.getLogger("ft144")
child  = logging.getLogger("ft144.module_a")
assert child.parent is parent  # True
```

子ロガーのログは `propagate=True`（デフォルト）の場合、
親ロガーのハンドラーにも伝播する。

### O4: `logging.Filter.filter()` の戻り値で通過/ブロックを制御できる

```python
class LevelRangeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return self.min_level <= record.levelno <= self.max_level
```

`True` を返すとレコードを通過させ、`False` を返すとブロックする。
ハンドラーにも直接 `addFilter()` で追加できる。

### O5: `@dataclass` と stdlib クラスの継承は `eq=False` + `__post_init__` が必須

stdlib の基底クラス（特に内部でロックや WeakRef を使うもの）を `@dataclass` で継承する場合:
1. `__post_init__` で `super().__init__()` を呼ぶ
2. `@dataclass(eq=False)` でハッシュ可能性を維持する

この2点を忘れると実行時エラーになる。

## まとめ

FT144 は摩擦2件（`@dataclass` + `logging.Handler` 継承の2段階の落とし穴）。
`@dataclass` と stdlib の基底クラスを組み合わせる際は
`__post_init__` と `eq=False` の両方が必要なことを確認した。
