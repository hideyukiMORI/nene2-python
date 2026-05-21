# FT185: contextlib

**日付**: 2026-05-21
**テーマ**: contextlib モジュール — コンテキストマネージャー・リソース管理・エラー抑制
**セキュリティ診断**: なし（185 % 3 = 2）
**クラッカーペンテスト**: なし（185 % 4 = 1）

---

## 概要

Python 標準ライブラリ `contextlib` は、コンテキストマネージャーの作成・合成・利用を支援するユーティリティ集である。
`@contextmanager` デコレーター、`suppress`、`ExitStack`、`closing`、`nullcontext`、`ContextDecorator`、`chdir`（3.11+）など多岐にわたるツールを検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft185-contextlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `timer(label)` | `@contextmanager` で経過時間を計測 |
| `capture_stdout()` | `redirect_stdout` で標準出力をキャプチャ |
| `temp_attr(obj, attr, value)` | 属性を一時的に変更して復元する |
| `safe_int(value)` | `suppress(ValueError)` で変換失敗を吸収 |
| `safe_delete(dict, key)` | `suppress(KeyError)` で削除失敗を吸収 |
| `query_with_closing(host, sql)` | `closing` で接続を確実にクローズ |
| `fake_transaction(fail_on)` | ロールバック/コミットを持つトランザクション |
| `ManagedBuffer` | `ExitStack` で複数バッファのライフサイクルを管理 |
| `process_data(data, lock)` | `nullcontext` でオプションのロックを抽象化 |
| `run_and_capture(func)` | `redirect_stdout` / `redirect_stderr` で出力をキャプチャ |
| `run_pipeline(steps)` | `ExitStack` + コールバックでパイプライン管理 |
| `RetryContext` | `AbstractContextManager` の具象実装 |
| `LoggingContext` | `ContextDecorator` でデコレーターとしても使用可 |
| `batched_writer(items, batch_size)` | アイテムをバッチ分割するコンテキストマネージャー |
| `read_file_safe(path)` | `suppress(OSError)` でファイル読み込み失敗を吸収 |
| `get_current_dir_in_context(path)` | `contextlib.chdir` で一時ディレクトリ移動 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/suppress/int` | 文字列→int 変換（失敗時 null）|
| POST | `/suppress/delete` | 辞書キーを安全に削除 |
| POST | `/transaction` | フェイクトランザクション（コミット/ロールバック）|
| POST | `/pipeline` | ExitStack パイプライン実行 |
| POST | `/buffer` | ManagedBuffer で複数バッファ管理 |
| POST | `/timer` | 経過時間計測 |
| POST | `/batch` | バッチ分割 |
| POST | `/query` | closing 付きクエリ実行 |

---

## テスト結果

**50 passed**

```
50 passed in 0.31s
```

mypy --strict: Success  
ruff check: All checks passed  
pip-audit: PYSEC-2025-183 (PyJWT via mcp transitive dep — 許容済み)

---

## 摩擦ポイント

### F-1: `__exit__` の戻り値型に `bool` は不可（mypy --strict）（深刻度: 低）

**事象**: `AbstractContextManager` サブクラスの `__exit__` メソッドで戻り値型を `bool` と宣言したところ、mypy --strict が以下のエラーを出力した。

```
"bool" is invalid as return type for "__exit__" that always returns False
Use "typing.Literal[False]" as the return type or change it to "None"
```

**原因**: mypy は `__exit__` が `True` を返すと「例外を抑制する」と解釈する。`bool` 型はその可能性を示すため、常に `False` を返す実装では `Literal[False]` か `None` を使うよう要求される。

**対応**: 戻り値型を `Literal[False]` に変更（`from typing import Literal` が必要）。

```python
from typing import Literal

def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
    return False
```

---

## 観察点

### 観察1: `@contextmanager` の yield 前後でのクリーンアップ

```python
@contextlib.contextmanager
def timer(label: str) -> Generator[dict[str, float], None, None]:
    result: dict[str, float] = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start
```

`try / finally` パターンによって、`with` ブロック内で例外が発生しても `finally` が確実に実行される。yield した辞書を通じて結果を呼び出し元に渡せる点が特徴的。

### 観察2: `ExitStack.callback` による動的クリーンアップ

```python
with contextlib.ExitStack() as stack:
    for resource in resources:
        stack.callback(release_resource, resource)
        acquired.append(resource)
```

コンテキストマネージャーを持たないリソースでも `callback` で後処理を登録できる。登録は LIFO 順で実行されるため、依存関係のあるリソースも安全に解放できる。

### 観察3: `ContextDecorator` で関数デコレーターを兼ねる

```python
class LoggingContext(contextlib.ContextDecorator):
    def __enter__(self): ...
    def __exit__(self, ...): ...

ctx = LoggingContext("fn")

# コンテキストマネージャーとして
with ctx:
    do_something()

# デコレーターとして
@ctx
def my_func():
    do_something()
```

`ContextDecorator` を継承するだけで `with` と `@decorator` の両方の文脈で使用できるようになる。テスト・ロギング・タイミングの実装で有用。

### 観察4: `nullcontext` でオプションのロックを統一的に扱う

```python
def process_data(data, lock=None):
    ctx = lock if lock is not None else contextlib.nullcontext()
    with ctx:
        return sum(data)
```

呼び出し元からロックを渡せる場合と不要な場合を、`with` 文を2回書かずに統一できる。シングルスレッドのテストでは `lock=None`、マルチスレッドでは実際のロックを渡すという設計が自然に表現できる。

### 観察5: `contextlib.chdir` (Python 3.11+)

```python
original = os.getcwd()
with contextlib.chdir("/tmp"):
    # /tmp が cwd
    pass
# original に戻っている
```

`os.chdir()` を手動で `try/finally` でラップする必要がなくなる。Python 3.11 以降でのみ使用可能なため、3.10 以下をサポートする場合は自前実装が必要。

---

## Follow-up Issues

今回の FT では実装上の重大な摩擦はなかった。F-1 は mypy の型精度要求によるものであり、Python 型システムの理解向上につながる知見として記録する。

GitHub Issues: なし

---

## DX Review — 6ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FastAPI でエラーを無視したいとき `try/except pass` を書いていたが、`contextlib.suppress` を知ることで「名前のついた意図表現」に切り替えられる。

**ドキュメント理解**: `@contextmanager` の `yield` の意味（「ここで with ブロックに入る」）が直感的でない。`yield result` が値を返すだけでなくコンテキストを区切るという二重の役割は、初見では混乱しやすい。

**事故リスク**: 低 — `suppress` の乱用で重要な例外を握りつぶすリスクはあるが、デモコードでは抑制対象の例外を明示しているため、コピペしても事故にはなりにくい。

**規約の使いやすさ**: 豊富なサンプルによって「suppress で受ける」「timer で囲む」「ExitStack で登録する」という用法がパターンとして身につく。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`ExitStack` の使い所が「複数のファイルを条件によって開く」といったシナリオで真価を発揮することが理解できれば、実務でのファイル・DB 接続管理が劇的にシンプルになる。

**コピペ可能性**: `timer`・`capture_stdout`・`temp_attr` はそのままコピーして使えるユーティリティとして価値がある。

**拡張時の罠**: `ManagedBuffer.close_all()` を呼び忘れた場合、バッファはGCまで残る。`__enter__/__exit__` を実装して `with` で使えるようにするほうが安全だが、今回のデモでは意図的に省略した。

**事故リスク**: 低

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `using` 宣言（TC39 Explicit Resource Management）と概念が近いことを理解すれば、Python の `with` 文の位置付けが掴みやすい。

**エラーレスポンスの質**: `/transaction` エンドポイントがロールバックした場合でも HTTP 200 を返し、`rolled_back: true` + `error` フィールドでエラーを示す設計はフロントエンドから見て扱いやすい。

**Python 固有概念の学習コスト**: `Generator[dict[str, float], None, None]` という型注釈は TS 経験者には冗長に見える。`@contextmanager` が `Generator` を返す理由を理解するには Python のジェネレーター仕組みへの理解が必要。

**事故リスク**: 低

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `transaction.atomic()` や Flask の `g` オブジェクトと比べると、`contextlib` のアプローチはより明示的で汎用的。特に `ExitStack` は Django ORM の接続管理でも応用できる。

**他フレームワークとの差異**: `fake_transaction` パターンは Django の `TestCase.databases` によるロールバックと異なり、テスト外のユースケースにも適用できる。

**nene2 の薄さへの評価**: `contextlib` 自体は標準ライブラリであり nene2 フレームワークとの結合はない。エンドポイントの薄さ（parse → use-case → response の3ステップ）が維持されており好印象。

**事故リスク**: 低

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

コードレビュー観点で最も重要なのは「suppress の対象を絞ること」。`suppress(Exception)` のように広すぎる例外クラスを指定するコードは必ずレビューで差し戻す。

**コードレビューチェックポイント**:
- `suppress` の引数は具体的な例外クラスか（`Exception` や `BaseException` でないか）
- `@contextmanager` の `try/finally` が欠落していないか（欠落するとクリーンアップが実行されない）
- `ExitStack` は使い終わったら必ず `close()` または `with` で囲まれているか
- `__exit__` の戻り値型が `Literal[False]` か `None` になっているか（mypy で強制されるが目視でも確認）

**チームでの安全なパターン**: `LoggingContext(ContextDecorator)` のパターンは横断的関心事（ログ・計測・トレーシング）に応用しやすく、チームで共有できるユーティリティになる。

**事故リスク**: 低

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `dataclass(frozen=True, slots=True)`: `ResourceHandle`・`TransactionResult`・`PipelineResult` で適用済み ✅
- Pydantic は HTTP 境界のみ: `app.py` の Request/Response モデルのみで使用 ✅
- `create_app()` はファイル末尾: 全エンドポイント定義後に配置 ✅（FT182 の教訓適用）
- `max_length` 指定: 全文字列フィールドに設定済み ✅
- `Literal[False]` 戻り値型: F-1 で修正済み ✅

**初心者でも安全な API 達成度**: `suppress` を使う際に抑制対象の例外を明示するパターンを見せることで、「なんでも suppress しない」という習慣を自然に身につけられる構成になっている。`ExitStack` の `callback` で lambda を避けて名前付き関数 `_noop` を使ったことで、mypy の型推論問題も回避できた。

---

*バージョン: v1.8.56*
