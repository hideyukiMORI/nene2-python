# FT164: contextlib モジュール

**日付**: 2026-05-21
**テーマ**: `contextlib` モジュール — `@contextmanager`、`@asynccontextmanager`、`suppress`、`redirect_stdout/stderr`、`ExitStack`、`AsyncExitStack`、`nullcontext`
**セキュリティ診断**: なし（164 % 3 = 2）

---

## 概要

Python 標準ライブラリの `contextlib` モジュールを nene2-python フレームワーク上で検証した。
`contextlib` はコンテキストマネージャーの作成・合成ユーティリティを提供し、
FastAPI の lifespan 管理・DI リソース制御・テスト補助に直結する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft164-contextlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `managed_resource(name)` | `@contextmanager` でリソースの open/close を管理 |
| `async_managed_resource(name)` | `@asynccontextmanager` の非同期版 |
| `suppress_demo(divisor)` | `suppress()` で `ZeroDivisionError` を握りつぶす |
| `capture_output_demo()` | `redirect_stdout/redirect_stderr` で出力をキャプチャ |
| `exit_stack_demo(names)` | `ExitStack` で複数リソースを動的に管理 |
| `async_exit_stack_demo(names)` | `AsyncExitStack` の非同期版 |
| `nullcontext_demo(use_real)` | `nullcontext()` で条件分岐なしにコンテキストを統一 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/contextlib/managed-resource` | `@contextmanager` デモ |
| GET | `/contextlib/suppress` | `suppress()` デモ |
| GET | `/contextlib/capture-output` | `redirect_stdout/stderr` デモ |
| POST | `/contextlib/exit-stack` | `ExitStack` デモ |
| POST | `/contextlib/async-exit-stack` | `AsyncExitStack` デモ |
| GET | `/contextlib/nullcontext` | `nullcontext()` デモ |

---

## テスト結果

**20 passed（摩擦1件あり → テスト修正で解消）**

```
20 passed in 0.31s
```

---

## 摩擦ポイント

### F-1: `dict.update()` はコピーを作るため参照テストに使えない（深刻度: 低）

**事象**: `resource_ref.update(resource)` で辞書をコピーしてから参照を確認しようとしたが、
`finally` ブロックで `resource["status"] = "closed"` に変更されても `resource_ref` は更新されない。

**原因**: `dict.update()` はキーと値のシャローコピーを行う。`str` は immutable なので
コピー後の変更は元の辞書に影響しない。

**対応**: `captured.append(resource)` でリスト内に参照を保持することで解決。
テスト内で辞書の「内側の値の変化」をテストする場合は `update()` ではなく参照を使う。
ドキュメント追記は不要（Python の基本動作）。

---

## 観察点

### 観察1: `@contextmanager` は例外でも `finally` が確実に動く

```python
@contextlib.contextmanager
def managed_resource(name: str) -> Generator[dict[str, str], None, None]:
    resource = {"name": name, "status": "open"}
    try:
        yield resource
    finally:
        resource["status"] = "closed"  # 例外時も実行される
```

`with` ブロック内で例外が発生しても `finally` が実行されるため、
リソースのクリーンアップが保証される。DB コネクション・ファイルハンドル・ロック解放に最適。

### 観察2: `@asynccontextmanager` は FastAPI lifespan と同じパターン

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup: DB 接続、キャッシュ初期化
    yield
    # shutdown: クリーンアップ
```

FastAPI の `lifespan` 引数は `@asynccontextmanager` が返す関数をそのまま受け取る。
`AsyncExitStack` と組み合わせると複数のリソースを lifespan 内で動的に管理できる。

### 観察3: `suppress()` は例外を握りつぶすのではなく「想定内の例外」を宣言する

```python
with contextlib.suppress(ZeroDivisionError):
    result = 100 // divisor
# divisor=0 でも例外が外に漏れない
```

`try/except: pass` の代替として可読性が高い。ただし `suppress` 対象外の例外は通常通り伝播する。
nene2 での使用例: Repository の「存在しないなら None を返す」パターン。

### 観察4: `redirect_stdout/redirect_stderr` でサードパーティ print 出力をキャプチャ

```python
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    third_party_function()  # print() を内部で使うライブラリ
captured = buf.getvalue()
```

ロギングモジュールに対応していないレガシーライブラリの出力をテストやログに取り込む場合に有効。
本番コードでは `logging` モジュールを使うべき（CLAUDE.md のポリシー通り）。

### 観察5: `ExitStack` で動的な複数リソース管理

```python
with contextlib.ExitStack() as stack:
    files = [stack.enter_context(open_file(name)) for name in names]
    # すべてのファイルが open
# すべてのファイルが close（LIFO 順）
```

管理するリソース数が実行時まで不定の場合に有効。
`stack.enter_context()` の戻り値は元のコンテキストマネージャーの `__enter__` 戻り値。
exit は LIFO（後入れ先出し）順で実行される。

### 観察6: `nullcontext()` で条件分岐なしにコンテキストを統一

```python
ctx = real_lock() if need_lock else contextlib.nullcontext()
with ctx:
    do_work()
```

`real_lock` を使うかどうかをフラグで切り替える際、`with` ブロック外に `if/else` を書かずに済む。
テストでモックコンテキストを渡す場合にも使える。

---

## nene2-python フレームワークとの統合

- `@asynccontextmanager` は FastAPI の `lifespan` パターンと完全に一致する
- `AsyncExitStack` を lifespan 内で使えば DB・キャッシュ・MCP クライアントを動的に管理できる
- `suppress(NotFoundException)` を Repository の `find_by_id` に使うと「None を返す」パターンが簡潔になる
- `redirect_stdout` はテストユーティリティとして有用（print デバッグのキャプチャ）
- `ExitStack` は `contextlib` を知らない経験者でも直感的に読める（`__exit__` の手動連鎖を避けられる）

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`contextlib` は Python ドキュメントで後半に出てくるモジュールで、
独学段階では「コンテキストマネージャーの作り方」を知らないことが多い。

**ドキュメント理解**: `@contextmanager` は `yield` を 1 回しか書けないというルールが直感と合わない。
nene2 ドキュメントに「DB トランザクションをコンテキストマネージャーで管理する how-to」があれば、
実用的なサンプルで理解できる。

**事故リスク**: 中。`yield` の後に複数行書けると思って `finally` を忘れるリスク。
`@contextmanager` の中で例外を再度 `raise` しないと外に伝播しないことを理解していない可能性。

**規約の使いやすさ**: `suppress()` と `nullcontext()` はサンプルを見れば機械的に書ける。
`ExitStack` は説明なしには使いにくい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`try/finally` を手で書く習慣があり、`@contextmanager` を「魔法」と感じて避けるかもしれない。
コピペ可能なサンプルがあれば使える。

**コピペ可能性**: `@contextmanager` + `try/yield/finally` の骨格が 1 箇所にあれば十分。
`ExitStack` は「なぜ使うのか」の説明がないと `try/finally` ネストで代替されてしまう。

**拡張時の罠**: `AsyncExitStack` を使わずに `async with` をネストさせてしまう可能性。
深くネストするとリソースが LIFO 順でクリーンアップされないリスクがある。

**セキュリティ的な事故リスク**: 低。`contextlib` 自体にセキュリティ的な罠はない。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `using` / Disposable 構文（TC39 Stage 3）と概念が近いため、
`with` 文のコンセプトは理解しやすい。

**エラーレスポンスの質**: `suppress()` を使う Repository 実装では 404 を返す責務が明確になる。
クライアント側には影響なし。

**Python 固有概念の学習コスト**: `yield` を使うジェネレーター関数としての `@contextmanager` は
JS との差異が大きい。「関数の途中で一時停止して戻ってくる」という説明が必要。

**事故リスク**: 低。コンセプト理解後は使いやすい。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django では `contextmanager` や `ExitStack` を明示的に使う機会が少ない（ORM・ミドルウェアが隠蔽）。
nene2-python の薄い設計では明示的に書く必要があることを歓迎するか、または冗長と感じるかが分かれる。

**他フレームワークとの差異**: Django の `@transaction.atomic` は内部で `ExitStack` を使っているが、
nene2-python では `SqlAlchemyTransactionManager` を使う必要がある。
`contextlib` を直接使う場面がどこにあるかを how-to で示す価値がある。

**nene2-python の薄さへの評価**: lifespan での `AsyncExitStack` は「明示的で追跡しやすい」と評価されやすい。

**本番投入可能性**: 問題なし。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] `@contextmanager` の中に `yield` が 1 回だけあるか（2 回以上は実行時エラー）
- [ ] `suppress()` で過剰に広い例外クラス（`Exception`）を指定していないか
- [ ] `ExitStack.enter_context()` の結果を使い忘れていないか
- [ ] `AsyncExitStack` を使うべき場面で同期 `ExitStack` を使っていないか（await を忘れる）

**チームでの安全なパターン**: `@contextmanager` のテンプレートをプロジェクトの `conftest.py` か
共通ユーティリティに置いておくと、初心者の誤実装を防げる。

**ツール追加の必要性**: `suppress(Exception)` の過剰な使用を ruff カスタムルールで検出するのは困難。
コードレビューでのチェックが主な防衛線。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 中
- `suppress()` と `nullcontext()` は初心者にも安全
- `ExitStack` / `AsyncExitStack` は概念説明なしには初心者が誤用しやすい

**設計上の負債・ドキュメント不足**:
- nene2-python の how-to に「リソースのライフサイクル管理（contextlib を使う場合）」がない
- `AsyncExitStack` を lifespan に組み込むパターンが未文書

**Follow-up Issue 候補**: `docs: contextlib を使ったリソース管理パターンの how-to 追加`

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `docs: contextlib.AsyncExitStack を lifespan に組み込む how-to 追加` | docs |

---

## まとめ

`contextlib` は nene2-python の lifespan 設計・DI リソース管理・テスト補助と直結するモジュール。
`@asynccontextmanager` が FastAPI lifespan のネイティブパターンであることを確認した。
摩擦は1件（テスト記述のミス）のみで、実装上の問題はゼロ。
`AsyncExitStack` を使った複数リソースの lifespan 管理パターンをドキュメント化することで
初心者の誤用リスクを下げられる。
