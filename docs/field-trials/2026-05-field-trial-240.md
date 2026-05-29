# FT240: 安全なデシリアライズ — pickle 不使用 / json + 型検証

**日付**: 2026-05-29
**テーマ**: 信頼できない入力の安全なデシリアライズ（pickle/eval を避け json + スキーマ検証）の実装と検証
**セキュリティ診断**: 🔒 あり（240 % 3 = 0）
**クラッカーペンテスト**: 🔍 あり（240 % 4 = 0）

---

## 概要

デシリアライズは最も危険な操作の一つ。`pickle.loads` / `yaml.load`（非安全 Loader）/ `eval` は、信頼できない入力で**任意コード実行（RCE）**を許す（`__reduce__` による os.system 呼び出し等）。CLAUDE.md でこれらは禁止。本 FT は **json + Pydantic スキーマ検証**のみでデシリアライズし、任意 JSON を「不活性なデータ」として扱う設計を、診断＋ペンテスト両面で検証した。

| 危険な方法 | 安全な代替（本 FT） |
|---|---|
| `pickle.loads(untrusted)` | `json` + Pydantic モデル検証 |
| `yaml.load(s)` | `yaml.safe_load` / json |
| `eval(s)` / `exec(s)` | スキーマ検証された構造化データ |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft240-safe-deserialization/`

| 関数 / モデル | 概要 |
|---|---|
| `ProfileBody`（Pydantic） | `extra="forbid"` + 型 + 範囲 + ロール上限 |
| `build_profile()` | 許可ロールのみ受理しドメイン `UserProfile` を構築 |
| `inspect_json()` | 任意 JSON を**反復走査**で構造解析（ネスト上限・実行しない） |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/deser/profile` | JSON を厳格に型検証して取り込む |
| POST | `/deser/inspect` | 任意 JSON を不活性に構造解析 |

---

## 摩擦点

### F-1: `pickle`/`eval`/`yaml.load` を使わない — json + スキーマが唯一の入口

**観察**: `pickle.loads` は `__reduce__` を持つオブジェクトをデシリアライズ時に**実行**するため、`base64` 化した悪意 pickle を送られると RCE になる。`yaml.load`（FullLoader 以外）・`eval` も同様。

**対処**: デシリアライズは json（FastAPI が安全にパース）→ Pydantic 検証のみ。ペンテストで送り込んだ pickle ペイロードは**単なる文字列/データ**として扱われ、コード実行は起きない。ソースに `pickle.loads`/`eval`/`exec`/`yaml.load` が**存在しない**ことを grep で確認（ヒットはドキュメント文字列のみ）。

### F-2: `extra="forbid"` で Mass Assignment を防ぐ

**観察**: Pydantic の既定（`extra="ignore"`）は未知フィールドを黙って無視する。これだと `{"name":...,"is_admin":true}` のような**権限昇格フィールド**が「無視されるが気付かれない」状態になり、別経路で拾われると危険。

**対処**: `model_config = ConfigDict(extra="forbid")` で未知フィールドを **422 で拒否**。`is_admin` / `__class__` 注入がともに弾かれることを確認。

### F-3: Pydantic v2 のラックス型強制（`"30"` → `30`）

**観察**: 診断で `age: "30"`（文字列）が **200** になった。Pydantic v2 は既定（lax）で数値文字列を int に強制変換する。`age: 3.5` は 422（非整数）、`"not-a-number"` も 422 だが、`"30"` は通る。これは仕様だが、厳密な型一致が要件なら認識が必要。

**対処**: 厳密一致が必要なフィールドは `Field(strict=True)` または `model_config` で strict モードを使う。本 FT のデモでは age の文字列許容は許容範囲（`"30"` は妥当な年齢表現）と判断し、範囲（0〜150）・ロール許可リストで実害を防ぐ。

---

## セキュリティ診断 & クラッカーペンテスト

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| Mass Assignment | `is_admin:true` / `__class__:"Admin"` 注入 | **422**（extra=forbid） |
| 権限昇格 | `roles:["admin","root"]` | **422**（ロール許可リスト） |
| 型混乱 | `age:3.5` / `roles:"admin"`（非配列） | **422** |
| 範囲 | `age:-1` / `age:151` | **422** |
| 上限 | `name` 101 文字 / `roles` 6 個 | **422** |
| ラックス強制（F-3） | `age:"30"` | 200（仕様・許容） |
| pickle RCE | `__reduce__`→os.system の pickle を base64 で送信 | **200 だが不活性**（文字列/データ、unpickle されない） |
| pickle inspect | `{"pickle_b64": <payload>}` | **200**（dict として構造解析のみ、実行なし） |
| ネスト DoS | 30 段ネスト配列 | **422**（深さ上限 20） |
| ソース監査 | `pickle/eval/exec/yaml.load` 呼び出し | **存在しない**（grep でドキュメントのみヒット） |
| セキュリティヘッダー | — | 付与あり |

### まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| Mass Assignment / 昇格 | 3 | 0 | 3 |
| 型混乱 / 範囲 / 上限 | 6 | 0 | 6 |
| pickle RCE | 2 | 0 | 2（不活性化） |
| ネスト DoS | 1 | 0 | 1 |

**総合評価: 合格**

RCE の根本原因（pickle/eval/yaml.load）を**コードから排除**し、json + Pydantic（extra=forbid・型・範囲・許可リスト）で安全にデシリアライズ。Mass Assignment・型混乱・ネスト DoS をすべて遮断。唯一の観察点は Pydantic の lax 型強制（`"30"`→`30`）で、厳密一致が要れば `strict=True` を使う。

---

## テスト結果

```
7 passed in 0.27s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「JSON を受け取って型チェックする」流れは FastAPI/Pydantic で自然。pickle が危険という話は知らないことが多い。

**ドキュメント理解**: なぜ pickle を使わないかをコメント・レポートで明示。
**事故リスク（高）**: ネットのサンプルで `pickle.loads` / `yaml.load` をコピペしがち。本 FT は使わない原則を強調。
**規約の使いやすさ**: Pydantic モデルで宣言的に検証できる。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

キャッシュやセッションに pickle を使う事例は多く危険。json + スキーマへの移行パターンが学べる。

**コピペ可能性**: `ProfileBody`（extra=forbid）・`inspect_json` は流用可。
**拡張時の罠**: 既定 `extra="ignore"` で Mass Assignment を見逃す。
**事故リスク（高）**: pickle/yaml.load の誤用。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JSON.parse 相当だが、サーバー側はスキーマ検証必須という感覚が身につく。`JSON.parse` に eval を使わないのと同じ発想。

**エラーレスポンスの質**: 不正は 422 Problem Details で詳細。
**Python 固有概念**: pickle の危険性・Pydantic 検証。
**事故リスク（低）**: スキーマ検証で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Insecure Deserialization は OWASP 常連（A08:2021）。pickle 排除 + extra=forbid + 許可リストは王道。Pydantic lax 強制は把握済みで strict 運用も選べる。

**他フレームワークとの差異**: DRF serializer も同様の検証。pickle セッションは避けるべき。
**nene2 の薄さへの評価**: json + Pydantic を入口に固定する設計が安全。
**事故リスク（低）**: RCE 経路をコードから排除。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `pickle.loads`/`eval`/`exec`/`yaml.load`（非 safe）/`marshal` を使っていないか — RCE。grep で監査。
- Pydantic モデルに `extra="forbid"` があるか — Mass Assignment。
- 型・範囲・許可リスト検証があるか。
- ネスト深さ・サイズに上限があるか（DoS）。
- 厳密型一致が要る箇所で `strict=True` を使っているか（lax 強制）。

**チームでの安全なパターン**: デシリアライズは json + Pydantic に統一、pickle/yaml.load を lint・CI で禁止。
**事故リスク（低）**: 診断＋ペンテストで全経路を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `pickle.loads`/`eval`/`exec` 不使用・HTTP 境界 Pydantic 検証・`ValidationException` 変換・`logging` 使用は完全準拠。本 FT は「Security first」と「HTTP 境界の全入力を Pydantic で検証」を体現。
**初心者でも安全な API 達成度**: 危険なデシリアライザを排除し、extra=forbid + 型/範囲/許可リストを既定にすることで RCE・Mass Assignment の余地を構造的に排除。
**改善提案**: 「危険プリミティブ回避」シリーズ（FT231 shlex / FT236 string.Template / FT240 本 FT）をまとめた how-to「信頼できない入力の安全な扱い方」を用意し、pickle/yaml.load/eval/format/shell=True の禁止と安全な代替を一覧化する。
