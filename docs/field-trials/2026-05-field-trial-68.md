# FT68: SimpleDomainHandler + extra_factory 実運用検証

**日付**: 2026-05-20  
**テーマ**: ドメイン例外ハンドラー (`SimpleDomainHandler`) + `extra_factory` の実運用確認  
**バージョン**: v1.8.18 → v1.8.19 (ドキュメント追加)  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft68-domain-handler/`

---

## 概要

`nene2.middleware.SimpleDomainHandler` を使って複数のドメイン例外クラスをそれぞれの
HTTP レスポンスにマッピングし、`extra_factory` による動的フィールドを検証した。

---

## 実装内容

- `ArticleNotFoundError`, `ArticleAccessDeniedError`, `ArticleTitleConflictError`: 独自例外クラス
- 各例外に `SimpleDomainHandler` + `detail_factory` + `extra_factory` を設定
- `ErrorHandlerMiddleware(domain_handlers=[...])` に渡して自動ハンドリング

---

## テスト結果

**7/7 passed** (テスト修正後)

| テスト | 結果 |
|---|---|
| `test_existing_article_returns_200` | PASSED |
| `test_not_found_returns_404_with_article_id` | PASSED |
| `test_access_denied_returns_403` | PASSED |
| `test_title_conflict_returns_409` | PASSED |
| `test_detail_factory_populates_detail_field` | PASSED |
| `test_problem_details_format_compliant` | PASSED |
| `test_successful_create_returns_201` | PASSED |

---

## Friction Points

### FP-1: `extra_factory` のフィールドがトップレベルにフラットマージされることが不明瞭

**発生箇所**: テストで `data["extra"]["article_id"]` とアクセスして `KeyError: 'extra'`

**症状**:
```python
# 期待していた構造
assert data["extra"]["article_id"] == 999  # → KeyError: 'extra'

# 実際の構造（RFC 9457 extension members = トップレベル）
assert data["article_id"] == 999  # ← 正しいアクセス方法
```

**原因**: `extra` という引数名が「ネストされた辞書」を連想させるが、
実際は RFC 9457 仕様の extension members としてトップレベルにフラットマージされる。

**修正**: `problem_details_response` と `SimpleDomainHandler` の docstring に
フラットマージである旨とRFC 9457 extension members との関係を明記 (Issue #308, v1.8.19)

---

## 結論

`SimpleDomainHandler` + `extra_factory` は実運用で問題なく使用できる。
extra フィールドのフラットマージ動作が docstring に明記され、今後は混同を防げる。
