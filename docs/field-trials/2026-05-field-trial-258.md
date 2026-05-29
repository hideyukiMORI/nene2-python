# FT258: random — 暗号用途に使わない / secrets を使う

**日付**: 2026-05-29
**テーマ**: Python `random` の非暗号性と `secrets` 代替の実装と検証
**セキュリティ診断**: 🔒 あり（258 % 3 = 0）
**クラッカーペンテスト**: なし（258 % 4 = 2）

---

## 概要

`random` は Mersenne Twister ベースの疑似乱数で、**シード（内部状態）が分かれば全出力を再現・予測できる**。トークン・パスワード・秘密値に使うと予測攻撃を許す。CLAUDE.md ポリシー（「セキュア乱数は `secrets`」）を実証し、`random` は**シミュレーション等の非セキュリティ用途のみ**に限定すべきことを診断した。

| 用途 | 使うべき |
|---|---|
| シミュレーション・ゲーム・サンプリング | `random`（再現性が利点） |
| トークン・パスワード・秘密・nonce | **`secrets`**（CSPRNG・予測不可） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft258-random/`

| 関数 | 概要 |
|---|---|
| `simulate_dice()` | シード付きサイコロ（再現可能・非セキュリティ、S311 を理由付き抑制） |
| `secure_token()` | `secrets.token_urlsafe`（予測不可なトークン） |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/random/simulate` | サイコロ（非セキュリティ） |
| POST | `/random/secure-token` | secrets で安全なトークン |

---

## 摩擦点

### F-1: `random` はシード既知で完全再現＝予測可能

**観察**: `Random(1337)` で振ったサイコロは**毎回まったく同じ列**を返す（診断で `[5,5,6,3,...]` が完全一致）。Mersenne Twister は 624 個の連続出力を観測すれば内部状態を復元でき、以降を予測できる。トークンに使うと攻撃者が次の値を予測する。

**対処**: トークン・秘密値は `secrets`。`random` はシミュレーション等、再現性が利点になる非セキュリティ用途に限定。

### F-2: `secrets` はシードを持たず再現できない＝予測不可

**観察**: `secrets.token_urlsafe` は OS の CSPRNG 由来で、シード引数を持たず**再現不可能**。診断で 100 トークンすべてユニーク。

**対処**: トークンは `secrets.token_urlsafe(32)`（256bit）。`random` の `seed` のような再現手段がないのが安全性の証。

### F-3: ruff S311 で `random` 使用を検出（CLAUDE.md ポリシーの自動化）

**観察**: ruff の `S311`（"Standard pseudo-random generators are not suitable for cryptographic purposes"）が `Random(...)` 使用を検出する。CLAUDE.md の「`random` 禁止（`secrets` を使う）」が lint で強制される。

**対処**: シミュレーション用途で意図的に使う箇所のみ `# noqa: S311` + 理由コメントで抑制。S311 はインスタンス化行（`Random(seed)`）で発火するため noqa はその行に置く。トークン生成では `secrets` を使い S311 を出さない。

---

## セキュリティ診断結果

| カテゴリ | 例 | 結果 |
|---|---|---|
| random の予測可能性 | seed 1337 を 2 回 | **完全一致**（予測可能） |
| secrets の予測不可能性 | 100 トークン生成 | **100 ユニーク**（再現不可） |
| シード/件数の境界 | count 0/1001 / seed 負 | **422** |
| トークン最小長 | 8 バイト | **422**（16 以上強制） |
| トークン長 | 32 バイト | 43 文字（base64url） |
| ruff S311 | random 使用 | **検出**（noqa + secrets で対処） |
| セキュリティヘッダー | — | 付与あり |

**総合評価: 合格**

`random` の予測可能性と `secrets` の予測不可能性を実証。**「秘密値は secrets、random は非セキュリティ用途のみ」**を ruff S311 でも強制。CLAUDE.md ポリシーの実証。

---

## テスト結果

```
6 passed in 0.30s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`random` でトークンを作る記事をコピペしがち。シード再現の実演で「予測できる＝危険」が腑に落ちる。

**ドキュメント理解**: random と secrets の用途分けをコメント/表で明示。
**事故リスク（高）**: `random` でトークン・パスワードを生成。
**規約の使いやすさ**: simulate と secure-token で対比が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`random.choice` でパスワード生成する事例が散見される。`secrets` への置換が要点。

**コピペ可能性**: secure_token は流用可。
**拡張時の罠**: `random` をトークンに流用。
**事故リスク（高）**: 予測可能トークン。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `Math.random()`（非暗号）と `crypto.getRandomValues()`（暗号）の違いに対応。

**エラーレスポンスの質**: 範囲外は 422。
**Python 固有概念**: random vs secrets、S311。
**事故リスク（低）**: secrets 既定。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

トークン・nonce・CSRF・パスワードリセットは secrets 一択。random はシミュレーション/サンプリング。S311 の lint 強制は良い。

**他フレームワークとの差異**: 各言語とも CSPRNG/非 CSPRNG の区別が重要。
**nene2 の薄さへの評価**: secrets を既定にし random を隔離する設計が適切。
**事故リスク（低）**: 予測不可を実証。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- トークン・秘密・nonce に `random` を使っていないか（`secrets` 必須）。
- `random` の使用箇所が非セキュリティ用途に限定され、S311 を理由付きで抑制しているか。
- グローバル `random` 状態ではなくローカル `Random` インスタンスを使っているか。
- トークン長が十分か（>= 128bit）。

**チームでの安全なパターン**: 秘密=secrets、シミュ=ローカル Random、S311 を CI で強制。
**事故リスク（低）**: 予測可能性を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 「セキュア乱数は `secrets`、`random` 禁止」を完全実証。ruff S311 でポリシーを自動強制。Pydantic 制限・`ValidationException` 変換・`logging` 使用も準拠。
**初心者でも安全な API 達成度**: secrets を既定にし random を非セキュリティ用途に隔離、S311 で誤用を検出。
**改善提案**: FT203（secrets）・FT222（hashlib）・FT249（hmac）と本 FT を束ねた「乱数・秘密の扱い」how-to を用意する。
