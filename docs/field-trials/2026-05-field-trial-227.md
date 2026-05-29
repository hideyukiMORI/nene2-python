# FT227: shutil — copy / move / rmtree（パストラバーサル防御）

**日付**: 2026-05-29
**テーマ**: Python `shutil` モジュールの高レベルファイル操作の実装と検証
**セキュリティ診断**: なし（227 % 3 = 2）
**クラッカーペンテスト**: なし（227 % 4 = 3）

---

## 概要

`shutil` は copy / move / rmtree などの高レベルファイル操作を提供する。HTTP API でラップする最大の課題は **パストラバーサル** — ユーザー由来のファイル名が `../` や絶対パスを含むと、作業ディレクトリの外を読み書き・削除できてしまう（特に `rmtree` は破壊的）。本 FT では全操作を**リクエストごとの `TemporaryDirectory`（ワークスペース）内**に閉じ込め、`resolve()` + `is_relative_to()` による二重封じ込めを検証した。

| API | ユースケース |
|---|---|
| `shutil.copy2(src, dst)` | メタデータ付きファイルコピー |
| `shutil.move(src, dst)` | ファイル移動/リネーム |
| `shutil.rmtree(path)` | ディレクトリの再帰削除（破壊的） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft227-shutil/`

| 関数 | 概要 |
|---|---|
| `_safe_path()` | 名前を検証し `resolve()` + `is_relative_to()` で base 配下に封じ込め |
| `copy_file()` | ワークスペース内で `copy2` 複製 |
| `move_file()` | `move` でリネーム、src 消失・dst 存在を確認 |
| `rmtree_subdir()` | サブツリーを作り `rmtree` で再帰削除 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/shutil/copy` | ファイル複製 |
| POST | `/shutil/move` | ファイル移動 |
| POST | `/shutil/rmtree` | サブツリー削除 |

---

## 摩擦点

### F-1: ユーザー由来の名前は `../`・絶対パスでワークスペースを脱出する

**観察**: `base / user_name` は `user_name` が `../../etc/passwd` や `/etc/passwd`（絶対パス）の場合に **base の外**を指す。`pathlib` の `/` 演算子は絶対パスを渡すと**左辺を無視して絶対パスそのもの**になる（`Path("/tmp/x") / "/etc/passwd"` == `Path("/etc/passwd")`）。`rmtree` でこれをやると致命的。

**対処**: `_safe_path()` で ① 名前に `os.sep` / `..` / null を含めば拒否、② `(base / name).resolve()` が `base.resolve()` 配下か `is_relative_to()` で二重チェック。テストで `../escape` と `/etc/passwd` がともに 422 になることを確認。

```python
target = (base / name).resolve()
if not target.is_relative_to(base.resolve()):
    raise ValueError("base ディレクトリ外を指しています")
```

### F-2: `shutil.move` は文字列パスを期待する場面がある

**観察**: `shutil.move` は `Path` も受けるが、バージョン差・環境差でのトラブルを避けるため `str(path)` を渡すのが無難（型スタブ上も `str` がもっとも安定）。

**対処**: `shutil.move(str(src), str(dst))` で明示的に文字列化。

### F-3: `rmtree` は破壊的でロールバックできない

**観察**: `rmtree` は再帰削除で取り返しがつかない。対象パスの封じ込めが甘いと事故が甚大。

**対処**: 操作対象を `TemporaryDirectory` に限定し、`_safe_path` を必ず通す。本 FT では削除後に `removed` と `remaining_entries` を返して結果を可視化。

---

## テスト結果

```
6 passed in 0.85s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

copy / move / rmtree は直感的だが、ファイル名にパスが混ざる危険は想像しにくい。

**ドキュメント理解**: `is_relative_to` による封じ込めは高度。コメントが理由を書いている。
**事故リスク（高）**: `base / user_name` の絶対パス吸収（`/etc/passwd`）を知らないと事故る。`rmtree` は特に危険。
**規約の使いやすさ**: 操作結果（size / removed / exists）が返るので挙動が見える。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

アップロードファイルの保存・移動でよく使う。`_safe_path` はコピペで使える。

**コピペ可能性**: `_safe_path` は再利用性が高い。
**拡張時の罠**: `pathlib` の `/` が絶対パスを吸収する挙動。検証を省くと脱出される。
**事故リスク（高）**: `rmtree` のパストラバーサル。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node の `fs.cp` / `fs.rm` に対応。サーバー側のパス検証の重要性が分かる。

**エラーレスポンスの質**: 不正名は 422 Problem Details で明確。
**Python 固有概念**: `pathlib` の絶対パス吸収・`resolve()` の正規化。
**事故リスク（低）**: 二重封じ込めで防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

パストラバーサルは定番の脆弱性。`resolve()` + `is_relative_to()` は王道。シンボリックリンク経由の脱出も `resolve()` が解決する。

**他フレームワークとの差異**: Django の `Storage` も同様の検証を内部で持つ。素の shutil ではアプリ責任。
**nene2 の薄さへの評価**: 薄いラップに封じ込めを足す設計は妥当。
**事故リスク（低）**: 名前検証 + resolve 二重防御。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `base / user_input` を検証なしで使っていないか — 絶対パス吸収・`..` 脱出。
- `resolve()` 後に `is_relative_to(base)` で封じ込めているか（シンボリックリンク対策含む）。
- `rmtree` の対象が確実に作業領域内か — 破壊的操作は特に厳格に。
- 操作を `TemporaryDirectory` 等の限定領域に閉じているか。

**チームでの安全なパターン**: `_safe_path` を共通化し、ファイル名を受ける全箇所で強制。
**事故リスク（低）**: 摩擦点が回帰テスト済み。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `pathlib.Path` 操作（`os.path.*` 不使用）・パストラバーサル防御・Pydantic 制限・`ValidationException` 変換は準拠。FT221（tempfile）の affix 検証と同系統の防御。
**初心者でも安全な API 達成度**: `_safe_path` を関数内に隠蔽し、生の `base / name` を書く余地を排除。
**改善提案**: FT221 の `_validate_affix` と本 FT の `_safe_path` を統合し、`nene2` の「安全なパス結合」ユーティリティとして提供する。
