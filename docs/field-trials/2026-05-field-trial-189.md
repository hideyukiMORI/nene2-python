# FT189: subprocess モジュール — 安全なプロセス実行・stdin/stdout 制御・ストリーミング

**日付**: 2026-05-21
**テーマ**: subprocess モジュールを使った安全なプロセス実行パターンと攻撃耐性の検証
**セキュリティ診断**: **あり**（189 % 3 = 0）
**クラッカーペンテスト**: なし（189 % 4 = 1）

---

## 概要

`subprocess` モジュールは Python から外部プロセスを起動する最も強力な機能の一つだが、
誤用すると OS コマンドインジェクション・情報漏洩・DoS を引き起こす。
このFTでは `shell=False` + コマンドアローリスト + タイムアウト + 出力サイズ制限という
4 本柱の防御パターンを FastAPI サンドボックスで実装し、
security audit でその有効性を確認する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft189-subprocess/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `run_safe()` | コマンドを allowlist 検証 + `shell=False` で安全に実行 |
| `run_with_input()` | stdin にテキストを流してコマンドを実行 |
| `run_streaming()` | `Popen` で stdout を 1 行ずつ収集 |
| `run_in_directory()` | 許可ベースディレクトリ外を `Path.resolve()` で拒否 |
| `run_with_env()` | 最小限の環境変数のみで実行（親環境を継承しない） |
| `parse_command_line()` | `shlex.split()` でコマンドライン文字列を安全にトークン分割 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/subprocess/run` | allowlist + `shell=False` で基本実行 |
| POST | `/subprocess/run-with-input` | stdin フィード実行 |
| POST | `/subprocess/stream` | Popen ストリーミング収集 |
| POST | `/subprocess/run-in-dir` | cwd 指定（パストラバーサル防止） |
| POST | `/subprocess/run-with-env` | 環境変数分離実行 |
| POST | `/subprocess/parse-command` | コマンドライン文字列のトークン分割 |

---

## テスト結果

**57 passed**

```
57 passed in 0.38s
```

---

## 摩擦ポイント

### F-1: ruff S603「`subprocess` call: check for execution of untrusted input」（深刻度: 低）

**事象**: `subprocess.run([command, *args], shell=False)` に対して ruff S603 が
「untrusted input の実行をチェックせよ」という警告を出す。

**原因**: S603 は `shell=False` でも `subprocess.run()` を呼ぶと発火する。
ruff はコマンドが信頼されているかどうかをコード構造から判定できないため、
原則として全 `subprocess.run()` を警告する。

**対応**: allowlist 検証済みの呼び出し箇所に `# noqa: S603` を付与。
コメントなしで `noqa` を使うと意図が不明になるため、
関数冒頭の docstring に「allowlist 検証済み」と明記する設計とした。
`# type: ignore` と同様、`noqa` も理由を docstring や周辺コメントで補足する慣行を推奨する。

---

## 観察点

### 観察1: `shell=False` がコマンドインジェクションを防ぐ仕組み

```python
# shell=True の場合 — シェルが ; を解釈してコマンドチェーン実行
subprocess.run("echo hello; cat /etc/passwd", shell=True)  # ← 危険

# shell=False の場合 — ; はコマンドではなく echo への文字列引数
subprocess.run(["echo", "hello; cat /etc/passwd"], shell=False)
# stdout: "hello; cat /etc/passwd" — /etc/passwd は読まれない
```

`shell=False` でもコマンド名（`tokens[0]`）をアローリストで検証しなければ、
`subprocess.run(["rm", "-rf", "/"])` のような直接呼び出しは防げない。
**アローリスト + `shell=False` の組み合わせが必須**。

### 観察2: パストラバーサルは `Path.resolve()` で一貫して防ぐ

```python
def run_in_directory(command, args, cwd: Path, ...) -> RunResult:
    resolved = cwd.resolve()  # /tmp/../etc → /etc に正規化
    if not any(_is_within(resolved, allowed) for allowed in ALLOWED_BASE_DIRS):
        raise ValueError(f"Directory not allowed: {resolved}")
```

`Path("/tmp/../etc")` は `resolve()` 後に `Path("/etc")` となり、
`ALLOWED_BASE_DIRS = (Path("/tmp"), Path("/home"))` に含まれないため拒否される。
`cwd` を文字列のまま扱うと `..` のエスケープバリエーション（`%2e%2e` 等）が通り抜ける可能性がある。

### 観察3: 環境変数分離で秘密情報の子プロセス漏洩を防ぐ

```python
# NG: 親の環境をそのまま継承（SECRET_KEY が子プロセスから見える）
subprocess.run(["env"], capture_output=True, text=True)

# OK: 最小環境セットのみ渡す
safe_env = {"PATH": "/usr/bin:/bin", **extra_env}
subprocess.run(["env"], capture_output=True, text=True, env=safe_env)
```

FastAPI サーバーは `DB_PASSWORD`・`SECRET_KEY` 等を環境変数で受け取っていることが多い。
`env=None`（デフォルト）で子プロセスを起動すると、これらがすべて子プロセスに見える。

### 観察4: 出力サイズ制限で stdout バッファ DoS を防ぐ

```python
MAX_OUTPUT_BYTES = 65536  # 64 KiB

proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
stdout = proc.stdout[:MAX_OUTPUT_BYTES]  # 上限クリップ
```

`capture_output=True` は stdout を全てメモリに保持する。
`cat /dev/zero` のような無限出力コマンドは `timeout` で制御するが、
タイムアウト前に大量の stdout が蓄積する可能性もあるため、
クリップによる二重防御が望ましい。

---

## nene2-python フレームワークとの統合

- `subprocess` は CPU/I/O バウンドな外部コマンド実行に使う。
  FastAPI の非同期ループ内で直接呼ぶとブロッキングになるため、
  `asyncio.get_event_loop().run_in_executor()` 経由で呼ぶことを検討する。
- CLAUDE.md の「絶対禁止」リストに `subprocess.run(cmd, shell=True)` が明示されており、
  ruff S602/S603 と二重に強制される設計になっている。
- コマンドアローリストは `frozenset` で定義し、定数として `demos.py` 上部に配置する。
  アローリストの変更は PR レビューで明示的に確認できる。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`subprocess.run()` で外部コマンドを実行したいと考え、公式ドキュメントを参照している。

**ドキュメント理解**: 公式ドキュメントの最初の例が `shell=True` を使っているケースも多く、
「なぜ `shell=False` にするのか」の説明が不足しがち。
nene2-python の CLAUDE.md で `subprocess.run(cmd, shell=True)` が「絶対禁止」と明記されているため、
初心者が `shell=True` を選ぶ前に気づける設計になっている。  
**事故リスク**: 高。`shell=True` を「動けばいい」と選んでしまうと OS コマンドインジェクションに直結する。
ruff S602 が `shell=True` の使用でエラーを出すため、静的解析を通している限りは防止される。  
**規約の使いやすさ**: `run_safe(command, args)` という関数シグネチャは直感的で覚えやすい。
アローリストを広げるだけで機能拡張できるため、最初の壁は低い。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

スクリプトで `os.system()` や `subprocess.run(cmd, shell=True)` を使ってきた経験を持つ。

**コピペ可能性**: `run_safe()` のパターンは ALLOWED_COMMANDS を変えるだけでコピー流用できる。
ただし、アローリストを変える際に `app.py` 側の `max_length` との整合を確認する必要があり、
この確認を怠りやすい。  
**拡張時の罠**: `timeout` パラメータを削除すると無限待機になる。
`DEFAULT_TIMEOUT = 10.0` 定数は意図を伝えているが、「とりあえず大きい値に変えたい」と
`timeout=None` に設定するミスが起きやすい。mypy では `None` を `float` に渡せないため検出可能。  
**セキュリティ的な事故リスク**: 高。アローリストを `frozenset(["*"])` や `set()` にしてしまうと
全コマンドが実行可能になる。コードレビューでアローリストの内容を必ず確認するルール化を推奨。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

API クライアント側の実装者として、各エンドポイントのエラーレスポンスを評価する。

**エラーレスポンスの質**: 許可されていないコマンドへの 400 エラーは
`{"detail": "Command not allowed: 'rm'"}` として返り、クライアント側で原因を特定しやすい。
Pydantic の 422 エラー（`timeout` が範囲外など）も自動で詳細なエラー構造が返る。  
**Python 固有概念の学習コスト**: `subprocess` 自体の概念（プロセス・パイプ・PIPE・DEVNULL）は
Node.js の `child_process` と類似しており学習コストは低め。
`shlex.split()` の「クォートを正しく処理するシェル風トークナイザ」という概念は独特だが、
`parse_command_line()` として抽象化されているため直接触れる必要は少ない。  
**事故リスク**: 低。HTTP 境界は Pydantic で保護されており、不正な入力は 400/422 で返る。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

CI/CD パイプラインやビルドスクリプト連携で `subprocess` を頻繁に使う立場。

**他フレームワークとの差異**: Django の `management command` や
`os.system()` を直接呼ぶスクリプト系との比較で、
`run_safe()` のアローリスト + `shell=False` パターンは「FastAPI 境界に組み込んだ場合」の
標準的なアプローチとして評価できる。  
**nene2-python の薄さへの評価**: subprocess のラップ関数が `demos.py` 層にあり、
HTTP ハンドラー（`app.py`）はリクエスト変換のみを担う設計は明確でレビューしやすい。
`run_safe()` を UseCase 層に組み込む場合も、HTTP 非依存の関数設計になっている。  
**本番投入可能性**: 本番環境では `asyncio.get_event_loop().run_in_executor()` でスレッドプールに
オフロードすることと、コンテナ環境で実行可能なコマンドをより厳密に管理することが必要。
アローリストはハードコードではなく設定ファイルから読む設計も検討価値がある。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームでの security review を担当する立場でリスクを評価する。

**コードレビューチェックポイント**:
- [x] `shell=True` が使われていないか（ruff S602 で自動検出）
- [x] `ALLOWED_COMMANDS` が適切に絞られているか（最小権限の原則）
- [x] `timeout` が全ての `subprocess.run()` / `Popen` に設定されているか
- [x] `env=None`（デフォルト）で子プロセスを起動していないか（環境変数漏洩）
- [x] stdout のサイズが `MAX_OUTPUT_BYTES` でクリップされているか
- [x] `cwd` パスが `Path.resolve()` + ベースディレクトリ検証を経ているか

**チームでの安全な共有パターン**: `run_safe(command: str, args: list[str])` という
「コマンドと引数を分離した関数」を共通化し、直接 `subprocess.run()` を呼ぶことを禁止するルール化が効果的。
ruff S603 の `# noqa` を使う場合は PR 説明で理由を明記させる。  
**ツール追加の必要性**: `bandit` の B603/B604 ルール（現行の ruff S603 に対応）は
`subprocess` の安全でない使用を検出するためすでに有効。
ただし `noqa` の乱用が増えた場合は `ruff.toml` で S603 を `per-file-ignores` で
特定ファイルのみに絞るか、別途 `semgrep` ルールで補強することを推奨。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の設計ポリシーと FT189 の実装を照合する。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  
**設計上の負債・ドキュメント不足**:
- `run_safe()` の `noqa: S603` が何を意味するか（allowlist 検証済みだから安全）を
  CLAUDE.md の「セキュリティポリシー」セクションに補足する価値がある（優先度: 低）。
- `timeout=None` を渡した場合の挙動（無限待機）を How-to ガイドに記載する価値がある（優先度: 低）。  
**Follow-up Issue 候補**: なし（既存ポリシーの範囲内で解決済み）

---

## セキュリティ診断（FT189 % 3 = 0）

> **診断方針**: subprocess は OS コマンドインジェクションの主要な攻撃面。
> CLAUDE.md の「絶対禁止」リストに直接掲載されている機能のため、
> 防御が実際に機能しているかを重点的に確認する。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- このFTでは認証・ユーザーデータが存在しないため N/A
- **結果**: N/A

#### API2: 認証の破損 (Broken Authentication)
- 認証機能なし（sandboxのため）
- **結果**: N/A（本番組み込み時は nene2 の `ApiKeyAuthMiddleware` を使用）

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- Pydantic モデルに定義されていないフィールドを `{"command": "echo", "is_admin": true}` で送信
- Pydantic デフォルト設定で unknown フィールドは無視される
- **結果**: ✅ 不明フィールドは無視される

#### API4: 無制限リソース消費
- `args: ["x"] * 11` → Pydantic `max_length=10` で 422
- `timeout: 31.0` → Pydantic `le=30.0` で 422
- `input_text: "x" * 10001` → Pydantic `max_length=10000` で 422
- **結果**: ✅ 全て Pydantic で遮断

#### API5: 機能レベルの認可不備
- 管理者専用エンドポイントなし（sandbox なので N/A）
- **結果**: N/A

#### API6: SSRF
- このFTでは URL を扱わない（N/A）
- **結果**: N/A

#### API7: セキュリティ設定ミス
- sandbox のため SecurityHeadersMiddleware は未使用
- エラーレスポンスに内部パスは含まれない（`str(exc)` のみ返す）
- **結果**: ✅ コマンド名のみ返却、内部スタックトレース不露出

#### API8-10
- N/A（バージョニング・在庫管理・外部API消費なし）

---

### 2. インジェクション攻撃

#### コマンドインジェクション（最重要）

```bash
# テスト1: shell=True での ; インジェクション試み
run_safe("echo", ["hello; cat /etc/passwd"])
# → stdout: "hello; cat /etc/passwd"
# → /etc/passwd の内容は読まれない（shell=False のため ; が引数扱い）
# ✅ 防止

# テスト2: バッククォート展開
run_safe("echo", ["`id`"])
# → stdout: "`id`"
# → uid= は含まれない
# ✅ 防止

# テスト3: $() 展開
run_safe("echo", ["$(cat /etc/passwd)"])
# → stdout: "$(cat /etc/passwd)"
# ✅ 防止

# テスト4: コマンド名アローリスト外
run_safe("rm", ["-rf", "/"])
# → ValueError: Command not allowed: 'rm'
# ✅ 防止（アローリストで即時拒否）

# テスト5: curl による外部接続
run_safe("curl", ["http://evil.example.com"])
# → ValueError: Command not allowed: 'curl'
# ✅ 防止

# テスト6: python3 による任意コード実行
run_safe("python3", ["-c", "import os; os.system('id')"])
# → ValueError: Command not allowed: 'python3'
# ✅ 防止
```

- **結果**: ✅ 全コマンドインジェクション試みが防止される

#### SQL インジェクション
- SQL を扱わない（N/A）

#### パストラバーサル

```bash
# cwd での パストラバーサル試み
run_in_directory("ls", [], Path("/tmp/../etc"))
# Path.resolve() → /etc
# /etc は ALLOWED_BASE_DIRS に含まれない → ValueError
# ✅ 防止

run_in_directory("ls", [], Path("/"))
# /は /tmp でも /home でもない → ValueError
# ✅ 防止

run_in_directory("ls", [], Path("/etc/passwd"))
# Not a directory: /etc/passwd → ValueError
# ✅ 防止
```

- **結果**: ✅ `Path.resolve()` + ベースディレクトリ検証で防止

#### SSTI / HTTP ヘッダーインジェクション
- テンプレートエンジン・レスポンスヘッダー操作なし（N/A）

---

### 3. 認証・認可

- このFTは sandbox（認証なし）のため本格的な評価対象外
- `secrets` モジュールは使用していない（N/A）
- **結果**: N/A

---

### 4. 入力バリデーション

| 入力 | Pydantic バリデーション | 結果 |
|---|---|---|
| `"A" * 65` (command) | `max_length=64` → 422 | ✅ |
| `["x"] * 11` (args) | `max_length=10` → 422 | ✅ |
| `timeout=0.0` | `ge=0.1` → 422 | ✅ |
| `timeout=31.0` | `le=30.0` → 422 | ✅ |
| `input_text="x"*10001` | `max_length=10000` → 422 | ✅ |
| `max_lines=1001` | `le=1000` → 422 | ✅ |
| `env` × 21 個 | アプリ層で `len(body.env) > 20` → 400 | ✅ |
| Null バイト `"\x00evil"` in args | OS レベルで `OSError` → 500 相当（改善余地あり） | ⚠️ |

Null バイトを引数に含む場合、OS が `EINVAL` を返すため Python が `OSError` を送出する。
これをアプリが 500 として返す可能性があり、エラーメッセージに内部情報が含まれないよう
`try/except OSError` で 400 に変換することを推奨する（優先度: 中）。

- **結果**: ⚠️ 条件付き合格（Null バイト OSError のハンドリングが不完全）

---

### 5. 情報漏洩

- 500 時のスタックトレース: `run_safe()` は `try/except` で全例外を捕捉、
  FastAPI が HTTPException の `detail` のみを返す → 内部情報不露出
- 環境変数漏洩: `run_with_env()` で `env=safe_env` を使い親環境を継承しない設計 → ✅
- `pip-audit` スキャン: PYSEC-2025-183 (PyJWT via mcp 推移的依存) のみ、許容済み

- **結果**: ✅ 情報漏洩なし（PYSEC-2025-183 は許容）

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS
- `shlex.split()` は正規表現を使っていないため ReDoS 非対象
- アローリスト検索は `frozenset` の `in` 演算（O(1) ハッシュ）で安全
- **結果**: ✅

#### pickle / yaml インジェクション
- `subprocess` モジュールは pickle/yaml を使わない（N/A）

#### 非同期レースコンディション
- `run_safe()` はグローバル状態を変更しない（stateless 関数設計）
- リクエストごとに独立した子プロセスを起動するため競合状態なし
- **結果**: ✅

#### Pydantic 型強制攻撃

```python
{"command": "echo", "args": [], "timeout": "1e2"}
# → Pydantic v2: "1e2" は float として解釈され 100.0 → le=30.0 で 422
# ✅ 許容範囲外は拒否

{"command": "echo", "args": [], "timeout": True}
# → Pydantic v2: True → 1.0 → ge=0.1 で合格（1.0 は有効値）
# ✅ 意図しない動作なし（True→1.0 は有効なタイムアウト）
```

- **結果**: ✅

#### subprocess 固有: `shell=True` バイパス試み

ruff S602 (`subprocess-run-without-check` with `shell=True`) が CI で強制されるため、
静的解析を通過した時点で `shell=True` は使われていない。
`# noqa: S602` を使っても PR レビューで発見される。

- **結果**: ✅ 二重防御（ruff + PR レビュー）

---

### 7. 依存関係の脆弱性スキャン

```
Name  Version ID             Fix Versions
pyjwt 2.12.1  PYSEC-2025-183 (未対応)
```

- **スキャン結果**: MEDIUM: 1件（PYSEC-2025-183）
- **対応方針**: mcp 推移的依存。mcp 側の修正待ち。文書化済み。許容。

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過（N/A 除く） | - |
| コマンドインジェクション | ✅ 全通過 | shell=False + allowlist で完全防御 |
| パストラバーサル | ✅ 全通過 | Path.resolve() で ../etc 等を防止 |
| 入力バリデーション | ⚠️ 軽微指摘 | Null バイト args の OSError → 500 の改善余地 |
| 情報漏洩 | ✅ 全通過 | 環境変数分離で SECRET_KEY 漏洩なし |
| ReDoS | ✅ 全通過 | shlex/frozenset は正規表現不使用 |
| 非同期レースコンディション | ✅ 全通過 | stateless 関数設計 |
| 型強制攻撃 | ✅ 全通過 | Pydantic le=30.0 等が適切に働く |
| 依存関係 CVE | ⚠️ MEDIUM 1件 | PYSEC-2025-183 (PyJWT / 許容済み) |

**総合評価**: 条件付き合格（Null バイト OSError ハンドリングを次FTまでに改善）  
**発見した問題**: 1件（MEDIUM: Null バイトを含む引数で OSError が 500 として露出する可能性）  
**新規セキュリティ Issue**: #524

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | [FT189] subprocess の args に Null バイトが含まれる場合の OSError を 400 で返す | fix |

---

## まとめ

FT189 では `subprocess` モジュールの 6 パターン（run_safe・run_with_input・run_streaming・
run_in_directory・run_with_env・parse_command_line）を FastAPI サンドボックスで実装した。

最重要の学習は **`shell=False` + コマンドアローリストの組み合わせ**。
どちらか片方だけでは不十分で、両方が揃うことでコマンドインジェクションを完全に防げる。
セキュリティ診断では Null バイトを含む引数による OSError の露出（MEDIUM）を発見し、
Follow-up Issue #524 として記録した。

ruff S603 の `# noqa` 使用については、周辺コメントや docstring で
「allowlist 検証済みであるため安全」という意図を補足する設計を採用した。
これは `# type: ignore[code]` の慣行と並ぶ「noqa の使用には理由を添える」パターンとして
CLAUDE.md への追記価値がある。

次の FT190 は `190 % 3 = 1` でセキュリティ診断なし、`190 % 4 = 2` でペンテストなし。
