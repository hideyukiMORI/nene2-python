# FT252: json — loads/dumps の堅牢化

**日付**: 2026-05-29
**テーマ**: Python `json` モジュールの安全なパース・シリアライズの実装と検証
**セキュリティ診断**: 🔒 あり（252 % 3 = 0）
**クラッカーペンテスト**: 🔍 あり（252 % 4 = 0）

---

## 概要

`json` は API の中核だが、デフォルト設定には**セキュリティ上の落とし穴**がある — NaN/Infinity を受理（非標準 JSON）、重複キーを黙殺（パーサ差異攻撃）、深いネストでスタック枯渇、巨大整数で計算 DoS。FastAPI/Pydantic は多くを吸収するが、生の `json.loads` を使う場面のために堅牢化パターンを診断＋ペンテストで検証した。

| 落とし穴 | 対策 |
|---|---|
| NaN/Infinity 受理 | `parse_constant` で拒否 |
| 重複キー黙殺 | `object_pairs_hook` で検出・拒否 |
| 深いネスト | 反復走査で深さ上限 + RecursionError 捕捉 |
| 巨大整数/サイズ | サイズ上限 + int 文字列桁数制限 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft252-json/`

| 関数 | 概要 |
|---|---|
| `parse_json()` | NaN/Inf 拒否・重複キー拒否・深さ/サイズ制限 |
| `serialize_json()` | `allow_nan=False` で非標準 JSON を出さない |
| `_reject_constant` / `_reject_duplicate_keys` / `_check_depth` | 各防御 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/json/parse` | JSON を堅牢に解析 |
| POST | `/json/serialize` | JSON を安全にシリアライズ |

---

## 摩擦点

### F-1: `json.loads` は NaN/Infinity を既定で受理する（非標準 JSON）

**観察**: `json.loads('{"x": NaN}')` は成功し `float('nan')` を返す。NaN/Infinity は**標準 JSON に存在しない**拡張で、他言語パーサとの相互運用で破綻し、`NaN != NaN` の性質がロジックを壊す。

**対処**: `parse_constant=_reject_constant` で `NaN`/`Infinity`/`-Infinity` を 422。シリアライズも `allow_nan=False`。

### F-2: 重複キーは「最後勝ち」で黙殺 — パーサ差異攻撃

**観察**: `{"role":"user","role":"admin"}` は `json.loads` で `{"role":"admin"}`（最後勝ち）になる。検証する層と使う層で**異なるキーを採用**すると認可バイパス（parser differential / HTTP parameter pollution の JSON 版）になる。

**対処**: `object_pairs_hook=_reject_duplicate_keys` で重複キーを検出して 422（ネストも）。

### F-3: 深いネスト・巨大整数・サイズの DoS

**観察**: 深くネストした JSON は CPython の C スキャナで `RecursionError`、巨大桁整数は `int` 変換が O(n²)（Python 3.11+ は既定 4300 桁で `ValueError`）、巨大入力はメモリ。

**対処**: サイズ上限（100k）、`RecursionError` 捕捉、反復走査で深さ上限（50）。診断で深さ 60/5000 を 5ms で 422、1 万桁整数を 422、サイズ超過を 422。

---

## セキュリティ診断 & クラッカーペンテスト

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| 非標準定数 | `{"x":NaN}` / `Infinity` / `-Infinity` / `[1,NaN,2]` | **すべて 422** |
| 重複キー（トップ） | `{"role":"user","role":"admin"}` | **422** |
| 重複キー（ネスト） | `{"o":{"k":1,"k":2}}` | **422** |
| 深いネスト | depth 50 / 60 / 5000 | **200 / 422 / 422**（5ms） |
| 巨大整数 | 1 万桁 | **422**（int 桁数制限） |
| サイズ | 100k 超 | **422** |
| 正常 | `{"a":{"b":[1,2,{"c":3}]}}` | **200** |
| シリアライズ | allow_nan=False | NaN 出力なし |
| セキュリティヘッダー | — | 付与あり |

### まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| 非標準定数 | 4 | 0 | 4 |
| 重複キー | 2 | 0 | 2 |
| ネスト/整数/サイズ DoS | 5 | 0 | 5 |

**総合評価: 合格**

`parse_constant` + `object_pairs_hook` + 深さ/サイズ/桁数制限で、NaN/Infinity・重複キー差異攻撃・各種 DoS をすべて遮断。生 `json.loads` を使う場合の堅牢化テンプレートとして有効。

---

## テスト結果

```
8 passed in 0.87s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`json.loads` がそのまま安全だと思いがち。NaN や重複キーの罠は知らないことが多い。

**ドキュメント理解**: 各落とし穴をコメントで明示。
**事故リスク（中）**: 生 loads を無防備に使う。
**規約の使いやすさ**: text → 解析結果が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

外部 API レスポンスや Webhook ボディの解析で使う。重複キー差異攻撃は知らないと盲点。

**コピペ可能性**: `parse_json` の堅牢化はそのまま流用可。
**拡張時の罠**: parse_constant/object_pairs_hook を付け忘れ。
**事故リスク（中）**: NaN・重複キー。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`JSON.parse` は NaN を受けない（より厳格）。Python の寛容デフォルトに驚く。

**エラーレスポンスの質**: 不正は 422。
**Python 固有概念**: parse_constant/object_pairs_hook。
**事故リスク（低）**: 堅牢化で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

FastAPI/Pydantic が境界を守るが、内部で生 json を使う箇所（キャッシュ・キュー）には本パターンが要る。重複キー差異は OWASP でも言及。

**他フレームワークとの差異**: 多くの言語で重複キー挙動が異なる（差異攻撃の根源）。
**nene2 の薄さへの評価**: parse_constant/hook/深さ制限の組み合わせが適切。
**事故リスク（低）**: 全 DoS を実測遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 生 `json.loads` に `parse_constant`（NaN 拒否）・`object_pairs_hook`（重複キー）を付けているか。
- 深さ・サイズ・整数桁数の上限（DoS）。
- シリアライズで `allow_nan=False` か。
- 認可に関わるキーの重複を検出しているか（差異攻撃）。

**チームでの安全なパターン**: 生 json は堅牢化ラッパー経由に統一。境界は Pydantic。
**事故リスク（低）**: 診断＋ペンテストを回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 「HTTP 境界の全入力を Pydantic で検証」と整合。`Any` 不使用（`JsonValue`）・`ValidationException` 変換・`logging` 使用も準拠。
**初心者でも安全な API 達成度**: 堅牢化を関数内に集約し、生 loads の落とし穴を排除。
**改善提案**: `parse_json` を `nene2.http` に「堅牢 JSON パーサ」として提供し、重複キー差異・NaN・DoS 対策を横断適用する。
