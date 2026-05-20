# Field Trial 40: 多ドメイン連携（Article + Tag 紐付け）実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.4 時点
**テーマ**: 1 つの UseCase が 2 つのリポジトリ（Article + Tag）を横断するパターンの実運用確認

---

## 概要

`TagArticleUseCase` が `InMemoryArticleRepository` と `InMemoryTagRepository` を
コンストラクタインジェクションで受け取り、記事へのタグ付けを管理するパターンを実装した。
複数の無効 TagId がある場合に `ValidationException` で全エラーを一度に収集するパターンも確認。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft40-multi-domain/` に以下を作成:

- **`app.py`** — Article + Tag の 2 ドメインを跨ぐ `TagArticleUseCase` と FastAPI エンドポイント
- **`test_app.py`** — 正常タグ付け・不正タグ・404・複数バリデーションエラー (7 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 11 件全通過 ✅

---

## 摩擦点

### FP40-1: 複数リポジトリを受け取る UseCase は自然に書ける（良い設計）

**分類**: 摩擦なし（設計の確認）

フレームワークは UseCase 構造に制約を課さないため、
複数のリポジトリを `__init__` で受け取るパターンが素直に実装できる。
CLAUDE.md の「UseCase は他の UseCase を呼ばない」ルールに従い、
各リポジトリを直接呼ぶことで依存関係がシンプルに保たれる。

---

### FP40-2: カスタムドメイン例外は SimpleDomainHandler 登録が必要

**分類**: 軽微な摩擦（設計通り・注意喚起）

`ValidationException` は `ErrorHandlerMiddleware` が自動で 422 に変換するが、
`ArticleNotFoundException` のようなカスタムドメイン例外は
`SimpleDomainHandler` を明示的に登録しないと 500 になる。
登録を忘れると意図しない 500 レスポンスになるため注意が必要。

```python
# 忘れると 500 になる
handlers = [
    SimpleDomainHandler(ArticleNotFoundException, "article-not-found", "Not Found", 404),
]
app.add_middleware(ErrorHandlerMiddleware, domain_handlers=handlers)
```

**判断**: ドメイン例外の HTTP マッピングを明示的にする設計は正しい。
`configure-auth.md` と同様に how-to ドキュメントでパターンを示す価値がある。

---

### FP40-3: 複数ドメイン横断バリデーションエラーを一括収集できる

**分類**: 良い設計の確認

`ValidationException` リストにエラーを積み上げてから raise するパターンで、
複数の無効 TagId を一度のリクエストでまとめてクライアントに通知できる。
FT33 で確認した `ValidationCode(StrEnum)` パターンと組み合わせると更に型安全になる。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.use_case.UseCaseProtocol`
- `nene2.validation.ValidationException`
- `nene2.middleware.SimpleDomainHandler`
- FT13 (ValidationException 実運用, v1.6.0)
- FT21 (SimpleDomainHandler 実装, v1.8.0)
- FT33 (ValidationCode StrEnum パターン, v1.8.3)
