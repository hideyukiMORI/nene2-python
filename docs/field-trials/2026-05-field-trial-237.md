# FT237: http.cookies — SimpleCookie / Morsel（クッキーインジェクション対策）

**日付**: 2026-05-29
**テーマ**: Python `http.cookies` のクッキー生成・解析とセキュア属性の実装と検証
**セキュリティ診断**: 🔒 あり（237 % 3 = 0）
**クラッカーペンテスト**: なし（237 % 4 = 1）

---

## 概要

`http.cookies` はクッキーの生成（`SimpleCookie`/`Morsel`）と解析を提供する。HTTP API でラップし、**クッキーインジェクション**（`;`/CRLF/制御文字で属性や追加クッキー・ヘッダーを注入）の遮断と、**セキュア属性**（HttpOnly / Secure / SameSite）の既定付与を検証した。診断回（237 % 3 = 0）。

| API | ユースケース |
|---|---|
| `SimpleCookie()[name] = value` | クッキー生成 |
| `Morsel["httponly"/"secure"/"samesite"]` | セキュア属性付与 |
| `SimpleCookie().load(header)` | Cookie ヘッダー解析 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft237-http-cookies/`

| 関数 | 概要 |
|---|---|
| `build_set_cookie()` | name/value を厳格検証し HttpOnly/Secure/SameSite=Lax/Path=/ で生成 |
| `parse_cookie_header()` | Cookie ヘッダーを名前→値の辞書に解析 |
| `_NAME_RE` / `_VALUE_RE` | RFC 6265 準拠の token / cookie-octet 検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/cookie/build` | セキュアな Set-Cookie 生成 |
| POST | `/cookie/parse` | Cookie ヘッダー解析 |

---

## 摩擦点

### F-1: name/value を検証しないとクッキー/ヘッダーインジェクションが通る

**観察**: クッキー値に `;`・空白・CRLF・制御文字を含めると、`session=tok; Domain=evil.com` のように**属性を注入**したり、CRLF で**追加の Set-Cookie やレスポンスヘッダーを注入**できる。`SimpleCookie` は不正値で `CookieError` を出す場合もあるが、頼り切らず入力側で弾くべき。

**対処**: name は RFC 6265 token（`_NAME_RE`）、value は制御文字・空白・`" , ; \` を含まない cookie-octet（`_VALUE_RE`）で検証。診断で `v; Domain=evil.com`・`\r\nSet-Cookie:`・null バイト・空白・`,`・`\` がすべて 422 になることを確認。

### F-2: セキュア属性はデフォルトで付与する

**観察**: `SimpleCookie` は HttpOnly/Secure/SameSite を**何も付けない**。付け忘れると XSS でのトークン窃取（HttpOnly 無し）・HTTP 平文送信（Secure 無し）・CSRF（SameSite 無し）のリスク。

**対処**: `build_set_cookie` で `httponly=True`・`secure=True`・`samesite="Lax"`・`path="/"` を既定付与。出力は `session=tok; HttpOnly; Path=/; SameSite=Lax; Secure`。

### F-3: `SimpleCookie.load` は不正入力で fail-closed（全破棄）

**観察**: `load("a=1; evil=2\r\nX-Injected: 1; b=3")` のような CRLF 混入ヘッダーを解析すると、`SimpleCookie` は**全体を破棄して空**を返す（`{}`）。部分的に注入が漏れることはない（fail-closed）。

**対処**: この挙動を信頼しつつヘッダー長も制限。解析結果は名前→値の素朴な辞書に正規化。

---

## セキュリティ診断結果

| カテゴリ | 例 | 結果 |
|---|---|---|
| 値インジェクション | `v; Domain=evil.com` / `v; Secure` / `a;HttpOnly` | **422** |
| CRLF ヘッダー注入 | `a\r\nSet-Cookie: x=y` | **422** |
| 制御文字 / 区切り | null `a\x00b` / 空白 / `"` / `,` / `\` | **422** |
| 名前インジェクション | `a=b` / `a;b` / `a b` / `a\r\nb` / `a,b` / 空 | **422** |
| 正規 | `session` / `__Host-id` / `ok123` | **200** |
| セキュア既定 | — | `HttpOnly; Path=/; SameSite=Lax; Secure` 付与 |
| parse CRLF 混入 | `a=1; evil=2\r\nX-Injected...` | **200 `{}`**（fail-closed） |
| DoS | value 1,001 / header 4,001 | **422** |

**総合評価: 合格**

name/value の RFC 準拠検証でクッキー・ヘッダーインジェクションを全遮断し、HttpOnly/Secure/SameSite を既定付与。`SimpleCookie.load` の fail-closed 挙動も確認。

---

## テスト結果

```
6 passed in 0.81s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

クッキーの生成・解析は理解しやすい。HttpOnly/Secure/SameSite の意味は学ぶ必要があるが、既定で付くので安全。

**ドキュメント理解**: セキュア属性の意味はコメントで補足。
**事故リスク（中）**: 生 `SimpleCookie` を使い属性を付け忘れる。
**規約の使いやすさ**: name/value → Set-Cookie が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

セッションクッキーやプリファレンス保存で使う。`;` 混入のインジェクションは知らないと作り込む。

**コピペ可能性**: `build_set_cookie` はそのまま流用可。
**拡張時の罠**: 値の検証を省く・セキュア属性を付け忘れる。
**事故リスク（中）**: インジェクション・属性欠如。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`document.cookie` と対応。HttpOnly が付くと JS から読めない理由（XSS 対策）が分かる。

**エラーレスポンスの質**: 不正は 422。
**Python 固有概念**: `Morsel` の属性 API。
**事故リスク（低）**: 既定でセキュア。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `set_cookie(secure, httponly, samesite)` と同じ。`__Host-` プレフィックスの活用や SameSite=Strict/Lax の選択は要件次第。

**他フレームワークとの差異**: フレームワークが既定で付ける箇所を素の SimpleCookie では自前付与。
**nene2 の薄さへの評価**: セキュア既定 + 検証を足す設計は妥当。
**事故リスク（低）**: 診断で全遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- クッキー name/value を RFC token/octet で検証しているか（インジェクション）。
- HttpOnly/Secure/SameSite を既定付与しているか。
- CRLF/制御文字を弾いているか（ヘッダーインジェクション）。
- セッションクッキーに `__Host-`/`__Secure-` プレフィックスを検討しているか。

**チームでの安全なパターン**: クッキー生成は `build_set_cookie` 経由に統一し、生 SimpleCookie を禁止。
**事故リスク（低）**: 診断を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 入力検証・`ValidationException` 変換・`logging` 使用・セキュリティヘッダー（ミドルウェア）は準拠。セキュア既定は「セキュリティは設計の出発点」。
**初心者でも安全な API 達成度**: セキュア属性を既定付与し検証を関数内に隠蔽、インジェクション・属性欠如の余地を排除。
**改善提案**: `build_set_cookie` を `nene2.http` に「セキュアクッキービルダー」として昇格し、`__Host-` プレフィックス対応・SameSite 選択を引数化する。
