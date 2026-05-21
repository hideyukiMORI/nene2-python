# FT173: pathlib モジュール

**日付**: 2026-05-21
**テーマ**: `pathlib.Path` によるパス操作・glob・stat・パストラバーサル防止
**セキュリティ診断**: なし（FT174 で実施）

---

## 概要

Python 標準ライブラリの `pathlib` モジュールを検証する。
`os.path` が提供してきた文字列ベースのパス操作を OOP スタイルで置き換え、
可読性・型安全性・クロスプラットフォーム対応を改善する。

このFTで確認する点:
- `Path` オブジェクトの基本属性（`name`, `stem`, `suffix`, `parent`, `parts`）
- パス結合（`/` 演算子、`Path / str`）の実用パターン
- `glob()` / `iterdir()` によるファイル一覧・再帰探索
- `stat()` でのファイルメタデータ取得
- `resolve()` + `relative_to()` によるパストラバーサル防止
- `tempfile` との組み合わせで安全な一時ファイル操作
- TypedDict による `dict` 戻り値の型安全化

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft173-pathlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `path_info(path_str)` | `Path` の全属性を `PathInfoDict` で返す |
| `join_paths(*parts)` | `Path / str` 演算子でパスを結合 |
| `resolve_relative(base, relative)` | トラバーサル防止つきの相対パス解決 |
| `write_text_file(path, content)` | UTF-8 テキスト書き込み、`WriteResultDict` 返却 |
| `read_text_file(path)` | UTF-8 テキスト読み込み |
| `append_line(path, line)` | 1行追記し総行数を返す |
| `ensure_directory(path)` | `mkdir(parents=True, exist_ok=True)` ラッパー |
| `list_directory(path, pattern)` | glob パターン付きディレクトリ一覧 |
| `glob_files(base, pattern)` | パストラバーサルチェック付き glob |
| `file_stat(path)` | `stat()` ラップ、不在なら `None` |
| `safe_temp_write(content)` | 一時ファイルへの書き込みと即時削除 |
| `walk_tree(base, max_depth)` | 再帰ツリー走査（最大深度制限付き） |
| `is_allowed_extension(path_str)` | 許可拡張子セットによるファイル検証 |
| `change_extension(path_str, new_ext)` | `with_suffix()` で拡張子変更 |
| `ALLOWED_EXTENSIONS` | 許可拡張子: `.txt .md .json .csv .log` |

TypedDict による型安全な戻り値:

| TypedDict | 使用関数 |
|---|---|
| `PathInfoDict` | `path_info()` |
| `WriteResultDict` | `write_text_file()` |
| `DirEntryDict` | `list_directory()` |
| `FileStatDict` | `file_stat()` |
| `TempWriteResultDict` | `safe_temp_write()` |
| `WalkEntryDict` | `walk_tree()` |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/pathlib/info` | パス属性を返す |
| POST | `/pathlib/join` | パス結合 |
| GET | `/pathlib/resolve` | パストラバーサル検出 |
| POST | `/pathlib/write` | サンドボックスへの書き込み（拡張子・トラバーサルチェック） |
| GET | `/pathlib/read` | サンドボックスからの読み込み |
| POST | `/pathlib/append` | 行追記 |
| GET | `/pathlib/list` | ファイル一覧 |
| GET | `/pathlib/glob` | glob パターン検索 |
| GET | `/pathlib/stat` | ファイル stat 情報 |
| POST | `/pathlib/temp-write` | 一時ファイル書き込み・読み返し |
| GET | `/pathlib/tree` | ディレクトリツリー走査 |
| GET | `/pathlib/extension-check` | 拡張子バリデーション |

---

## テスト結果

**34 passed**

```
test_app.py::test_path_info_absolute PASSED
test_app.py::test_path_info_with_extension PASSED
test_app.py::test_join_paths PASSED
test_app.py::test_join_paths_single PASSED
test_app.py::test_join_paths_empty PASSED
test_app.py::test_resolve_relative_safe PASSED
test_app.py::test_resolve_relative_traversal_blocked PASSED
test_app.py::test_resolve_relative_traversal_encoded PASSED
test_app.py::test_resolve_relative_absolute_path_in_relative PASSED
test_app.py::test_write_and_read PASSED
test_app.py::test_append_line PASSED
test_app.py::test_list_directory PASSED
test_app.py::test_list_directory_with_pattern PASSED
test_app.py::test_glob_files PASSED
test_app.py::test_file_stat_exists PASSED
test_app.py::test_file_stat_not_found PASSED
test_app.py::test_safe_temp_write PASSED
test_app.py::test_walk_tree PASSED
test_app.py::test_is_allowed_extension_allowed PASSED
test_app.py::test_is_allowed_extension_disallowed PASSED
test_app.py::test_change_extension PASSED
test_app.py::test_http_path_info PASSED
test_app.py::test_http_join PASSED
test_app.py::test_http_resolve_safe PASSED
test_app.py::test_http_resolve_traversal PASSED
test_app.py::test_http_write_and_read PASSED
test_app.py::test_http_write_disallowed_extension PASSED
test_app.py::test_http_write_path_traversal PASSED
test_app.py::test_http_read_not_found PASSED
test_app.py::test_http_list PASSED
test_app.py::test_http_temp_write PASSED
test_app.py::test_http_extension_check_allowed PASSED
test_app.py::test_http_extension_check_disallowed PASSED
test_app.py::test_security_headers PASSED

34 passed in 0.46s
```

---

## 摩擦ポイント

### F-1: `dict[str, object]` 戻り値が mypy で型エラーになる（深刻度: 中）

**事象**: 初期実装で `write_text_file()` などが `dict[str, object]` を返していたため、
テスト側で `result["size"] > 0` が mypy エラー（`object < int` 比較不可）になった。

**原因**: `dict[str, object]` の値型は `object` なので算術比較が型エラーになる。
CLAUDE.md で「`dict[str, Any]` 禁止・TypedDict を使え」と明示しているが、
sandbox の初期実装で見落とした。

**対応**: 全戻り値に TypedDict (`PathInfoDict`, `WriteResultDict` など6種) を定義。
mypy エラーが即時発見されたことで設計ミスを早期に修正できた。

### F-2: `Generator` 型注釈が必要な yield フィクスチャ（深刻度: 低）

**事象**: pytest フィクスチャで `yield` を使う場合、戻り値型を `Path` と書くと
mypy が `Generator` を期待するエラーを出す。

**原因**: `yield` を含む関数は `Path` ではなく `Generator[Path, None, None]` を返すジェネレーター関数として扱われる。

**対応**: `from collections.abc import Generator` をインポートし、
戻り値型を `Generator[Path, None, None]` に修正した。

---

## 観察点

### 観察1: `Path.resolve()` + `relative_to()` によるパストラバーサル完全防止

```python
def resolve_relative(base: str, relative: str) -> str | None:
    base_path = Path(base).resolve()
    target = (base_path / relative).resolve()
    try:
        target.relative_to(base_path)
        return str(target)
    except ValueError:
        return None
```

`../../etc/passwd` は `resolve()` でシンボリックリンクと `..` を展開した後、
`relative_to(base_path)` が `ValueError` を送出するため `None` を返す。
絶対パス（`/etc/passwd`）を `relative` に渡した場合も、
`(base_path / "/etc/passwd")` が `Path("/etc/passwd")` に解決されるため同様にブロックされる。

```
resolve_relative("/tmp", "../../etc/passwd") → None   ✅ ブロック
resolve_relative("/tmp", "/etc/passwd")       → None   ✅ ブロック
resolve_relative("/tmp", "safe/file.txt")     → "/tmp/safe/file.txt" ✅ 通過
```

URL エンコード (`%2e%2e%2f...`) は `Path` がリテラル文字列として扱うためブロックされず安全側に倒れる:
`Path("/tmp") / "%2e%2e%2fetc%2fpasswd"` → `/tmp/%2e%2e%2fetc%2fpasswd`（実際の `..` にならない）

### 観察2: `/` 演算子と絶対パスの組み合わせ

```python
# 直感的に思えるが、右辺が絶対パスのとき左辺が無視される
Path("/base") / "/etc/passwd"  # → PosixPath("/etc/passwd")
```

これは `os.path.join()` と同じ仕様。`resolve_relative()` が絶対パスを
`relative` に受け取ったとき `None` を返す理由がここにある。
`/` 演算子を直接使う実装では必ずこのケースを忘れる。

### 観察3: `frozenset` による許可拡張子の不変集合

```python
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".json", ".csv", ".log"})

def is_allowed_extension(path_str: str) -> bool:
    return Path(path_str).suffix.lower() in ALLOWED_EXTENSIONS
```

`frozenset` を使うことで `in` 演算子が O(1) になり、誤って要素を追加できない。
`Path(path_str).suffix` は `.py` のようにドット付きの拡張子を返す。
`.lower()` で大文字拡張子（`.TXT`、`.Txt`）もブロックできる。

### 観察4: `walk_tree()` のネストされた関数でクロージャーを活用

```python
def walk_tree(base: Path, max_depth: int = 3) -> list[WalkEntryDict]:
    results: list[WalkEntryDict] = []

    def _walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        for child in sorted(path.iterdir()):
            results.append({...})
            if child.is_dir():
                _walk(child, depth + 1)

    if base.is_dir():
        _walk(base, 1)
    return results
```

内部関数 `_walk` が外側の `results` リストと `base`, `max_depth` をクロージャーで参照している。
再帰時に `results` をパラメーターとして渡す必要がなく、関数シグネチャがシンプル。
`max_depth` で無限再帰（シンボリックリンクループ等）を防止している。

---

## nene2-python フレームワークとの統合

- `nene2.middleware` の3ミドルウェア（`ErrorHandlerMiddleware`, `SecurityHeadersMiddleware`, `RequestIdMiddleware`）を正しい順序（LIFO）で追加。`test_security_headers` が `x-request-id` と `x-content-type-options` を確認している
- サンドボックスディレクトリは `tempfile.mkdtemp()` で作成し、`lifespan` で `shutil.rmtree()` により自動クリーンアップ。テスト間の分離は `TestClient(create_app())` で別インスタンスを生成することで担保
- `WriteBody`, `AppendBody`, `JoinBody` が全フィールドに `max_length` を設定。Pydantic v2 による境界検証が機能している

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`pathlib` の基本操作（`/` 演算子でパス結合、`.name` でファイル名取得）は直感的で
公式ドキュメントを読めば理解できる。

**ドキュメント理解**: `Path / "subdir"` という演算子オーバーロードは最初は奇妙に見えるが、
一度理解すれば機械的に使える。`glob()` パターン（`*.txt`, `**/*.py`）は Unix glob の知識が
そのまま使えるため、シェルに慣れていれば問題ない。  
**事故リスク**: 中。`Path("/base") / "/absolute/path"` が左辺を無視するトラップは
初心者には気づきにくい。`resolve_relative()` という安全なラッパーを提供することで回避できる。  
**規約の使いやすさ**: TypedDict の定義が多く最初は戸惑うが、IDE 補完が効くようになるため
慣れると書きやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`os.path.join()` に慣れている人は `Path / str` を最初に使わず
`str(Path(base) / subdir)` と書きがちだが、機能的には同じなので実害はない。

**コピペ可能性**: `resolve_relative()` の実装パターン（`resolve()` + `relative_to()`）は
コピペで正しく動く設計になっている。  
**拡張時の罠**: `glob_files()` に `**` パターンを追加するとき、
サブディレクトリを含む結果が返るようになる点を知らないと予期しない動作になる可能性がある。  
**セキュリティ的な事故リスク**: 中。`resolve_relative()` を使わずに直接 `Path(base) / user_input`
とするコードを書いた場合、絶対パスインジェクションが通る。ラッパー関数を必ず経由する規約が必要。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

ファイル操作は Node.js の `fs` モジュールより Python の `pathlib` の方が直感的に感じるはず。
TypeScript の `interface` と Python の `TypedDict` の対応が理解できれば、型エラーへの対処も容易。

**エラーレスポンスの質**: 422 (拡張子不許可)、404 (ファイル不在) が明確に返るため
クライアント実装がしやすい。拡張子エラーで許可リストがレスポンスに含まれるのも親切設計。  
**Python 固有概念の学習コスト**: `frozenset` はやや Python 固有だが、
「変更不可な Set」という説明で十分理解できる。`TypedDict` は TS の `interface` と
ほぼ同じ概念なので学習コストが低い。  
**事故リスク**: 低。HTTP 境界は Pydantic で守られており、型エラーは 422 で返る。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`pathlib` の `glob()` と Django の `FileSystemStorage` / FastAPI の `UploadFile` との
組み合わせパターンが即座に想像できる。TypedDict の活用は好意的に評価されるはず。

**他フレームワークとの差異**: Django は `default_storage` で抽象化、FastAPI は raw ファイル操作が多い。
nene2-python の `resolve_relative()` パターンは明示的で理解しやすい。  
**nene2-python の薄さへの評価**: ファイル操作に ORM 的な抽象層を設けていない点は
「シンプルで良い」と評価されるだろう。`ensure_directory()` が `is_dir()` を返す
boolean 契約が明確。  
**本番投入可能性**: `safe_temp_write()` の「書いて読んで即削除」パターンは、
本番では `/tmp` のディスクフルやシンボリックリンク攻撃への対策が別途必要。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`resolve_relative()` の設計は正しい。`Path.resolve()` が symlink を展開し、
`relative_to()` が ValueError を使って範囲外を検出するパターンは慣用的で信頼できる。

**コードレビューチェックポイント**:
- [x] `resolve_relative()` をバイパスした直接の `open(filename)` がないか — `app.py` では `_safe_sandbox_path()` を経由しているため OK
- [x] `glob()` でシンボリックリンクを `..` に張ることでのトラバーサルが封じられているか — `resolve()` でシンボリックリンクを展開済みなので OK
- [ ] `walk_tree()` に `followlinks=False` 相当の保護がない — シンボリックリンクで深さが無限になりうる（`max_depth` で制限しているが symlink ループには注意）
- [ ] `append_line()` が `path.open()` を2回呼んでいる（書き込みと行数カウントで別々）— TOCTOU ではないが非効率

**チームでの安全な共有パターン**: `_safe_sandbox_path()` のようなプライベート関数で
パス解決を一元化するパターンはチーム内での標準化に適している。  
**ツール追加の必要性**: `ruff` の `PTH` ルール（pathlib 推奨）を有効にすると
`os.path` の誤用を自動検出できる。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の「パス操作は `pathlib.Path` で操作し、パストラバーサルを防ぐ」方針を
具体的なコードパターンとして実証できた FT となった。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高（`resolve_relative()` ラッパーが防衛線になっている）  
**設計上の負債・ドキュメント不足**:
- `walk_tree()` のシンボリックリンクループ対策が未実装（`max_depth` は深さで止めるが symlink ループは止められない）
- `append_line()` の「総行数を返す」仕様が実用上は不要なケースが多い。`bool` で十分かもしれない
- TypedDict 6種の定義が `demos.py` のモジュールサイズを増やしているが、300行制限内（225行）なので許容範囲

**Follow-up Issue 候補**: `walk_tree()` に `followlinks=False` 相当の symlink ループ検出を追加する Issue を検討

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `walk_tree()` にシンボリックリンクループ検出（訪問済みパスの set で管理）を追加 | feat |
| 低 | `ruff PTH` ルールを有効化して `os.path` 誤用を静的検出 | chore |
| 低 | `append_line()` の戻り値を `int`（行数）から `int`（追記後行数）に統一する命名改善 | docs |

---

## まとめ

FT173 では `pathlib.Path` の主要機能を一通り実装し、
パストラバーサル防止の標準パターン（`resolve()` + `relative_to()`）を実証した。
TypedDict による `dict` 戻り値の型安全化は mypy が即時エラーを発見する仕組みとして機能した。
`/` 演算子に絶対パスを渡すと左辺が無視される Python 仕様トラップは、
`resolve_relative()` のような安全なラッパーで封じることが重要と確認できた。

次の FT174 は 174 % 3 = 0 → セキュリティ診断が必要。
