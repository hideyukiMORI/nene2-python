# Field Trial 150: configparser モジュール

## テーマ

`configparser.ConfigParser`, `RawConfigParser`, `BasicInterpolation`,
デフォルト値, `getint`/`getfloat`/`getboolean`, `Sniffer` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft150-configparser/` に以下を実装:

- `parse_ini()` — `ConfigParser.read_string()` で INI テキストをパース
- `parse_ini_with_defaults()` — `defaults` 引数でデフォルト値付きパース
- `get_value()` / `get_int()` / `get_float()` / `get_bool()` — 型変換付き値取得
- `build_ini()` — セクション辞書から INI テキストを生成
- `parse_with_interpolation()` — `%(key)s` 形式の変数展開
- `parse_raw()` — `RawConfigParser` でインターポレーションなしパース
- HTTP エンドポイント 4 本
- 23 テスト全通過（摩擦1件）

## テスト結果

初回: 2 失敗 → 修正後: 23 テスト全通過。

## Friction Points

### FP1: セクション名は大文字小文字を保持するが、オプションキーは小文字に変換される

```python
ini = "[Section]\nMyKey = value"
parser = configparser.ConfigParser()
parser.read_string(ini)

# セクション名: 大文字小文字そのまま保持
list(parser.sections())  # → ["Section"] (小文字化されない)

# オプションキー: 自動的に小文字に変換される
dict(parser["Section"])  # → {"mykey": "value"} ("MyKey" → "mykey")
```

`ConfigParser` のデフォルト動作ではオプションキー（各セクション内のキー）は
自動的に小文字に変換される（`optionxform = str.lower`）。
しかしセクション名は大文字小文字を保持する。

テストで `result["section"]` と書いたが、実際は `result["Section"]` でないとアクセスできない。

**対処**: テストの期待値をセクション名 `"Section"` に修正した。

**カスタマイズ**: `optionxform = str` に変更すると、キーも大文字小文字を保持できる：

```python
parser = configparser.ConfigParser()
parser.optionxform = str  # キーの大文字小文字を保持
```

## 観察

### O1: `io.StringIO` でファイルなしに INI パース/生成できる

```python
def parse_ini(text: str) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser()
    parser.read_string(text)  # ファイルパスではなく文字列を直接渡す
    return {section: dict(parser[section]) for section in parser.sections()}

def build_ini(config: dict[str, dict[str, str]]) -> str:
    parser = configparser.ConfigParser()
    for section, options in config.items():
        parser.add_section(section)
        for key, value in options.items():
            parser.set(section, key, value)
    output = io.StringIO()
    parser.write(output)
    return output.getvalue()
```

`read_string()` で文字列からパース、`write(io.StringIO())` でインメモリ生成できる。

### O2: `getint()` / `getfloat()` / `getboolean()` で型変換できる

```python
parser.getint("database", "port")         # → 5432 (int)
parser.getfloat("values", "rate")         # → 3.14 (float)
parser.getboolean("server", "debug")      # → True (bool)
```

`getboolean()` は `yes`/`no`/`true`/`false`/`1`/`0` を解釈する。
各メソッドに `fallback` 引数でデフォルト値を指定できる。

### O3: `defaults` で全セクション共通のデフォルト値を設定できる

```python
parser = configparser.ConfigParser(defaults={"env": "production"})
parser.read_string("[app]\nname = myapp")
parser.get("app", "env")  # → "production" (デフォルト値)
```

`defaults` に指定した値は `[DEFAULT]` セクション相当になり、
各セクションで上書きできる。

### O4: `BasicInterpolation` で `%(key)s` 形式の変数展開ができる

```python
ini = """
[paths]
base = /opt/app
data = %(base)s/data
"""
parser = configparser.ConfigParser(interpolation=configparser.BasicInterpolation())
parser.read_string(ini)
parser.get("paths", "data")  # → "/opt/app/data"
```

`RawConfigParser` または `interpolation=configparser.NoInterpolation()` を使うと
変数展開を無効化できる。

### O5: `ConfigParser` の `[DEFAULT]` セクションは `sections()` に含まれない

```python
ini = """
[DEFAULT]
timeout = 30

[app]
name = myapp
"""
parser = configparser.ConfigParser()
parser.read_string(ini)
list(parser.sections())  # → ["app"] (DEFAULT は除外)
parser.get("app", "timeout")  # → "30" (DEFAULT から継承)
```

`[DEFAULT]` セクションはすべてのセクションの基底値として機能する。

## まとめ

FT150 は摩擦1件（セクション名大文字小文字保持とオプションキー小文字化の非対称な動作）。
`configparser` は `io.StringIO` でファイルなし処理ができ、
型変換メソッドや `BasicInterpolation` による変数展開が便利。
