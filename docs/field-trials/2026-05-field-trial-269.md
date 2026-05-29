# FT269: contextvars — ContextVar によるコンテキストローカル状態

**日付**: 2026-05-29
**テーマ**: Python `contextvars` モジュールのコンテキストローカル状態の実装と検証
**セキュリティ診断**: なし（269 % 3 = 2）
**クラッカーペンテスト**: なし（269 % 4 = 1）

---

## 概要

`contextvars.ContextVar` は**コンテキストローカル**（スレッド/async タスクごとに独立）な状態を提供する。リクエストスコープの相関 ID・ユーザー情報の伝播に使う（nene2 の `RequestScopedContext[T]` の基盤）。HTTP API でラップし set/get/reset の往復を検証した。

| API | ユースケース |
|---|---|
| `ContextVar("name", default=...)` | コンテキスト変数（デフォルト付き） |
| `.set(value)` → Token | 値設定（復元用 Token を返す） |
| `.reset(token)` | 前の状態に復元 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft269-contextvars/`

| 関数 | 概要 |
|---|---|
| `context_roundtrip()` | default → set → get → reset → default を確認 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/context/demo` | ContextVar の往復 |

---

## 摩擦点

### F-1: デフォルトを与えないと未設定で `LookupError`

**観察**: `ContextVar("x")`（デフォルトなし）で未設定のまま `.get()` すると `LookupError`。リクエスト処理の途中で必ず set される保証がないと例外になる。

**対処**: `ContextVar("request_tag", default="<unset>")` でデフォルトを与える。未設定でも安全に取得できる。

### F-2: `set` の Token で確実に `reset` する

**観察**: `.set(value)` は `Token` を返し、`.reset(token)` で前の状態に戻せる。reset しないと値がコンテキストに残り、同じコンテキストを再利用する場合（スレッドプール等）に**前のリクエストの値が漏れる**。

**対処**: set の Token を保持し処理後に reset。ミドルウェアでは try/finally で reset するのが定石。診断でリクエスト間の分離（毎回デフォルトに戻る）を確認。

### F-3: async タスク間の分離

**観察**: ContextVar は `asyncio` タスクごとにコピーされ独立する（グローバル変数と違いタスク間で混ざらない）。これがリクエストスコープ伝播に適する理由。

**対処**: 本 FT は同期で set/reset を検証。async では各タスクが独立コンテキストを持つ。

---

## テスト結果

```
3 passed in 0.89s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「グローバル変数だけどスレッド/タスクごとに別」という概念は難しい。set/reset の往復で挙動が見える。

**ドキュメント理解**: default と Token の役割をコメントで明示。
**事故リスク（低）**: 状態管理のみ。
**規約の使いやすさ**: value → 往復結果が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ログの相関 ID 伝播で使う。reset 忘れで値が漏れる罠に注意。

**コピペ可能性**: context_roundtrip は流用可。
**拡張時の罠**: reset 忘れ・デフォルトなしの LookupError。
**事故リスク（中）**: コンテキスト再利用時の値漏れ。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

React Context に名前が似るが用途が異なる（スレッド/タスクローカル）。AsyncLocalStorage（Node）に近い。

**エラーレスポンスの質**: 空値は 422。
**Python 固有概念**: ContextVar・Token・タスク分離。
**事故リスク（低）**: デフォルトあり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

リクエスト相関 ID・ユーザー・テナントの伝播に使う。ミドルウェアで set、finally で reset が定石。structlog の contextvars 連携も。

**他フレームワークとの差異**: グローバル変数より安全（タスク分離）。
**nene2 の薄さへの評価**: RequestScopedContext の基盤として妥当。
**事故リスク（低）**: 分離を確認。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- ContextVar にデフォルトを与えているか（LookupError 回避）。
- set の Token で finally reset しているか（値漏れ防止）。
- グローバル変数ではなく ContextVar を使っているか（タスク分離）。
- 機密値を ContextVar に入れてログに出していないか（FT220）。

**チームでの安全なパターン**: ミドルウェアで set/finally reset、相関 ID 等の伝播に限定。
**事故リスク（低）**: 分離・reset を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。`RequestScopedContext[T]`（既存）と一貫。
**初心者でも安全な API 達成度**: デフォルト + Token reset を関数内に示し、LookupError・値漏れの理解を促す。
**改善提案**: ミドルウェアでの set/finally reset パターンと structlog 連携を how-to に補足する。
