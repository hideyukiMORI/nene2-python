# FT75: ミドルウェアスタック順序依存性の実運用検証

**日付**: 2026-05-20  
**テーマ**: Starlette LIFO ミドルウェア順序の落とし穴 — エラーレスポンスにヘッダーが付かない問題  
**バージョン**: v1.8.20  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft75-middleware-order/`

---

## 概要

nene2 が提供する 6 つのミドルウェアを組み合わせた際の順序依存バグを検証した。
「ErrorHandler を最外側に」という直感が **間違い** であることを実際のテストで実証し、
全レスポンスに X-Request-Id とセキュリティヘッダーを付与するための正しい順序を確認した。

---

## 発見した問題

### Starlette BaseHTTPMiddleware の動作原理

`app.add_middleware(X)` は **LIFO**（後から追加したものが外側になる）で積まれる。

```python
app.add_middleware(A)  # 内側
app.add_middleware(B)  # 外側
# スタック: B(A(Router))
# リクエスト: B → A → Router
# レスポンス: Router → A → B
```

### 落とし穴: ErrorHandler を最外側にすると何が起きるか

```python
# 「直感」による書き方
app.add_middleware(RequestIdMiddleware)       # 内側
app.add_middleware(SecurityHeadersMiddleware) # 内側
app.add_middleware(ErrorHandlerMiddleware)    # 最外側（最後に追加）

# スタック: ErrorHandler(SecurityHeaders(RequestId(Router)))
```

ハンドラーが例外を raise すると:
1. `ErrorHandlerMiddleware.dispatch` が例外を捕捉
2. `problem_details_response(...)` で **新しい Response を直接 return**
3. この Response は内側の `SecurityHeaders` も `RequestId` も **通過しない**
4. 結果: **500 エラーに X-Request-Id もセキュリティヘッダーも付かない**

### 正しい順序

ErrorHandler を **最内側** に置き、RequestId と SecurityHeaders を **外側** に置く。

```python
# 正しい書き方（最初に add するものが最内側）
app.add_middleware(ErrorHandlerMiddleware)           # 最内側
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ThrottleMiddleware, ...)
app.add_middleware(RequestSizeLimitMiddleware, ...)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)              # 最外側

# スタック: RequestId(SecurityHeaders(SizeLimit(Throttle(RequestLogging(ErrorHandler(Router))))))
# 全レスポンス（エラー含む）が SecurityHeaders と RequestId を通過する ✓
```

---

## テスト結果

**10/10 passed**

| テスト | 結果 | 観察内容 |
|---|---|---|
| `test_correct_order_500_is_problem_details` | PASSED | ErrorHandler は内側でも 500 を捕捉できる |
| `test_correct_order_500_has_request_id` | PASSED | RequestId が外側 → 500 にも付く |
| `test_correct_order_500_has_security_headers` | PASSED | SecurityHeaders が外側 → 500 にも付く |
| `test_correct_order_413_is_problem_details` | PASSED | SizeLimitMiddleware は内部で直接 problem_details_response を返す |
| `test_correct_order_413_has_request_id` | PASSED | 413 にも X-Request-Id が付く |
| `test_correct_order_413_has_security_headers` | PASSED | 413 にもセキュリティヘッダーが付く |
| `test_naive_order_500_missing_request_id` | PASSED | 直感的順序だと 500 に X-Request-Id が**付かない**ことを実証 |
| `test_naive_order_500_missing_security_headers` | PASSED | 直感的順序だと 500 にセキュリティヘッダーが**付かない**ことを実証 |

---

## Friction Points

### 🔴 重大: ミドルウェア推奨順序がドキュメント化されていない

`add_middleware` の呼び出し順序について nene2 のドキュメントに推奨順序が存在しない。
Starlette の LIFO 動作は非直感的であり、「ErrorHandler が最外側にあるべき」という誤解を招きやすい。

実際の影響:
- **ErrorHandler を最外側に置く（最後に add する）と** 500 エラーに X-Request-Id が付かない
- **Security audit で「エラーレスポンスにセキュリティヘッダーがない」と指摘される**
- 本番環境で気づかずに運用してしまう可能性が高い

**推奨順序（コメント付き）をドキュメントに追加すべき。**

---

## 使用感（主観評価）

**直感性: ★★☆☆☆**  
LIFO の仕組みを知っていても、「外側に置きたいものを後から add する」という逆転発想は
毎回確認しないと間違える。Express.js でも同じ罠があり、FastAPI/Starlette ユーザーが
最も頻繁にハマる問題のひとつ。

**実害の深刻さ: ★★★★★**  
単に動かない（すぐ気づく）ではなく、**動くが一部の非機能要件が欠落する**パターン。
Security headers がエラーページだけ欠落していても CI は通るし、
X-Request-Id がエラーレスポンスにないことはログ追跡するまで気づかない。

**修正のしやすさ: ★★★★★**  
順序を正しくするだけなので、原因がわかれば修正は 1 分。
問題は「原因に気づく」のが遅いこと。

**フレームワーク側で改善できること**:  
CLAUDE.md や how-to ガイドに推奨スタック順序を明記するだけで解決できる。
ミドルウェアを `ErrorHandlerMiddleware.install()` のように一括登録する
`setup_middlewares(app)` ユーティリティがあると事故を防げる。

---

## 結論

ミドルウェア順序のバグは **動作するが静かに壊れている** 類の問題で、
実際の本番事故に直結しやすい。正しい順序（ErrorHandler 最内側・RequestId 最外側）を
nene2 の公式ドキュメントと CLAUDE.md に追記することを強く推奨する。
