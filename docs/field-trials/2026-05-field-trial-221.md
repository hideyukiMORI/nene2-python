# FT221: tempfile — NamedTemporaryFile / mkstemp / TemporaryDirectory

**日付**: 2026-05-29
**テーマ**: Python `tempfile` モジュールの NamedTemporaryFile / mkstemp / TemporaryDirectory の実装と検証
**セキュリティ診断**: なし（221 % 3 = 2）
**クラッカーペンテスト**: なし（221 % 4 = 1）

---

## 概要

`tempfile` は安全な一時ファイル・一時ディレクトリを生成する標準モジュール。HTTP API でラップし「内容を受け取り、一時ファイルに書いてメタデータを返す」パターンを検証した。一時ファイルは歴史的に **TOCTOU レースコンディション**（`mktemp`）と **予測可能なファイル名**による攻撃の温床であり、`tempfile` の「安全な API」と「危険な API」の境界を実装者目線で確かめることが本 FT の主眼。

| API | ユースケース |
|---|---|
| `tempfile.NamedTemporaryFile()` | close 時に自動削除される名前付き一時ファイル |
| `tempfile.mkstemp()` | fd とパスを返す低レベル API（close / unlink は呼び出し側責任） |
| `tempfile.TemporaryDirectory()` | with 終了でディレクトリごと自動削除 |
| `tempfile.mktemp()` | **非推奨**（TOCTOU 脆弱）。本 FT では使わない |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft221-tempfile/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `write_named_tempfile()` | `NamedTemporaryFile` で書き込み、close 時に自動削除 |
| `write_with_mkstemp()` | `mkstemp` で fd を取得し、`os.fdopen` + `try/finally` で close / unlink を明示管理 |
| `use_temporary_directory()` | `TemporaryDirectory` 内にファイルを作り、with 終了で自動削除されることを確認 |
| `_validate_affix()` | prefix / suffix / filename のパス区切り・null バイト・`..` を拒否 |
| `_mode_octal()` | 作成ファイルのパーミッションを 8 進文字列で取得 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/tempfile/named` | NamedTemporaryFile で書き込み |
| POST | `/tempfile/mkstemp` | mkstemp で書き込み（prefix / suffix 指定可） |
| POST | `/tempfile/directory` | TemporaryDirectory 内にファイル作成 |

---

## 摩擦点

### F-1: `mkstemp` は prefix / suffix をサニタイズしない（パストラバーサル）

**観察**: `tempfile.mkstemp(suffix=...)` は suffix を**生成パスに直接連結**する。`suffix="../../etc/passwd"` を渡すと内部的に `/tmp/tmpXXXXXX../../etc/passwd` というパスになり、**一時ディレクトリの外**を指す。今回の検証環境では中間ディレクトリが存在せず `FileNotFoundError` になったが、**書き込み先のディレクトリが存在すれば一時ディレクトリ外へファイルを生成できてしまう**。`tempfile` 自身はこの検証を行わない。

```python
>>> tempfile.mkstemp(suffix="../../etc/passwd")
FileNotFoundError: [Errno 2] ... '/tmp/tmpwk_cpt59../../etc/passwd'
```

**対処**: ユーザー由来の prefix / suffix / filename は `_validate_affix()` で `os.sep` / `os.altsep` / `\x00` / `..` を含む場合に `ValueError` を投げ、422 で遮断する。`tempfile` に渡る前にアプリ側で防ぐのが鉄則。

```python
_FORBIDDEN_AFFIX = tuple(t for t in (os.sep, os.altsep, "\x00", "..") if t)
```

---

### F-2: `mkstemp` は fd を返すだけ — close / unlink が呼び出し側責任

**観察**: `mkstemp()` は `(fd, path)` を返す低レベル API で、`NamedTemporaryFile` と違い**自動クローズも自動削除もしない**。fd を閉じ忘れるとファイルディスクリプタリークになり、unlink を忘れると `/tmp` にゴミが残り続ける（長期稼働でディスク枯渇 DoS の温床）。

**対処**: fd は `os.fdopen(fd, ...)` で file object に包み `with` で確実にクローズし、パスの削除は `try/finally` で `path.unlink(missing_ok=True)` を必ず実行する。

```python
fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
path = Path(raw_path)
try:
    with os.fdopen(fd, "w+") as handle:  # fd の所有権を渡し with でクローズ
        ...
finally:
    path.unlink(missing_ok=True)         # mkstemp は自動削除しない
```

---

### F-3: 安全な API でもパーミッションは確認すべき（0o600）

**観察**: `tempfile` の安全な API（`NamedTemporaryFile` / `mkstemp`）はファイルを **`0o600`（オーナーのみ読み書き可）** で生成する。これは設計上の保証だが、レビュー時に「本当にその権限か」を確認する習慣がないと、`os.open` を手書きした箇所で `0o644` を作ってしまう事故に気付けない。

**対処**: レスポンスに `mode`（`oct(stat.S_IMODE(...))`）を含め、テストで `mode == "0o600"` を回帰検証する。`NamedTemporaryFile` / `mkstemp` 双方で `0o600` を確認した。

---

## テスト結果

```
10 passed in 0.91s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

主要なテスト観点:
- `mode == "0o600"`（NamedTemporaryFile / mkstemp の両方）
- `name` がベース名のみ（絶対パス非公開）
- suffix の `../../etc/passwd` → 422
- prefix の null バイト → 422
- filename の `../escape.txt` → 422
- TemporaryDirectory の `removed_after_exit is True`（自動削除）

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「一時ファイルを作って読み書きして返す」という流れは理解しやすい。`NamedTemporaryFile` を `with` で使う形は他のファイル操作と同じなので入りやすい。

**ドキュメント理解**: `mkstemp` が fd（整数）を返す点は初見で戸惑う。`os.fdopen` で包む必要性の説明が要る。
**事故リスク（高）**: `mktemp`（末尾に p が無い方）をネットのサンプルからコピペすると TOCTOU 脆弱性を持ち込む。名前が 1 文字違いで紛らわしい。
**規約の使いやすさ**: `content` を送れば `mode` / `size` / `name` が返る形は素直。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

アップロードファイルの一時保管やバッチの中間ファイルで `tempfile` を使う場面は多い。`mkstemp` の `try/finally` 削除パターンはコピペで流用できる。

**コピペ可能性**: `write_with_mkstemp()` の fd 管理＋ unlink は実務でそのまま使える完成度。
**拡張時の罠**: ユーザー入力を prefix / suffix にそのまま渡してパストラバーサル（F-1）を作り込みやすい。`_validate_affix` を省略すると危険。
**事故リスク（中）**: unlink 忘れによる `/tmp` のゴミ蓄積。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node の `os.tmpdir()` / `fs.mkdtemp()` と概念が対応するので理解しやすい。一時ファイルが自動削除される点は Node より親切に感じる。

**エラーレスポンスの質**: 不正な suffix / filename は 422 で `{field, message, code}` が返り扱いやすい。
**Python 固有概念の学習コスト**: ファイルパーミッション（`0o600`）の概念は Unix 文脈で、フロント出身者には新鮮。`mode` をレスポンスに含めると学習の助けになる。
**事故リスク（低）**: 入力は Pydantic と `_validate_affix` で二重に制限。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`tempfile` の安全/危険 API の境界は周知。`mkstemp` + `try/finally` は王道。`TemporaryDirectory` の自動クリーンアップを `removed_after_exit` で明示検証している点が良い。

**他フレームワークとの差異**: Django の `FileSystemStorage` や `NamedTemporaryFile` 直叩きと同じ。フレームワーク横断で `mktemp` 禁止・affix 検証は共通の注意点。
**nene2 の薄さへの評価**: tempfile を HTTP でラップする薄い層として適切。パス検証だけアプリ側に寄せる設計は妥当。
**事故リスク（低）**: パストラバーサル・パーミッションともテストで担保。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `mktemp()`（末尾 p 無し）を使っていないか — TOCTOU 脆弱。`mkstemp` / `NamedTemporaryFile` を使う。
- ユーザー入力を prefix / suffix / dir に直接渡していないか — パストラバーサル（F-1）。affix 検証必須。
- `mkstemp` の fd を `with`/`finally` でクローズし、パスを unlink しているか — リーク・ゴミ防止。
- 生成ファイルのパーミッションが `0o600` か — `os.open` を手書きした場合は特に確認。
- 絶対パスをレスポンスやログに出していないか — `/tmp` 構造の情報漏洩。本 FT は `name`（ベース名）のみ返す。

**チームでの安全なパターン**: `_validate_affix` を共通ユーティリティ化し、tempfile を使う全箇所で強制する。
**事故リスク（低）**: 摩擦点 F-1〜F-3 が明示され回帰テスト済み。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `pathlib.Path` でのパス操作（`os.path.*` 不使用）・Pydantic 長さ制限・`ValidationException` 変換・`logging` 使用はすべて準拠。パストラバーサル防御は「ファイルパスは `pathlib.Path` で操作しパストラバーサルを防ぐ」ポリシーの実践例。
**初心者でも安全な API 達成度**: `_validate_affix` でユーザー affix を遮断し、`mkstemp` の fd / unlink を `with` / `finally` で隠蔽することで、初心者が `mktemp` やリークを書く余地を最小化できている。
**改善提案**:
- `_validate_affix` は `nene2.http` か `nene2` のパスユーティリティに昇格し、ファイル名・アップロード名検証で再利用する価値がある。
- how-to に「`mktemp` 禁止 / affix 検証 / `mkstemp` の fd・unlink 管理」を 1 本まとめると、tempfile を使う実装者の事故を減らせる。
