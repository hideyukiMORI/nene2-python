# FT66: AppSettings 実運用検証

**日付**: 2026-05-20  
**テーマ**: 型付き設定オブジェクト (`AppSettings`) の実運用確認  
**バージョン**: v1.8.17  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft66-app-settings/`

---

## 概要

`nene2.config.AppSettings` を直接インスタンス化し、環境変数によるオーバーライド・
バリデーション・`db_url` プロパティ・`SecretStr` の動作を検証した。

---

## 実装内容

- `AppSettings()`: デフォルト値確認
- `monkeypatch.setenv()`: 環境変数でのオーバーライド
- 不正値（`APP_ENV=staging`、`LOG_LEVEL=VERBOSE`）でのバリデーション確認
- `db_url` プロパティで SQLAlchemy URL 生成を確認
- `CORS_ORIGINS` の JSON リスト形式パース確認

---

## テスト結果

**10/10 passed**

---

## Friction Points

### FP-1 (軽微): `str(SecretStr(""))` が `""` を返す

**発生箇所**: `assert str(settings.db_password) != ""` テストが失敗

**症状**: 空の `SecretStr("")` を `str()` に渡すと `""` が返る（マスクされない）。
非空 `SecretStr("secret")` は `**********` が返る。

**原因**: Pydantic の設計上の挙動で、空文字列は空文字列のまま。
`repr()` では `SecretStr('')` と表示される。

**対応**: テストを `get_secret_value() == ""` で修正。フレームワーク側は変更不要。

---

## 結論

`AppSettings` は実運用で問題なく使用できる。
環境変数からの自動パース（bool・int・list[str] の JSON 形式）が便利。
