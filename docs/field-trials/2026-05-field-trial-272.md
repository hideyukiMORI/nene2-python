# FT272: tarfile — tar slip / tar bomb / symlink 対策

**日付**: 2026-05-29
**テーマ**: Python `tarfile` の安全な展開（tar slip / tar bomb / symlink）の実装と検証
**セキュリティ診断**: なし（272 % 3 = 2）
**クラッカーペンテスト**: 🔍 あり（272 % 4 = 0）

---

## 概要

tar 展開は zip（FT260）と同様の **tar slip**（パストラバーサル）・**tar bomb** に加え、tar 固有の **symlink/hardlink/デバイスファイル member** による攻撃面を持つ。シンボリックリンクを展開すると、後続の member 書き込みがリンク先（`/etc/...` 等）へ波及する。Python 3.12+ は `filter='data'` を提供するが、本 FT は**明示的に拒否**する設計で検証した。

| 脅威 | 対策 |
|---|---|
| tar slip | `resolve()` + `is_relative_to()` + `\` 拒否 |
| symlink/hardlink/device | member 種別を**通常ファイル/ディレクトリのみ**に制限 |
| tar bomb | 宣言サイズ合計 + 実展開の上限 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft272-tarfile/`

| 関数 | 概要 |
|---|---|
| `safe_extract()` | tar bomb 検査 + エントリ数上限 |
| `_validate_member()` | 種別制限 + tar slip 検証 + サイズ上限 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/tar/safe-extract` | tar を安全に展開 |

---

## 摩擦点

### F-1: tar 固有 — symlink/hardlink/デバイス member を拒否

**観察**: tar は zip と異なり**シンボリックリンク・ハードリンク・デバイスファイル・FIFO** を member として持てる。symlink を展開すると、その後の書き込みがリンク先に波及し任意ファイル書き込み（CVE 多数）。`isfile()`/`isdir()` 以外を許すと危険。

**対処**: `member.isfile() or member.isdir()` 以外を 422。診断で symlink/hardlink/fifo がすべて拒否。

### F-2: tar slip（パストラバーサル）

**観察**: `../../etc/passwd`・絶対パス・`a/../../b` で展開先外へ書き込み。

**対処**: `(base / name).resolve()` が base 配下か `is_relative_to` で検証、`\`（Windows 区切り）も拒否（FT260 と同様 OS 非依存）。

### F-3: tar bomb（宣言サイズ + 圧縮 tar）

**観察**: tar 自体は非圧縮だが `.tar.gz`/`.tar.xz` は高圧縮で、小さなアーカイブが巨大展開になる。member ヘッダの宣言サイズで事前検査でき、実展開も上限で打ち切る。

**対処**: `sum(m.size)` で宣言サイズ合計を検査、実展開も `read(MAX+1)`。gz 圧縮 20MB 爆弾を 422。

---

## クラッカーペンテスト

### フェーズ2: 攻撃実行ログ

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| tar slip（相対） | `../../etc/passwd` | **422** |
| tar slip（絶対） | `/tmp/evil` | **422** |
| tar slip（ネスト） | `a/../../b` | **422** |
| symlink member | `link → /etc/passwd` | **422**（種別制限） |
| hardlink member | `hl → a.txt` | **422** |
| fifo member | `pipe` | **422** |
| tar bomb（gz） | 20MB 宣言 | **422** |
| 不正 tar | `deadbeef` | **422** |
| 正常 | `a.txt`/`sub/b.txt` | **200** |

### フェーズ3: まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| tar slip | 3 | 0 | 3 |
| 特殊 member（symlink 等） | 3 | 0 | 3 |
| tar bomb / 不正 | 2 | 0 | 2 |

**攻撃耐性評価**: 堅牢
**発見した弱点**: なし。tar 固有の symlink/hardlink/device を種別制限で遮断、tar slip/bomb も封じ込め + 上限で防御。

---

## テスト結果

```
5 passed in 0.33s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

zip（FT260）と同じ罠 + symlink という追加の罠を学べる。`extractall` の危険を知る。

**ドキュメント理解**: symlink 攻撃をコメントで明示。
**事故リスク（高）**: `extractall` を無防備に使う。
**規約の使いやすさ**: tar_hex → entries が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

アップロード tar.gz の展開で頻出。symlink member の存在を知らない。

**コピペ可能性**: `_validate_member` は流用価値大。
**拡張時の罠**: 種別制限漏れ・宣言サイズの過信。
**事故リスク（高）**: symlink/tar slip。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

tar はバックエンド領域。symlink 経由の任意書き込みは新しい概念。

**エラーレスポンスの質**: 攻撃は 422。
**Python 固有概念**: TarInfo の種別。
**事故リスク（低）**: 種別制限。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

tarfile の CVE（CVE-2007-4559 等）は長命。Python 3.12+ の `filter='data'` も使えるが明示拒否がより明快。symlink/hardlink の遮断が肝。

**他フレームワークとの差異**: zip より member 種別が多く攻撃面が広い。
**nene2 の薄さへの評価**: 種別制限 + 封じ込め + 上限で堅牢。
**事故リスク（低）**: 全攻撃遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `extractall` を無検証で使っていないか（CVE-2007-4559）。
- member 種別を通常ファイル/ディレクトリに制限しているか（symlink/hardlink/device）。
- tar slip 封じ込め（resolve + is_relative_to + `\`）。
- 宣言サイズ + 実展開の二重上限（bomb）。
- Python 3.12+ なら `filter='data'` も検討。

**チームでの安全なパターン**: 種別制限 + 封じ込め + 上限、または filter='data'。`extractall` 無検証を禁止。
**事故リスク（低）**: 全攻撃を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `pathlib.Path`・パストラバーサル防御・Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。FT260（zipfile）の延長で symlink 対策を追加。
**初心者でも安全な API 達成度**: 種別制限・封じ込め・上限を関数内に隠蔽し `extractall` の罠を排除。
**改善提案**: 「アーカイブ展開の安全則」how-to（FT225/226/260/272）に symlink 種別制限を追記する。
