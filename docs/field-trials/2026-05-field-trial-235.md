# FT235: pprint — pformat / pp（再帰・幅・深さ制御）

**日付**: 2026-05-29
**テーマ**: Python `pprint` モジュールのデータ整形の実装と検証
**セキュリティ診断**: なし（235 % 3 = 1）
**クラッカーペンテスト**: なし（235 % 4 = 3）

---

## 概要

`pprint` は Python オブジェクトを人間可読に整形する。HTTP API で JSON 値を受け取り `pformat` で整形して返す形を検証した。`width`/`depth`/`sort_dicts` の制御と、深いネストの `depth` 省略による出力肥大化防止が観察ポイント。

| API | ユースケース |
|---|---|
| `pprint.pformat(obj, width, depth, sort_dicts)` | 整形済み文字列を返す |
| `depth` | 指定深さを超える階層を `...` に省略 |
| `sort_dicts` | 辞書キーのソート有無 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft235-pprint/`

| 関数 | 概要 |
|---|---|
| `format_value()` | `JsonValue` を `pformat`、width 10〜200 / depth 1〜10 に制限 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/pprint/format` | JSON 値を pprint 整形 |

入力型に Pydantic の `JsonValue`（再帰的 union）を採用し、`Any` を使わず型安全に任意 JSON を受ける。

---

## 摩擦点

### F-1: `sort_dicts` 既定 True — 入力順が保持されない

**観察**: `pprint.pformat` は既定（`sort_dicts=True`）で**辞書キーをソート**する。入力順を保ちたい場合（順序が意味を持つデータ）は `sort_dicts=False` が必要。Python 3.7+ の dict は挿入順を保持するが pprint は既定で崩す。

**対処**: `sort_dicts` をパラメータ化。`{"b":1,"a":2}` が True で `a,b`、False で `b,a` 順になることをテストで確認。

### F-2: `depth` で深いネストを省略し出力肥大化を防ぐ

**観察**: 深くネストした構造をそのまま整形すると出力が巨大化する。`depth` を指定すると超過階層を `...` に省略できる。

**対処**: `depth` を 1〜10 に制限。`{l1:{l2:{l3:{l4}}}}` を depth=2 で整形すると `...` が現れ `deep` が出力されないことを確認。入力 JSON 自体の深さは FastAPI/json パーサの制限に依存する点も認識。

### F-3: `JsonValue` で `Any` を回避

**観察**: 任意 JSON を受ける際に `dict[str, Any]` を使うと CLAUDE.md の `Any` 禁止に抵触する。

**対処**: Pydantic の `JsonValue`（`str | int | float | bool | None | list | dict` の再帰 union）を入力型に採用。mypy strict を通過しつつ任意 JSON を型安全に受ける。

---

## テスト結果

```
5 passed in 0.90s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`print` より見やすい整形が得られるのは嬉しい。width/depth の効果が出力に見えて学びやすい。

**ドキュメント理解**: `sort_dicts` の既定 True は意外。コメントで明示。
**事故リスク（低）**: 表示用途で破壊性なし。
**規約の使いやすさ**: data + width/depth が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

デバッグ出力やログ整形で使う。`sort_dicts=False` を知らないと順序が崩れて混乱する。

**コピペ可能性**: `format_value` は流用可。
**拡張時の罠**: sort_dicts 既定・深いネストの出力肥大化。
**事故リスク（低）**: depth/width 制限あり。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`JSON.stringify(obj, null, 2)` に対応。pprint は Python repr 形式（シングルクォート）な点が異なる。

**エラーレスポンスの質**: 範囲外は 422。
**Python 固有概念**: pprint の repr 形式・`JsonValue`。
**事故リスク（低）**: 制限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ログには構造化（structlog/JSON）を使うべきで、pprint は人手デバッグ向け。機密データを pprint でログ出力しない規律が重要。

**他フレームワークとの差異**: 本番ログは JSON 一択。pprint は開発時。
**nene2 の薄さへの評価**: 薄いラップとして妥当。`JsonValue` 採用が型安全で good。
**事故リスク（低）**: depth で肥大化抑制。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `pprint` で機密データを出力していないか（ログ漏洩 — FT220 と同じ注意）。
- `depth`/`width` に上限があるか（出力肥大化）。
- 任意 JSON 受け口に `Any` ではなく `JsonValue` を使っているか。
- 入力 JSON の深さ・サイズ上限（パーサ側）。

**チームでの安全なパターン**: pprint は開発用に限定、本番ログは構造化ログ。
**事故リスク（低）**: 範囲制限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Any` 不使用（`JsonValue` 採用）・Pydantic 範囲制限・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: width/depth 制限と `JsonValue` 型で安全側に固定。
**改善提案**: 「デバッグは pprint / 本番ログは structlog（FT220）」の使い分けを how-to に明記する。
