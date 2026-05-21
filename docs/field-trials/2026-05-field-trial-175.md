# FT175: logging モジュール

**日付**: 2026-05-21
**テーマ**: `logging` モジュール — センシティブデータマスキング・LoggerAdapter・dictConfig
**セキュリティ診断**: なし（FT176 で実施）

---

## 概要

Python 標準ライブラリの `logging` モジュールを検証する。
CLAUDE.md で「`print()` 禁止・`logging` モジュールのみ使用」と明示されており、
nene2-python の根幹ポリシーに直結するモジュールである。

このFTで確認する点:
- `logging.Filter` によるセンシティブデータのマスキング（パスワード・トークン・カード番号）
- `logging.LoggerAdapter` によるリクエストIDの全ログへの付与
- `setup_logger()` パターン（テスト用 StringIO へのキャプチャ）
- `parse_log_level()` によるログレベルの安全な変換
- `logging.config.dictConfig` による宣言的ログ設定
- `capture_logs()` / `release_capture()` テストユーティリティ

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft175-logging/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `mask_sensitive(message)` | パスワード・トークン・API鍵・カード番号をマスク |
| `SensitiveFilter` | `logging.Filter` サブクラス — LogRecord のメッセージを自動マスク |
| `RequestIdAdapter` | `LoggerAdapter[Logger]` — 全ログに `[request_id]` を付与 |
| `setup_logger(name, level, stream)` | テスト用 StringIO 出力ロガーを作成 |
| `parse_log_level(level_str)` | 文字列 → `logging.DEBUG` 等の定数、不明は `INFO` |
| `log_event(logger, level, message, extra)` | 構造化ログエントリ（辞書）を記録して返す |
| `is_level_enabled(logger, level)` | ログレベルが有効かを `bool` で返す |
| `effective_level_name(logger)` | 有効ログレベル名を文字列で返す |
| `LOGGING_CONFIG` | `dictConfig` 用設定辞書（SensitiveFilter 組み込み） |
| `apply_logging_config()` | dictConfig を適用する |
| `capture_logs(logger)` | テスト用キャプチャハンドラーを追加して `(StringIO, handler)` を返す |
| `release_capture(logger, handler)` | キャプチャハンドラーを解放する |

マスキングパターン:

| パターン | 置換後 |
|---|---|
| `password=<4文字以上>` | `password=***` |
| `token: <4文字以上>` | `token: ***` |
| `api_key=<4文字以上>` | `api_key=***` |
| `\b\d{13,19}\b`（カード番号） | `****-****-****-****` |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/logging/mask` | センシティブデータをマスクした文字列を返す |
| GET | `/logging/level` | ロガーのレベル有効判定 |
| POST | `/logging/event` | イベントを記録（センシティブマスク付き） |
| GET | `/logging/events` | 記録済みイベント一覧 |
| DELETE | `/logging/events` | イベント一覧をクリア |
| GET | `/logging/parse-level` | 文字列をログレベル数値に変換 |
| GET | `/logging/buffer` | インメモリバッファのログ行一覧 |

---

## テスト結果

**32 passed**

```
32 passed in 0.34s
```

---

## 摩擦ポイント

### F-1: `logging.StreamHandler` のジェネリック型注釈（深刻度: 低）

**事象**: `logging.StreamHandler` は `StreamHandler[StringIO]` とジェネリック型注釈できるが、
mypy が `# type: ignore[type-arg]` なしでは警告を出すケースがある。

**原因**: `StreamHandler` は Python 3.12 でジェネリック対応済みだが、
`StreamHandler` の型スタブが `Generic[TextIO]` として定義されているため
`StreamHandler` 単独だと型引数省略警告が出ることがある。

**対応**: 関数シグネチャに `# type: ignore[type-arg]` を追記。
これは mypy の型スタブ側の制約であり実装ミスではないため、CLAUDE.md 規約に従いコード添付コメントで理由を明記した。

### F-2: `LoggerAdapter.extra` の型（深刻度: 低）

**事象**: `LoggerAdapter[Logger]` の `self.extra` の型が `Mapping[str, Any] | None` なので
`self.extra.get("request_id")` の前に `if self.extra` のガードが必要。

**原因**: `LoggerAdapter.__init__` の `extra` パラメーターが `Mapping[str, Any] | None` で
初期化できるため、mypy がnullチェックを要求する。

**対応**: `request_id = self.extra.get("request_id", "-") if self.extra else "-"` で対応。

---

## 観察点

### 観察1: `SensitiveFilter` によるパイプライン的マスキング

```python
class SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_sensitive(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_sensitive(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(mask_sensitive(str(a)) for a in record.args)
        return True
```

`logging.Logger.info("user %s password=%s", username, password)` のように
フォーマット引数を分離して渡すケースでは `record.args` をマスクする必要がある。
`record.msg` だけマスクしても `%s` 置換後の最終文字列に平文が現れるためである。

### 観察2: `RequestIdAdapter` でコンテキストを注入する

```python
class RequestIdAdapter(logging.LoggerAdapter[logging.Logger]):
    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        request_id = self.extra.get("request_id", "-") if self.extra else "-"
        return f"[{request_id}] {msg}", kwargs
```

FastAPI のリクエストスコープで `RequestIdAdapter` インスタンスを生成し、
同一リクエスト内の全ログに `[req-xxxxxxxx]` プレフィックスを付与できる。
`logging.getLogger()` グローバルシングルトンと異なり、スコープごとに別インスタンスを作れる。

### 観察3: `parse_log_level` の安全な変換

```python
def parse_log_level(level_str: str) -> int:
    level = logging.getLevelName(level_str.upper())
    if not isinstance(level, int):  # 不明な文字列は int ではなく文字列を返す
        return logging.INFO
    return level
```

`logging.getLevelName("UNKNOWN")` は `"Level UNKNOWN"` という文字列を返す（None ではない）。
`isinstance(level, int)` チェックでフォールバックを実装する必要がある。

### 観察4: `dictConfig` で `SensitiveFilter` を `()` 形式でインスタンス化

```python
"filters": {
    "sensitive": {
        "()": SensitiveFilter,  # クラスを直接参照してインスタンス化
    },
},
```

`logging.config.dictConfig` では `"()"` キーを使ってカスタムクラスのコンストラクターを呼べる。
`class` キーは `logging` 組み込みクラスのみに使われ、カスタムクラスには `()` を使う。

---

## nene2-python フレームワークとの統合

- nene2-python の `nene2.log` には `structlog` ベースの設定が既に存在する。
  `logging` モジュールの `SensitiveFilter` パターンは `structlog` の `processor` と
  役割が対応する（`structlog` では `ProcessorFormatter` で同様のマスキングが可能）
- CLAUDE.md の「`logging` モジュールのみ使用（`print()` 禁止）」を実証する FT となった
- `RequestIdAdapter` と nene2 の `RequestIdMiddleware` が生成する `x-request-id` を
  連動させることで、ログとHTTPレスポンスの追跡IDを統一できる

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`logging.basicConfig(level=logging.DEBUG)` から入る人には、
`logging.Filter` のサブクラス化は最初のハードルになる。

**ドキュメント理解**: `filter()` が `True` を返すとログ通過、`False` で破棄という
Python の慣習は直感と逆に感じる場合がある（True = 「フィルターを通す」という意味）。  
**事故リスク**: 高。`record.args` のマスクを忘れてフォーマット引数に平文パスワードが
残るパターンは気づきにくい。`SensitiveFilter` のような共通フィルターを強制するのが安全。  
**規約の使いやすさ**: `setup_logger()` ファクトリ関数でテスト・本番の切り替えができる。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`print()` から `logging` への移行は「なぜ面倒なことをするのか」と感じやすい層。
センシティブデータの事故事例を見せることが動機付けに有効。

**コピペ可能性**: `setup_logger()` はそのままコピーして使える。  
**拡張時の罠**: `logger.propagate = False` を忘れると親ロガーにも出力され、
二重ログ・センシティブデータ漏洩につながる。  
**セキュリティ的な事故リスク**: 高。パスワードをログに書いて CloudWatch / Datadog に流れた
インシデントは実際に多数報告されている。`SensitiveFilter` は必須。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `winston` / `pino` と比較すると Python の `logging` は低レベル API に感じるが、
`dictConfig` による宣言的設定で同様の構成が可能。

**エラーレスポンスの質**: `/logging/mask` エンドポイントで
「original_length（入力長）+ masked（マスク後）」を返す設計でクライアント側が動作確認しやすい。  
**Python 固有概念の学習コスト**: `LogRecord` の `msg` と `args` の分離は
Python %-style フォーマットの知識が必要で、JS 開発者には説明が必要。  
**事故リスク**: 中。HTTP API として使う分には Pydantic が入力を保護している。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `LOGGING` 設定辞書と `dictConfig` はほぼ同じ形式なので即理解できる。
`SensitiveFilter` の `record.args` マスクは見落としがちなポイントで評価が高い。

**他フレームワークとの差異**: Django の `LOGGING` は `dictConfig` のラッパー。
FastAPI では自前で `logging.config.dictConfig()` を `lifespan` で呼ぶ必要がある。  
**nene2-python の薄さへの評価**: `structlog` との共存方法を明確にするドキュメントがほしい。  
**本番投入可能性**: `SensitiveFilter` + `RequestIdAdapter` のペアは本番環境でそのまま使える品質。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`record.args` のマスク実装が適切。ただし `%` フォーマット以外（`{}`形式）への対応が未検討。

**コードレビューチェックポイント**:
- [x] `SensitiveFilter.filter()` が `record.args` も処理しているか — OK
- [x] `mask_sensitive()` の正規表現が ReDoS リスクを持っていないか — `[^\s,\"'&;]{4,}` は量指定子が単純で爆発しない ✅
- [ ] `logging.LogRecord.args` が `dict` / `tuple` 以外の型（例: `int`）のとき `isinstance` チェックが抜ける — `else` ブロックなし（稀なケースで問題発生する可能性）
- [ ] `_LOGGED_EVENTS: list[dict]` がモジュールレベルのグローバル変数 — 複数 `create_app()` 呼び出し時に状態が混在する

**チームでの安全な共有パターン**: `SensitiveFilter` を `nene2.log` に組み込み、
デフォルトで全ロガーに適用される設計が理想。  
**ツール追加の必要性**: `ruff S314` (print statement) は `print()` を禁止するが、
Python 3 では `print` は関数なので別アプローチ（プリコミットフック等）が必要。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md の「`logging` モジュールのみ使用」ポリシーを、実際の使用パターンとして実証した。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中（`record.args` マスク忘れのリスクがある）  
**設計上の負債・ドキュメント不足**:
- `nene2.log` の `structlog` 設定と標準 `logging` の共存について ADR が必要
- `SensitiveFilter` を `nene2-python` フレームワーク本体に組み込む価値がある
- `LOGGING_CONFIG` 辞書は `nene2.log` の設定と統一すべき

**Follow-up Issue 候補**: `SensitiveFilter` を `nene2.middleware` または `nene2.log` に追加

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | `SensitiveFilter` を `nene2.log` または `nene2.middleware` に追加 | feat |
| 中 | `structlog` と標準 `logging` の共存 ADR を作成 | docs |
| 低 | `SensitiveFilter.filter()` の `record.args` が dict/tuple 以外のとき `str` として処理する | fix |

---

## まとめ

FT175 では `logging` モジュールの実践的パターンを実証した。
`SensitiveFilter` による `record.args` を含む完全マスキング、
`RequestIdAdapter` によるリクエストスコープのコンテキスト注入、
`dictConfig` による宣言的設定が核心。
`record.args` のマスク忘れは実際の本番事故につながるため、
`SensitiveFilter` を nene2-python フレームワーク本体に取り込むことを検討すべき。

次の FT176 は 176 % 3 = 2 → セキュリティ診断なし。176 % 4 = 0 → クラッカーペンテスト実施。
