# FT273: marshal — 信頼できないデータに使わない / json 代替

**日付**: 2026-05-29
**テーマ**: Python `marshal` の危険性と json 代替の実装と検証
**セキュリティ診断**: 🔒 あり（273 % 3 = 0）
**クラッカーペンテスト**: なし（273 % 4 = 1）

---

## 概要

`marshal` は Python 内部のシリアライズ（`.pyc` 等に使用）。公式ドキュメントは明確に警告する — **「marshal は誤った/悪意あるデータに対して安全ではない。信頼できないソースから受け取ったデータを unmarshal してはならない」**。`marshal.loads` は細工されたバイト列で**インタプリタをクラッシュ/セグフォルト**させ得る（pickle のような RCE とは別の危険）。本 FT は marshal を**ユーザー入力に一切使わず**、json + Pydantic で安全に往復する設計を診断した。FT240（pickle）と同系統。

| 危険 | 安全（本 FT） |
|---|---|
| `marshal.loads(untrusted)` | `json.loads` + Pydantic 検証 |
| `pickle.loads(untrusted)`（FT240） | json + スキーマ |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft273-marshal/`

| 関数 | 概要 |
|---|---|
| `safe_roundtrip()` | json でシリアライズ/デシリアライズ（marshal 不使用） |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/serialize/roundtrip` | json で安全に往復 |

---

## 摩擦点

### F-1: `marshal.loads` を信頼できないデータに使わない

**観察**: `marshal.loads` は内部フォーマット用で堅牢性の保証がなく、悪意あるバイト列でインタプリタがクラッシュする可能性がある（公式警告）。バージョン間互換性もない。外部入力のデシリアライズには絶対に使わない。

**対処**: API はユーザー入力に marshal を一切適用しない。デシリアライズは `json.loads`（自前の信頼できる出力のみ loads）+ Pydantic 検証。ソース監査で `marshal` がドキュメント/コメントにのみ出現し、`import marshal`/`marshal.loads` が**存在しない**ことを確認。

### F-2: 危険な検証はしない（クラッシュを誘発しない）

**観察**: 「marshal の危険性」を実証するために細工バイトを `marshal.loads` に渡すと、まさに警告どおりインタプリタがクラッシュし得る。診断としてそれを実行するのは不適切。

**対処**: 攻撃の実行はせず、**ソースに marshal.loads が無いこと**と公式警告の引用で診断する（防御は「使わない」ことそのもの）。

### F-3: 用途の整理（marshal / pickle / json）

**観察**: marshal は `.pyc` 等の内部用途専用、pickle は Python オブジェクトの永続化（信頼できるデータのみ）、json は言語横断のデータ交換。用途を取り違えると危険。

**対処**: 外部とのデータ交換は json（または TOML/MessagePack）。pickle/marshal は信頼できるデータ・内部用途のみ。

---

## セキュリティ診断結果

| カテゴリ | 結果 |
|---|---|
| ソース監査（marshal.loads 使用） | **なし**（ドキュメント/コメントのみ） |
| デシリアライズ手段 | **json.loads**（自前出力のみ）+ Pydantic |
| json 往復 | dict/scalar/unicode を保持 |
| シリアライズ長上限 | 100k 超で 422 |
| セキュリティヘッダー | 付与あり |

**総合評価: 合格**

marshal をユーザー入力に一切使わず json + 検証で安全に処理。公式警告に従い「信頼できないデータを unmarshal しない」原則を実証。FT240（pickle）と合わせ「危険なデシリアライザを使わない」シリーズ。

---

## テスト結果

```
4 passed in 0.84s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

marshal という存在自体を知らないことが多い。「内部用で外部入力に使わない」と学べる。

**ドキュメント理解**: 公式警告の引用で危険性を明示。
**事故リスク（中）**: ネット記事で marshal を「速いシリアライザ」と紹介され誤用。
**規約の使いやすさ**: value → 往復が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

キャッシュ高速化で marshal を使う事例があるが外部入力には危険。json/MessagePack が安全。

**コピペ可能性**: safe_roundtrip は流用可。
**拡張時の罠**: marshal を外部入力に使う・バージョン非互換。
**事故リスク（中）**: marshal.loads(untrusted)。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

データ交換は JSON 一択という感覚と一致。marshal/pickle は Python 内部事情と理解。

**エラーレスポンスの質**: 長さ超過は 422。
**Python 固有概念**: marshal/pickle/json の用途差。
**事故リスク（低）**: json 使用。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

marshal は .pyc 用で外部入力厳禁。Insecure Deserialization（OWASP A08）の一環。データ交換は json/MessagePack、永続化は慎重に。

**他フレームワークとの差異**: 各言語とも内部シリアライザを外部入力に使わない。
**nene2 の薄さへの評価**: marshal を構造的に排除し json + 検証で安全。
**事故リスク（低）**: 使わない設計。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `marshal.loads`/`pickle.loads`（FT240）を外部入力に使っていないか（grep 監査）。
- デシリアライズは json + スキーマ検証か。
- 速度目的で marshal を使う場合、入力が完全に信頼できるか。
- バージョン非互換（marshal）の考慮。

**チームでの安全なパターン**: 外部データは json、内部高速化が要れば MessagePack 等。marshal/pickle を lint/監査で外部入力から排除。
**事故リスク（低）**: 監査で確認。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `pickle.loads` 禁止と同思想で marshal も外部入力に使わない。`Any` 不使用（`JsonValue`）・Pydantic 制限・`logging` 使用も準拠。FT240/FT264 と並ぶ「危険プリミティブ回避」。
**初心者でも安全な API 達成度**: marshal を排除し json + 検証を既定にし誤用の余地を排除。
**改善提案**: 「外部データのデシリアライズは json/スキーマ、marshal/pickle は外部入力厳禁」を how-to の危険プリミティブ一覧に統合する。
