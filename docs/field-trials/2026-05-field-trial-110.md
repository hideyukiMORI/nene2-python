# Field Trial 110: ソフトデリートパターン（論理削除）

## テーマ

`deleted_at: datetime | None` フィールドを使った論理削除パターンを検証する。
- `DELETE /resources/{id}` が物理削除ではなく `deleted_at` をセットする
- `GET /resources` / `GET /resources/{id}` が削除済みアイテムを除外する
- DELETE は冪等（既に削除済みでも 204）
- `deleted_at` を公開レスポンスに含めない（管理エンドポイントのみ）

## 実施内容

`/home/xi/docker/nene2-python-FT/ft110-soft-delete/` に以下を実装:

- `Article` dataclass — `deleted_at: datetime | None = None`、`is_deleted` プロパティ
- `dataclasses.replace()` で frozen dataclass を更新（`deleted_at` をセット）
- `ArticleResponse` に `deleted_at` フィールドを含めない設計
- 管理用 `/articles/{id}/deleted` エンドポイントで `deleted_at` を確認
- 9 テスト通過

## テスト結果

全 9 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: frozen dataclass の更新は dataclasses.replace() で簡潔に書ける

```python
from dataclasses import replace

_articles[article_id] = replace(article, deleted_at=datetime.now(UTC))
```

`frozen=True` な dataclass でも `replace()` で新しいインスタンスを作成できる。
イミュータブル設計を壊さずに更新できる。

### O2: is_deleted プロパティでビジネスロジックをドメインに閉じ込める

```python
@property
def is_deleted(self) -> bool:
    return self.deleted_at is not None
```

クエリフィルタ（`a.is_deleted`）でリポジトリ層が `deleted_at is not None` を意識しなくてよい。

### O3: DELETE は 204 + 冪等が REST ベストプラクティス

既に削除済みのリソースへの DELETE も 204 を返すことで冪等性を保つ。
存在しないリソースへの DELETE も同様。

### O4: deleted_at をレスポンスモデルから除外するのは Pydantic の通常設計で簡単

`ArticleResponse` に `deleted_at` フィールドを定義しなければ、自動的に除外される。
`exclude=` や `model_config` の設定は不要。

## まとめ

FT110 は摩擦ゼロ。ソフトデリートは nene2 + Python dataclass で自然に実装できる。
`dataclasses.replace()` / `is_deleted` プロパティ / Pydantic レスポンスフィルタリングの
各パターンを how-to に記録する。
