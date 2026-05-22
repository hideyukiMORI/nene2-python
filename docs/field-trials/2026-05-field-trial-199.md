# FT199: uuid モジュール — UUID 生成・解析・バリデーション

**日付**: 2026-05-22
**テーマ**: Python `uuid` モジュールの UUID v3/v4/v5 生成・構造解析・バリデーションの実装と検証
**セキュリティ診断**: なし（199 % 3 = 1）
**クラッカーペンテスト**: なし（199 % 4 = 3）

---

## 概要

`uuid` は Python 標準ライブラリの UUID 生成・解析モジュール。
バージョン 1〜5 の UUID 生成・解析に対応しており、実用上は v4（乱数ベース）と v5/v3（名前ベース）が
主要な用途となる。今回は UUID の生成（v3/v4/v5）・構造解析・バリデーションを FastAPI エンドポイントとして
実装し、`uuid.UUID` の内部フィールド（`version`, `variant`, `hex`, `int`）の型と挙動を検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft199-uuid/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `generate_v4()` | ランダムな UUID v4 を文字列で生成 |
| `generate_v5(namespace_str, name)` | 名前空間 + 名前から UUID v5（SHA-1 ベース）を決定論的に生成 |
| `generate_v3(namespace_str, name)` | 名前空間 + 名前から UUID v3（MD5 ベース）を決定論的に生成 |
| `analyze_uuid(uuid_str)` | UUID 文字列を解析して `UuidInfo` を返す |
| `validate_uuid(uuid_str)` | 文字列が有効な UUID か検証して `ValidationResult` を返す |
| `UuidInfo` | version / variant / hex / is_nil / int_value を保持する frozen dataclass |
| `ValidationResult` | is_valid / reason を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/uuid/v4` | ランダムな UUID v4 を生成して返す |
| POST | `/uuid/v5` | 名前空間 + 名前から UUID v5 を生成（同一入力 → 同一出力） |
| POST | `/uuid/v3` | 名前空間 + 名前から UUID v3 を生成（同一入力 → 同一出力） |
| POST | `/uuid/analyze` | UUID 文字列の構成要素を分解して返す（無効な UUID は 422） |
| POST | `/uuid/validate` | 文字列が有効な UUID かを検証して `is_valid` を返す |

---

## テスト結果

**25 passed**

```
25 passed in 0.07s
```

---

## 摩擦ポイント

### F-1: `uuid.UUID.variant` が整数でなく文字列定数を返す（深刻度: 低）

**事象**: `uuid.UUID.variant` の型が `int` だと思い込んで `_variant_name(variant: int) -> str`
というマッピング関数を実装した。mypy が `Argument 1 to "_variant_name" has incompatible type "str"; expected "int"` と報告してコンパイルエラー。

**原因**: `uuid.UUID.variant` は `uuid.RESERVED_NCS`, `uuid.RFC_4122`, `uuid.RESERVED_MICROSOFT`,
`uuid.RESERVED_FUTURE` という文字列定数（`str`）を返す。
たとえば RFC 4122 準拠 UUID の場合は `"specified in RFC 4122"` という文字列が返る。
Python ドキュメントには "The UUID variant" と書かれているだけで、
型が `str` であることは記述が薄く、公式ソースを確認するまで気づかなかった。

**対応**: `_variant_name()` 変換関数を削除し、`parsed.variant` をそのまま `UuidInfo.variant: str` として格納。
テストも `info.variant == "rfc_4122"` ではなく `info.variant == uuid.RFC_4122` の定数参照に修正。

---

## 観察点

### 観察1: v5 と v3 は同じ名前空間・名前に対して常に同一 UUID を返す

```python
a = generate_v5("url", "https://example.com")
b = generate_v5("url", "https://example.com")
assert a == b  # 常に True
```

名前空間（DNS/URL/OID/X.500）+ 名前のペアが同じなら実行環境・タイミングを問わず結果が一致する。
これはリソース識別子の冪等な UUID 生成（データベース行のサロゲートキーなど）に有用。

### 観察2: `uuid.UUID` のコンストラクタは入力形式を柔軟に許容する

```python
uuid.UUID("urn:uuid:12345678-1234-5678-1234-567812345678")  # URN 形式
uuid.UUID("{12345678-1234-5678-1234-567812345678}")          # 波括弧あり
uuid.UUID("12345678123456781234567812345678")                 # ハイフンなし 32 文字
```

いずれも正常にパースされる。`validate_uuid()` で "有効な UUID" と判定されるが、
エンドポイントの `AnalyzeBody` には `max_length=36` を設定しているため
URN 形式（46 文字）は 422 で弾かれる。想定利用者には `-` 区切りの標準形式を示すドキュメントが必要。

### 観察3: nil UUID (`00000000-...`) は version フィールドが None になる

```python
info = analyze_uuid("00000000-0000-0000-0000-000000000000")
assert info.version is None   # variant が RFC_4122 でないため
assert info.is_nil is True
assert info.int_value == 0
```

`uuid.UUID.version` は `variant == uuid.RFC_4122` のときのみ有効。
nil UUID は `variant == uuid.RESERVED_NCS` のため `version` にアクセスすると `ValueError` が発生する。
`UuidInfo.version: int | None` とすることで安全に扱える。

---

## nene2-python フレームワークとの統合

- `validate_uuid()` は例外を投げず `ValidationResult(is_valid=False)` を返すため、
  エンドポイントは `ValidationException` を使わずそのまま `ValidationResult` を返せる。
  「失敗が通常状態」のバリデーションは例外よりも Result 型の方が自然。
- `analyze_uuid()` は失敗が例外扱い（`ValueError`）のため、エンドポイント側で try-except し
  `ValidationException` に変換する。`AnalyzeBody.value: str = Field(max_length=36)` で
  UUID 文字列の長さ上限を定義しておくことで Pydantic 層でも不正入力を弾ける。
- `uuid` モジュール自体は外部依存なし。`pyproject.toml` への追記が不要な点でゼロコスト導入。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FastAPI のエンドポイントとして UUID を扱う実装に取り組んでいる。

**ドキュメント理解**: `uuid.uuid4()` の基本用途は Python チュートリアルや Stack Overflow でよく見かける。
一方で `uuid.RFC_4122` などの定数値（実際は文字列）や `version` が `variant` に依存する点は
公式ドキュメントだけでは把握しにくい。F-1 と同じ罠に陥りやすい。  
**事故リスク**: 低。`uuid` は副作用なし・外部通信なし・状態なしのピュア関数群。
最悪でも型エラーに終わる。  
**規約の使いやすさ**: `generate_v4()` を 1 行で書けるため、最初の壁は低い。
v5 の決定論的生成を使いたい場合は名前空間の概念説明が必要。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存コードをコピーして API に組み込む作業を担当している。

**コピペ可能性**: `generate_v4()` / `validate_uuid()` はそのままコピーして使える。
`analyze_uuid()` の `variant == uuid.RFC_4122` 比較は定数のインポートが必要な点で一瞬詰まるかもしれない。  
**拡張時の罠**: `UuidInfo.version` が `None` になるケースを見落として `version + 1` など書くと
`TypeError`。`int | None` の型注釈があれば mypy が検出するが、コピペ時に型注釈を削ると静かに壊れる。  
**セキュリティ的な事故リスク**: 低。UUID は外部入力の検証もシンプル。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

フロントエンドと API の両方を実装する立場で、エラーレスポンスの質を重視する。

**エラーレスポンスの質**: `/uuid/analyze` への無効な UUID 送信で 422 + `invalid_uuid` コードが返る。
`/uuid/validate` は 200 + `is_valid: false` を返す。2 種類の「失敗」が異なるステータスで返るのは
一貫性を欠いて見えるかもしれない。ただしセマンティクスの違い（「解析失敗は例外」vs「バリデーション失敗は通常状態」）
を理解すれば納得できる。  
**Python 固有概念の学習コスト**: `dataclass(frozen=True, slots=True)` や `int | None` は
TypeScript の `readonly` や `number | null` と近いため理解しやすい。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `UUIDField` や `uuid.uuid4` を日常的に使っている立場。

**他フレームワークとの差異**: Django では `models.UUIDField(default=uuid.uuid4)` で UUIDを
DB のプライマリキーとして使うパターンが一般的。nene2-python の FT199 はサービス層での
UUID 操作に焦点を当てており、DB 統合は対象外なため、実務的な使いどころが分かりにくい。  
**nene2-python の薄さへの評価**: UseCase や DB 非依存の純粋関数群として `demos.py` を構成しているのは
テスタビリティが高く評価できる。  
**本番投入可能性**: UUID 生成・バリデーションの用途なら問題なし。`UuidInfo.variant` が
`str` 定数で返る挙動はチームに共有すべき知識。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チーム全体のコード品質を維持する責任を持つ。

**コードレビューチェックポイント**:
- [ ] `version` フィールドが `None` になるケースのハンドリング（nil UUID・variant が RFC_4122 以外）
- [ ] `validate_uuid` と `analyze_uuid` の使い分けが明確か（バリデーション目的なら前者を使う）
- [ ] `AnalyzeBody.value` の `max_length=36` が URN/波括弧形式を意図的に除外していることの理解

**チームでの安全な共有パターン**: `validate_uuid()` を汎用バリデーターとして使い、
成功した場合のみ `analyze_uuid()` を呼ぶパターンが安全。`ValidationResult` → 200 / `ValidationException` → 422 の
2 層設計はコードレビューで説明しやすい。  
**ツール追加の必要性**: 特になし。mypy --strict が `int | None` の安全でない使用を検出する。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の設計ポリシーとの整合性を確認する。

**ポリシー達成度**: 高。`dataclass(frozen=True, slots=True)`・型注釈・Pydantic バリデーション・
`ErrorHandlerMiddleware` の組み合わせが適切に機能している。  
**「初心者でも安全な API」達成度**: 高。副作用なし・外部通信なし・明確な型で、
初心者が誤って使いにくいモジュール構成になっている。  
**設計上の負債・ドキュメント不足**: `uuid.UUID.variant` が文字列定数を返す点は Python ドキュメントでは
目立たない。CLAUDE.md への追記は不要だが、FT199 レポートに摩擦ポイントとして記録済み。  
**Follow-up Issue 候補**: なし

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`uuid` モジュールは副作用なし・外部依存なし・ピュア関数の集合であり、
nene2-python の FastAPI エンドポイントに最もシームレスに統合できるモジュールのひとつ。
実装・テスト・全チェック通過まで摩擦はほぼゼロで、25 テストが 0.07s で完了した。

唯一の落とし穴は `uuid.UUID.variant` が `int` でなく文字列定数（`uuid.RFC_4122 = "specified in RFC 4122"` 等）
を返す点。mypy --strict がこれを即座に検出するため、静的解析を通過させる習慣があれば実害には至らない。

次の FT200 は `200 % 4 = 0` のためクラッカーペンテストを実施する。
