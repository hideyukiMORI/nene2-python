# FT279: plistlib — plist 解析の安全性

**日付**: 2026-05-29
**テーマ**: Python `plistlib` の plist 解析と XXE 耐性の実装と検証
**セキュリティ診断**: 🔒 あり（279 % 3 = 0）
**クラッカーペンテスト**: なし（279 % 4 = 1）

---

## 概要

`plistlib` は Apple の plist（XML/バイナリ）を解析する。XML を扱うが、**`xml.etree`（XXE・展開爆弾に脆弱、FT180 で defusedxml 推奨）とは異なり、plistlib は実体宣言を一切サポートしない**ため XXE・エンティティ展開に構造的に安全。診断回（279 % 3 = 0）としてこの耐性とサイズ/深さ制限を検証した。

| API | ユースケース |
|---|---|
| `plistlib.loads(data, fmt=FMT_XML)` | XML plist 解析 |
| `plistlib.InvalidFileException` | 不正 plist の例外 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft279-plistlib/`

| 関数 | 概要 |
|---|---|
| `parse_plist()` | XML plist 解析 + 深さ/サイズ制限 |
| `_depth()` | 反復走査で深さ検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/plist/parse` | plist を安全に解析 |

---

## 摩擦点

### F-1【良い性質】plistlib は実体宣言を拒否し XXE に安全

**観察**: 生の `xml.etree.ElementTree` は外部実体（XXE）・展開爆弾に脆弱で `defusedxml` が必要（FT180）。一方 `plistlib` は **`<!ENTITY ...>` 宣言を含む plist を `InvalidFileException`（"XML entity declarations are not supported in plist files"）で拒否**する。XXE（`file:///etc/passwd`）も billion-laughs も解析前に弾かれる。

**対処**: plistlib の XML パースは XXE 耐性があり、追加の defusedxml は不要。診断で XXE・実体爆弾がともに 422。

### F-2: 深いネストの DoS

**観察**: plistlib 自体に深さ上限はなく、深くネストした array/dict で大きな構造を作れる。

**対処**: 解析後に `_depth()`（反復走査）で深さを検証し上限超過を 422。35 段ネストを拒否。

### F-3: 不正データ・サイズ

**観察**: 不正な XML は `ExpatError`/`InvalidFileException`、巨大入力はメモリ。

**対処**: 例外を捕捉して 422、入力長を上限化。

---

## セキュリティ診断結果

| カテゴリ | 例 | 結果 |
|---|---|---|
| 正常 plist | dict/string/integer | **200** |
| XXE | `<!ENTITY x SYSTEM "file:///etc/passwd">` | **422**（実体宣言非サポート） |
| 実体展開爆弾 | ネスト ENTITY | **422**（実体宣言非サポート） |
| 深いネスト | 35 段 array | **422**（深さ上限） |
| 不正データ | `not xml {{{` | **422**（syntax error） |
| サイズ | 100k 超 | **422** |
| セキュリティヘッダー | — | 付与あり |

**総合評価: 合格**

plistlib は**実体宣言を構造的に拒否**するため XXE・展開爆弾に安全（xml.etree と対照的）。加えて深さ/サイズ制限で DoS も防御。

---

## テスト結果

```
5 passed in 0.28s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

plist は Apple 設定で見かける。XML だが XXE に安全と知れる。

**ドキュメント理解**: XXE 非脆弱性をコメントで明示。
**事故リスク（低）**: 安全なパーサ。
**規約の使いやすさ**: text → value が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

iOS/macOS 連携で plist を扱う。XML だからと身構えるが plistlib は安全。

**コピペ可能性**: parse_plist は流用可。
**拡張時の罠**: 深いネスト・バイナリ plist。
**事故リスク（低）**: XXE 耐性 + 深さ制限。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

plist は JSON 的な構造。XML パーサの XXE リスクと、plistlib がそれを免れる点を理解。

**エラーレスポンスの質**: 不正・XXE は 422。
**Python 固有概念**: plist 形式・InvalidFileException。
**事故リスク（低）**: 安全。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

XML 系は XXE が定番リスク。plistlib が実体宣言を拒否するのは安心材料。一般 XML は defusedxml（FT180）。

**他フレームワークとの差異**: plistlib は専用パーサで XXE 面がない。
**nene2 の薄さへの評価**: XXE 耐性を活かしつつ深さ/サイズ制限を足す設計が適切。
**事故リスク（低）**: 構造的に安全。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- XML 解析に生 `xml.etree` を使っていないか（XXE → defusedxml、FT180）。plist なら plistlib で安全。
- 深さ/サイズ上限（DoS）。
- バイナリ plist の場合の不正データ処理。
- 解析結果の値検証（Pydantic）。

**チームでの安全なパターン**: plist=plistlib、一般 XML=defusedxml、深さ/サイズ制限。
**事故リスク（低）**: XXE 耐性を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 「XML 処理には defusedxml を使用」（FT180）と整合し、plist は plistlib で安全。`Any` 不使用（`JsonValue`）・Pydantic 制限・`ValidationException` 変換・`logging` 使用も準拠。
**初心者でも安全な API 達成度**: XXE 耐性 + 深さ/サイズ制限で安全側に固定。
**改善提案**: 「XML 系の安全則（一般 XML=defusedxml / plist=plistlib / 深さ・サイズ制限）」を how-to に FT180 と統合する。
