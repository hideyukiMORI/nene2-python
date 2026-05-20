# Field Trial 35: 混合認証（Bearer Token OR API Key）実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.3 時点
**テーマ**: `BearerTokenMiddleware` と `ApiKeyAuthMiddleware` の組み合わせパターン、
および「いずれか一方で可（OR 条件）」認証の実装コストを確認する

---

## 概要

Bearer Token 専用・API Key 専用の各ベースラインを確認した後、
2 つのミドルウェアをスタックした場合の挙動と、
OR 条件認証のカスタム実装を比較した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft35-mixed-auth/` に以下を作成:

- **`app.py`** — 4 パターンのアプリ（Bearer のみ・API Key のみ・両方スタック・EitherOr カスタム）
- **`test_app.py`** — 全パターンの動作検証 (13 件)
- **`test_friction.py`** — 摩擦点の確認テスト (3 件)

**テスト結果**: 16 件全通過 ✅

---

## 摩擦点

### FP35-1: ミドルウェアを2つスタックすると AND 条件になる

**分類**: 摩擦あり（設計上の制約）

`BearerTokenMiddleware` と `ApiKeyAuthMiddleware` を両方 `add_middleware` すると、
各ミドルウェアが独立して検証するため「両方必須（AND）」になる。
Bearer Token のみ・API Key のみの場合どちらも 401。

```python
# この設定は AND 条件（両方必須）
app.add_middleware(ApiKeyAuthMiddleware, ...)
app.add_middleware(BearerTokenMiddleware, ...)
```

**判断**: Starlette のミドルウェアスタックの仕様通り。
`configure-auth.md` に明記し、AND と OR の違いを説明する。

---

### FP35-2: OR 条件の認証にはカスタムミドルウェアの実装が必要

**分類**: 摩擦あり（実装コスト発生）

「Bearer または API Key のいずれかで可」を実現するには
`BaseHTTPMiddleware` を継承してカスタム実装する必要がある。
フレームワークに汎用 OR ミドルウェアはない。

ただし、`LocalTokenVerifier` / `TokenVerifierProtocol` は再利用可能なため、
カスタム実装のコードは約 30 行と軽量。

**判断**: OR 条件の仕様はプロジェクトによって多様すぎるため、
フレームワークが汎用実装を提供するより、パターンをドキュメントで示す方が適切。

**対応**: `docs/how-to/configure-auth.md` に `EitherOrAuthMiddleware` パターンを追記。

---

### FP35-3: TokenVerifierProtocol の再利用性が高い（好印象）

**分類**: 良い設計の確認

`LocalTokenVerifier` はそのままカスタムミドルウェア内で使えるため、
トークン比較ロジック（`secrets.compare_digest`）を重複実装する必要がない。
Protocol 分離の設計が効いている。

---

## フレームワーク変更

- `docs/how-to/configure-auth.md` に「AND / OR の違い」と `EitherOrAuthMiddleware` パターンを追記 (FP35-1, FP35-2 対応)

---

## 関連

- `nene2.auth.BearerTokenMiddleware`
- `nene2.auth.ApiKeyAuthMiddleware`
- `nene2.auth.LocalTokenVerifier`
- FT11 (exclude_paths, LocalTokenVerifier.from_env, v1.4.0)
