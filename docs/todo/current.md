# TODO — current

最終更新: 2026-05-21
現状: **v1.8.65 安定版 / フィールドトライアルループ継続中（FT193 完了）**

---

## 状態サマリー

v1.8.65 完了済み。FT193（socket — TCP/UDP socketpair・DNS 解決・ソケットオプション）を含む FT193 件を実施済み。
フィールドトライアルループは FT194 以降も継続中。

---

## オープン PR

なし（現在 main ブランチはクリーン）

---

## オープン Issue（優先度順）

なし（すべて解消済み）

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
| v1.8.65 | FT193: socket — TCP/UDP socketpair・DNS 解決・ソケットオプション |
| v1.8.64 | FT192: asyncio — コルーチン・タスク・Lock・Event・Semaphore・Queue・TaskGroup（診断＋ペンテスト） |
| v1.8.63 | FT191: concurrent.futures — ThreadPoolExecutor / ProcessPoolExecutor / Future |
| v1.8.62 | FT190: multiprocessing — プロセスベース並行処理・共有状態・プロセスプール |
| v1.8.61 | バックログ Issue 一括解消（CLAUDE.md ルール更新・FT サンドボックス修正・ドキュメント追記） |
| v1.8.60 | FT189: subprocess — 安全なプロセス実行・stdin/stdout 制御・ストリーミング（セキュリティ診断、Issue #524） |
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

**実施済み**: FT1〜FT193（全 193 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT194 以降を継続（FT194 は 194 % 3 = 2 → 診断なし、194 % 4 = 2 → ペンテストなし）

---

## 改善検討事項

| 課題 | 優先度 | 備考 |
|---|---|---|
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | mcp 側の修正を待ち。文書化済み |
| APIRouter パターンを FT テンプレートに反映 | 完了 | #526 で CLAUDE.md に追記済み |
| FT サマリ索引 | 完了 | `docs/field-trials/INDEX.md` 作成済み |
| stdlib 並行系知見 → AsyncUseCase how-to | 中 | FT188〜192 の知見を1本 how-to にまとめる |
