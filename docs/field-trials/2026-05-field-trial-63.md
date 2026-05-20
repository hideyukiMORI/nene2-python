# FT63: configure_problem_details / PROBLEM_DETAILS_BASE_URL 実運用検証

**日付**: 2026-05-20  
**テーマ**: Problem Details 設定 API (`configure_problem_details`, `PROBLEM_DETAILS_BASE_URL`) の実運用確認  
**バージョン**: v1.8.15 → v1.8.16 (修正含む)  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft63-problem-details-config/`

---

## 概要

`nene2.http.configure_problem_details()` でプロジェクト全体の base_url を設定し、
RFC 9457 Problem Details レスポンスの `type` フィールドを自社 URL に変更する
パターンを検証した。

---

## 実装内容

- `configure_problem_details("https://api.example.com/errors/")`: アプリ起動時にグローバル設定
- `reset_problem_details()`: テスト間のリセット（autouse fixture）
- per-call `base_url` 引数がグローバル設定より優先されることを確認
- `ValidationException` 経由の 422 でも configured base_url が使われることを確認

---

## テスト結果

**7/7 passed** (v1.8.16 で修正後)

| テスト | 結果 |
|---|---|
| `test_default_base_url_in_type_field` | PASSED |
| `test_custom_base_url_applied_via_configure` | PASSED |
| `test_custom_base_url_affects_all_problem_details_in_app` | PASSED |
| `test_reset_problem_details_restores_default` | PASSED |
| `test_problem_details_structure_is_rfc9457_compliant` | PASSED |
| `test_validation_exception_uses_configured_base_url` | PASSED |
| `test_per_call_base_url_overrides_configured` | PASSED |

---

## Friction Points

### FP-1: `PROBLEM_DETAILS_BASE_URL` が `nene2.http` からエクスポートされていない

**発生箇所**: `test_app.py` で `from nene2.http import PROBLEM_DETAILS_BASE_URL` を試みた際

**症状**: `ImportError: cannot import name 'PROBLEM_DETAILS_BASE_URL' from 'nene2.http'`

**影響**: テストコードでデフォルト URL を文字列のハードコードを避けられない。
定数は `problem_details.py` に定義されているが `__init__.py` に含まれていなかった。

**修正**: `nene2.http.__init__` に `PROBLEM_DETAILS_BASE_URL` を追加 (Issue #296, v1.8.16)

---

## 結論

`configure_problem_details()` は実運用で問題なく使用できる。
`PROBLEM_DETAILS_BASE_URL` のエクスポート漏れが修正され、テストでの文字列ハードコードを避けられる。
