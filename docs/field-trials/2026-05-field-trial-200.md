# FT200: base64 モジュール — Base64 エンコード・デコード・URL セーフ変換

**日付**: 2026-05-22
**テーマ**: Python `base64` モジュールの標準/URL セーフ Base64 エンコード・デコード・バリデーションの実装と検証
**セキュリティ診断**: なし（200 % 3 = 2）
**クラッカーペンテスト**: **あり**（200 % 4 = 0）

---

## 概要

`base64` は Python 標準ライブラリのバイナリ-テキスト変換モジュール。
`b64encode` / `b64decode`（標準形式）と `urlsafe_b64encode` / `urlsafe_b64decode`（URL セーフ形式）が
主要な API。JWT のペイロード部分や HTTP Authorization ヘッダーでも用いられるため、
パディング処理とデコード失敗のハンドリングが実装上の主要な関心事になる。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft200-base64/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `encode_text(text, url_safe)` | テキストを Base64 エンコードして `EncodeResult` を返す |
| `decode_text(encoded, url_safe)` | Base64 をデコードして UTF-8 テキストとして返す（失敗は `is_valid=False`） |
| `encode_bytes_to_str(data, url_safe)` | バイト列を Base64 文字列にエンコード |
| `encode_url_safe(text)` | URL セーフ Base64 エンコードのショートカット |
| `decode_url_safe(encoded)` | URL セーフ Base64 デコードのショートカット |
| `validate_base64(encoded, url_safe)` | 文字列が有効な Base64 かを検証して `ValidationResult` を返す |
| `EncodeResult` | original_bytes / encoded / url_safe を保持する frozen dataclass |
| `DecodeResult` | decoded_bytes / decoded_text / is_valid / reason を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/base64/encode` | テキストを Base64 エンコード（標準または URL セーフ） |
| POST | `/base64/decode` | Base64 をデコード（失敗は 422） |
| POST | `/base64/encode/url-safe` | URL セーフ Base64 エンコード専用 |
| POST | `/base64/decode/url-safe` | URL セーフ Base64 デコード専用 |
| POST | `/base64/validate` | Base64 フォーマット検証（200 + is_valid） |

---

## テスト結果

**27 passed**

```
27 passed in 0.08s
```

---

## 摩擦ポイント

### F-1: `base64.b64decode(encoded + "==")` のパディング追加が二重パディングを引き起こす（深刻度: 低）

**事象**: `_decode_bytes()` の最初の実装で `encoded + "=="` を常に渡した。
すでにパディングされた文字列（例: `aGVsbG8=`）に `==` をさらに追加すると
`base64.b64decode(validate=True)` が `binascii.Error` を送出する。
テストで日本語文字列のラウンドトリップが失敗して発覚した。

**原因**: Base64 のパディング文字 `=` の最大付加量は 2 文字だが、
"常に `==` を追加" するアプローチは既存パディングを考慮していない。

**対応**: `rstrip("=")` で既存パディングを除去した後、
`(4 - len(stripped) % 4) % 4` で必要分だけ `=` を補完する正規パターンに修正。

```python
stripped = encoded.rstrip("=")
padding = (4 - len(stripped) % 4) % 4
padded = stripped + "=" * padding
```

---

## 観察点

### 観察1: `validate=True` フラグで不正文字を即座に検出できる

```python
base64.b64decode("AAAA!!!!", validate=True)  # → binascii.Error: Non-base64 digit found
base64.b64decode("AAAA!!!!")                  # → 不正文字を無視してデコード
```

`validate=True` を省略すると不正文字が無視されてデコードが成功してしまう。
セキュリティ観点では `validate=True` を常に指定すべき。

### 観察2: URL セーフ形式の `urlsafe_b64decode` は `validate` パラメータを持たない

```python
base64.urlsafe_b64decode(data)  # validate フラグなし
# 不正文字は内部で silently 変換または無視される
```

URL セーフ版には `validate` がない。標準形式とは挙動が微妙に異なる点に注意が必要。

### 観察3: UTF-8 非準拠バイト列のデコードは明示的に分離すべき

バイナリデータを Base64 デコードしてそのまま UTF-8 文字列に変換しようとすると
`UnicodeDecodeError` が発生する。エンドポイントの設計として
「テキスト専用 decode」（失敗は 422）と「バイナリ decode」を分けるか、
`decoded_text: str | None` のように失敗を表現できるデータ型を返すかを選ぶ必要がある。
今回は後者（Result 型）を採用した。

---

## nene2-python フレームワークとの統合

- `decode_text()` は失敗を例外でなく `DecodeResult(is_valid=False)` で返し、
  エンドポイント側で `ValidationException` への変換を担う。
  この層分離は FT199（uuid `validate_uuid`）と同じパターンで一貫している。
- `EncodeBody.text: str = Field(max_length=4096)` で入力上限を設定。
  対応して `DecodeBody.encoded: str = Field(max_length=5600)` は
  4096 バイトを Base64 エンコードした際の最大長（ceil(4096/3)*4 ≈ 5460）を考慮した上限。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FastAPI エンドポイントで Base64 を使うユースケースに取り組んでいる。

**ドキュメント理解**: `base64.b64encode()` / `b64decode()` 自体はシンプル。
パディングの補完ロジック（F-1）は自力では気づきにくく、
「なぜか日本語文字列でだけ失敗する」というデバッグ体験になりやすい。  
**事故リスク**: 低。Base64 は副作用なし・純粋変換。
最悪でも `binascii.Error` が発生する。  
**規約の使いやすさ**: `encode_text()` / `decode_text()` の関数に包んで
パディング処理を隠蔽すれば初心者でも安全に使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存サービスの API に Base64 エンコードを追加する作業を担当している。

**コピペ可能性**: `encode_text()` / `decode_text()` のコードはそのまま使える。
`_decode_bytes()` の補完ロジックはコピーしても意味が分かりにくいため、コメントが必要。  
**拡張時の罠**: `validate=True` を外したままコピーして使うと不正入力を素通りさせるリスクあり。  
**セキュリティ的な事故リスク**: 低。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JWT や画像データの Base64 変換を API として実装している。

**エラーレスポンスの質**: デコード失敗が 422 + `decode_failed` コードで返り、
クライアント実装がしやすい。`is_valid: false` を返す `/validate` も用途に応じて使い分けられる。  
**Python 固有概念の学習コスト**: `bytes.decode("utf-8")` と `base64.b64decode()` を
区別する必要があるが、TypeScript の `atob`/`btoa` との対応で理解しやすい。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

JWT や OAuth2 実装で Base64 を扱う経験がある。

**他フレームワークとの差異**: Django の `base64.b64encode` 直呼びと比較して、
nene2-python の Result 型ラッパーは定型コードだが意図が明示されている。  
**nene2-python の薄さへの評価**: `validate=True` を明示している点は良い。
URL セーフ版の `validate` フラグ不在という Python の API 非対称性を FT で発見・記録した価値がある。  
**本番投入可能性**: 問題なし。JWT ペイロードの Base64url デコードにも対応可能。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

Base64 を使うコードのレビューを担当する。

**コードレビューチェックポイント**:
- [ ] `b64decode` に `validate=True` が設定されているか（なければ不正文字を無視してデコード）
- [ ] パディング補完ロジックに `rstrip("=")` があるか（ないと二重パディングでエラー）
- [ ] `urlsafe_b64decode` は `validate` 非対応のため、入力を信頼できる経路に限定しているか

**チームでの安全な共有パターン**: パディング補完を内部関数 `_decode_bytes()` に集約し、
外部に公開する `decode_text()` / `validate_base64()` のみを使うルールが有効。  
**ツール追加の必要性**: なし。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。`frozen=True, slots=True` dataclass・型注釈・Pydantic バリデーション・
`max_length` 設定・`ErrorHandlerMiddleware` の組み合わせが一貫している。  
**「初心者でも安全な API」達成度**: 高。パディング処理と `validate=True` を内部関数に隠蔽し、
公開 API では意識不要。  
**設計上の負債・ドキュメント不足**: `urlsafe_b64decode` の `validate` 非対応は Python の仕様。
CLAUDE.md への追記は不要だが FT200 レポートに記録済み。  
**Follow-up Issue 候補**: なし

---

## クラッカーペンテスト

> **実施方針**: Base64 エンドポイントへの型強制・パディング操作・バイナリインジェクション・
> DoS を試みる。

### フェーズ1: 構造推測（攻撃者の視点）

- `/base64/encode` の `text` フィールドは文字列を Base64 に変換するだけ。
  機密データは扱わない設計だが、エンコード結果がそのままレスポンスに出る点は確認が必要。
- `/base64/decode` はデコード失敗で 422 を返す。エラーメッセージに内部情報が含まれるか確認する。
- `url_safe` フラグが `bool` であることから、文字列や数値で送り込めるか試みる。

### フェーズ2: 攻撃実行ログ

#### A. Pydantic 型強制攻撃

```
POST /base64/encode  {"text": 12345}        → 422 (string_type エラー)
POST /base64/encode  {"text": true}          → 422 (string_type エラー)
POST /base64/encode  {"text": null}          → 422
POST /base64/encode  {"text": []}            → 422
POST /base64/encode  {"url_safe": "yes"}     → 200 (Pydantic が "yes" → True に変換)
```

**結果**: `text` の型強制はすべて 422 で拒否。
`url_safe` フィールドへの文字列 `"yes"` は `True` に変換された（Pydantic v2 のデフォルト）。
セキュリティ上の問題はないが、意図しない `true` 扱いになる可能性あり。

#### B. パディング操作攻撃

```
POST /base64/decode  {"encoded": "aGVsbG8"}     → 200 (パディングなしでも成功)
POST /base64/decode  {"encoded": "aGVsbG8="}    → 200
POST /base64/decode  {"encoded": "aGVsbG8=="}   → 200 (余分なパディングも正規化して成功)
POST /base64/decode  {"encoded": "aGVsbG8==="}  → 200 (3つでも正規化成功)
POST /base64/decode  {"encoded": "aGVsbG8======"} → 200 (すべて rstrip で除去後に正規化)
```

**結果**: パディング正規化ロジックにより、いかなるパディング量でも正常デコード。
攻撃者が「パディング操作で例外を出させてスタックトレースを得る」攻撃は不成功。
`ErrorHandlerMiddleware` が内部例外を 422 に変換するため情報漏洩もなし。

#### C. バイナリインジェクション攻撃

```
POST /base64/decode  {"encoded": "<UTF-8不可バイナリ>"}  → 422 ("decoded bytes are not valid UTF-8")
POST /base64/decode  {"encoded": "\x00evil base64"}       → 422 (invalid base64)
POST /base64/encode  {"text": "hello\x00world"}           → 200 (null バイト含む 11 バイト)
```

**結果**: 非 UTF-8 バイナリのデコードは 422 で拒否。
`text` フィールドへの null バイト含む文字列は受容される（Base64 エンコード自体は問題なし）。
これは Base64 の設計上正常な動作。

#### D. 情報収集攻撃

```
POST /base64/decode  {"encoded": "!!!!"}  → 422 + {"errors": [{"field": "encoded", "message": "invalid base64", "code": "decode_failed"}]}
```

**結果**: エラーレスポンスにスタックトレース・内部パス・モジュール名は含まれない。
`ErrorHandlerMiddleware` が Problem Details 形式（RFC 9457）で返す。

#### E. DoS 試み

```
POST /base64/encode  {"text": "A" * 4096}  → 200 (上限ちょうど)
POST /base64/encode  {"text": "A" * 4097}  → 422 (Pydantic max_length 超過)
POST /base64/validate {"encoded": "A" * 5600} → 200 (上限ちょうど)
POST /base64/validate {"encoded": "A" * 5601} → 422 (max_length 超過)
```

**結果**: `max_length` による上限が機能しており、巨大入力は 422 で拒否される。
Base64 デコード処理自体は O(n) のためサービス妨害にはなりにくい。

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | 5 | 0 | 5 | 1（`url_safe="yes"` → True 変換） |
| パディング操作 | 5 | 0 | 5 | 0 |
| バイナリインジェクション | 3 | 0 | 3 | 0 |
| 情報収集 | 1 | 0 | 1 | 0 |
| DoS | 4 | 0 | 4 | 0 |

**攻撃耐性評価**: 堅牢  
**発見した弱点**:
- `url_safe="yes"` が `True` に型強制される（Pydantic v2 デフォルト、セキュリティ影響なし）。
  `ConfigDict(strict=True)` を設定するか `url_safe: Annotated[bool, Field(strict=True)]` で防げる。
  今回のデモスコープでは許容。

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`base64` モジュールは nene2-python と非常にスムーズに統合できた。
摩擦ポイントはパディング補完ロジックのみで、`rstrip("=") + 正規計算` パターンを覚えれば再発しない。

クラッカーペンテストでは 18 攻撃すべてを耐え、情報漏洩ゼロ・突破ゼロを確認。
`url_safe="yes"` が `True` に変換される Pydantic v2 の型強制はセキュリティ影響なしと判定した。

次の FT201 は `201 % 3 = 0` のためセキュリティ診断を実施する。
