# TODO — current

最終更新: 2026-05-29
現状: **v1.8.109 / FT231（shlex）完了 / CI グリーン**

---

## 状態サマリー

FT231（shlex — split / quote / join）完了。**セキュリティ診断あり（231 % 3 = 0）合格**・ペンテストなし（231 % 4 = 3）。
コマンドは一切実行せず（subprocess shell=True / os.system 不使用）、トークン化とクォートのみ検証。
`shlex.quote`/`join` が `; | & $ \` > 改行` 等のメタ文字を全中和（11 種が単一トークンに）、`split` は実行せずトークン化のみ。第一選択は shell=False + 引数リスト。
**サンドボックス 7 tests**、フレームワーク本体 466 tests 据え置き。フィールドトライアルループは FT232 以降も継続中。

---

## オープン PR

なし（main ブランチはクリーン）

---

## オープン Issue

| # | タイトル | 優先度 | 種別 |
|---|---|---|---|
| [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | handler の response_model を統一して CLAUDE.md ポリシーに準拠 | 中 | enhancement |
| [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT ループの目的と終着点を明文化する | 中 | docs |
| [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | PyPI 公開フロー検証（uv publish ワークフロー） | 中 | enhancement |

---

## 直近の完了マイルストーン

| バージョン | 主な内容 |
|---|---|
| v1.8.109 | FT231: shlex — split / quote / join（セキュリティ診断合格・シェルインジェクション中和） |
| v1.8.108 | FT230: difflib — unified_diff / SequenceMatcher / get_close_matches（O(n^2) 入力制限） |
| v1.8.107 | FT229: html — escape / unescape（quote=True 属性コンテキスト安全） |
| v1.8.106 | FT228: urllib.parse — urlparse / urlencode / quote（診断＋ペンテスト合格・SSRF 対策） |
| v1.8.105 | FT227: shutil — copy / move / rmtree（resolve + is_relative_to 封じ込め） |
| v1.8.104 | FT226: gzip — compress / decompress / GzipFile（mtime=0・解凍上限） |
| v1.8.103 | FT225: zlib — compress / decompress / crc32（セキュリティ診断合格・解凍爆弾対策） |
| v1.8.102 | FT224: binascii — hexlify / unhexlify / crc32（クラッカーペンテスト合格） |
| v1.8.101 | FT223: base64 — b64encode / urlsafe_b64encode / b64decode（厳格デコード） |
| v1.8.100 | FT222: hashlib — sha256 / pbkdf2_hmac / blake2 / compare_digest（セキュリティ診断合格）|
| v1.8.99 | FT221: tempfile — NamedTemporaryFile / mkstemp / TemporaryDirectory（affix 検証・0o600）|
| v1.8.98 | FT220: logging — Logger / Handler / Formatter / Filter（クラッカーペンテスト合格）|
| v1.8.97 | docs: README / roadmap / reference を v1.8.96 現状に同期、starlette CVE 解消反映 |
| v1.8.96 | FT219: argparse — ArgumentParser / add_argument / parse_args / subcommands（セキュリティ診断合格）|
| v1.8.95 | FT218: configparser — read / write / sections / interpolation |
| v1.8.94 | FT217: csv — reader / writer / DictReader / DictWriter / Sniffer |
| v1.8.93 | FT216: codecs — encode / decode / lookup / IncrementalEncoder（セキュリティ診断・クラッカーペンテスト合格）|
| v1.8.92 | FT215: struct — pack / unpack / calcsize / Struct（フォーマット文字列ホワイトリスト検証・unpack 型変換）|
| v1.8.91 | FT214: io — StringIO / BytesIO / TextIOWrapper / BufferedReader |
| v1.8.90 | FT213: abc — ABC / abstractmethod / register / __subclasshook__（セキュリティ診断）|
| v1.8.89 | FT212: dataclasses — field / asdict / astuple / replace / __post_init__ |
| v1.8.88 | FT211: typing — TypedDict / Protocol / get_type_hints / Literal |
| v1.8.87 | FT210: contextlib — contextmanager / suppress / ExitStack / nullcontext |
| v1.8.86 | FT209: functools — partial / lru_cache / reduce / wraps |
| v1.8.85 | FT208: itertools — chain / islice / groupby / product / combinations（クラッカーペンテスト） |
| v1.8.84 | FT207: collections — namedtuple / defaultdict / Counter / deque（セキュリティ診断） |
| v1.8.83 | FT206: pathlib — Pure パス解析・パストラバーサル防御 |
| v1.8.82 | FT205: enum — StrEnum・IntEnum・IntFlag・Flag |
| v1.8.81 | FT204: datetime — ISO 8601 パース・タイムゾーン変換（診断＋ペンテスト） |
| v1.8.80 | FT203: secrets — セキュア乱数・トークン生成・OTP |
| v1.8.79 | #560/#561: query ヘルパー関数群・RequestScopedContext[T] |
| v1.8.78 | #559: LocalTokenIssuer / LocalTokenIssuerVerifier |
| v1.8.77 | #558: RateLimitStorageProtocol / InMemoryRateLimitStorage |
| v1.8.76 | #557: CompositeAuthMiddleware |
| v1.8.75 | #555/#556: check_not_modified / check_precondition |
| v1.8.74–66 | FT194–202 + deps: starlette 1.0.1（#611, PYSEC-2026-161） |

---

## フィールドトライアル進捗

**実施済み**: FT1〜FT231（全 231 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT232 を開始（232 % 3 = 1 → セキュリティ診断なし、232 % 4 = 0 → **クラッカーペンテストあり**）
- テーマ候補: `fnmatch` モジュール（fnmatch / filter / translate）

---

## 明日以降の優先タスク

| 優先度 | Issue | タスク | 種別 |
|---|---|---|---|
| 高 | — | FT232 実施（fnmatch、クラッカーペンテストあり） | FT |
| 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | handler の response_model 統一 | enhancement |
| 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT ループの目的・終着点を明文化 | docs |
| 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | PyPI 公開フロー検証（uv publish） | enhancement |
| 中 | — | 古い FT サンドボックスを整理（`ft-status.sh --clean`） | infra |
| 低 | — | PostgreSQL / MySQL 実 DB 統合テスト | infra |
| 低 | — | PyJWT 推移的 CVE（PYSEC-2025-183）— mcp 修正待ち | 保留 |

---

## 改善検討事項

| 課題 | 優先度 | Issue | 備考 |
|---|---|---|---|
| handler response_model 未使用 | 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | CLAUDE.md ポリシー違反 |
| FT ループ目的の明文化 | 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | フェーズ変化の記録 |
| PyPI 未公開 | 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | uv publish フロー検証が必要 |
| 古い FT サンドボックス肥大化 | 中 | — | 210+ ディレクトリ。定期クリーンアップ |
| ログ秘匿 Filter は形式依存の best-effort | 低 | — | FT220 D3。主防御は `SecretStr`。how-to に「秘匿は多層防御の保険」を明記予定 |
| http.server Content-Length 上限なし | 低 | — | FT198 診断。デモスコープでは許容 |
| http.client DNS リバインディング未防御 | 中 | — | FT196。本番化時の追加実装 |
| parse_qs vs parse_qsl how-to | 低 | — | FT197。クエリ文字列 how-to に追記予定 |
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | — | CI Docker service ジョブ |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | — | mcp 側の修正を待ち（CI ignore 済み） |
| ~~starlette PYSEC-2026-161~~ | — | — | ✅ 解消済み（#611, starlette 1.0.1） |
| ~~roadmap / README 陳腐化~~ | — | — | ✅ 2026-05-23 docs 同期 PR で更新 |
