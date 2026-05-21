# FT171: asyncio モジュール

**日付**: 2026-05-21
**テーマ**: `asyncio` モジュール — `Task`・`gather`・`Lock`・`Queue`・`Semaphore`・`Event`・タイムアウト
**セキュリティ診断**: **あり**（171 % 3 = 0）

---

## 概要

Python 標準ライブラリの `asyncio` モジュールを nene2-python フレームワーク上で検証した。
FastAPI は ASGI フレームワークであり、すべてのリクエストハンドラーが非同期で動作するため、
`asyncio` の正しい使い方は nene2-python の設計の根幹。
非同期レースコンディション・TOCTOU・グローバル状態の安全性が FT171 のセキュリティ診断の中心。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft171-asyncio/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `fetch_simulated()` / `fetch_all()` | `asyncio.gather` で並列フェッチ（模擬） |
| `fetch_with_timeout()` | `asyncio.wait_for()` タイムアウト付きフェッチ |
| `SafeCounter` | `asyncio.Lock()` で保護された並行カウンター |
| `race_condition_demo()` | Lock あり/なしでのカウンター競合デモ |
| `producer_consumer()` | `asyncio.Queue` を使ったプロデューサー・コンシューマー |
| `limited_fetch()` | `asyncio.Semaphore` で並行数を制限したフェッチ |
| `event_demo()` | `asyncio.Event` でタスク間シグナリング |
| `run_with_timeout()` | `asyncio.wait_for` でタイムアウト制御 |
| `measure_parallel_vs_sequential()` | 並列 vs 逐次の実行時間比較 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/asyncio/fetch-all` | gather で並列フェッチ |
| GET | `/asyncio/fetch-timeout` | wait_for タイムアウト付きフェッチ |
| GET | `/asyncio/race-condition` | Lock あり/なし競合デモ |
| GET | `/asyncio/counter/increment` | Lock 保護カウンター加算 |
| GET | `/asyncio/counter` | カウンター取得 |
| POST | `/asyncio/counter/reset` | カウンターリセット |
| GET | `/asyncio/producer-consumer` | Queue プロデューサー・コンシューマー |
| POST | `/asyncio/limited-fetch` | Semaphore 並行数制限フェッチ |
| GET | `/asyncio/event` | Event シグナリング |
| GET | `/asyncio/timeout` | タイムアウト制御デモ |
| GET | `/asyncio/parallel-vs-sequential` | 並列 vs 逐次の実行時間比較 |

---

## テスト結果

**27 passed（摩擦1件: pytest-asyncio 追加が必要）**

```
27 passed in 1.22s
```

---

## 摩擦ポイント

### F-1: `pytest-asyncio` がデフォルト依存に含まれておらずエラー（深刻度: 低）

**事象**: `@pytest.mark.asyncio` を使ったテストを書いたが、`pytest-asyncio` が未インストールで `ModuleNotFoundError`。  
**原因**: FT サンドボックスの `pyproject.toml` には `pytest` しか含まれておらず、`pytest-asyncio` が未追加。  
**対応**: `uv add pytest-asyncio` で追加。今後の asyncio 系 FT では最初から依存に含める。

---

## 観察点

### 観察1: `asyncio.gather()` で複数タスクを並列実行し全完了を待つ

```python
tasks = [asyncio.create_task(fetch_simulated(url)) for url in urls]
results = list(await asyncio.gather(*tasks))
```

`asyncio.gather()` はすべてのタスクの完了を待ち、結果リストを返す。
順序はタスクの投入順が保証される（完了順ではない）。
n 個の IO 待ちタスクを並列化すると実測でほぼ n 倍速くなることを確認（speedup > 1.5倍保証）。

### 観察2: `asyncio.Lock()` でグローバル状態を保護する

```python
class SafeCounter:
    def __init__(self) -> None:
        self._count = 0
        self._lock = asyncio.Lock()

    async def increment(self) -> int:
        async with self._lock:
            self._count += 1
            return self._count
```

asyncio は GIL があるため Python の `count += 1` は通常 atomic だが、
`await asyncio.sleep(0)` 等の協調切り替えポイントがある場合、
チェックと更新の間に他のコルーチンが割り込む可能性がある。
FastAPI で `_count = await get(); await something(); await set(_count + 1)` のような分割書き込みは Lock 必須。

### 観察3: `asyncio.Semaphore` で外部 API の並行数を制限する

```python
sem = asyncio.Semaphore(3)  # 同時に3つまで

async def guarded_fetch(url: str) -> ...:
    async with sem:
        return await fetch(url)

await asyncio.gather(*[guarded_fetch(url) for url in urls])
```

外部 API・DB 接続プールには必ず Semaphore で上限を設定する。
`asyncio.gather()` に 1000 タスクを渡すと 1000 並列になり、外部サービスの DoS になりうる。

### 観察4: `asyncio.wait_for()` はキャンセル後も内部タスクが走り続ける

```python
try:
    result = await asyncio.wait_for(slow_operation(10), timeout=1.0)
except asyncio.TimeoutError:
    pass  # ← タイムアウトしたが内部の slow_operation は???
```

`asyncio.wait_for()` は `TimeoutError` 時にコルーチンに `CancelledError` を発生させる。
コルーチンが `CancelledError` を適切にハンドリングしなければリソースリークになる。
`try/finally` でクリーンアップを確実に行うパターンが必要。

### 観察5: `asyncio.Event` でタスク間の順序を保証する

```python
ready = asyncio.Event()
await ready.wait()   # シグナルを待つ
ready.set()          # シグナルを発する
```

`asyncio.Event` は `threading.Event` の非同期版。
ウェブソケット接続確立後に処理開始・DB 初期化完了後にリクエスト受付開始、などに使える。

---

## nene2-python フレームワークとの統合

- FastAPI のルートハンドラーはすべて非同期のため、`asyncio.Lock` + グローバル状態パターンは nene2 の `TtlCache[V]` に適用済み
- `asyncio.Semaphore` は外部 API 呼び出し（`httpx.AsyncClient`）の並行数制限に必須
- `asyncio.Queue` は nene2 の MCP サーバーでのメッセージキューとして直接使える
- `asyncio.wait_for()` タイムアウトは nene2 の DB クエリタイムアウトパターンに適用できる
- `asyncio.gather()` の `return_exceptions=True` オプションで個別の失敗を無視してできるだけ多く取得するパターンも有効

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`async def` と `await` の概念は FastAPI のチュートリアルで最初に触れるが、
「なぜ await が必要か」の理解が浅いまま使う傾向がある。

**ドキュメント理解**: `asyncio.gather()` の使い方は直感的。
`asyncio.Lock()` が必要な場面（グローバル状態の変更）は説明なしでは気づかない。
nene2 how-to に「FastAPI で共有状態を使う場合は Lock 必須」の例があると事故を防げる。

**事故リスク**: 高。`await` を書き忘れるとコルーチンオブジェクトが戻り値になり、
実行されないまま成功したように見えるサイレントエラーになる。mypy / ruff が検出できる。

**規約の使いやすさ**: `async with lock:` のパターンはコピペで使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

同期コードを async に変換するとき、ブロッキング処理（`time.sleep`・`open()`・`requests`）を
`await` なしで呼んでしまいイベントループをブロックするミスが多い。

**コピペ可能性**: `asyncio.gather()` と `asyncio.Semaphore()` はサンプルを見れば再現できる。

**拡張時の罠**: `asyncio.Lock()` を使わずにグローバルな `dict` を書き換えると、
同時リクエストで key が消えたりすることがある。テストでは再現しにくい。

**セキュリティ的な事故リスク**: 高。非同期 TOCTOU は認証バイパスに直結する（後述のセキュリティ診断参照）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `Promise.all()` と `asyncio.gather()` は概念的に同等。
`async/await` 構文も TypeScript と同じなので学習コストが低い。

**エラーレスポンスの質**: `asyncio.TimeoutError` が `ErrorHandlerMiddleware` で捕捉されて 500 になる場合、
クライアントには情報が少ない。エンドポイントレベルで 422 か 504 を返す設計が必要。

**事故リスク**: 中。asyncio のイベントループブロッキングは JavaScript の概念と同じで理解しやすい。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django は WSGI（同期）が主流で、非同期対応は Django 3.1+ で追加された後付け機能。
nene2-python の FastAPI は最初から非同期前提のため、`asyncio.Lock`・`asyncio.Semaphore` が設計の基本になる。

**他フレームワークとの差異**:
- Django: `django-channels` で非同期対応（後付け）
- nene2-python: FastAPI + asyncio で最初から非同期
- スレッドセーフな Django ミドルウェアの発想を asyncio に持ち込むと `threading.Lock` を使ってしまうミス

**本番投入可能性**: 問題なし。`asyncio.Semaphore` による外部 API 並行数制限は本番必須。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] グローバル/クラス変数への非同期書き込みに `asyncio.Lock()` が使われているか
- [ ] ブロッキング IO（`open()`・`requests.get()`・`time.sleep()`）をイベントループで直接呼んでいないか
- [ ] `asyncio.wait_for()` のキャンセル後にリソースリークが発生しないか（`try/finally` の確認）
- [ ] 外部 API 呼び出しに `asyncio.Semaphore` で並行数制限があるか
- [ ] `asyncio.gather(*tasks)` でエラーが1件でも起きると他タスクも失敗するが、`return_exceptions=True` が必要な場面かどうか

**チームでの安全なパターン**: 認証チェックと状態変更の間に `await` がある場合は必ず TOCTOU レビューを実施する。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高

**「初心者でも安全な API」達成度**: 中
- `SafeCounter` のように Lock を隠蔽した API を提供するパターンが必要
- グローバル状態（`_lru`・`_counter` 等）を使う場合の Lock 要件が CLAUDE.md に未記載

**設計上の負債**:
- CLAUDE.md のセキュリティポリシーに「非同期レースコンディション」が明記されていない（テンプレートにはある）
- nene2 の `TtlCache` の asyncio 安全性が明文化されていない

**Follow-up Issue 候補**: `docs: CLAUDE.md の非同期セクションに asyncio.Lock 要件を追記`

---

## セキュリティ診断（FT171 % 3 = 0）

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。
> 実装ミスが起きやすい箇所を意図的に探し、問題がなければその理由まで記録する。

### 1. OWASP API Security Top 10 (2023)

#### API1: BOLA / IDOR
- **結果**: ✅ 該当なし（ユーザー所有リソースなし）。

#### API2: 認証の破損
- **結果**: ✅ 認証なし（FT サンドボックス）。

#### API3: Mass Assignment
- **結果**: ✅ Pydantic デフォルト（extra="ignore"）で未知フィールドは無視される。

#### API4: 無制限リソース消費
- `FetchBody.urls: list[str] = Field(max_length=20)` で最大20 URL
- `LimitedFetchBody.concurrency: int = Field(ge=1, le=10)` で最大10並行
- `Queue(maxsize=3)` で back-pressure あり  
- **結果**: ✅ 全入力に上限あり。Semaphore で外部リソース使用量を制限している。

#### API5〜API10
- **結果**: ✅ 該当なし（外部 URL フェッチなし・認証エンドポイントなし）。

---

### 2. インジェクション攻撃

- **結果**: ✅ 全体的に該当なし。`demos.py` はネットワーク接続なし・ファイル操作なし・SQL なし。

---

### 3. 認証・認可

- **結果**: ✅ FT サンドボックスのため認証なし。nene2 本体の認証実装は FT165 で検証済み。

---

### 4. 入力バリデーション

- `urls`, `concurrency`, `n`, `items`, `timeout`, `duration` すべてに `max_length` または `ge/le` あり  
- **結果**: ✅ 全 HTTP 境界に型 + 範囲バリデーション済み。

---

### 5. 情報漏洩

- **結果**: ⚠️ PyJWT PYSEC-2025-183 継続中（mcp 経由）。

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### 非同期レースコンディション — **FT171 の重点診断項目**

**実測: asyncio でのグローバル状態競合**

```python
# 危険パターン — 認証チェックと処理の間に await がある
async def handler() -> str:
    if not authorized_users[user_id]:
        return "denied"
    await something()  # ← ここで他のコルーチンが user_id を無効化できる
    return do_privileged_action(user_id)
```

実測 TOCTOU デモ: `authorized_users["user1"] = True` の状態で
`check_and_use(user1)` と `revoke_in_race()` を `gather()` した結果、
**revoke タスクがチェック後に実行されたにもかかわらず `"allowed: user1"` が返った**。

これは「認証チェック → await → 権限変更 → 権限前提の操作」という TOCTOU の典型例。
FastAPI のリクエストハンドラーで認証状態をグローバルな辞書で管理する場合に発生する。

**FT171 サンドボックスの状況**: `/asyncio/counter` はグローバルな `_counter` を使用するが、
`SafeCounter` の `asyncio.Lock()` で保護されているため安全。
ただし `/asyncio/counter/increment` と `/asyncio/counter/reset` が連続して呼ばれると
意図しないカウンターリセットが起きる（これは仕様上の問題であり、セキュリティ上の問題ではない）。

**防御策（実装済み）**:
- `SafeCounter._lock = asyncio.Lock()` でインクリメントを atomic 化
- `async with self._lock:` で確認と更新を不可分に

**残存リスク**: 認証に関わるグローバル状態（セッション管理等）を asyncio アプリで持つ場合、
チェックと使用の間に `await` があれば必ず `asyncio.Lock()` でガードが必要。
nene2-python はリクエストスコープで認証状態を持ちグローバル変数に書かないため、
この問題は nene2 コアでは発生しない設計になっている。

- **結果**: ✅ FT171 スコープでは Lock で保護済み。TOCTOU の概念的リスクを記録。

#### イベントループブロッキング

```python
# 危険 — async 関数内でブロッキング IO を呼ぶ
async def bad_handler() -> None:
    time.sleep(5)         # ← イベントループ全体を5秒ブロック
    data = open("file.txt").read()  # ← sync IO でブロック
    requests.get(url)     # ← sync HTTP でブロック
```

FastAPI は `asyncio.run_in_executor()` または `await asyncio.to_thread()` で
同期処理を別スレッドに委ねることができる。
FT171 のデモ関数はすべて `asyncio.sleep()` を使い、ブロッキング処理なし。

- **結果**: ✅ FT171 内にブロッキング IO なし。

#### `asyncio.wait_for()` キャンセルリーク

`asyncio.wait_for()` タイムアウト時、内部コルーチンに `CancelledError` が発生する。
コルーチンが `CancelledError` を `except Exception:` で握りつぶすと、
タスクが完了せずリソースがリークする可能性がある。

FT171 の `slow_operation()` は `asyncio.sleep()` のみを使っており、
`CancelledError` は `asyncio.sleep()` から正しく伝播する。

- **結果**: ✅ `slow_operation()` はキャンセル安全。

#### Semaphore 枯渇

`asyncio.Semaphore(n)` を使っても、コルーチン内で例外が発生した場合
`async with sem:` ブロックが `__aexit__` を呼んでセマフォを解放するかが重要。
Python の `async with` は例外時も `__aexit__` を保証するため安全。

- **結果**: ✅ `async with sem:` は例外時も正しく解放される。

#### pickle / yaml
- **結果**: ✅ 該当なし。

#### 型強制攻撃 (Pydantic)
- `concurrency: int = Field(ge=1, le=10)` — `"3"` 文字列は int 変換後に範囲チェック
- **結果**: ✅ 範囲制限が適切。

---

### 7. 依存関係スキャン

```
Found 1 known vulnerability: pyjwt 2.12.1 PYSEC-2025-183 (mcp 経由)
```

- **スキャン結果**: 継続中（FT168 から変更なし）
- **対応方針**: mcp の更新を待つ

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | 無制限リソース消費: Semaphore で適切に制限 |
| インジェクション攻撃 | ✅ | 該当なし |
| 認証・認可 | ✅ | FT サンドボックス |
| 入力バリデーション | ✅ | 全境界に ge/le/max_length あり |
| 情報漏洩 | ⚠️ | PyJWT 継続中 |
| **非同期レースコンディション** | ✅ | Lock で保護済み。TOCTOU 概念リスクを文書化 |
| イベントループブロッキング | ✅ | ブロッキング IO なし |
| asyncio.wait_for キャンセルリーク | ✅ | 正しくキャンセル伝播 |
| Semaphore 枯渇 | ✅ | async with が例外時も解放 |
| 依存関係 CVE | ⚠️ | PYSEC-2025-183（継続中） |

**総合評価**: 合格  
**発見した新規脆弱性**: 0件  
**セキュリティ観察**: TOCTOU パターンの概念リスクを記録（FT171 実装では発生しない設計）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | `docs: CLAUDE.md の非同期セクションに asyncio.Lock 要件と TOCTOU 注意点を追記` | docs |
| 中 | `docs: FastAPI でブロッキング IO を asyncio.to_thread() で安全に実行する how-to` | docs |
| 低 | `feat: TtlCache の asyncio 安全性（Lock 保護）を明文化しテストを追加` | feat |

---

## まとめ

`asyncio` モジュールは nene2-python の FastAPI 基盤に直結する重要機能。
27 テスト全通過（摩擦1件: pytest-asyncio の追加が必要）。

**セキュリティ診断**: 非同期レースコンディションの実測デモを実施した。
TOCTOU（認証チェック後に `await` を挟んで状態変更が入るパターン）が概念的リスクとして存在するが、
FT171 の実装では `asyncio.Lock()` で保護されているため安全。
Semaphore による外部リソース並行数制限・`asyncio.wait_for()` のキャンセル安全性も確認した。

`asyncio.gather()` による並列化（最大5倍高速化確認）・`asyncio.Semaphore` による流量制御・
`asyncio.Queue` によるプロデューサー・コンシューマーパターンが nene2 本番実装で直接使えるパターンとして確立された。

