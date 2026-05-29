# TODO — current

最終更新: 2026-05-29
現状: **v1.8.156 / FT278（string）完了 / CI グリーン**

---

## 状態サマリー

FT278（string — capwords / 定数）完了。診断なし（278 % 3 = 2）・ペンテストなし（278 % 4 = 1）。
`capwords` は空白を畳む（title() の誤動作を回避）。string 定数（ascii_letters/digits/punctuation）はロケール非依存の ASCII 限定で文字種判定に適する。
集合演算で ASCII 英数字判定。homoglyph 対策（FT246）の ASCII 限定とも整合。
**サンドボックス 6 tests**、フレームワーク本体 466 tests 据え置き。フィールドトライアルループは FT279 以降も継続中。

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
| v1.8.156 | FT278: string — capwords / 定数（ASCII 文字種判定） |
| v1.8.155 | FT277: keyword — iskeyword / issoftkeyword（安全な識別子検証） |
| v1.8.154 | FT276: subprocess — 安全なコマンド実行（診断＋ペンテスト合格） |
| v1.8.153 | FT275: cmath — 複素数演算 / 極座標（isfinite ガード・real/imag 分離） |
| v1.8.152 | FT274: colorsys — RGB / HSV 変換（0-1 正規化・範囲検証） |
| v1.8.151 | FT273: marshal — 信頼できないデータに使わない（セキュリティ診断合格・json 代替） |
| v1.8.150 | FT272: tarfile — tar slip / tar bomb / symlink 対策（クラッカーペンテスト合格） |
| v1.8.149 | FT271: stat — モードビット解釈（world-writable/setuid 検出） |
| v1.8.148 | FT270: ssl — create_default_context（セキュリティ診断合格・TLS 検証既定） |
| v1.8.147 | FT269: contextvars — ContextVar（コンテキストローカル状態・Token reset） |
| v1.8.146 | FT268: lzma — compress / decompress（クラッカーペンテスト合格・解凍爆弾対策） |
| v1.8.145 | FT267: glob — パターンマッチ（セキュリティ診断合格・パストラバーサル防御） |
| v1.8.144 | FT266: types — MappingProxyType（読み取り専用ビュー・ライブビュー） |
| v1.8.143 | FT265: zoneinfo — ZoneInfo（IANA タイムゾーン変換・DST 自動） |
| v1.8.142 | FT264: ast.literal_eval — eval の安全な代替（診断＋ペンテスト合格） |
| v1.8.141 | FT263: tomllib — TOML 読み込み（読み取り専用・安全な設定パース） |
| v1.8.140 | FT262: graphlib — TopologicalSorter（トポロジカルソート・循環検出） |
| v1.8.139 | FT261: mimetypes — guess_type / アップロード検証（セキュリティ診断合格・Content-Type 非信頼） |
| v1.8.138 | FT260: zipfile — zip slip / zip bomb 対策（クラッカーペンテスト合格） |
| v1.8.137 | FT259: weakref — WeakValueDictionary（弱参照キャッシュの自動退避） |
| v1.8.136 | FT258: random — 非暗号性の実証（セキュリティ診断合格・secrets 推奨） |
| v1.8.135 | FT257: array — typecode / tobytes（typecode 許可リスト・オーバーフロー処理） |
| v1.8.134 | FT256: email.message — ヘッダーインジェクション対策（クラッカーペンテスト合格） |
| v1.8.133 | FT255: sqlite3 — パラメータ化クエリ（セキュリティ診断合格・SQL インジェクション防御） |
| v1.8.132 | FT254: queue — Queue / LifoQueue / PriorityQueue（安定化タプル） |
| v1.8.131 | FT253: copy — copy / deepcopy（浅い/深いコピーの共有参照） |
| v1.8.130 | FT252: json — loads/dumps の堅牢化（診断＋ペンテスト合格） |
| v1.8.129 | FT251: fractions — Fraction / limit_denominator（厳密有理数・用途別分母制限） |
| v1.8.128 | FT250: decimal — Decimal / quantize / 丸めモード（金額計算・文字列受け） |
| v1.8.127 | FT249: hmac — new / compare_digest（セキュリティ診断合格・署名検証） |
| v1.8.126 | FT248: string.Formatter — format string 攻撃の防御（クラッカーペンテスト合格） |
| v1.8.125 | FT247: operator — itemgetter / 演算子関数（許可リストディスパッチ） |
| v1.8.124 | FT246: unicodedata — NFKC / category（セキュリティ診断・条件付き合格・homoglyph 限界明示） |
| v1.8.123 | FT245: reprlib — Repr（多軸上限・ログ肥大化防止） |
| v1.8.122 | FT244: html.parser — HTMLParser（クラッカーペンテスト合格・script 除外） |
| v1.8.121 | FT243: uuid — uuid4 / uuid1 / uuid5（セキュリティ診断合格・予測可能性） |
| v1.8.120 | FT242: heapq — heappush / heappop / nlargest / merge（min-heap・merge ソート前提） |
| v1.8.119 | FT241: bisect — bisect_left / insort / 範囲検索（ソート前提検証・left/right） |
| v1.8.118 | FT240: 安全なデシリアライズ — pickle 不使用 / json + Pydantic 検証（診断＋ペンテスト合格） |
| v1.8.117 | FT239: statistics — mean / median / stdev / quantiles（StatisticsError 処理・点数上限） |
| v1.8.116 | FT238: calendar — monthrange / weekday / isleap（0=月曜・うるう年規則） |
| v1.8.115 | FT237: http.cookies — SimpleCookie / Morsel（セキュリティ診断合格・セキュア既定） |
| v1.8.114 | FT236: string.Template — substitute / safe_substitute（クラッカーペンテスト合格・SSTI 安全） |
| v1.8.113 | FT235: pprint — pformat / pp（width/depth 制限・JsonValue 型安全） |
| v1.8.112 | FT234: ipaddress — ip_address / ip_network / is_global（セキュリティ診断合格・IP ベース SSRF） |
| v1.8.111 | FT233: textwrap — wrap / fill / shorten / indent（width 制限・長語分割） |
| v1.8.110 | FT232: fnmatch — fnmatch / filter / translate（クラッカーペンテスト合格） |
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

**実施済み**: FT1〜FT278（全 278 件）

索引: [`docs/field-trials/INDEX.md`](../field-trials/INDEX.md)

**次のアクション**:
- FT279 を開始（279 % 3 = 0 → **セキュリティ診断あり**、279 % 4 = 3 → クラッカーペンテストなし）
- テーマ候補: `plistlib` モジュール（plist 解析の安全性・サイズ制限）

---

## 明日以降の優先タスク

| 優先度 | Issue | タスク | 種別 |
|---|---|---|---|
| 高 | — | FT279 実施（plistlib、セキュリティ診断あり） | FT |
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
