# FT231: shlex — split / quote / join（シェルインジェクション対策）

**日付**: 2026-05-29
**テーマ**: Python `shlex` モジュールのシェル構文トークン化・クォートの実装と検証
**セキュリティ診断**: 🔒 あり（231 % 3 = 0）
**クラッカーペンテスト**: なし（231 % 4 = 3）

---

## 概要

`shlex` はシェル構文のトークン化（`split`）とクォート（`quote` / `join`）を提供する。HTTP API でラップし、ユーザー入力をシェルに渡す際のインジェクション対策を検証した。**本 FT はコマンドを一切実行しない** — CLAUDE.md ポリシーどおり `subprocess(shell=True)` / `os.system` を使わず、`shlex` のトークン化とクォートのみを扱う。最大の教訓は「シェル文字列を組むなら必ず `shlex.quote`、だが本来は `subprocess` に**引数リスト**を渡して shell を介さないのが最善」。

| API | ユースケース |
|---|---|
| `shlex.split(s)` | POSIX クォート規則でトークン化（**評価・実行はしない**） |
| `shlex.quote(s)` | 危険メタ文字を含む引数をシングルクォートで無力化 |
| `shlex.join(list)` | 引数リストを各要素クォートして連結 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft231-shlex/`

| 関数 | 概要 |
|---|---|
| `split_command()` | `shlex.split`、未閉じクォートは `ValueError` → 422 |
| `quote_argument()` | `shlex.quote`、変更有無も返す |
| `join_arguments()` | `shlex.join` で安全連結 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/shlex/split` | シェル構文トークン化 |
| POST | `/shlex/quote` | 引数の安全クォート |
| POST | `/shlex/join` | 引数リストのクォート連結 |

---

## 摩擦点

### F-1: `shlex.split` は「パース」であり「実行」ではない — 誤解に注意

**観察**: `shlex.split("echo $(rm -rf /)")` は `['echo', '$(rm', '-rf', '/)']` のように**トークンに分解するだけ**で、コマンド置換 `$(...)` を評価したりコマンドを実行したりしない。これを知らないと「split は危険」と過剰に恐れたり、逆に「split したから安全」と油断したりする。

**対処**: split は安全なトークナイザとして使い、得たトークンを `subprocess.run([...], shell=False)` のように**リストで**渡す（本 FT では実行しないが原則を明記）。

### F-2: シェル文字列を組むなら `shlex.quote`、ただし shell=False が最善

**観察**: どうしてもコマンド文字列を組む場合、`shlex.quote` で各引数を包まないとインジェクションが通る。`shlex.quote("; rm -rf /")` → `'; rm -rf /'`（全体をシングルクォートで包む）。埋め込みシングルクォートも `''"'"'...'` の形で安全に処理される。

**対処**: 文字列組み立て時は必ず `quote`/`join`。だが第一選択は `subprocess([...], shell=False)` でシェルを介さないこと（CLAUDE.md `shell=True` 禁止）。

### F-3: `split` の未閉じクォートは `ValueError`

**観察**: `shlex.split("cmd 'unclosed")` は `ValueError: No closing quotation`。ユーザー入力をそのまま渡すと例外になる。

**対処**: `except ValueError` で捕捉し 422。

---

## セキュリティ診断結果

| # | 攻撃シナリオ | 結果 | 対処 |
|---|---|---|---|
| 1 | `quote` でメタ文字中和（`; rm -rf /` / `$(cat /etc/passwd)` / `` `whoami` `` / `\|` / `&&` / `$IFS$9` / 改行 / `>` / 埋め込み`'` / `&`） | **全 11 種が単一トークンに無力化**（再 split で原文字列に戻る） | `shlex.quote`（F-2） |
| 2 | `split` がコマンド置換を実行するか | **実行せず**トークン化のみ（`$(rm -rf /)` は文字列トークン） | F-1 |
| 3 | 未閉じクォート | **422**（ValueError 捕捉） | F-3 |
| 4 | `join` が注入を連結で混入させるか | **混入なし**（`x; rm -rf /` は 1 引数として保持、再 split で復元） | `shlex.join` |
| 5 | DoS: command 4,001 文字 / args 101 個 | **422**（長さ・件数制限） | 入力制限 |
| 6 | セキュリティヘッダー | 付与あり | ミドルウェア |

**総合評価: 合格**

`shlex.quote`/`join` がすべてのシェルメタ文字（`; | & $ \` > 改行` 等）を無力化し、`split` は実行せずトークン化のみを行うことを実測で確認。最重要の設計原則は「**シェルを介さない（`shell=False` + 引数リスト）**」であり、`shlex.quote` はやむを得ず文字列を組む場合の保険。

---

## テスト結果

```
7 passed in 0.82s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「コマンド文字列を安全に分解/組み立てる」流れは理解できる。`split` が実行しないことは明示されないと誤解しやすい。

**ドキュメント理解**: `quote` が全体をシングルクォートで包む様子が結果に見える。
**事故リスク（高）**: ネットのサンプルで `os.system(f"cmd {user}")` をコピペしがち。本 FT は実行しない原則を強調。
**規約の使いやすさ**: split → tokens、quote → quoted が直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

バッチや CLI ラッパーで `subprocess` を多用する層。`shell=True` + f-string が事故の温床。`shlex.join` で安全に組める。

**コピペ可能性**: `quote_argument`/`join_arguments` は流用可。
**拡張時の罠**: `subprocess(cmd, shell=True)` に戻すとインジェクション。`shlex.split` の結果をリストで渡すのが正解。
**事故リスク（高）**: shell=True 誤用。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node の `child_process.execFile`（引数配列）と `exec`（シェル文字列）の違いに対応。シェルを介さない設計の重要性が分かる。

**エラーレスポンスの質**: 未閉じクォート・超過は 422。
**Python 固有概念**: POSIX クォート規則。
**事故リスク（低）**: 実行しない設計。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

コマンドインジェクションは定番。`subprocess([...], shell=False)` が鉄則で `shlex` は補助。`shlex.quote` の埋め込みクォート処理（`''"'"'`）の正しさは安心材料。

**他フレームワークとの差異**: どの言語でも「引数配列 > シェル文字列」。
**nene2 の薄さへの評価**: 実行を含めず安全側に倒した設計が適切。
**事故リスク（低）**: 診断で全中和を確認。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `subprocess(shell=True)` / `os.system` を使っていないか（CLAUDE.md 禁止）。
- シェル文字列を組むなら `shlex.quote`/`join` を通しているか。
- `shlex.split` の結果を**リストで** subprocess に渡しているか（再度文字列化しない）。
- 未閉じクォートの例外処理・入力長制限。

**チームでの安全なパターン**: コマンド実行は「引数リスト + shell=False」を標準とし、文字列組み立てを lint で警告。
**事故リスク（低）**: 診断で全中和を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `subprocess(shell=True)`/`os.system` 不使用・Pydantic 制限・`ValidationException` 変換・`logging` 使用は完全準拠。本 FT は「セキュリティは設計の出発点」を体現。
**初心者でも安全な API 達成度**: 実行を含めず、quote/join を関数化することで shell=True 誤用の余地を排除。
**改善提案**: how-to に「コマンド実行の安全テンプレート（`subprocess.run([...], shell=False, timeout=...)` + `shlex` 補助）」を 1 本用意し、`shell=True` 禁止を実例で補強する。
