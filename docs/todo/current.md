# TODO — current

最終更新: 2026-05-21
現状: **v1.8.51 安定版 / フィールドトライアルループ継続中（FT180 完了）**

---

## 状態サマリー

v1.8.51 完了済み。FT180（xml / XXE防御・展開爆弾対策・RSS パース）を含む FT180 件を実施済み。
フィールドトライアルループは FT181 以降も継続中。

---

## オープン PR

なし（現在 main ブランチはクリーン）

---

## オープン Issue（優先度順）

| Issue | 内容 | 優先度 |
|---|---|---|
| [#507](https://github.com/hideyukiMORI/nene2-python/issues/507) | [FT180] build_xml() の子タグ名にも NCName バリデーションを追加 | 低 |
| [#506](https://github.com/hideyukiMORI/nene2-python/issues/506) | [FT180] defusedxml を XML 処理の必須依存として CLAUDE.md に追記 | 中 |
| [#501](https://github.com/hideyukiMORI/nene2-python/issues/501) | [FT177] FastAPI アプリファクトリで APIRouter パターンを標準化 | 中 |
| [#500](https://github.com/hideyukiMORI/nene2-python/issues/500) | [FT176] parse_decimal_safe() の Unicode 全角数字受け入れ挙動を文書化 | 低 |
| [#499](https://github.com/hideyukiMORI/nene2-python/issues/499) | [FT176] calculate_tax/discount にビジネスロジックバリデーション追加 | 中 |

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
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

**実施済み**: FT1〜FT180（全 180 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT181 以降を継続（FT184 は 184 % 4 = 0 → クラッカーペンテスト対象）
- FT183 は 183 % 3 = 0 → セキュリティ診断も実施

---

## 改善検討事項

| 課題 | 優先度 | 備考 |
|---|---|---|
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | mcp 側の修正を待ち。文書化済み |
| APIRouter パターンを FT テンプレートに反映 | 中 | Issue #501 |
| FT サマリ索引 | 完了 | `docs/field-trials/INDEX.md` 作成済み |
