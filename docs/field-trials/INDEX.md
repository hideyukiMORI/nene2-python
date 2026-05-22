# Field Trial INDEX

フィールドトライアル一覧。テーマ・カテゴリ・診断種別から検索する用途を想定。

**凡例**:
- 🔒 セキュリティ診断実施（FT番号 % 3 = 0）
- 🔍 クラッカーペンテスト実施（FT172, 176, 180…）
- 列 "Follow-up" に関連 GitHub Issue 番号を記載

---

## カテゴリ1: 初期統合検証 (FT1〜FT18)

| FT# | テーマ | 診断 | Follow-up |
|-----|--------|------|-----------|
| [FT1](2026-05-field-trial-1.md) | lunchlog — git+ インストール・新規プロジェクト構築 | | |
| [FT2](2026-05-field-trial-2.md) | bookshelf — SQLite 永続化リポジトリ DX | | |
| [FT3](2026-05-field-trial-3.md) | tasklist — Bearer Token 認証 + MCP サーバー | 🔒 | |
| [FT4](2026-05-field-trial-4.md) | snippets — SQLite 共有 MCP・ApiKey 認証・CORS | | |
| [FT5](2026-05-field-trial-5.md) | wallet — transactional() DX | | |
| [FT6](2026-05-field-trial-6.md) | weather — AsyncUseCaseProtocol DX | 🔒 | |
| [FT7](2026-05-field-trial-7.md) | bookmark — PyPI publish フロー | | |
| [FT8](2026-05-field-trial-8.md) | blog — 親子リソース (Nested REST) + datetime | | |
| [FT9](2026-05-field-trial-9.md) | recipe — HttpxMcpClient + streamable-http | 🔒 | |
| [FT10](2026-05-field-trial-10.md) | inventory — MySQL アダプター | | |
| [FT11](2026-05-field-trial-11.md) | journal — BearerTokenMiddleware + HttpxMcpClient | | |
| [FT12](2026-05-field-trial-12.md) | ThrottleMiddleware + RequestSizeLimitMiddleware | 🔒 | |
| [FT13](2026-05-field-trial-13.md) | ValidationException 実運用 | | |
| [FT14](2026-05-field-trial-14.md) | AsyncUseCaseProtocol 実運用 | | |
| [FT15](2026-05-field-trial-15.md) | SecurityHeadersMiddleware 実運用 | 🔒 | |
| [FT16](2026-05-field-trial-16.md) | transactional(callback) パターン | | |
| [FT17](2026-05-field-trial-17.md) | 複数ドメイン連携 | | |
| [FT18](2026-05-field-trial-18.md) | RequestLoggingMiddleware 実運用 | 🔒 | |

---

## カテゴリ2: フレームワーク実運用検証 (FT19〜FT80)

| FT# | テーマ | 診断 | Follow-up |
|-----|--------|------|-----------|
| [FT19](2026-05-field-trial-19.md) | problem_details_response() RFC 9457 | | |
| [FT20](2026-05-field-trial-20.md) | ThrottleMiddleware 実運用 | | |
| [FT21](2026-05-field-trial-21.md) | DomainExceptionHandler | 🔒 | |
| [FT22](2026-05-field-trial-22.md) | HealthCheckProtocol | | |
| [FT23](2026-05-field-trial-23.md) | RequestSizeLimitMiddleware | | |
| [FT24](2026-05-field-trial-24.md) | AppSettings | 🔒 | |
| [FT25](2026-05-field-trial-25.md) | RequestIdMiddleware | | |
| [FT26](2026-05-field-trial-26.md) | nene2.log structlog 統合 | | |
| [FT27](2026-05-field-trial-27.md) | ThrottleMiddleware 長時間運用 | 🔒 | |
| [FT28](2026-05-field-trial-28.md) | ThrottleMiddleware パスごとレート制限 | | |
| [FT29](2026-05-field-trial-29.md) | AsyncUseCaseProtocol 実運用 | | |
| [FT30](2026-05-field-trial-30.md) | RequestLoggingMiddleware + structlog バインディング | 🔒 | |
| [FT31](2026-05-field-trial-31.md) | DatabaseHealthCheck + ヘルスエンドポイント | | |
| [FT32](2026-05-field-trial-32.md) | SecurityHeadersMiddleware CSP カスタマイズ | | |
| [FT33](2026-05-field-trial-33.md) | ValidationException カスタムエラーコード | 🔒 | |
| [FT34](2026-05-field-trial-34.md) | DatabaseIntegrityException + SimpleDomainHandler | | |
| [FT35](2026-05-field-trial-35.md) | 混合認証（Bearer Token OR API Key） | | |
| [FT36](2026-05-field-trial-36.md) | CompositeHealthCheck | 🔒 | |
| [FT37](2026-05-field-trial-37.md) | PaginationResponse + PaginationQueryParser | | |
| [FT38](2026-05-field-trial-38.md) | SqlAlchemyTransactionManager.transactional() | | |
| [FT39](2026-05-field-trial-39.md) | RequestSizeLimitMiddleware | 🔒 | |
| [FT40](2026-05-field-trial-40.md) | 多ドメイン連携（Article + Tag） | | |
| [FT41](2026-05-field-trial-41.md) | structlog テスト統合 — configure_for_testing() + caplog | | |
| [FT42](2026-05-field-trial-42.md) | get_request_id() Depends + configure_problem_details() | 🔒 | |
| [FT43](2026-05-field-trial-43.md) | ThrottleMiddleware path_limits | | |
| [FT44](2026-05-field-trial-44.md) | PaginationQueryParser + PaginationResponse | | |
| [FT45](2026-05-field-trial-45.md) | SecurityHeadersMiddleware 詳細カスタマイズ | 🔒 | |
| [FT46](2026-05-field-trial-46.md) | DatabaseIntegrityException | | |
| [FT47](2026-05-field-trial-47.md) | SqlAlchemyTransactionManager.transactional() | | |
| [FT48](2026-05-field-trial-48.md) | CompositeHealthCheck + AsyncCompositeHealthCheck | 🔒 | |
| [FT49](2026-05-field-trial-49.md) | AppSettings | | |
| [FT50](2026-05-field-trial-50.md) | ValidationException + ValidationCode(StrEnum) | | |
| [FT51](2026-05-field-trial-51.md) | SimpleDomainHandler | 🔒 | |
| [FT52](2026-05-field-trial-52.md) | ミドルウェアスタック組み合わせ | | |
| [FT53](2026-05-field-trial-53.md) | ApiKeyAuthMiddleware | | |
| [FT54](2026-05-field-trial-54.md) | RequestSizeLimitMiddleware + path_limits | 🔒 | |
| [FT55](2026-05-field-trial-55.md) | parse_db_datetime | | |
| [FT56](2026-05-field-trial-56.md) | CompositeHealthCheck + http_status_code | | |
| [FT57](2026-05-field-trial-57.md) | AsyncCompositeHealthCheck | 🔒 | |
| [FT58](2026-05-field-trial-58.md) | ThrottleMiddleware | | |
| [FT59](2026-05-field-trial-59.md) | SecurityHeadersMiddleware | | |
| [FT60](2026-05-field-trial-60.md) | RequestIdMiddleware | 🔒 | |
| [FT61](2026-05-field-trial-61.md) | AsyncUseCaseProtocol | | |
| [FT62](2026-05-field-trial-62.md) | RequestLoggingMiddleware | | |
| [FT63](2026-05-field-trial-63.md) | configure_problem_details / PROBLEM_DETAILS_BASE_URL | 🔒 | |
| [FT64](2026-05-field-trial-64.md) | ValidationException 複数エラー | | |
| [FT65](2026-05-field-trial-65.md) | DatabaseHealthCheck | | |
| [FT66](2026-05-field-trial-66.md) | AppSettings | 🔒 | |
| [FT67](2026-05-field-trial-67.md) | SqlAlchemyTransactionManager | | |
| [FT68](2026-05-field-trial-68.md) | SimpleDomainHandler + extra_factory | | |
| [FT69](2026-05-field-trial-69.md) | PaginationQueryParser + PaginationResponse | 🔒 | |
| [FT70](2026-05-field-trial-70.md) | 複数ドメイン連携 | | |
| [FT71](2026-05-field-trial-71.md) | 完全レイヤードアーキテクチャ | | |
| [FT72](2026-05-field-trial-72.md) | DatabaseIntegrityException + write() 戻り値パターン | 🔒 | |
| [FT73](2026-05-field-trial-73.md) | PaginationQueryParser.parse() 静的メソッド | | |
| [FT74](2026-05-field-trial-74.md) | カスタム HealthCheckProtocol 実装 | | |
| [FT75](2026-05-field-trial-75.md) | ミドルウェアスタック順序依存性 | 🔒 | |
| [FT76](2026-05-field-trial-76.md) | async ハンドラー + sync SQLAlchemy イベントループブロッキング | | |
| [FT77](2026-05-field-trial-77.md) | BearerToken + ApiKey 混在認証 | | |
| [FT78](2026-05-field-trial-78.md) | ThrottleMiddleware 境界動作 | 🔒 | |
| [FT79](2026-05-field-trial-79.md) | RequestLoggingMiddleware と構造化ログ | | |
| [FT80](2026-05-field-trial-80.md) | MCP E2E — LocalMcpServer + HttpxMcpClient | | |

---

## カテゴリ3: 応用パターン検証 (FT81〜FT120)

| FT# | テーマ | 診断 | Follow-up |
|-----|--------|------|-----------|
| [FT81](2026-05-field-trial-81.md) | CORS — setup_middlewares() + CORSMiddleware | 🔒 | |
| [FT82](2026-05-field-trial-82.md) | Background Tasks — FastAPI BackgroundTasks | | |
| [FT83](2026-05-field-trial-83.md) | Depends() DI — nene2 アーキテクチャ統合 | | |
| [FT84](2026-05-field-trial-84.md) | 認証 Depends ユーティリティ — CurrentUser / require_auth | 🔒 | |
| [FT85](2026-05-field-trial-85.md) | OpenAPI スキーマ品質 — JSONResponse と response_model | | |
| [FT86](2026-05-field-trial-86.md) | Lifespan イベント — startup/shutdown | | |
| [FT87](2026-05-field-trial-87.md) | カスタムレスポンスヘッダー — X-Total-Count / X-RateLimit | 🔒 | |
| [FT88](2026-05-field-trial-88.md) | ドメインイベント — 同期イベントバスパターン | | |
| [FT89](2026-05-field-trial-89.md) | カスタムバリデーション — Pydantic + ValidationException 統合 | | |
| [FT90](2026-05-field-trial-90.md) | ファイルアップロード — multipart/form-data | 🔒 | |
| [FT91](2026-05-field-trial-91.md) | ストリーミングレスポンス — StreamingResponse + SSE | | |
| [FT92](2026-05-field-trial-92.md) | APIRouter パターン | | |
| [FT93](2026-05-field-trial-93.md) | Dependency Override パターン | 🔒 | |
| [FT94](2026-05-field-trial-94.md) | ミドルウェア順序とエラーレスポンスのヘッダー | | |
| [FT95](2026-05-field-trial-95.md) | Pydantic model_validator / field_validator + nene2 統合 | | |
| [FT96](2026-05-field-trial-96.md) | カスタム例外ハンドラーと ErrorHandlerMiddleware 共存 | 🔒 | |
| [FT97](2026-05-field-trial-97.md) | HTTP キャッシュヘッダー (ETag / Cache-Control) | | |
| [FT98](2026-05-field-trial-98.md) | PATCH / Partial Update パターン | | |
| [FT99](2026-05-field-trial-99.md) | Webhook HMAC-SHA256 署名検証 | 🔒 | |
| [FT100](2026-05-field-trial-100.md) | In-memory TTL レスポンスキャッシュ | | |
| [FT101](2026-05-field-trial-101.md) | Query Parameter Filter/Sort パターン | | |
| [FT102](2026-05-field-trial-102.md) | response_model と PaginationResponse の型整合性 | 🔒 | |
| [FT103](2026-05-field-trial-103.md) | カスタムミドルウェアで認証情報をリクエストスコープに格納 | | |
| [FT104](2026-05-field-trial-104.md) | AsyncIterator を返す UseCase + StreamingResponse | | |
| [FT105](2026-05-field-trial-105.md) | マルチテナント DB 接続 | 🔒 | |
| [FT106](2026-05-field-trial-106.md) | Idempotency Key パターン | | |
| [FT107](2026-05-field-trial-107.md) | Bulk Operations（一括作成・削除） | | |
| [FT108](2026-05-field-trial-108.md) | Pydantic computed_field と property パターン | 🔒 | |
| [FT109](2026-05-field-trial-109.md) | API バージョニング（v1/v2 ルーティング） | | |
| [FT110](2026-05-field-trial-110.md) | ソフトデリート（論理削除）パターン | | |
| [FT111](2026-05-field-trial-111.md) | カーソルベースページネーション | 🔒 | |
| [FT112](2026-05-field-trial-112.md) | バルクアップデート（PATCH /items/bulk） | | |
| [FT113](2026-05-field-trial-113.md) | Pydantic 識別共用体（Discriminated Union） | | |
| [FT114](2026-05-field-trial-114.md) | プラグインレジストリパターン | 🔒 | |
| [FT115](2026-05-field-trial-115.md) | structlog 構造化ログ + リクエストコンテキスト伝播 | | |
| [FT116](2026-05-field-trial-116.md) | @contextmanager リソース管理 + FastAPI lifespan | | |
| [FT117](2026-05-field-trial-117.md) | TypedDict + @overload による型安全な辞書操作 | 🔒 | |
| [FT118](2026-05-field-trial-118.md) | Python match 文パターンマッチング | | |
| [FT119](2026-05-field-trial-119.md) | functools.lru_cache / cache による関数レベルキャッシュ | | |
| [FT120](2026-05-field-trial-120.md) | dataclasses.field 高度な使い方 | 🔒 | |

---

## カテゴリ4: Python 標準ライブラリ検証 (FT121〜FT177)

| FT# | テーマ | 診断 | Follow-up |
|-----|--------|------|-----------|
| [FT121](2026-05-field-trial-121.md) | asyncio.gather + asyncio.TaskGroup 並列処理 | 🔒 | |
| [FT122](2026-05-field-trial-122.md) | 型安全なインプロセス イベントバス | | |
| [FT123](2026-05-field-trial-123.md) | pydantic.SecretStr + 環境変数セキュアな設定管理 | | |
| [FT124](2026-05-field-trial-124.md) | pathlib.Path + セキュアなファイル操作 | 🔒 | |
| [FT125](2026-05-field-trial-125.md) | Python 3.12 ジェネリッククラス + Pydantic Generic | | |
| [FT126](2026-05-field-trial-126.md) | StrEnum / IntEnum の高度な活用 | | |
| [FT127](2026-05-field-trial-127.md) | collections モジュールの高度な活用 | 🔒 | |
| [FT128](2026-05-field-trial-128.md) | itertools モジュール | | |
| [FT129](2026-05-field-trial-129.md) | functools モジュール | | |
| [FT130](2026-05-field-trial-130.md) | operator + heapq + bisect | 🔒 | |
| [FT131](2026-05-field-trial-131.md) | デスクリプタープロトコル | | |
| [FT132](2026-05-field-trial-132.md) | __init_subclass__ + クラスデコレーター | | |
| [FT133](2026-05-field-trial-133.md) | contextlib の高度な活用 | 🔒 | |
| [FT134](2026-05-field-trial-134.md) | typing モジュール | | |
| [FT135](2026-05-field-trial-135.md) | abc モジュール + 抽象基底クラス | | |
| [FT136](2026-05-field-trial-136.md) | re モジュール | 🔒 | |
| [FT137](2026-05-field-trial-137.md) | datetime + zoneinfo | | |
| [FT138](2026-05-field-trial-138.md) | decimal + fractions + statistics | | |
| [FT139](2026-05-field-trial-139.md) | concurrent.futures + threading | 🔒 | |
| [FT140](2026-05-field-trial-140.md) | io モジュール + バイナリ処理 | | |
| [FT141](2026-05-field-trial-141.md) | asyncio 高度機能 | | |
| [FT142](2026-05-field-trial-142.md) | uuid モジュール | 🔒 | |
| [FT143](2026-05-field-trial-143.md) | inspect モジュール | | |
| [FT144](2026-05-field-trial-144.md) | logging 高度機能 | | |
| [FT145](2026-05-field-trial-145.md) | weakref モジュール | 🔒 | |
| [FT146](2026-05-field-trial-146.md) | copy モジュール | | |
| [FT147](2026-05-field-trial-147.md) | urllib.parse モジュール | | |
| [FT148](2026-05-field-trial-148.md) | json 高度機能 | 🔒 | |
| [FT149](2026-05-field-trial-149.md) | csv モジュール | | |
| [FT150](2026-05-field-trial-150.md) | configparser モジュール | | |
| [FT151](2026-05-field-trial-151.md) | argparse モジュール | 🔒 | |
| [FT152](2026-05-field-trial-152.md) | hashlib モジュール（初回） | | |
| [FT153](2026-05-field-trial-153.md) | struct モジュール | | |
| [FT154](2026-05-field-trial-154.md) | array モジュールと memoryview | 🔒 | |
| [FT155](2026-05-field-trial-155.md) | queue モジュール | | |
| [FT156](2026-05-field-trial-156.md) | threading モジュール | | |
| [FT157](2026-05-field-trial-157.md) | multiprocessing モジュール | 🔒 | |
| [FT158](2026-05-field-trial-158.md) | tempfile モジュール | | |
| [FT159](2026-05-field-trial-159.md) | fnmatch と glob モジュール | | |
| [FT160](2026-05-field-trial-160.md) | difflib モジュール | 🔒 | |
| [FT161](2026-05-field-trial-161.md) | shutil モジュール | | |
| [FT162](2026-05-field-trial-162.md) | zipfile モジュール | | |
| [FT163](2026-05-field-trial-163.md) | sqlite3 モジュール | 🔒 | |
| [FT164](2026-05-field-trial-164.md) | contextlib モジュール（再検証） | | |
| [FT165](2026-05-field-trial-165.md) | secrets モジュール | | |
| [FT166](2026-05-field-trial-166.md) | functools モジュール（再検証） | 🔒 | |
| [FT167](2026-05-field-trial-167.md) | enum モジュール | | |
| [FT168](2026-05-field-trial-168.md) | re モジュール（再検証） | | |
| [FT169](2026-05-field-trial-169.md) | typing モジュール（再検証） | 🔒 | |
| [FT170](2026-05-field-trial-170.md) | collections モジュール（再検証） | | |
| [FT171](2026-05-field-trial-171.md) | asyncio モジュール（再検証） | | |
| [FT172](2026-05-field-trial-172.md) | dataclasses モジュール | 🔒🔍 | |
| [FT173](2026-05-field-trial-173.md) | pathlib モジュール（再検証） | | |
| [FT174](2026-05-field-trial-174.md) | itertools モジュール（再検証） | 🔒 | |
| [FT175](2026-05-field-trial-175.md) | logging モジュール — SensitiveFilter / RequestIdAdapter | | |
| [FT176](2026-05-field-trial-176.md) | decimal モジュール — 金融計算・精度制御 | 🔍 | [#499](https://github.com/hideyukiMORI/nene2-python/issues/499) [#500](https://github.com/hideyukiMORI/nene2-python/issues/500) |
| [FT177](2026-05-field-trial-177.md) | hashlib モジュール — PBKDF2 / scrypt / Blake2 | 🔒 | [#501](https://github.com/hideyukiMORI/nene2-python/issues/501) |
| [FT178](2026-05-field-trial-178.md) | base64 モジュール — エンコード・URL セーフ・データ URI | | |
| [FT179](2026-05-field-trial-179.md) | zlib モジュール — 圧縮・解凍・展開爆弾対策・チェックサム | | |
| [FT180](2026-05-field-trial-180.md) | xml モジュール — XXE/展開爆弾防御・構造検証・RSS パース | 🔒🔍 | [#506](https://github.com/hideyukiMORI/nene2-python/issues/506) [#507](https://github.com/hideyukiMORI/nene2-python/issues/507) |
| [FT181](2026-05-field-trial-181.md) | gzip モジュール — 圧縮・解凍・メタデータ・ビルド再現性 | | |
| [FT182](2026-05-field-trial-182.md) | email モジュール — MIME 構築・RFC 2047・パース・アドレス操作 | | |
| [FT183](2026-05-field-trial-183.md) | smtplib モジュール — SMTP 送信・STARTTLS・ヘッダーインジェクション防御 | 🔒 | [#513](https://github.com/hideyukiMORI/nene2-python/issues/513) [#514](https://github.com/hideyukiMORI/nene2-python/issues/514) |
| [FT184](2026-05-field-trial-184.md) | urllib.request モジュール — URL フェッチ・Basic 認証・SSRF 防御 | 🔍 | [#516](https://github.com/hideyukiMORI/nene2-python/issues/516) [#517](https://github.com/hideyukiMORI/nene2-python/issues/517) |
| [FT185](2026-05-field-trial-185.md) | contextlib モジュール — コンテキストマネージャー・リソース管理・エラー抑制 | | |
| [FT186](2026-05-field-trial-186.md) | functools モジュール — キャッシュ・部分適用・デコレーター・比較・ディスパッチ | 🔒 | [#520](https://github.com/hideyukiMORI/nene2-python/issues/520) |
| [FT187](2026-05-field-trial-187.md) | collections モジュール — Counter・defaultdict・deque・ChainMap・NamedTuple・OrderedDict | | |
| [FT188](2026-05-field-trial-188.md) | threading モジュール — Thread・Lock・RLock・Semaphore・Event・ThreadPoolExecutor・Queue・Timer | 🔍 | |
| [FT189](2026-05-field-trial-189.md) | subprocess モジュール — 安全なプロセス実行・stdin/stdout 制御・ストリーミング | 🔒 | [#524](https://github.com/hideyukiMORI/nene2-python/issues/524) |
| [FT190](2026-05-field-trial-190.md) | multiprocessing モジュール — プロセスベース並行処理・共有状態・プロセスプール | | |
| [FT191](2026-05-field-trial-191.md) | concurrent.futures モジュール — ThreadPoolExecutor / ProcessPoolExecutor / Future | | |
| [FT192](2026-05-field-trial-192.md) | asyncio モジュール — コルーチン・タスク・Lock・Event・Semaphore・Queue・TaskGroup | 🔒🔍 | |
| [FT193](2026-05-field-trial-193.md) | socket モジュール — TCP/UDP socketpair・DNS 解決・ソケットオプション | | |
| [FT194](2026-05-field-trial-194.md) | ipaddress モジュール — IPv4/IPv6 解析・CIDR 計算・SSRF 防御パターン | | |
| [FT195](2026-05-field-trial-195.md) | ssl モジュール — SSLContext・暗号スイート列挙・セキュリティ評価 API | 🔒 | |
| [FT196](2026-05-field-trial-196.md) | http.client モジュール — 低レベル HTTP クライアント・接続管理・SSRF 防御 | 🔍 | |
| [FT197](2026-05-field-trial-197.md) | urllib.parse モジュール — URL 解析・エンコード・クエリ文字列処理 | | |
| [FT198](2026-05-field-trial-198.md) | http.server モジュール — カスタム HTTP ハンドラー・インメモリサーバー | 🔒 | |
| [FT199](2026-05-field-trial-199.md) | uuid モジュール — UUID v3/v4/v5 生成・構造解析・バリデーション | | |
| [FT200](2026-05-field-trial-200.md) | base64 モジュール — Base64 エンコード・デコード・URL セーフ変換 | 🔍 | |
| [FT201](2026-05-field-trial-201.md) | hashlib モジュール — ハッシュ計算・整合性検証・弱アルゴリズム警告 | 🔒 | |
| [FT202](2026-05-field-trial-202.md) | hmac モジュール — HMAC 計算・検証・timing-safe 比較 | | |

---

## セキュリティ診断実施済み一覧（🔒）

FT3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 81, 84, 87, 90, 93, 96, 99, 102, 105, 108, 111, 114, 117, 120, 121, 124, 127, 130, 133, 136, 139, 142, 145, 148, 151, 154, 157, 160, 163, 166, 169, 172, 174, 177, 180, 183, 186, 189, 192, 195, 198, 201

合計: **67件**（202 FT 中 約 33%）

## クラッカーペンテスト実施済み一覧（🔍）

FT172, FT176, FT180, FT184, FT188, FT192, FT196, FT200

---

*最終更新: 2026-05-22 (FT202 / v1.8.79)*
