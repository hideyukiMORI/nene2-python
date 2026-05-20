# Field Trial 151: argparse モジュール

## テーマ

`argparse.ArgumentParser`, サブコマンド, 型変換, 相互排他グループ,
`Namespace`, `exit_on_error` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft151-argparse/` に以下を実装:

- `parse_args()` — 基本的な位置引数・オプション引数のパース
- `parse_typed_args()` — `type=int/float`, `choices`, `action="append"`, `nargs="+"` を持つパーサー
- `parse_exclusive_args()` — 相互排他グループ（`--quiet` と `--verbose` は同時指定不可）
- `parse_subcommand_args()` — `create` / `delete` サブコマンド
- `get_parser_info()` — パーサーのアクション情報を辞書で取得
- HTTP エンドポイント 5 本
- 26 テスト全通過（摩擦0件）

## テスト結果

初回: 26 テスト全通過。摩擦なし。

## 摩擦なし

今回はブロッカーとなる摩擦なし。`exit_on_error=False` の指定が重要だった。

## 観察

### O1: `exit_on_error=False` でパースエラーを例外として受け取れる

```python
parser = argparse.ArgumentParser(exit_on_error=False)

# exit_on_error=True (デフォルト): エラー時に sys.exit(2) を呼ぶ
# exit_on_error=False: argparse.ArgumentError を送出する
try:
    namespace = parser.parse_args(["--invalid"])
except argparse.ArgumentError as e:
    print(f"Error: {e}")
```

デフォルトの `exit_on_error=True` では、パースエラー時に `sys.exit(2)` を呼ぶため
FastAPI のリクエストハンドラー内で使うと致命的。
`exit_on_error=False` を指定して `argparse.ArgumentError` を catch するパターンが必要。

### O2: `action="store_true"` でフラグ引数を作る

```python
parser.add_argument("--verbose", "-v", action="store_true", help="詳細表示")
# --verbose が指定されれば True、指定なければ False
```

`action="store_false"` は逆の動作。`action="count"` は出現回数をカウントする。

### O3: `action="append"` で複数回指定を許容する

```python
parser.add_argument("--tag", action="append", help="タグ（複数指定可）")
# --tag python --tag fastapi → ["python", "fastapi"]
# --tag なし → None
```

`nargs="+"` との違い: `action="append"` はフラグを複数回指定、
`nargs="+"` はフラグの後に複数値を列挙する。

### O4: 相互排他グループで同時指定を禁止できる

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--quiet", action="store_true")
group.add_argument("--verbose", action="store_true")
# --quiet --verbose を同時指定すると ArgumentError
```

`required=True` を `add_mutually_exclusive_group()` に指定すると
グループ内のどれか 1 つを必須にできる。

### O5: サブコマンドは `add_subparsers()` で追加する

```python
subparsers = parser.add_subparsers(dest="command")
create_p = subparsers.add_parser("create")
create_p.add_argument("name")
# ["create", "myapp"] → Namespace(command="create", name="myapp")
# [] → Namespace(command=None)
```

`dest="command"` でサブコマンド名を `namespace.command` から参照できる。
サブコマンドなしは `command=None` になる。

### O6: `vars(namespace)` で Namespace を辞書に変換できる

```python
namespace = parser.parse_args(["file.txt", "--count", "3"])
result = vars(namespace)
# → {"filename": "file.txt", "count": 3, "verbose": False, "output": "out.txt"}
```

`vars()` は `namespace.__dict__` を返す。
`Namespace` オブジェクトは `namespace.filename` のようにも属性アクセスできる。

### O7: `--dry-run` のような hyphen 引数は underscore に変換される

```python
parser.add_argument("--dry-run", action="store_true")
namespace = parser.parse_args(["--dry-run"])
namespace.dry_run  # True (dry-run → dry_run)
```

`argparse` はオプション引数のハイフン `-` をアンダースコア `_` に変換して
`Namespace` の属性名にする。

## まとめ

FT151 は摩擦ゼロ。`exit_on_error=False` パターンが Web サービス内での
安全な `argparse` 使用の鍵となる。型変換・相互排他・サブコマンドが
すべて単一のパーサーで扱えるため、CLI ツールの設定パースに有用。
