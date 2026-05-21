# TODO — current

最終更新: 2026-05-21
現状: **v1.8.54 安定版 / フィールドトライアルループ継続中（FT183 完了）**

---

## 状態サマリー

v1.8.54 完了済み。FT183（smtplib / SMTP 送信・STARTTLS・ヘッダーインジェクション防御）を含む FT183 件を実施済み。
フィールドトライアルループは FT184 以降も継続中。

---

## オープン PR

なし（現在 main ブランチはクリーン）

---

## オープン Issue（優先度順）

| Issue | 内容 | 優先度 |
|---|---|---|
| [#514](https://github.com/hideyukiMORI/nene2-python/issues/514) | [FT183] SmtpConfig.password を SecretStr に変更 | 低 |
| [#513](https://github.com/hideyukiMORI/nene2-python/issues/513) | [FT183] /send・/check-server の SSRF 対策（Private IP ブロック） | 中 |
| [#511](https://github.com/hideyukiMORI/nene2-python/issues/511) | [FT182] parseaddr() の寛容な挙動を How-to ドキュメントに記載 | 低 |
| [#510](https://github.com/hideyukiMORI/nene2-python/issues/510) | [FT182] CLAUDE.md に create_app() はファイル末尾に定義するルールを追記 | 中 |
| [#507](https://github.com/hideyukiMORI/nene2-python/issues/507) | [FT180] build_xml() の子タグ名にも NCName バリデーションを追加 | 低 |
| [#506](https://github.com/hideyukiMORI/nene2-python/issues/506) | [FT180] defusedxml を XML 処理の必須依存として CLAUDE.md に追記 | 中 |
| [#501](https://github.com/hideyukiMORI/nene2-python/issues/501) | [FT177] FastAPI アプリファクトリで APIRouter パターンを標準化 | 中 |
| [#500](https://github.com/hideyukiMORI/nene2-python/issues/500) | [FT176] parse_decimal_safe() の Unicode 全角数字受け入れ挙動を文書化 | 低 |
| [#499](https://github.com/hideyukiMORI/nene2-python/issues/499) | [FT176] calculate_tax/discount にビジネスロジックバリデーション追加 | 中 |

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
| v1.8.54 | FT183: smtplib — SMTP 送信・STARTTLS・ヘッダーインジェクション防御（診断実施） |
| v1.8.53 | FT182: email — MIME 構築・RFC 2047・パース・アドレス操作 |
| v1.8.52 | FT181: gzip — 圧縮・解凍・メタデータ手動解析・ビルド再現性 |
| v1.8.51 | FT180: xml — XXE/展開爆弾防御・RSS パース（診断＋ペンテスト） |
| v1.8.50 | FT179: zlib — 圧縮・解凍・展開爆弾対策・CRC32/Adler-32 |
| v1.8.49 | FT178: base64 — エンコード・URL セーフ・データ URI・HTTP Basic Auth |
| v1.8.48 | FT177: hashlib — PBKDF2 / scrypt / Blake2 キー付きハッシュ |
| v1.8.47 | FT176: decimal — 金融計算・精度制御（クラッカーペンテスト実施） |
| v1.8.46 | FT175: logging — SensitiveFilter / RequestIdAdapter |
| v1.8.45 | FT174: itertools — 安全な組み合わせ計算（セキュリティ診断実施） |
| v1.8.44 | FT173: pathlib — セキュアなファイル操作 |
| v1.8.43 | FT172: dataclasses — フリーズ・スロット・バリデーション（診断＋ペンテスト） |

---

## フィールドトライアル進捗

**実施済み**: FT1〜FT183（全 183 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT183 以降を継続（FT184 は 184 % 4 = 0 → クラッカーペンテスト対象）
- FT184 は 184 % 3 = 1 → セキュリティ診断なし、ただしペンテストあり

---

## 改善検討事項

| 課題 | 優先度 | 備考 |
|---|---|---|
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | mcp 側の修正を待ち。文書化済み |
| APIRouter パターンを FT テンプレートに反映 | 中 | Issue #501 |
| FT サマリ索引 | 完了 | `docs/field-trials/INDEX.md` 作成済み |
