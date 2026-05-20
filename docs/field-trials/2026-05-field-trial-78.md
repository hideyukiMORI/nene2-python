# FT78: ThrottleMiddleware 境界動作

**日付**: 2026-05-20  
**テーマ**: レート制限のウィンドウリセット・バースト動作・path_limits の挙動検証  
**バージョン**: v1.8.23  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft78-throttle-boundary/`

---

## 概要

`ThrottleMiddleware` の境界動作を詳細に検証した。
基本機能（429 返却、Retry-After ヘッダー、path_limits）は期待通り動作した。
一方で、Fixed Window アルゴリズムの構造的な制限と、
マルチプロセス環境での in-memory 共有不可という制約が明確になった。

---

## 動作確認

### 429 レスポンス形式

```json
{
  "type": "https://httpstatuses.com/too-many-requests",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded. Retry after 58 seconds."
}
```

Retry-After ヘッダーあり ✅

### レート制限ヘッダー（全レスポンスに付与）

```
X-RateLimit-Limit: 3
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1747742980
```

全レスポンス（200 も 429 も）にヘッダーが付く ✅

### path_limits: グローバルカウンターと独立 ✅

```python
app.add_middleware(ThrottleMiddleware, limit=100, path_limits={"/api/search": 5})
```

`/api/search` の制限 (5) は `/api/data` のグローバル制限 (100) と完全に独立。

---

## 発見した問題

### 問題1: Fixed Window バースト問題（設計上の制限）

固定ウィンドウ方式では、ウィンドウ境界で最大 `2 × limit` のリクエストが短時間に通過できる。

```
window=60s, limit=3 の場合:
  t=59s: 3 req 通過（ウィンドウ1の末尾）
  t=61s: 3 req 通過（ウィンドウ2の先頭）
  → 2秒間に 6 req が通ってしまう
```

Flask-Limiter デフォルトの Sliding Window では防げるが、
nene2 は計算コストの低い Fixed Window を採用している。

ドキュメントにこの制限を明記すべき。

### 問題2: in-memory カウンターはマルチプロセス非対応

`_counts` は Python の `dict` で保持されており、
複数の uvicorn ワーカー（`gunicorn -w 4`）や Docker Pod では共有されない。

実効的な制限は `limit × worker_count` になる。
本番で水平スケールさせると全くレート制限が機能しない。

**ドキュメントに警告はある**（コードの docstring）が、README や使用例には書かれていない。

### 問題3: カウント状態の観察手段がない

現在のカウント状態（「このIPが今 N/M 消費」）を外部から取得する手段がない。
デバッグ時に困る。

```python
# これが欲しいが存在しない
info = middleware.get_rate_info(ip="192.168.1.1")
print(info.current_count, info.remaining)
```

### 問題4: exclude_paths はヘッダーも返さない

除外パスにはレート制限ヘッダーが一切付かない。
クライアントが「このパスは制限外か？」を知る方法がない。

---

## テスト結果（全14件パス）

```
test_requests_within_limit_are_allowed              PASSED
test_exceeding_limit_returns_429                    PASSED
test_429_response_is_problem_details                PASSED
test_rate_limit_headers_present_on_200              PASSED
test_rate_limit_remaining_decrements                PASSED
test_retry_after_header_present_on_429              PASSED
test_retry_after_reasonable_value                   PASSED
test_path_limits_independent_from_global            PASSED
test_path_limits_headers_show_path_limit            PASSED
test_exclude_paths_bypass_throttle                  PASSED
test_window_resets_after_elapsed                    PASSED
test_friction_no_global_ip_tracking_visible_to_user PASSED
test_friction_in_memory_state_not_shared_across_workers  PASSED
test_friction_fixed_window_burst_at_boundary        PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F78-1 | Fixed Window バースト問題がドキュメントに明記されていない | 中 |
| F78-2 | マルチプロセス非対応（in-memory）がドキュメントに明記されていない | 高 |
| F78-3 | カウント状態の観察 API がない | 低 |
| F78-4 | exclude_paths のパスにレート制限ヘッダーが付かない | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

`setup_middlewares(app, throttle_limit=60, throttle_window=60)` で一発設定できる点は非常に快適。
`path_limits` / `exclude_paths` のパラメーター名も直感的。
`Retry-After` が自動で付くのはエレガント。

### 実害の深刻さ ★★★★☆

マルチプロセス非対応は本番で深刻。
「レート制限を設定したのに効いていない」というデバッグは非常に時間がかかる。
ただし docstring に警告が書かれており、見れば分かる（見逃しやすいが）。

### 修正のしやすさ ★★★★★

ドキュメント追記のみで対応できる問題が多い。
実装変更（Redis 対応）は将来的な機能拡張として Issues に記録する程度でよい。

### 総合コメント

基本機能は非常によくできている。
問題は「制限の文書化」が不足している点。
Fixed Window の特性とマルチプロセス制約を README や使用例に追記するだけで
UX が大幅に改善する。実装は変えなくてよい。

---

## 推奨アクション

1. **Issue**: ThrottleMiddleware のドキュメントに Fixed Window バースト特性を追記
2. **Issue**: ThrottleMiddleware のドキュメントにマルチプロセス非対応の警告を目立つ位置に追記
3. **将来**: Redis カウンターバックエンドの検討（外部依存なので慎重に）
