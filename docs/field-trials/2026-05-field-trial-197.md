# FT197: urllib.parse モジュール — URL 解析・エンコード・クエリ文字列処理

**日付**: 2026-05-22
**テーマ**: Python `urllib.parse` モジュールの URL 解析・組み立て・エンコード・クエリ文字列処理の実装と検証
**セキュリティ診断**: なし（197 % 3 = 2）
**クラッカーペンテスト**: なし（197 % 4 = 1）

---

## 概要

`urllib.parse` は URL の分解・組み立て・エンコード・デコードを担う Python 標準ライブラリ。
`requests` や `httpx` が内部で使うプリミティブで、スキーム検証・クエリ文字列の正規化・
URL エンコーディングの差異（`%20` vs `+`）を理解するのに重要なモジュールである。

FT194（ipaddress）・FT196（http.client）の続きとして「URL の安全な取り扱い」を担う層を検証した。
スキーム別の `is_allowed_scheme` フラグを ParsedUrl に含め、SSRF 対策の最初の門番として使えることを示した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft197-urllib-parse/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_url(url)` | `urlparse()` で URL を 6 要素に分解し `is_allowed_scheme` フラグを付与 |
| `build_url(scheme, netloc, path, query_params, fragment)` | `urlunparse()` + `urlencode()` で URL を組み立て |
| `parse_query_string(query)` | `parse_qsl()` でクエリ文字列をペア一覧に変換（重複キー保持） |
| `encode_query_params(params)` | `urlencode()` で dict を `application/x-www-form-urlencoded` 形式に変換 |
| `url_quote_text(text)` | `quote()` と `quote_plus()` の両形式でエンコードして比較できる形で返す |
| `url_unquote_text(text)` | `unquote()` と `unquote_plus()` の両形式でデコードして比較できる形で返す |
| `join_url(base, relative)` | `urljoin()` でベース URL と相対パスを結合 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/url/parse` | URL を構成要素に分解 |
| POST | `/url/build` | 構成要素から URL 文字列を生成 |
| POST | `/url/query/parse` | クエリ文字列をキー・バリューペア一覧に変換 |
| POST | `/url/query/encode` | dict を URL クエリ文字列にエンコード |
| POST | `/url/encode` | 文字列を %XX / + 形式でエンコード |
| POST | `/url/decode` | URL エンコードされた文字列をデコード |
| POST | `/url/join` | ベース URL と相対パスを結合 |

---

## テスト結果

**28 passed**

```
28 passed in 0.07s
```

---

## 摩擦ポイント

### F-1: `parse_qs` と `parse_qsl` の使い分けが非自明（深刻度: 低）

**事象**: 重複キーを持つクエリ文字列 `tag=python&tag=fastapi` を解析したい場合、
`parse_qs("tag=python&tag=fastapi")` は `{"tag": ["python", "fastapi"]}` を返すが、
`parse_qsl` は `[("tag", "python"), ("tag", "fastapi")]` を返す。

どちらを使うかは「キーの一意性を仮定するか否か」によって異なるが、名前だけでは判別できない。

**対応**: `parse_qsl` を選択。順序と重複を保持するため、API 側で `list[QueryParam]` に
マッピングしやすい。クライアントが `dict` を期待するなら `parse_qs` を使うべき。

**CLAUDE.md への示唆**: クエリ文字列処理の how-to に `parse_qs` vs `parse_qsl` の使い分けを記載する価値がある。

### F-2: `dataclasses.field` を未使用のままインポートしてしまった（深刻度: 低）

**事象**: `demos.py` に `from dataclasses import dataclass, field` と書いたが、
`field` を使う `@dataclass` フィールドは存在しなかった。`ruff check` が `F401` で検出。

**原因**: FT195 の `SecurityAssessment` は `field(default_factory=list)` を使っていたため
慣習的にコピーしてしまった。

**対応**: `uv run ruff check --fix` で自動修正。

### F-3: `urljoin` の動作が RFC 3986 に準拠しており直感に反する場合がある（深刻度: 低）

**事象**: `urljoin("https://example.com/api/v1/users", "users")` は
`https://example.com/api/v1/users` になると思いきや `https://example.com/api/v1/users`（同じ）になった。
一方で `urljoin("https://example.com/api/v1/", "users")` は
`https://example.com/api/v1/users` となる（末尾スラッシュが重要）。

**原因**: `urljoin` は RFC 3986 の相対 URI 解決アルゴリズムを実装している。
ベース URL の最後のパスセグメントが `/` で終わらない場合、そのセグメントを捨てて結合する。

**対応**: テスト `test_join_url_relative_path` で末尾スラッシュあり（`/api/v1/`）を使う。
ドキュメントや API 定義にこの挙動を明記するのが良い。

---

## 観察点

### O-1: `quote(text, safe="")` と `quote_plus(text)` の差異

`quote("hello world/test", safe="")` → `hello%20world%2Ftest`（スペースは `%20`）
`quote_plus("hello world/test")` → `hello+world%2Ftest`（スペースは `+`）

HTML フォームの `application/x-www-form-urlencoded` では `+` が正規。
URL パスには `%20` が正規。用途で使い分けが必要。

### O-2: `urlparse` はスキームなしでも例外を投げない

`urlparse("example.com/path")` は scheme=`""`, netloc=`""`, path=`"example.com/path"` を返す。
スキームなしの文字列も黙って受け付けるため、`is_allowed_scheme` チェックで
`scheme == ""` の場合も弾く設計が必要（SSRF 文脈では重要）。

### O-3: `ParseResult` は `typing.NamedTuple` のサブクラス

`urlparse()` の戻り値 `ParseResult` は `NamedTuple` のサブクラスなので
`parsed.scheme`, `parsed.netloc` のようにドット記法でアクセスできる。
`parsed[0]`, `parsed[1]` のようなインデックスアクセスも可能だが、可読性のため使わない。

---

## DX Review — 6ペルソナ

### ペルソナ 1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

URL を扱う作業で `urllib.parse` と `requests` のどちらを使うべきか迷う可能性がある。
`requests.get(url)` で十分な場面に `urllib.parse` を持ち出すと冗長になる。

**ドキュメント理解**: `parse_url()` 関数の入出力が dataclass で型付けされているため、
何が返るかを IDE で確認しやすい。
**事故リスク**: 中。`urljoin` の末尾スラッシュ問題（F-3）は気づかないまま
パスが変になるバグとして現れる可能性がある。
**規約の使いやすさ**: `is_allowed_scheme` フラグは分かりやすいが、
「どのスキームが許可されているか」がコードを見ないと分からない。定数 `ALLOWED_SCHEMES` を
エンドポイントのレスポンスに含めるとより親切。

### ペルソナ 2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`requests` ユーザーが `urllib.parse` を知るのは「URL の部品を取り出したい」「クエリ文字列を組み立てたい」
という具体的ユースケースが発生したとき。

**コピペ可能性**: `parse_url()` と `build_url()` は典型的なユースケースで即コピペ可能。
**拡張時の罠**: F-3（`urljoin` の末尾スラッシュ）はデバッグで時間を取られる典型的なはまりポイント。
**事故リスク**: 低。`urllib.parse` 自体は副作用のない純粋な変換関数群。

### ペルソナ 3: フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `URL` クラスや `URLSearchParams` と概念が近いため比較的理解しやすい。
`new URL(str)` に相当するのが `urlparse()`、`url.searchParams.get()` に相当するのが `parse_qs()` / `parse_qsl()`。

**エラーレスポンスの質**: 422 で `max_length` 超過が明確に分かる。
**Python 固有概念の学習コスト**: 低（`urllib.parse` は純粋な変換関数で副作用なし）。
**事故リスク**: 低。

### ペルソナ 4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django では `from django.utils.http import urlencode` や `QueryDict` を使う場面が多く、
標準の `urllib.parse` を直接使うことは少ない。`parse_qsl` の存在を知らないケースもある。

**他フレームワークとの差異**: Django の `QueryDict` は重複キーを `getlist()` で取れるが、
`parse_qsl` はシンプルなタプルリストとして返す点が異なる。
**nene2 の薄さへの評価**: `demos.py` に純粋関数として切り出した設計は `UseCase` 層として
再利用しやすく評価できる。
**事故リスク**: 低。

### ペルソナ 5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`ParsedUrl.is_allowed_scheme` でスキーム検証を行っているが、
エンドポイント側でこのフラグを強制チェックしていないことに気づく（API は情報を返すだけ）。
SSRF 防御として使うには `is_allowed_scheme == False` の場合に `ValidationException` を上げる
エンドポイントが必要。

**コードレビューチェックポイント**:
- `ALLOWED_SCHEMES` は frozenset で不変 ✓
- `MAX_QUERY_PAIRS = 50` で無限ループ対策 ✓
- `ParseResult` インポートを使っていないなら削除を推奨（実際は型注釈に使用）
- `is_allowed_scheme` の活用場面をコメントで示すと良い

**チームでの安全なパターン**: `parse_url()` の結果をそのまま信用せず、
`is_allowed_scheme` チェック後に接続する設計パターンを how-to に記述する価値がある。
**事故リスク**: 低（コード自体は安全。使い方の問題）。

### ペルソナ 6: 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `frozen=True, slots=True` dataclass ✓
- Pydantic `max_length` による入力制限 ✓
- `response_model=str` の明示（文字列返却エンドポイント）✓
- `ErrorHandlerMiddleware` 追加 ✓（init-ft.sh ボイラープレートが機能した）

**初心者でも安全な API 達成度**: `is_allowed_scheme` フラグは情報提供のみで強制しないため、
初心者がそのまま「URL をプロキシする」実装を書くと SSRF になる余地がある。
「スキームが許可されていない場合は 422 を返す」エンドポイントを追加すると完結する。

**F-1 への対応**: `parse_qs` vs `parse_qsl` の使い分けを how-to ガイドに追記予定（並行系 how-to と同列に整理）。

---

## Follow-up

- 追加修正なし（全 F は FT サンドボックス内で解消済み）
- `parse_qs` vs `parse_qsl` の比較を how-to ガイドにまとめる作業は中優先として今後対応
