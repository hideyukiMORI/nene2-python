# FT73: PaginationQueryParser.parse() 静的メソッド実運用検証

**日付**: 2026-05-20  
**テーマ**: `PaginationQueryParser.parse(Request)` レガシーパターンと `ErrorHandlerMiddleware.install()` の連携確認  
**バージョン**: v1.8.20  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft73-pagination-parse/`

---

## 概要

`PaginationQueryParser.parse(request)` 静的メソッド（`Depends()` を使わないパターン）を検証した。
カスタム `default_limit` / `max_limit` の動作と、
v1.8.20 で追加した `ErrorHandlerMiddleware.install()` との連携も確認した。

---

## 実装内容

- `GET /items` — `PaginationQueryParser.parse(request)` でデフォルト (limit=20, max=100)
- `GET /items/custom` — `parse(request, default_limit=5, max_limit=10)` でカスタム値
- `ErrorHandlerMiddleware.install(app)` を使用（v1.8.20 の新機能）
- `ValidationException` による 422 を nene2 Problem Details 形式で返す

---

## テスト結果

**11/11 passed**

| テスト | 結果 |
|---|---|
| `test_default_pagination_returns_20_items` | PASSED |
| `test_custom_limit_and_offset` | PASSED |
| `test_limit_too_large_returns_422` | PASSED |
| `test_limit_zero_returns_422` | PASSED |
| `test_negative_offset_returns_422` | PASSED |
| `test_non_integer_limit_returns_422` | PASSED |
| `test_non_integer_offset_returns_422` | PASSED |
| `test_custom_default_limit_applied` | PASSED |
| `test_custom_max_limit_enforced` | PASSED |
| `test_custom_max_limit_at_boundary` | PASSED |
| `test_last_page_returns_remaining_items` | PASSED |

---

## Friction Points

なし。

**特筆点**:
- `PaginationQueryParser.parse()` は `ValidationException` を raise するため、
  `ErrorHandlerMiddleware.install(app)` と組み合わせると
  非整数値・範囲外の入力が自動的に 422 nene2 Problem Details で返る。
- `parse()` が返す `PaginationQuery` (named dataclass) は `limit` / `offset` を保持し、
  `Depends()` パターンの `PaginationQueryParser` インスタンスと同じインターフェースで使える。
- `default_limit` / `max_limit` のカスタマイズが `parse()` の引数で完結するため、
  ルートごとに異なるページネーション制限を設定しやすい。
- `ErrorHandlerMiddleware.install(app)` が v1.8.20 で正式追加され、
  `ValidationException` の 422 フォーマット統一が一行で完了するようになった。

---

## 結論

`PaginationQueryParser.parse()` は `Depends()` パターンが使えないシナリオ
（例: ミドルウェアや `WebSocket` ハンドラー内）で有効な代替手段。
`default_limit` / `max_limit` のカスタマイズと `ValidationException` の自動 422 変換が
`ErrorHandlerMiddleware.install()` との組み合わせで自然に機能する。
