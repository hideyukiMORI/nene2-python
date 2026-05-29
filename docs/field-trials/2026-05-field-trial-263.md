# FT263: tomllib — TOML 読み込み・安全な設定パース

**日付**: 2026-05-29
**テーマ**: Python `tomllib` の TOML パースの実装と検証
**セキュリティ診断**: なし（263 % 3 = 2）
**クラッカーペンテスト**: なし（263 % 4 = 3）

---

## 概要

`tomllib`（Python 3.11+）は TOML を**読み取り専用**で解析する。`yaml.load`（任意オブジェクト構築）や `eval` と異なり**コード実行の余地がない**ため、設定ファイルの安全なパースに適する。HTTP API でラップし TOML 解析を検証した。

| API | ユースケース |
|---|---|
| `tomllib.loads(text)` | TOML 文字列を dict に解析 |
| `tomllib.TOMLDecodeError` | 不正 TOML の例外 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft263-tomllib/`

| 関数 | 概要 |
|---|---|
| `parse_toml()` | TOML を解析し dict・トップレベルキーを返す |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/toml/parse` | TOML を安全に解析 |

---

## 摩擦点

### F-1: tomllib は安全（yaml.load との対比）

**観察**: YAML の `yaml.load`（非 SafeLoader）は `!!python/object` タグで任意オブジェクトを構築でき RCE につながる。TOML にはそのような機構がなく、`tomllib` は**データのみ**を返す。設定形式として TOML/JSON は YAML より攻撃面が小さい。

**対処**: 設定パースは `tomllib`（または `json`/`yaml.safe_load`）を使う。本 FT は読み取り専用パースを検証。

### F-2: `loads`（str）と `load`（バイナリファイル）の使い分け

**観察**: `tomllib.load` は**バイナリモードで開いたファイル**を取る（`open(path, "rb")`）。テキストモードだと `TypeError`。文字列からは `loads`。

**対処**: HTTP では文字列を受けるので `loads`。ファイルからは `load` + `"rb"`。

### F-3: 入力サイズ制限

**観察**: 巨大 TOML はパースコスト・メモリを消費する。

**対処**: 入力長を上限化（100k）。不正 TOML は `TOMLDecodeError` 捕捉で 422。

---

## テスト結果

```
5 passed in 0.84s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

設定ファイル形式として TOML は読みやすい。標準で安全にパースできるのが嬉しい。

**ドキュメント理解**: loads/load の違いをコメントで明示。
**事故リスク（低）**: 読み取り専用で破壊性なし。
**規約の使いやすさ**: text → data が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`pyproject.toml` でお馴染み。設定読み込みで yaml.load を使う事故を避けられる。

**コピペ可能性**: parse_toml は流用可。
**拡張時の罠**: load のバイナリモード要件。
**事故リスク（低）**: 安全なパーサ。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JSON に近い構造。コメントや型を持てる設定形式として理解しやすい。

**エラーレスポンスの質**: 不正 TOML は 422。
**Python 固有概念**: tomllib の読み取り専用性。
**事故リスク（低）**: 安全。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

設定は TOML/JSON が安全。YAML を使うなら必ず safe_load。tomllib は書き込み非対応（書くなら tomli-w）。

**他フレームワークとの差異**: YAML の攻撃面を避けられる。
**nene2 の薄さへの評価**: 薄いラップとして妥当。
**事故リスク（低）**: 安全なパーサ。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 設定パースに yaml.load（非 safe）/eval を使っていないか → TOML/JSON/safe_load。
- load のバイナリモード要件。
- 入力サイズ上限。
- 信頼できない TOML でも安全（コード実行なし）だが、値の検証（Pydantic）は別途必要。

**チームでの安全なパターン**: 設定は TOML、値は Pydantic 検証。
**事故リスク（低）**: 安全なパーサを採用。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Any` 不使用（`JsonValue`）・Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。安全なデシリアライズ（FT240）の思想と一貫。
**初心者でも安全な API 達成度**: 読み取り専用パーサを採用し、コード実行の余地を排除。
**改善提案**: 「設定形式は TOML/JSON、YAML は safe_load 必須」を how-to に明記し、FT240（安全なデシリアライズ）と相互リンクする。
