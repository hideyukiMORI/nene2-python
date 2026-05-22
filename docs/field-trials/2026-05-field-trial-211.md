# FT211: typing モジュール — TypedDict / Protocol / runtime_checkable / get_type_hints / Literal

**日付**: 2026-05-22
**テーマ**: Python `typing` モジュールの TypedDict / Protocol / runtime_checkable / get_type_hints / Literal / Annotated の実装と検証
**セキュリティ診断**: なし（211 % 3 = 1）
**クラッカーペンテスト**: なし（211 % 4 = 3）

---

## 概要

`typing` モジュールは Python の静的型注釈システムの中核。今 FT では静的解析（mypy）だけでなく「実行時に型システムを活用する」パターンを重点的に検証した。

| API | ユースケース |
|---|---|
| `TypedDict` | 構造化データのスキーマ定義（total=False でオプションフィールド） |
| `Protocol` + `@runtime_checkable` | 構造的サブタイピング — `isinstance` で動作確認 |
| `get_type_hints()` | データクラスのアノテーションを実行時に検査 |
| `Literal` | 列挙定数による型安全な値限定（Pydantic と組み合わせて自動バリデーション）|
| `Annotated` | 型にメタデータを付与して境界チェックを表現 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft211-typing/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_user_profile` | `TypedDict`（`UserProfile`）から必要フィールドを取り出し `ProfileResult` に変換 |
| `check_describable` | `@runtime_checkable Protocol` で `isinstance(obj, Describable)` を検証 |
| `introspect_dataclass` | `get_type_hints(cls)` でデータクラスの全アノテーションを取得 |
| `format_log_entry` | `Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]` 型で受け付けてフォーマット |
| `clamp_value` | `Annotated[int, "min=0,max=100"]` パターンで境界値クランプ |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/typing/profile` | TypedDict プロファイル解析 |
| POST | `/typing/check-product` | Describable Protocol 実装確認 |
| POST | `/typing/check-rawitem` | Describable Protocol 非実装確認 |
| POST | `/typing/introspect` | get_type_hints によるアノテーション検査 |
| POST | `/typing/log` | Literal ログレベルでエントリ生成 |
| POST | `/typing/clamp` | Annotated 型の境界値クランプ |

---

## 摩擦点

### F-1: `@runtime_checkable` の isinstance 後も mypy は型を絞り込まない

**観察**: `isinstance(obj, Describable)` が `True` になった後でも mypy は `obj` を `Describable` 型に絞り込まない。`implements = isinstance(obj, Describable); description = obj.describe() if implements else None` と書くと `"object" has no attribute "describe"` エラーが出る。

**原因**: mypy は `@runtime_checkable` Protocol での `isinstance` に対する型絞り込みを完全にはサポートしていない（Python 3.12 時点）。Protocol の `isinstance` は「メソッドが存在する」ことは確認するが、mypy の型推論ガードとしては認識されない場合がある。

**対処**: `isinstance(obj, Describable)` を再度書いて絞り込みを明示する。

```python
# Before（mypy エラー）
implements = isinstance(obj, Describable)
description = obj.describe() if implements else None

# After（正しい）
implements = isinstance(obj, Describable)
description = obj.describe() if isinstance(obj, Describable) else None
```

---

### F-2: Pydantic + `Literal` 型フィールドは手動バリデーション不要

**観察**: `LogBody.level` を `str` 型で受けて手動で `if body.level not in _LOG_LEVELS:` と検証するアプローチは不要。`Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]` を直接 Pydantic フィールド型に使えば、無効な値は Pydantic が自動で 422 エラーを返す。

**修正前**:
```python
class LogBody(BaseModel):
    level: str = Field(description="ログレベル")
    
def post_log(body: LogBody) -> LogEntry:
    if body.level not in _LOG_LEVELS:
        raise ValidationException([...])
    level: LogLevel = body.level  # type: ignore[assignment]  ← CLAUDE.md 禁止
    return format_log_entry(level, body.message)
```

**修正後**:
```python
class LogBody(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(...)
    message: _BoundedStr = Field(...)

def post_log(body: LogBody) -> LogEntry:
    return format_log_entry(body.level, body.message)  # ← 型も一致、cast 不要
```

`type: ignore[assignment]` を完全に排除でき、CLAUDE.md ポリシーに適合。

---

## テスト結果

```
22 passed in 0.50s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`TypedDict` は「辞書に型が付く」という概念が分かりにくいが、`UserProfile` と `parse_user_profile` のペアを見れば「スキーマを定義して取り出す」パターンは理解できる。`Protocol` は「インターフェースみたいなもの」という説明があれば掴める。

**ドキュメント理解**: `Literal` + Pydantic の組み合わせ（F-2）は非常に直感的で「型を書くだけでバリデーション」という nene2 の設計哲学が体現されている。

**事故リスク（中）**: `TypedDict` の `total=False` を意識せず使うと「フィールドがない場合」の `None` チェック漏れが起きやすい。`data.get("name", "")` パターンを見ておくと安心。

**規約の使いやすさ**: `get_type_hints` は上級機能だが、`introspect_dataclass` のような薄いラッパー関数として提供されれば初心者でも使える。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`TypedDict` は `dict` に型ヒントをつけるだけなので、ランタイムの挙動が変わらないことを知っていれば安心してコピペできる。`Protocol` の `@runtime_checkable` は既存クラスに適用できる点が Duck Typing の延長で分かりやすい。

**コピペ可能性**: F-2 の `Literal` パターンはほぼコピペで使えて安全。

**拡張時の罠**: `get_type_hints` は前方参照（文字列アノテーション）があると `NameError` を起こすことがある。今回は `from __future__ import annotations` を使っていないため問題なし。

**事故リスク（低）**: mypy --strict が F-1 の型絞り込み問題を検出してくれる。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `interface` / `type` に相当する概念が Python にも存在する（`TypedDict` ≈ TypeScript の `interface`、`Protocol` ≈ TypeScript の structural typing）ことに気づくと学習が加速する。

**エラーレスポンスの質**: Literal フィールドが無効値で 422 を返すレスポンスは TS の `zod` のバリデーションと近い感覚で使いやすい。

**Python 固有概念**: `get_type_hints` はランタイムのリフレクションで、TypeScript にはない強力な機能。フォームビルダーやシリアライザーの自動生成に応用できることが分かれば興味を持てる。

**事故リスク（低）**: 型注釈が充実しており mypy で守られている。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`Protocol` + `runtime_checkable` は Django の `BaseModel` 継承より軽量で依存関係が少ない。`TypedDict` は FastAPI の `TypedDict` サポートと組み合わせてレスポンス型として使う場面が多い。

**他フレームワークとの差異**: Django では `Model` 継承が基本だが、nene2 ではドメイン層を `Protocol`/`dataclass` で定義して HTTP 層と分離できる。

**nene2 の薄さへの評価**: `_CLASS_REGISTRY` パターンは ORM の動的クエリビルダーへの応用が見えており、フレームワークの拡張ポイントとして自然。

**事故リスク（低）**: F-1 の mypy issue は経験者なら知識として持っている。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `TypedDict` の `total=False` フィールドに `data.get("field")` でアクセスしているか（`.get()` なしで `data["field"]` はランタイムエラー）
- `@runtime_checkable` Protocol で `isinstance` 後に再度 isinstance しているか（F-1 の再発防止）
- `Literal` 型を Pydantic に直接使って `type: ignore` を排除しているか（F-2）

**チームでの安全なパターン**: F-2 の `Literal` パターンは「Pydantic に型を語らせる」原則の最良の例。`str` + 手動 if チェック + `type: ignore` を書くチームメンバーへの指導材料になる。

**事故リスク（低）**: mypy --strict + ruff が主要な問題を捕捉する。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: F-2 の `type: ignore[assignment]` 排除は CLAUDE.md の「`type: ignore` は禁止」ポリシーを実践した事例。`Literal` + Pydantic の組み合わせは「HTTP 境界の全入力を Pydantic で検証」というポリシーの完全な実装。

**初心者でも安全な API 達成度**: 全エンドポイントで `Literal` または `Field(ge/le/max_length)` による境界検証が完備。`_BoundedStr` パターンが FT210 から継続して適用されており一貫性がある。

**改善提案**: `TypedDict` のランタイム特性（`.get()` 必須・isinstance チェック不可）と `dataclass` の違いをドキュメント化する価値がある。どちらを選ぶかの判断基準（HTTP 境界 → Pydantic / ドメイン層 → dataclass / 既存 dict との互換 → TypedDict）も how-to として整備できる。
