# FT206: pathlib モジュール — パス操作・Pure パス解析・パストラバーサル防御

**日付**: 2026-05-22
**テーマ**: Python `pathlib` モジュールの Pure パス操作・パス解析・パストラバーサル防御パターンの実装と検証
**セキュリティ診断**: なし（206 % 3 = 2）
**クラッカーペンテスト**: なし（206 % 4 = 2）

---

## 概要

`pathlib` モジュールは Python 3.4 で追加されたパス操作ライブラリ。
`os.path.*` の手続き型 API に代わるオブジェクト指向インターフェースを提供する。
CLAUDE.md のセキュリティポリシーに「ファイルパスは `pathlib.Path` で操作し、パストラバーサルを防ぐ」と明記されており、
今 FT では特にファイルシステムにアクセスしない **Pure パス操作** と
**パストラバーサル防御パターン** を重点的に検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft206-pathlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_path_info(path_str)` | `PurePosixPath` でパスを解析して name/stem/suffix/parts を返す |
| `safe_join(base, relative)` | ベースパスに相対パスを結合し、`..` 脱出を `is_safe=False` で検出 |
| `analyze_pure_path(path_str)` | POSIX と Windows 両形式で解析（`PurePosixPath` + `PureWindowsPath`） |
| `check_traversal(base, user_input)` | パストラバーサル脅威の詳細分析（教育目的） |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/paths/info` | パス文字列を解析（`?path=...`） |
| POST | `/paths/safe-join` | 安全なパス結合・トラバーサル検出 |
| GET | `/paths/analyze` | POSIX / Windows 両形式で解析 |
| POST | `/paths/check-traversal` | パストラバーサル検査 |

---

## テスト結果

**20 passed**

```
20 passed in 0.40s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

`pathlib` の `PurePosixPath` はファイルシステムにアクセスしないため、
テスト環境を問わず安全に使用できる。
`resolve()` はファイルシステム依存のため、Pure パス操作のみで `..` を手動解決する実装を選択した。

---

## 観察点

### 観察1: `PurePath` vs `Path` の使い分け

```python
from pathlib import Path, PurePosixPath

# PurePosixPath: ファイルシステムに触れない（テスト環境でも安全）
p = PurePosixPath("/home/user/file.txt")
p.name    # → "file.txt"
p.parent  # → PurePosixPath('/home/user')

# Path: ファイルシステムに触れる（exists() / stat() / read_text() など）
p = Path("/home/user/file.txt")
p.exists()  # → ファイルシステムアクセスが発生
```

HTTP API で「パス文字列の構造解析」をするだけなら `PurePosixPath` で十分。
`Path.resolve()` はファイルシステムに依存するため、APIサンドボックスでは使えない。

### 観察2: `Path.resolve()` なしでのパストラバーサル検出

`Path.resolve()` は実際のファイルシステムの symlink まで解決するが、
HTTP API では `Path.resolve()` は使えない（存在しないパスでも呼ばれうる）。
Pure パスで `..` を手動解決してベースパスからの脱出を検出する実装が必要:

```python
parts: list[str] = []
for part in str(joined).split("/"):
    if part == "..":
        if parts:
            parts.pop()
    elif part not in ("", "."):
        parts.append(part)
resolved = "/" + "/".join(parts)
is_safe = resolved.startswith(str(base))
```

### 観察3: `.suffix` は最後の拡張子のみ、`.suffixes` は全拡張子

```python
p = PurePosixPath("archive.tar.gz")
p.suffix    # → ".gz"（最後の拡張子のみ）
p.suffixes  # → [".tar", ".gz"]（全拡張子）
p.stem      # → "archive.tar"（最後の拡張子を除いた名前）
```

`backup.tar.gz` の場合:
- `suffix` = `.gz`（圧縮形式の確認に使う）
- `suffixes` = `[".tar", ".gz"]`（アーカイブ + 圧縮の確認に使う）

### 観察4: 絶対パスのユーザー入力は `..` より危険

```python
base = PurePosixPath("/uploads")
user_input = "/etc/passwd"

# /etc/passwd は base に結合できない — PurePosixPath は絶対パスを上書きする
joined = base / "/etc/passwd"
str(joined)  # → "/etc/passwd" — base が完全に無視される！
```

`PurePosixPath("/uploads") / "/etc/passwd"` は `/etc/passwd` になる。
ユーザー入力が絶対パスの場合、`/` による結合でベースが無視されるため、
**絶対パス入力は `..` と同様に脅威として検出する必要がある**。

### 観察5: `PureWindowsPath` はクロスプラットフォームテストに使える

```python
from pathlib import PureWindowsPath

p = PureWindowsPath("C:/Users/user/file.txt")
p.name    # → "file.txt"
p.drive   # → "C:"
p.root    # → "/"
p.parts   # → ('C:\\', 'Users', 'user', 'file.txt')
```

Linux 上でも `PureWindowsPath` を使うことで Windows パスのテストが可能。
API がクロスプラットフォーム対応を謳う場合に有用。

---

## nene2-python フレームワークとの統合

- ファイルパスを受け取るフィールドには `max_length` を設定（今回は 200 文字）。
- `PurePosixPath` でパストラバーサルを検出し、Safe でない場合は `is_safe=False` を返す。
  実際のアップロードエンドポイントでは `is_safe=False` の場合に `ValidationException` を送出すること。
- `Path.resolve()` はファイルシステム依存のため HTTP テストでは使わない。
  Pure パス演算で `..` を手動解決する。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

ユーザーがアップロードしたファイルを保存するパスを動的に生成しようとしている。

**ドキュメント理解**: `Path("base") / "relative"` の `/` 演算子は直感的。
ただし **絶対パスを右辺に置くとベースが無視される** ことは公式ドキュメントをよく読まないと見落とす。  
**事故リスク**: 高。`Path(upload_dir) / user_filename` で `user_filename = "/etc/passwd"` が渡ると致命的。
CLAUDE.md の「pathlib で操作してトラバーサルを防ぐ」だけでは不十分で、ベース確認が必須。  
**規約の使いやすさ**: `safe_join()` のようなヘルパー関数として提供するのが正解。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`os.path.join()` を使ってきた経験者が `pathlib` に移行しようとしている。

**コピペ可能性**: `os.path.join()` → `Path() / ""` の置き換えは直感的。
ただし `os.path.join("/base", "/abs")` は OS 依存で挙動が変わるため注意が必要。  
**拡張時の罠**: `Path.resolve()` を使って symlink まで解決しようとすると、
テスト環境でファイルが存在しないときに予期しないパスが返る（シンボリックリンク解決）。  
**セキュリティ的な事故リスク**: 高。`../` のエスケープより絶対パス注入の方が見落としやすい。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `path.join()` / `path.resolve()` との対応関係を理解しようとしている。

**エラーレスポンスの質**: 422 + `"code": "invalid_path"` は明確。  
**Python 固有概念の学習コスト**: Node.js の `path.join("/base", "/abs")` は `/abs` を返す（Python と同じ）ため、
この罠は Python 固有ではない。  
**事故リスク**: 中。Node.js でも同じ罠があるため注意できる可能性は高い。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `FileField` / `ImageField` での安全なパス管理と比較する。

**他フレームワークとの差異**: Django は `FileField(upload_to=...)` でアップロードパスを制限する。
生の `pathlib` でファイルアップロードを扱う場合は手動でトラバーサル防御が必要。  
**nene2-python の薄さへの評価**: `safe_join()` を共通ユーティリティとして nene2 のコアに追加する価値がある。  
**本番投入可能性**: `safe_join()` + `is_safe` チェック + `ValidationException` の組み合わせで本番投入可能。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームのコードレビューでファイルパス処理の安全性を確認する。

**コードレビューチェックポイント**:
- [ ] `Path(base) / user_input` の `user_input` に絶対パスが渡せないか
- [ ] `Path.resolve()` の結果をベースパスと比較しているか（symlink 含む）
- [ ] `open(user_filename)` のような直接 `open()` がないか（ruff S603 でも検出不可）
- [ ] `max_length` でファイル名の長さが制限されているか

**チームでの安全なパターン**: `safe_join()` ヘルパーを共通ライブラリに置き、
直接 `Path() /` でユーザー入力を結合するコードを禁止するコーディング規約を設ける。  
**ツール追加の必要性**: ruff の PTH ルールは `os.path` → `pathlib` の移行を促すが、
パストラバーサル自体は検出しない。静的解析で補完できない部分はコードレビューが必要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。CLAUDE.md の「pathlib でパス操作・パストラバーサルを防ぐ」ポリシーを実装で実証。  
**「初心者でも安全な API」達成度**: 中。`safe_join()` ヘルパーがあれば初心者も安全に使える。
ただし「絶対パスをユーザー入力として渡すとベースが無視される」という罠を文書化すべき。  
**設計上の負債**: `safe_join()` を nene2 コアの `nene2.http.path` に追加する価値がある（FT の観察）。  
**Follow-up Issue 候補**: `safe_join()` を nene2 コアに追加（優先度: 低）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `safe_join()` / `check_traversal()` を nene2 コアユーティリティとして追加検討 | enhancement |

---

## まとめ

`pathlib` の `PurePosixPath` はファイルシステムに触れない純粋なパス解析に適しており、
HTTP API のテストを容易にする。

最大の学習ポイントは:
1. **絶対パスをユーザー入力として `Path() /` に渡すとベースが無視される** — `..` 以上に危険
2. **`Path.resolve()` はファイルシステム依存** — HTTP テストには Pure パス演算が必要
3. **`.suffix` は最後の拡張子、`.suffixes` は全拡張子** — `backup.tar.gz` は `.gz` / `[".tar", ".gz"]`

次の FT207 は `207 % 3 = 0` → セキュリティ診断あり、`207 % 4 = 3` → クラッカーペンテストなし。
