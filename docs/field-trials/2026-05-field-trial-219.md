# FT219: argparse モジュール — ArgumentParser / add_argument / parse_args / subcommands

**日付**: 2026-05-23
**テーマ**: Python `argparse` モジュールの ArgumentParser / add_argument / parse_args / subcommands の実装と検証
**セキュリティ診断**: あり（219 % 3 = 0）
**クラッカーペンテスト**: なし（219 % 4 = 3）

---

## 概要

`argparse` モジュールは Python の標準 CLI 引数パーサー。HTTP API でラップすることで「引数リストを受け取って構造化データを返す」パターンを検証した。

| API | ユースケース |
|---|---|
| `ArgumentParser.add_argument()` | 引数の型・デフォルト・choices を宣言 |
| `parse_args(argv)` | 文字列リストを Namespace にパース |
| `action="store_true"` | フラグ引数（bool）のパース |
| `nargs="*"` | 可変長引数リストのパース |
| `add_subparsers()` / `add_parser()` | サブコマンドのディスパッチ |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft219-argparse/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `parse_deploy_args()` | `--env` / `--replicas` / `--verbose` / `--dry-run` のデプロイ引数をパース |
| `parse_typed_args()` | `str` / `int` / `float` / `bool` / `list[str]` の型変換を検証 |
| `parse_subcommand()` | `deploy` / `rollback` のサブコマンドをディスパッチ |
| `_SilentParser` | `error()` / `exit()` を `ValueError` に変換するカスタムパーサー |
| `_validate_argv()` | argv の数・各引数の長さを検証 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/argparse/deploy` | デプロイ引数のパース |
| POST | `/argparse/typed` | 型変換付き引数のパース |
| POST | `/argparse/subcommand` | サブコマンドのディスパッチ |

---

## 摩擦点

### F-1: `error()` / `exit()` の戻り値型が `Never`（mypy strict 問題）

**観察**: `argparse.ArgumentParser.error()` と `exit()` の戻り値型は `Never`（Python の型スタブで定義）。サブクラスで `-> None` でオーバーライドすると mypy strict が `Return type "None" of "error" incompatible with return type "Never"` エラーを出す。

**対処**: `from typing import NoReturn` を使い、オーバーライドの戻り値型を `-> NoReturn` に変更。`raise ValueError(message)` で常に例外を送出するため、関数が正常終了することなく mypy も `NoReturn` として正しく認識する。

```python
class _SilentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        raise ValueError(message or f"argparse exited with status {status}")
```

---

### F-2: `--help` / `--version` が `sys.exit(0)` を呼ぶ

**観察**: デフォルトの `ArgumentParser` は `--help` を受け取ると `sys.exit(0)` を呼ぶ。HTTP API コンテキストでは `sys.exit()` はプロセスを終了させる危険がある（実際は ASGI の非同期コンテキストでは少し挙動が異なるが、`SystemExit` が `BaseException` として伝播する）。

**対処**: `_SilentParser.exit()` を `-> NoReturn` で `ValueError` を投げるようにオーバーライドしたことで `--help` も 422 で応答する（セキュリティ診断で確認）。`add_help=False` でヘルプ引数自体を無効化する方法もあるが、今 FT では `exit()` のオーバーライドで対処。

---

## セキュリティ診断結果

| 攻撃シナリオ | 結果 | 対処 |
|---|---|---|
| シェルメタ文字を `--env` 値に注入（`prod; rm -rf /`） | 422（choices バリデーションで遮断） | 対策済み |
| null バイトを引数値に埋め込む | 422（choices バリデーションで遮断） | 対策済み |
| argv 数が上限（50）を超過 | 422（Pydantic `max_length=50` で遮断） | 対策済み |
| 引数文字列が上限（200 文字）を超過 | 422（Pydantic `max_length=200` で遮断） | 対策済み |
| `--help` フラグ注入 | 422（`_SilentParser.exit()` → ValueError → ValidationException） | 対策済み |
| `--version` フラグ注入 | 422（`_SilentParser.error()` → ValueError → ValidationException） | 対策済み |
| サブコマンドにシェルインジェクション文字列 | 422（未知サブコマンドとして argparse がエラー） | 対策済み |
| Unicode RTL 文字を値に注入 | 422（choices バリデーションで遮断） | 対策済み |
| 必須引数欠落（`rollback` で `--version` なし） | 422（argparse error → ValueError → ValidationException） | 対策済み |
| サブコマンドなしで呼び出し | 422（`command is None` チェックで ValidationException） | 対策済み |
| SQL インジェクション風文字列を argv に注入 | 422（choices バリデーションで遮断） | 対策済み |

**総合評価: 合格**

argparse は引数値を文字列として扱うだけでシェルに渡さないため、シェルインジェクションのリスクは構造的にない。`choices` による列挙型制限と `_SilentParser` による `sys.exit()` の無力化が主要な防御ポイント。

---

## テスト結果

```
16 passed in 0.91s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

CLI 引数パーサーを HTTP API でラップするという発想は少し難しいが、「引数のリストを送ると解析結果が返ってくる」として理解できる。`--env dev` → `{"env": "dev"}` の変換は直感的。

**ドキュメント理解**: `action="store_true"` でフラグが `bool` になること、`nargs="*"` で可変長リストになることは最初は驚きがある。

**事故リスク（高）**: argparse をそのまま HTTP で使う場合、`sys.exit()` の罠を知らないと本番でプロセスが落ちる。`_SilentParser` パターンは必須だが、初心者は思いつかない。

**規約の使いやすさ**: 引数を `list[str]` で渡す API 設計は CLI コマンドをそのまま分割して送れるため理解しやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

CLI ツールを API 化するユースケースは実務でよくある（Jupyter Notebook や社内バッチ処理の API 化）。`_SilentParser` パターンはコピーして使える。

**コピペ可能性**: `_make_deploy_parser()` のパターンはそのまま自社ツールの引数定義に流用できる。

**拡張時の罠**: `type=Path` など argparse のカスタム型コンバーターを使うと、変換エラーが `error()` 経由で `ValueError` になる。今 FT の `_SilentParser` でそのまま処理できる。

**事故リスク（中）**: `--help` / `--version` の `sys.exit()` を知らないと本番で落ちる。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`argv: list[str]` を受け取る API は `process.argv` の概念に近い。`subcommand` エンドポイントは `git` や `docker` の CLI 構造と対応する。

**エラーレスポンスの質**: 不正な引数は `_SilentParser.error()` → `ValueError` → `ValidationException` → 422 という変換チェーンで処理され、`{field: "argv", message: "...", code: "parse_error"}` として返る。

**Python 固有概念**: `argparse.Namespace` は `dict` に変換してから JSON シリアライズする点が Python 固有。`vars(namespace)` でアクセスできる。

**事故リスク（低）**: 入力は `list[str]` で Pydantic が長さ制限を担保。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django Management Command の実装では `argparse.ArgumentParser` をサブクラス化するパターンが標準。`_SilentParser` は Django の `BaseCommand.create_parser()` が内部でやっていることに近い。

**他フレームワークとの差異**: Click や Typer のような宣言的 CLI フレームワークは `sys.exit()` の問題を内部で処理している。argparse を直接使う場合は `_SilentParser` パターンが必要。

**nene2 の薄さへの評価**: argparse を HTTP でラップする薄い API として適切。`choices` バリデーションが argparse 側に委譲されているため nene2 の独自バリデーションは最小限で済む。

**事故リスク（低）**: セキュリティ診断合格、二重バリデーション（Pydantic + argparse）で堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `sys.exit()` をオーバーライドしているか — argparse を API コンテキストで使う最大の罠
- `error()` / `exit()` の戻り値型が `NoReturn` になっているか — mypy strict で強制される
- `add_help=False` か `exit()` オーバーライドかを選んでいるか — 今 FT は `exit()` オーバーライドで両方対応
- サブコマンドで `dest="command"` が設定されているか — `None` チェックのために必要

**チームでの安全なパターン**: `_SilentParser` を共通モジュールに切り出して全 argparse 利用箇所で再利用できる。

**事故リスク（低）**: セキュリティ診断合格。`NoReturn` の型付けも正確。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Pydantic` での入力検証（`max_length=50` / `max_length=200`）・`frozen=True, slots=True` の dataclass・`ValidationException` への例外変換はすべてポリシー準拠。`_SilentParser` による `sys.exit()` の無力化は「HTTP 境界の安全性」の観点で正しい。

**初心者でも安全な API 達成度**: `argv: list[str]` の直感的な入力形式と、エラー時の 422 一貫性で達成。`--help` / `--version` も安全に処理される。

**改善提案**: `_SilentParser` はフレームワークコア（`nene2.utils`）に切り出す価値がある。argparse を API でラップするユースケースは多く、共通パターンとして提供できる。
