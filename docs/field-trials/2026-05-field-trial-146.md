# Field Trial 146: copy モジュール

## テーマ

`copy.copy` (シャローコピー), `copy.deepcopy` (ディープコピー),
カスタム `__copy__` / `__deepcopy__` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft146-copy/` に以下を実装:

- `Person` / `Address` / `TreeNode` — シャロー/ディープコピーの違いを示すサンプルクラス
- `shallow_copy_person()` / `deep_copy_person()` — `copy.copy` / `copy.deepcopy` の比較
- `deep_copy_tree()` — 再帰的な TreeNode の完全コピー
- `BudgetConfig` — `__copy__` と `__deepcopy__` をカスタム実装（使用カウンターのリセット）
- HTTP エンドポイント（シャロー/ディープコピーの挙動デモ）
- 17 テスト通過（摩擦1件あり）

## テスト結果

初回: 1失敗 → 修正後: 17テスト全通過。

## Friction Points

### FP1: `@dataclass` のシャローコピーでリストも共有されると誤認していた

```python
@dataclass
class Person:
    name: str
    address: Address
    hobbies: list[str]  # mutable フィールド

copied = copy.copy(person)
assert copied.hobbies is person.hobbies  # True — 同じリスト
```

`copy.copy` でリストは独立してコピーされる（`False`）と思い込んでテストを書いたが、
実際は `@dataclass` のシャローコピーではリストも共有される（`True`）。

**対処**: テストのアサーションを `is True` に修正した。
`copy.copy` はすべてのフィールドを参照コピーする（値の種類に関わらず）。

## 観察

### O1: `copy.copy` は全フィールドを参照コピーする（ネストされた可変オブジェクトも共有）

```python
original = Person("Alice", Address("Main St", "Tokyo"), ["reading"])
copied = copy.copy(original)

assert copied.address is original.address  # True — 同じ Address
assert copied.hobbies is original.hobbies  # True — 同じリスト

copied.address.city = "Osaka"
assert original.address.city == "Osaka"   # original も変わる!
```

シャローコピーは「一段階のコピー」— トップレベルのオブジェクトは新しいが、
そのフィールドが指すオブジェクトは元のものを共有する。

### O2: `copy.deepcopy` は全ネスト構造を再帰的にコピーする

```python
copied = copy.deepcopy(original)

assert copied.address is not original.address  # True — 独立した Address
assert copied.hobbies is not original.hobbies  # True — 独立したリスト

copied.address.city = "Sapporo"
assert original.address.city == "Tokyo"        # original は変わらない
```

ディープコピーは完全な独立コピー。循環参照も `memo` dict で安全に処理される。

### O3: `__copy__` と `__deepcopy__` で挙動をカスタマイズできる

```python
class BudgetConfig:
    def __copy__(self) -> "BudgetConfig":
        new = BudgetConfig(budget=self.budget, categories=self.categories)  # 共有
        new._use_count = 0  # カスタムリセット
        return new

    def __deepcopy__(self, memo: dict[int, Any]) -> "BudgetConfig":
        new = BudgetConfig(budget=self.budget, categories=copy.deepcopy(self.categories, memo))
        new._use_count = 0
        return new
```

`memo` dict は再帰的なディープコピー中に同一オブジェクトを一度だけコピーするために使う。
`copy.deepcopy(self.categories, memo)` のように渡すことで循環参照を防ぐ。

### O4: `@dataclass(frozen=True)` はコピーでも `frozen` 制約が維持される

`frozen=True` の dataclass の属性を変更しようとすると `FrozenInstanceError` になる。
コピーした後も同様に `frozen` が維持されるため、安全な value object を作成できる。

## まとめ

FT146 は摩擦1件（シャローコピーではリストも共有されることへの誤認）。
`copy.copy` vs `copy.deepcopy` の違いと、`__copy__`/`__deepcopy__` による
カスタム挙動（使用カウンターリセット等）を FastAPI で確認した。
