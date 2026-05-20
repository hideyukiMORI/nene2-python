# FT21: DomainExceptionHandler 実運用検証

**日付**: 2026-05-20
**テーマ**: `DomainExceptionHandlerProtocol` を使ったカスタム例外ハンドリングの実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft21-domain-exception/`

---

## 目的

`nene2.middleware.ErrorHandlerMiddleware` の `domain_handlers` オプションを使い、
複数のカスタムドメイン例外を Problem Details に変換するパターンを検証する。

---

## 実施内容

ブログ記事 API（`/posts/{post_id}`）を作成し、以下のドメイン例外を実装:

- `PostNotFoundError` → 404 problem-details
- `PostAccessDeniedError` → 403 problem-details
- `PostAlreadyPublishedError` → 409 problem-details

各例外に対応する `DomainExceptionHandlerProtocol` 実装クラスを作成し、
`ErrorHandlerMiddleware(domain_handlers=[...])` に登録。

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_get_existing_post_returns_200 | PASS |
| test_get_nonexistent_post_returns_404_problem_details | PASS |
| test_get_other_users_post_returns_403 | PASS |
| test_publish_already_published_returns_409 | PASS |
| test_publish_unpublished_post_succeeds | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_no_base_class_for_domain_exception_handlers | PASS | あり |
| test_handler_registration_requires_list_at_middleware_init | PASS | あり（軽微） |
| test_unregistered_exception_falls_through_to_500 | PASS | あり（仕様だが摩擦） |

---

## 発見した摩擦点

### FT21-F1: DomainExceptionHandler のボイラープレートが多い

**概要**: `DomainExceptionHandlerProtocol` を満たすクラスを毎回 `handles()`/`handle()` の
2 メソッドで実装する必要がある。多くのケースでパターンは同じ:
1. `isinstance()` チェック
2. `problem_details_response()` を呼ぶ

**影響**: 3 つのドメイン例外に対して 3 つのハンドラークラスを書かなければならず、
コード量が増える。

**期待する解決策**:
```python
# 現状（各例外ごとにクラスが必要）
class PostNotFoundHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, PostNotFoundError)
    def handle(self, exc: Exception) -> Response:
        return problem_details_response("post-not-found", "Not Found", 404)

# 期待: ファクトリで一行
handler = SimpleDomainHandler(PostNotFoundError, "post-not-found", "Post Not Found", 404)
```

---

### FT21-F2: ハンドラーをミドルウェア初期化時にしか登録できない

**概要**: `ErrorHandlerMiddleware` に `register_handler()` や `add_handler()` のような
動的登録メソッドがないため、ミドルウェア初期化時に全ハンドラーをリストで渡す必要がある。

**影響**: ドメインモジュールが分散している場合、一箇所に集めて渡す必要がある。
（これは設計上妥当とも言えるが、大規模プロジェクトでは不便）

**判断**: 初期化時一括登録は依存関係が明示的で好ましい設計のため、今回は修正しない。

---

### FT21-F3: 未登録ドメイン例外は 500 にフォールスルーする

**概要**: `domain_handlers` への登録を忘れると 500 応答になる。
ログを確認しないと原因が分からない。

**判断**: `debug=True` で例外メッセージが `detail` に含まれるため、
開発中は `ErrorHandlerMiddleware(debug=True)` を使えばデバッグ可能。
ドキュメントに明記する対応が適切。

---

## まとめ

`DomainExceptionHandlerProtocol` + `ErrorHandlerMiddleware` の組み合わせは機能するが、
各例外ごとにクラスを 1 つ書く必要があるボイラープレートが摩擦の主な原因。

`SimpleDomainHandler` ファクトリを追加することで DX が大幅に向上する（FT21-F1 → Issue化・修正対象）。
