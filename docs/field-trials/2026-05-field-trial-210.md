# FT210: contextlib モジュール — contextmanager / suppress / ExitStack / nullcontext

**日付**: 2026-05-22
**テーマ**: Python `contextlib` モジュールの contextmanager / suppress / redirect_stdout / ExitStack / nullcontext の実装と検証
**セキュリティ診断**: あり（210 % 3 = 0）
**クラッカーペンテスト**: なし（210 % 4 = 2）

---

## 概要

`contextlib` モジュールはコンテキストマネージャーの作成・合成・拡張を支援する Python 標準ライブラリ。
今 FT では以下の 5 機能を HTTP API として実装した。

| API | ユースケース |
|---|---|
| `@contextmanager` | インメモリトランザクション（yield を挟んだ setup/teardown） |
| `suppress` | 型変換失敗の安全な握りつぶし |
| `redirect_stdout` | 標準出力のバッファキャプチャ |
| `ExitStack` | 複数リソースの動的管理・LIFO クリーンアップ |
| `nullcontext` | 条件付きコンテキスト（分岐なし） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft210-contextlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `fake_transaction` | `@contextmanager` で yield を挟んで commit / rollback を制御 |
| `run_transaction` | `fake_transaction` を呼び出し、エラー注入もサポート |
| `safe_parse` | `suppress(ValueError, TypeError)` で int/float 変換を安全に試みる |
| `capture_output` | `redirect_stdout` で `print()` 出力を StringIO に取り込む |
| `manage_multiple_resources` | `ExitStack` で内部クラス `_Resource` を複数積み、LIFO 順クリーンアップを検証 |
| `compute_with_optional_context` | `nullcontext` or `fake_transaction` を三項演算子で切り替え |
| `measured_section` | `@contextmanager` でログリストを yield して start/end を自動付与 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/contextlib/transaction` | トランザクション実行（エラー注入オプション付き） |
| POST | `/contextlib/measured` | ログ収集セクション |
| POST | `/contextlib/safe-parse` | 安全な型変換（suppress） |
| POST | `/contextlib/capture` | 標準出力キャプチャ |
| POST | `/contextlib/exit-stack` | ExitStack LIFO リソース管理 |
| POST | `/contextlib/conditional` | 条件付きコンテキスト（nullcontext） |

---

## 摩擦点

### F-1: `__exit__` の戻り値型は常に `False` を返す場合 `None` が正しい

**観察**: `ExitStack` に登録する内部クラス `_Resource` の `__exit__` を `-> bool: ... return False` と書いたところ、mypy が `exit-return` エラーを報告した。

```
error: "bool" is invalid as return type for "__exit__" that always returns False.
Use "None" as the return type or change the return statement to "return False"  [exit-return]
```

**原因**: `__exit__` が `True` を返すと例外が抑制される。`bool` と宣言すると「例外を抑制する可能性がある」とみなされ、実際には `False` しか返さないコードと型が矛盾する。常に例外を伝播させる場合は `-> None` が正確な型。

**対処**: 戻り値型を `-> None` に変更し、`return False` を削除。

```python
# Before
def __exit__(self, *args: object) -> bool:
    cleanup_order.append(self.name)
    return False

# After
def __exit__(self, *args: object) -> None:
    cleanup_order.append(self.name)
```

---

### F-2: `list[str]` フィールドの要素ごとの文字列長制約が漏れやすい（セキュリティ診断で発見）

**観察**: `operations: list[str] = Field(max_length=MAX_ITEMS)` の `max_length` はリストの要素数上限であり、各文字列の長さ制約ではない。CLAUDE.md は「文字列フィールドには長さ制限を必ず設定」と規定しているが、`list[str]` の場合は内側の型注釈に `Annotated` が必要で見落としがちだった。

**修正**: `_BoundedStr = Annotated[str, Field(max_length=MAX_TEXT_LENGTH)]` という型エイリアスを定義し、全 `list[str]` フィールドで使用した。

```python
_BoundedStr = Annotated[str, Field(max_length=MAX_TEXT_LENGTH)]

class TransactionBody(BaseModel):
    operations: list[_BoundedStr] = Field(max_length=MAX_ITEMS, ...)
```

---

## テスト結果

```
18 passed in 0.43s
```

- `pytest`, `mypy --strict`, `ruff check`, `ruff format --check` すべて通過

---

## セキュリティ診断（210 % 3 = 0）

### 1. OWASP API Security Top 10 (2023)

| 項目 | 結果 | 備考 |
|---|---|---|
| BOLA/IDOR | 合格 | ユーザー固有リソースなし |
| 認証破損 | 合格 | auth 不要のデモスコープ |
| Mass Assignment | 合格 | 全フィールドを明示的に定義 |
| リソース消費 | **修正済み（F-2）** | per-item length 未設定 → `_BoundedStr` で修正 |
| SSRF | 合格 | 外部 HTTP 呼び出しなし |
| セキュリティ設定ミス | 合格 | SecurityHeadersMiddleware / ErrorHandlerMiddleware 実装済み |

### 2. インジェクション攻撃

| 項目 | 結果 | 備考 |
|---|---|---|
| コマンドインジェクション | 合格 | `exec`/`eval` なし。operations はリストに格納するのみ |
| パストラバーサル | 合格 | ファイルシステム操作なし |
| HTTP ヘッダーインジェクション | 合格 | レスポンスヘッダーにユーザー入力を含めない |

### 3. 入力バリデーション

| 項目 | 結果 | 備考 |
|---|---|---|
| 上限なし文字列 | **修正済み（F-2）** | `_BoundedStr` で対処 |
| 数値オーバーフロー | 合格 | `value` は `±10^6` に制限、`result = value * 2` 最大 `±2×10^6` |
| Null バイト | 合格 | 文字列はリスト格納または `int()`/`float()` 変換のみ、副作用なし |

### 4. 情報漏洩

| 項目 | 結果 | 備考 |
|---|---|---|
| スタックトレース公開 | 合格 | `ErrorHandlerMiddleware` が吸収 |
| ログへの機密データ | 合格 | `logging` モジュールのみ使用 |
| pip-audit CVE | 合格 | 既知 CVE なし |

### 5. Python/FastAPI 固有

| 項目 | 結果 | 備考 |
|---|---|---|
| ReDoS | 合格 | 正規表現なし |
| pickle/yaml | 合格 | 使用なし |
| 非同期レースコンディション | 合格 | 同期エンドポイント・スレッドローカルな状態のみ |
| Pydantic 型強制 | 合格 | 全フィールドに適切な型と制約 |

### 総合判定: **条件付き合格 → 同 PR 内修正で合格**

唯一の指摘（MEDIUM: per-item length 未設定）は F-2 として PR 内で修正済み。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`@contextmanager` は `yield` の位置が直感的でなく、try/finally の必要性も初見では分かりにくい。`measured_section` のサンプルは「start を append → yield → finally で end を append」という構造が明示されており、デコレータを読めば動作が追えるレベルに収まっている。

**ドキュメント理解**: `suppress` は「例外を飲み込む」という概念が掴みにくいが、`safe_parse` のように「変換を試みる、失敗したら None」というユースケースが具体的に示されていれば理解しやすい。

**事故リスク（中）**: `@contextmanager` に `try/except` を書き忘れると yield 後の cleanup が走らない可能性がある。F-1 の `__exit__` 型エラーは初心者では mypy がなければ気づけない。

**規約の使いやすさ**: `_BoundedStr` の型エイリアスパターンは `list[str]` 制約を一か所でまとめる方法として理解しやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`contextlib.suppress` はよく知らずに `try/except: pass` を書いてしまうパターンを正規化できる点で有用。コピペして `suppress(ValueError)` だけ書けば機能する明快な API。

**コピペ可能性**: `fake_transaction` のパターンはほぼそのままロールバック付きトランザクションとして流用できる。

**拡張時の罠**: `ExitStack` を使ってファイルや DB 接続を管理する場合、`stack.enter_context()` の失敗中途でも入門済みリソースは cleanup されるが、その順序について意識できていないと混乱する可能性がある。

**事故リスク（中）**: `__exit__` の戻り値型（`None` vs `bool`）は間違えやすく mypy なしでは発見困難。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `using` キーワード（Explicit Resource Management）に近い概念として `with` 文は理解しやすい。`ExitStack` は TypeScript にない動的スタック概念なので説明が必要だが、LIFO の cleanup_order テストが「どう動くか」を示す具体的な証拠として機能する。

**エラーレスポンスの質**: `ValidationException` で 422 を返すパターンが一貫しており、空リスト入力で何が起きるかテストから読み取れる。

**Python 固有概念**: `contextlib.nullcontext` は「何もしないコンテキスト」という発想が TS にはなく新鮮。三項演算子での切り替えパターンは条件分岐ゼロという点で慣れると便利。

**事故リスク（低）**: 型注釈が充実しているためエラーの種類は限定的。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`@contextmanager` の実装はシンプルで Django の `transaction.atomic()` に相当する薄いラッパーとして有用。`ExitStack` の LIFO 保証は複数 DB 接続やファイルハンドルの cleanup に応用しやすい。

**他フレームワークとの差異**: Django の `TestCase` は `setUpTestData` / `setUp` で同様の管理を行うが、`ExitStack` はより明示的でテスト外でも使いやすい。

**nene2 の薄さへの評価**: `ErrorHandlerMiddleware` がデフォルトで Problem Details を返すため、例外ハンドリングのボイラープレートが不要。標準的な FastAPI 実装より洗練されている。

**事故リスク（低）**: `__exit__` の型制約は mypy が守ってくれる。経験者なら F-1 も読んで学習できる。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`_Resource` のような内部クラスを関数内に定義する実装は局所性が高く読みやすいが、チームによっては「関数が長くなりすぎる」と判断されうる。今回の `manage_multiple_resources` は 25 行以内に収まっており許容範囲。

**コードレビューチェックポイント**:
- `list[str]` フィールドに `_BoundedStr` が使われているか（F-2 の再発防止）
- `@contextmanager` に `try/finally` があるか（リソースリークを防ぐ）
- `__exit__` の戻り値型が意図と一致しているか（`None` vs `bool`）

**チームでの安全なパターン**: `_BoundedStr` 型エイリアスの慣習はチームに広めやすい。`Annotated[str, Field(max_length=N)]` を毎回書くより可読性が高い。

**事故リスク（低）**: mypy --strict + ruff が守ってくれる。CI で全チェックを通過させる仕組みが整備されていれば安心。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: F-2 の per-item length 未設定はポリシー違反だったが、セキュリティ診断で発見・修正した。`_BoundedStr` パターンをポリシーに追記する価値がある（`list[str]` には `Annotated` が必要という注記）。

**初心者でも安全な API 達成度**: `suppress` の使い方・`ExitStack` の LIFO 保証・`nullcontext` のパターンがすべてエンドポイントとテストで実証されている。型注釈と `Field(max_length=...)` の組み合わせにより、初心者がコピペしても安全な実装になっている。

**改善提案**: CLAUDE.md の「文字列フィールドには長さ制限」のセクションに `list[Annotated[str, Field(max_length=N)]]` の例を追加すると F-2 の再発を防げる。
