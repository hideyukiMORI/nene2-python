# TODO — current

最終更新: 2026-05-22
現状: **v1.8.67 安定版 / フィールドトライアルループ継続中（FT195 完了）**

---

## 状態サマリー

v1.8.67 完了済み。FT195（ssl — SSLContext・暗号スイート・セキュリティ評価 API）まで全 195 件を実施済み。
並行系（FT188〜192）→ ネットワーク系（FT193〜195）の縦断を完了。
リポジトリは main ブランチ 1 本・Issue/PR/ブランチ全ゼロのクリーンな状態。
フィールドトライアルループは FT196 以降も継続中。

---

## オープン PR

なし（main ブランチはクリーン）

---

## オープン Issue

なし（すべて解消済み）

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
| v1.8.67 | FT195: ssl — SSLContext・暗号スイート列挙・セキュリティ評価 API（セキュリティ診断、条件付き合格） |
| v1.8.66 | FT194: ipaddress — IPv4/IPv6 解析・CIDR 計算・SSRF 防御パターン |
| v1.8.65 | FT193: socket — TCP/UDP socketpair・DNS 解決・ソケットオプション |
| v1.8.64 | FT192: asyncio — コルーチン・タスク・Lock・Event・Semaphore・Queue・TaskGroup（診断＋ペンテスト） |
| v1.8.63 | FT191: concurrent.futures — ThreadPoolExecutor / ProcessPoolExecutor / Future |
| v1.8.62 | FT190: multiprocessing — プロセスベース並行処理・共有状態・プロセスプール |
| v1.8.61 | バックログ Issue 一括解消（CLAUDE.md ルール更新・FT サンドボックス修正・ドキュメント追記） |
| v1.8.60 | FT189: subprocess — 安全なプロセス実行・stdin/stdout 制御・ストリーミング（セキュリティ診断） |
| v1.8.59 | FT188: threading — Thread・Lock・RLock・Semaphore・Event・ThreadPoolExecutor・Queue・Timer（クラッカーペンテスト） |
| v1.8.58 | FT187: collections — Counter・defaultdict・deque・ChainMap・NamedTuple・OrderedDict |
| v1.8.57 | FT186: functools — キャッシュ・部分適用・デコレーター・比較・ディスパッチ（診断実施） |
| v1.8.56 | FT185: contextlib — コンテキストマネージャー・リソース管理・エラー抑制 |
| v1.8.55 | FT184: urllib.request — URL フェッチ・Basic 認証・SSRF 防御（クラッカーペンテスト実施） |
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

**実施済み**: FT1〜FT195（全 195 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT196 を開始（196 % 3 = 1 → セキュリティ診断なし、196 % 4 = 0 → **クラッカーペンテストあり**）
- テーマ候補: `http.client`（低レベル HTTP クライアント）または `select` / `selectors`（I/O 多重化）

---

## 明日以降の優先タスク

| 優先度 | タスク | 種別 | 備考 |
|---|---|---|---|
| 高 | FT196 実施（クラッカーペンテストあり） | FT | テーマ: `http.client` or `select`/`selectors` |
| 中 | 並行系 how-to ガイド作成 | docs | FT188〜192 の知見（threading / asyncio / concurrent.futures）を 1 本にまとめる |
| 中 | PyPI 公開フロー検証（Field Trial 7） | FT | `uv publish` ワークフロー・バージョン管理・twine 代替 |
| 低 | PostgreSQL / MySQL 実 DB 統合テスト | infra | CI に Docker service ジョブを追加検討 |
| 低 | PyJWT 推移的 CVE（PYSEC-2025-183） | 保留 | mcp 側の修正を待ち。文書化済み |

---

## 改善検討事項

| 課題 | 優先度 | 備考 |
|---|---|---|
| 並行系 how-to（AsyncUseCase / threading / multiprocessing 比較） | 中 | FT188〜192 の知見を 1 本 how-to にまとめる |
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | mcp 側の修正を待ち。文書化済み |
