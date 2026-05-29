# FT270: ssl — create_default_context の検証既定

**日付**: 2026-05-29
**テーマ**: Python `ssl` モジュールの TLS クライアント検証設定の実装と検証
**セキュリティ診断**: 🔒 あり（270 % 3 = 0）
**クラッカーペンテスト**: なし（270 % 4 = 2）

---

## 概要

TLS クライアントは**証明書検証を必ず有効**にしなければならない。`check_hostname=False` や `verify_mode=CERT_NONE` は中間者攻撃（MITM）を許す。`ssl.create_default_context()` はセキュアな既定（検証有効）を提供する。本 FT はネットワーク接続をせず、セキュアコンテキストの設定値確認と「検証無効化を拒否する」原則を診断した。

| API | 性質 |
|---|---|
| `ssl.create_default_context()` | check_hostname=True / CERT_REQUIRED |
| `context.minimum_version` | 最低 TLS バージョン |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft270-ssl/`

| 関数 | 概要 |
|---|---|
| `build_secure_context()` | セキュアコンテキスト構築、verify=False は拒否 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/tls/context` | セキュア TLS コンテキストを構築 |

---

## 摩擦点

### F-1: 証明書検証を無効化しない（check_hostname / CERT_REQUIRED）

**観察**: `context.check_hostname = False` や `context.verify_mode = ssl.CERT_NONE` は TLS の中間者攻撃防御を無力化する。「証明書エラーを回避するため」と安易に無効化するのが事故の典型。

**対処**: `create_default_context()` の既定（check_hostname=True / CERT_REQUIRED）を維持し、無効化要求は 422 で拒否。診断で `verify=False` を拒否・`is_secure=True` を確認。

### F-2: 最低 TLS バージョンを 1.2 以上にする

**観察**: 古い TLS 1.0/1.1 は既知の脆弱性があり非推奨。`minimum_version` を上げないと古いプロトコルでネゴシエートされる可能性。

**対処**: `context.minimum_version = ssl.TLSVersion.TLSv1_2`。診断で最低 TLS 1.2 を確認（現代の Python は既定でも 1.2）。

### F-3: ネットワーク接続をしない検証

**観察**: TLS の正しさは接続して初めて分かるが、本 FT は CI/サンドボックスで再現可能にするため**コンテキストの設定値のみ**を確認する。

**対処**: 接続せず `create_default_context()` のプロパティを検証。実接続時はこの context を `urllib`/`httpx` に渡す。

---

## セキュリティ診断結果

| カテゴリ | 結果 |
|---|---|
| check_hostname | **True** |
| verify_mode | **CERT_REQUIRED** |
| minimum_tls_version | **TLSv1_2** |
| is_secure | **True** |
| 検証無効化（verify=False） | **422**（拒否） |
| デフォルト（verify 省略） | **is_secure=True** |
| セキュリティヘッダー | 付与あり |

**総合評価: 合格**

`create_default_context` のセキュア既定を維持し、検証無効化を拒否。MITM を許す設定（CERT_NONE/check_hostname=False）を作れない設計。

---

## テスト結果

```
4 passed in 0.93s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「証明書エラーが出たから検証を切る」は危険と知れる。デフォルトが安全なのが安心。

**ドキュメント理解**: MITM の説明をコメントで明示。
**事故リスク（高）**: 証明書エラー回避で verify を切る。
**規約の使いやすさ**: verify → context 情報が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

外部 API 連携で `verify=False` を使う事故が多い（requests/httpx でも）。本 FT が拒否する設計は良い教材。

**コピペ可能性**: build_secure_context は流用可。
**拡張時の罠**: 検証無効化・古い TLS。
**事故リスク（高）**: verify=False の常用。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`NODE_TLS_REJECT_UNAUTHORIZED=0` の危険と同じ。検証を切らない原則は共通。

**エラーレスポンスの質**: 無効化は 422。
**Python 固有概念**: SSLContext・TLSVersion。
**事故リスク（低）**: 既定でセキュア。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`requests(verify=False)`/`httpx(verify=False)` は本番厳禁。自己署名証明書は CA バンドルに追加するのが正道。最低 TLS 1.2/1.3 の強制も重要。

**他フレームワークとの差異**: どの HTTP クライアントも検証無効化は厳禁。
**nene2 の薄さへの評価**: 検証無効化を構造的に拒否する設計が良い。
**事故リスク（低）**: セキュア既定。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `verify=False`/`CERT_NONE`/`check_hostname=False` を使っていないか（MITM）。
- 最低 TLS バージョン（1.2 以上）を設定しているか。
- 自己署名証明書を検証無効化で回避していないか（CA バンドルに追加）。
- create_default_context を使っているか（手組みの context は設定漏れリスク）。

**チームでの安全なパターン**: create_default_context + minimum TLS 1.2、検証無効化を lint/レビューで禁止。
**事故リスク（低）**: 無効化を拒否。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 「セキュリティは設計の出発点」を体現。Pydantic 制限・`ValidationException` 変換・`logging` 使用も準拠。
**初心者でも安全な API 達成度**: セキュア既定を維持し検証無効化を拒否、MITM 設定の余地を排除。
**改善提案**: 外部 HTTP クライアント（httpx）使用時も verify=False を禁止する旨を how-to に明記する。
