# TODO — current

最終更新: 2026-05-23
現状: **v1.8.96 安定版 / FT219（argparse）完了**

---

## 状態サマリー

v1.8.96 完了済み。FT219（argparse — ArgumentParser / add_argument / parse_args / subcommands）完了。
セキュリティ診断あり（219 % 3 = 0）、クラッカーペンテストなし（219 % 4 = 3）。
`_SilentParser` で `sys.exit()` を `ValueError` に変換、`NoReturn` 型注釈で mypy strict 通過。セキュリティ診断 11 件全合格。フィールドトライアルループは FT220 以降も継続中。

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
| v1.8.96 | FT219: argparse — ArgumentParser / add_argument / parse_args / subcommands（セキュリティ診断合格）|
| v1.8.95 | FT218: configparser — read / write / sections / interpolation |
| v1.8.94 | FT217: csv — reader / writer / DictReader / DictWriter / Sniffer |
| v1.8.93 | FT216: codecs — encode / decode / lookup / IncrementalEncoder（セキュリティ診断・クラッカーペンテスト合格）|
| v1.8.92 | FT215: struct — pack / unpack / calcsize / Struct（フォーマット文字列ホワイトリスト検証・unpack 型変換）|
| v1.8.91 | FT214: io — StringIO / BytesIO / TextIOWrapper / BufferedReader（tell() タイミング依存性・TextIOWrapper write_through=True）|
| v1.8.90 | FT213: abc — ABC / abstractmethod / register / __subclasshook__（セキュリティ診断: Infinity/NaN DoS 修正・__subclasshook__ mypy 回避策）|
| v1.8.89 | FT212: dataclasses — field / asdict / astuple / replace / __post_init__（Infinity/NaN 500 DoS 発見・修正）|
| v1.8.88 | FT211: typing — TypedDict / Protocol / get_type_hints / Literal（isinstance 後の型絞り込み・Literal+Pydantic で type:ignore 排除）|
| v1.8.87 | FT210: contextlib — contextmanager / suppress / ExitStack / nullcontext（__exit__ None 型・list[str] per-item length 制約）|
| v1.8.86 | FT209: functools — partial / lru_cache / reduce / wraps（@wraps ANN401 回避・Python 3.14 type: ignore 不要化） |
| v1.8.85 | FT208: itertools — chain / islice / groupby / product / combinations（クラッカーペンテスト: 堅牢） |
| v1.8.84 | FT207: collections — namedtuple / defaultdict / Counter / deque（セキュリティ診断合格） |
| v1.8.83 | FT206: pathlib — Pure パス解析・パストラバーサル防御（絶対パス注入検出） |
| v1.8.82 | FT205: enum — StrEnum・IntEnum・IntFlag・Flag（Python 3.11+ Flag iteration 変更点） |
| v1.8.81 | FT204: datetime — ISO 8601 パース・タイムゾーン変換・日時演算（セキュリティ診断・クラッカーペンテスト、ruff DTZ ルール追加） |
| v1.8.80 | FT203: secrets — セキュア乱数・トークン生成・OTP |
| v1.8.79 | #560/#561: query ヘルパー関数群・RequestScopedContext[T] |
| v1.8.78 | #559: LocalTokenIssuer / LocalTokenIssuerVerifier — 開発用 HMAC 署名トークン |
| v1.8.77 | #558: RateLimitStorageProtocol / InMemoryRateLimitStorage |
| v1.8.76 | #557: CompositeAuthMiddleware — パスプレフィックスベース認証方式切り替え |
| v1.8.75 | #555/#556: check_not_modified / check_precondition |
| v1.8.74 | FT202: hmac — HMAC 計算・検証・timing-safe 比較 |
| v1.8.73 | FT201: hashlib — ハッシュ計算・整合性検証・弱アルゴリズム警告（セキュリティ診断） |
| v1.8.72 | FT200: base64 — Base64 エンコード・デコード・URL セーフ変換（クラッカーペンテスト） |
| v1.8.71 | FT199: uuid — UUID v3/v4/v5 生成・構造解析・バリデーション |
| v1.8.70 | FT198: http.server — カスタム HTTP ハンドラー・インメモリサーバー（セキュリティ診断、条件付き合格） |
| v1.8.69 | FT197: urllib.parse — URL 解析・エンコード・クエリ文字列処理 |
| v1.8.68 | FT196: http.client — 低レベル HTTP クライアント・接続管理・SSRF 防御（クラッカーペンテスト） |
| v1.8.67 | FT195: ssl — SSLContext・暗号スイート列挙・セキュリティ評価 API（セキュリティ診断） |
| v1.8.66 | FT194: ipaddress — IPv4/IPv6 解析・CIDR 計算・SSRF 防御パターン |
| v1.8.65 | FT193: socket — TCP/UDP socketpair・DNS 解決・ソケットオプション |

---

## フィールドトライアル進捗

**実施済み**: FT1〜FT219（全 219 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT220 を開始（220 % 3 = 1 → セキュリティ診断なし、220 % 4 = 0 → クラッカーペンテストあり）
- テーマ候補: `logging` モジュール（Logger / Handler / Formatter / Filter）

---

## 明日以降の優先タスク

| 優先度 | Issue | タスク | 種別 |
|---|---|---|---|
| 高 | — | FT220 実施（セキュリティ診断なし、クラッカーペンテストあり） | FT |
| 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | handler の response_model 統一 | enhancement |
| 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | FT ループの目的・終着点を明文化 | docs |
| 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | PyPI 公開フロー検証（uv publish） | enhancement |
| 中 | — | 並行系 how-to ガイド作成（FT188〜192 まとめ） | docs |
| 低 | — | PostgreSQL / MySQL 実 DB 統合テスト | infra |
| 低 | — | PyJWT 推移的 CVE（PYSEC-2025-183）— mcp 修正待ち | 保留 |

---

## 改善検討事項

| 課題 | 優先度 | Issue | 備考 |
|---|---|---|---|
| handler response_model 未使用 | 中 | [#539](https://github.com/hideyukiMORI/nene2-python/issues/539) | CLAUDE.md ポリシー違反 |
| FT ループ目的の明文化 | 中 | [#540](https://github.com/hideyukiMORI/nene2-python/issues/540) | フェーズ変化の記録 |
| PyPI 未公開 | 中 | [#541](https://github.com/hideyukiMORI/nene2-python/issues/541) | uv publish フロー検証が必要 |
| http.server Content-Length 上限なし | 低 | — | FT198 診断で発見。デモスコープでは許容。本番化時要修正 |
| http.client DNS リバインディング未防御 | 中 | — | FT196 で発見。本番化時の追加実装事項 |
| parse_qs vs parse_qsl how-to | 低 | — | FT197 で観察。クエリ文字列 how-to に追記予定 |
| 並行系 how-to（threading / asyncio 比較） | 中 | — | FT188〜192 の知見まとめ |
| PostgreSQL / MySQL 実 DB 統合テスト | 中〜高 | — | CI に Docker service ジョブを追加検討 |
| PyJWT 推移的 CVE（PYSEC-2025-183） | 低 | — | mcp 側の修正を待ち |
