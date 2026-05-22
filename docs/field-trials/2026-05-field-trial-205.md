# FT205: enum モジュール — StrEnum・IntEnum・IntFlag・Flag の実装と検証

**日付**: 2026-05-22
**テーマ**: Python `enum` モジュールの StrEnum・IntEnum・IntFlag・Flag の実装と検証
**セキュリティ診断**: なし（205 % 3 = 1）
**クラッカーペンテスト**: なし（205 % 4 = 1）

---

## 概要

`enum` モジュールは Python 3.4 で追加された列挙型ライブラリ。
Python 3.11 で `StrEnum` が標準追加され、`auto()` と組み合わせた用途が大幅に広がった。
Pydantic v2 との親和性（バリデーション・シリアライゼーション）と、
nene2-python の設計ポリシー（型安全・明示的定数）との組み合わせを検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft205-enum/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `HttpMethod(StrEnum)` | HTTP メソッドの列挙型。`auto()` で小文字値を生成 |
| `HttpStatus(IntEnum)` | HTTP ステータスコードの列挙型。`is_success` / `is_client_error` プロパティ付き |
| `Permission(IntFlag)` | ビットフラグ権限定義。`READ \| WRITE \| DELETE` の合成と検査 |
| `Priority(StrEnum)` | タスク優先度（LOW/MEDIUM/HIGH/CRITICAL） |
| `LogLevel(StrEnum)` | ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `TaskStatus(Flag)` | 複合フラグ状態（`ACTIVE = PENDING \| IN_PROGRESS`） |
| `get_enum_info(enum_name)` | 列挙型名から情報を取得。`__members__` で複合フラグを含む全メンバーを返す |
| `classify_http_status(code)` | HTTP ステータスコードを `HttpStatus(IntEnum)` で分類 |
| `combine_permissions(names)` | 権限名リストをビット演算で合成して `PermissionResult` を返す |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/enums/info` | 列挙型情報を取得（`?enum_name=HttpMethod`） |
| GET | `/enums/http-status/{code}` | HTTP ステータスコードを分類 |
| POST | `/enums/permissions/combine` | 権限フラグを合成 |
| GET | `/enums/http-methods` | HTTP メソッド一覧 |
| GET | `/enums/priorities` | 優先度一覧 |
| GET | `/enums/log-levels` | ログレベル一覧 |
| GET | `/enums/task-statuses` | タスクステータス一覧（複合フラグ含む） |

---

## テスト結果

**24 passed**

```
24 passed in 0.45s
```

---

## 摩擦ポイント

### F-1: Python 3.11+ で `Flag` の iteration が atomic メンバーのみ返す（深刻度: 中）

**事象**: `ADMIN = READ | WRITE | DELETE` のような複合フラグを `for m in Permission` でイテレートすると、
`ADMIN` が含まれない。Python 3.11 より前は含まれていた。

```python
# Python 3.11+
class Permission(IntFlag):
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    ADMIN = READ | WRITE | DELETE

list(Permission)  # → [READ, WRITE, DELETE] — ADMIN が含まれない
```

**原因**: Python 3.11 での仕様変更。`Flag` iteration が「境界値（atomic）フラグのみ」を返すように変更された。
複合フラグ（別名含む）は `__members__` を通じてのみアクセス可能。

**対応**: `__members__.keys()` / `__members__.items()` を使用することで複合フラグを含む全メンバーにアクセス。

```python
# ✅ Python 3.11+ での正しい方法
list(Permission.__members__.keys())  # → ['NONE', 'READ', 'WRITE', 'DELETE', 'ADMIN']

# ❌ Python 3.11+ では複合フラグが含まれない
list(m.name for m in Permission)    # → ['NONE', 'READ', 'WRITE', 'DELETE']
```

### F-2: `mypy --strict` での `list[dict[str, str | int]]` 型注釈（深刻度: 低）

**事象**: リスト内包表記で `dict[str, str]` 型が推論されるが、
`EnumMembersResponse.members: list[dict[str, str | int]]` に渡すと型エラー。

**原因**: mypy はリスト内包表記の型を要素の型から推論するため、明示的な型注釈が必要。

**対応**: 変数に `list[dict[str, str | int]]` の型注釈を付けてから渡す。

---

## 観察点

### 観察1: `StrEnum` + `auto()` は名前を小文字に変換して値にする

```python
class HttpMethod(StrEnum):
    GET = auto()
    POST = auto()

HttpMethod.GET         # → <HttpMethod.GET: 'get'>
str(HttpMethod.GET)    # → 'get'（小文字）
HttpMethod.GET == "get"  # → True（StrEnum は文字列として比較可能）
HttpMethod.GET == "GET"  # → False（大文字は一致しない）
```

Pydantic フィールドの型に `HttpMethod` を使うと、
`"get"` / `"post"` で入力を受け付ける。`"GET"` は失敗する点に注意。

### 観察2: `IntEnum` は整数として比較・演算可能

```python
class HttpStatus(IntEnum):
    OK = 200
    NOT_FOUND = 404

HttpStatus.OK == 200       # → True
HttpStatus.NOT_FOUND > 400  # → False（404 > 400 は True だが）
int(HttpStatus.OK)         # → 200
```

`isinstance(HttpStatus.OK, int)` は `True`。
JSON シリアライズ時に整数として出力されるため、HTTP ステータスコードの定数管理に最適。

### 観察3: `IntFlag` のビット演算と `in` 演算子

```python
class Permission(IntFlag):
    READ = auto()   # 1
    WRITE = auto()  # 2
    DELETE = auto() # 4
    ADMIN = READ | WRITE | DELETE  # 7

perm = Permission.READ | Permission.WRITE  # 3
Permission.READ in perm   # → True
Permission.DELETE in perm # → False
perm == Permission.ADMIN  # → False（DELETE がないため）
```

`|=` で権限を動的に追加できる。`in` 演算子で特定権限を検査できる。

### 観察4: `StrEnum` は Pydantic バリデーションと親和性が高い

```python
from pydantic import BaseModel
from enum import StrEnum, auto

class Priority(StrEnum):
    LOW = auto()
    HIGH = auto()

class TaskBody(BaseModel):
    priority: Priority

# ✅ 正常
TaskBody.model_validate({"priority": "low"})   # → priority=Priority.LOW
# ❌ 失敗（大文字は許可されない）
TaskBody.model_validate({"priority": "LOW"})   # → ValidationError
```

Pydantic は `StrEnum` の値（小文字）でバリデーションする。
大文字で送信するクライアントとのインターフェース設計時は注意が必要。

### 観察5: `LogLevel(StrEnum)` の `CRITICAL` と `Priority(StrEnum)` の `CRITICAL` 名前衝突

```python
class Priority(StrEnum):
    CRITICAL = auto()  # value: "critical"

class LogLevel(StrEnum):
    CRITICAL = auto()  # value: "critical"
```

同じ名前・同じ値だが別クラス。Pydantic モデルのフィールドに型を指定すれば衝突なし。
ただし、Union 型 `Priority | LogLevel` で使う場合は最初にマッチした方が採用される。

---

## nene2-python フレームワークとの統合

- `StrEnum` は Pydantic フィールドの型として直接使用可能。文字列バリデーションが自動化される。
- `IntEnum` は HTTP ステータスコードの定数管理に使うと、整数として使える上に名前で参照できる。
- `IntFlag` は権限管理のビットフラグとして nene2 の認証システムに組み込める。
- Python 3.11+ での `Flag` iteration の変更点 (`__members__` 必要) を CLAUDE.md に追記した。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`if method == "GET"` のような文字列リテラル比較を enum に置き換えようとしている。

**ドキュメント理解**: `StrEnum` + `auto()` は覚えやすいが、値が小文字になることを忘れやすい。
「`GET = auto()` なのに値が `"get"` になる」は初見だと混乱する。  
**事故リスク**: 中。Pydantic に渡したときに `"GET"` が通らず `"get"` が必要と知らずに詰まるリスク。  
**規約の使いやすさ**: `HttpMethod.GET` の命名規則は直感的。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`ENUM_VALUES = {"GET": "get", "POST": "post"}` を使っているコードを enum に移行する。

**コピペ可能性**: Stack Overflow の `Enum` → `StrEnum` の移行例は豊富。`auto()` の使い方は覚えやすい。  
**拡張時の罠**: `Flag` に複合フラグを追加したとき、Python バージョンによって iteration 結果が変わる。
`__members__` と `list(enum)` の違いに気づかず、メンバー一覧 API が不完全になるリスク。  
**セキュリティ的な事故リスク**: 低（enum の誤用はバグだが通常セキュリティインシデントにならない）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `enum` や `union type` との対応関係を理解しようとしている。

**エラーレスポンスの質**: `"unknown_enum"` / `"unknown_status_code"` コードは明確。  
**Python 固有概念の学習コスト**: TypeScript の `enum` は数値ベースが多いが、Python の `StrEnum` は文字列ベース。
`StrEnum` は TypeScript の `string literal union` に近い感覚で使える。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `TextChoices` / `IntegerChoices` との比較視点を持つ。

**他フレームワークとの差異**: Django の `TextChoices` は `StrEnum` ベースで同等機能。
`IntegerChoices` は `IntEnum` ベース。移行は自然。  
**nene2-python の薄さへの評価**: Django のような `choices` パラメータ不要。`StrEnum` をフィールド型として指定するだけ。  
**本番投入可能性**: 権限管理・ステータスコード・優先度すべてに enum を使う設計は保守性が高い。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームでの enum の使い方の一貫性を重視する。

**コードレビューチェックポイント**:
- [ ] `StrEnum` フィールドに入力する値が小文字であることをクライアント仕様書に明記しているか
- [ ] `Flag` 複合メンバーに `__members__` vs `list(enum)` の違いを把握しているか
- [ ] `IntEnum` を `isinstance(x, int)` チェックで使う場合に意図しない True が返らないか
- [ ] `auto()` の使用箇所で値が変わらないことを保証しているか（メンバー追加で既存値がずれないか）

**チームでの安全なパターン**: HTTP ステータスコード・メソッド・優先度・権限をすべて enum で定義し、
文字列リテラルの散在を防ぐ。  
**ツール追加の必要性**: なし（ruff が `Enum` 関連の問題を概ね検出）。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。`StrEnum` は Pydantic との親和性が高く、API 境界での型安全を実現。  
**「初心者でも安全な API」達成度**: 中。`StrEnum` + `auto()` の値が小文字になることを文書化しないと事故が起きる。  
**設計上の負債**: `Flag.__members__` vs `list(Flag)` の Python 3.11 変更点をチームに周知する必要あり。  
**Follow-up Issue 候補**: なし

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`enum` モジュールは nene2-python の型安全ポリシーと非常に相性が良い。
`StrEnum` は Pydantic フィールドの型として直接使えるため、
文字列リテラルの散在を防ぎつつ型チェックが機能する。

最大の摩擦は **Python 3.11 での `Flag` iteration の変更**（複合フラグが `iter()` に含まれなくなった）。
`__members__` を使えば回避できるが、チームに周知が必要。

次の FT206 は `206 % 3 = 2` → セキュリティ診断なし、`206 % 4 = 2` → クラッカーペンテストなし。
