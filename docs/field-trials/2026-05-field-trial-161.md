# FT161: shutil モジュール

**日付**: 2026-05-21
**テーマ**: `shutil` モジュール — copy/copy2/copytree/rmtree/move/disk_usage/make_archive/unpack_archive/which/get_terminal_size

---

## 概要

Python 標準ライブラリの `shutil` モジュールを nene2-python フレームワーク上で検証した。
`shutil` (shell utilities) はファイル・ディレクトリの高水準操作を提供するモジュールで、
コピー、移動、削除、アーカイブ作成など日常的なファイルシステム操作をカバーする。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft161-shutil/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `copy_file(content, filename)` | `shutil.copy()` と `shutil.copy2()` の比較 |
| `copy_directory_tree(files)` | `shutil.copytree()` でディレクトリツリーをコピー |
| `remove_tree(files)` | `shutil.rmtree()` でディレクトリツリーを削除 |
| `move_file(content)` | `shutil.move()` でファイルを移動 |
| `get_disk_usage(path)` | `shutil.disk_usage()` でディスク使用量を取得 |
| `archive_and_extract(files, format)` | `make_archive()` + `unpack_archive()` のラウンドトリップ |
| `find_executable(name)` | `shutil.which()` で実行可能ファイルを検索 |
| `get_terminal_size()` | `shutil.get_terminal_size()` でターミナルサイズを取得 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/shutil/copy` | ファイルをコピー（copy/copy2） |
| POST | `/shutil/copytree` | ディレクトリツリーをコピー |
| POST | `/shutil/rmtree` | ディレクトリツリーを削除 |
| POST | `/shutil/move` | ファイルを移動 |
| GET | `/shutil/disk-usage` | ディスク使用量を取得 |
| POST | `/shutil/archive` | アーカイブ作成・展開ラウンドトリップ |
| POST | `/shutil/which` | 実行可能ファイルを検索 |
| GET | `/shutil/terminal-size` | ターミナルサイズを取得 |

---

## テスト結果

初回実行: 1 failed (disk_usage 等値テスト)
修正後: **30 passed**

```
30 passed in 0.32s
```

---

## 摩擦ポイント

### 摩擦1: `disk_usage()` で `total != used + free`（Linux の予約領域）

**状況**: テストで `total_bytes == used_bytes + free_bytes` を検証したが、実際には等しくならない。

```
assert 1081101176832 == (232262582272 + 793846239232)
# 差分: 54,992,355,328 バイト ≈ 51.2 GiB（約 4.7% が予約）
```

**原因**: Linux の ext4 等のファイルシステムは、ルートユーザー用にデフォルト 5% の
スペースを予約している（`mke2fs` の `-m` オプションで設定）。
`shutil.disk_usage()` の各フィールドの関係:
- `total`: 全領域（予約含む）
- `used`: 実際に使用中の領域
- `free`: 非ルートユーザーが利用可能な空き領域

正確な関係: `used + free + reserved = total`
つまり `used + free <= total` が常に成立する。

**修正**: テストを `==` から `<=` に変更。

```python
# 修正後
assert result["used_bytes"] + result["free_bytes"] <= result["total_bytes"]
```

**教訓**: `shutil.disk_usage()` は `os.statvfs()` をラップしており、
`free` は `f_bavail * f_frsize`（非ルート利用可能）を返す。
厳密な等値チェックは Windows と Linux で挙動が異なるため避けるべき。

---

## 観察点

### 観察1: `copy` vs `copy2` のメタデータ保持

`shutil.copy()` はファイルの内容とパーミッションのみをコピーする。
`shutil.copy2()` はさらに `atime`（アクセス日時）と `mtime`（修正日時）も保持する。

```python
shutil.copy(src, dst)   # 内容 + パーミッション
shutil.copy2(src, dst)  # 内容 + パーミッション + atime/mtime
```

バックアップツールなど変更日時の保持が必要な場合は `copy2` を使う。

### 観察2: `make_archive` / `unpack_archive` のフォーマット対応

```python
shutil.make_archive(base_name, format, root_dir)
```

利用可能なフォーマット: `zip`, `tar`, `gztar`（tar.gz）, `bztar`（tar.bz2）, `xztar`（tar.xz）

`shutil.get_archive_formats()` でサポートフォーマット一覧を取得できる。
`unpack_archive()` はフォーマット自動判別もサポート（拡張子から推測）。

### 観察3: `copytree` の `dirs_exist_ok` パラメータ（Python 3.8+）

デフォルトでは `copytree()` はコピー先が存在するとエラーになる。
`dirs_exist_ok=True` を指定すると上書きマージが可能。

```python
shutil.copytree(src, dst, dirs_exist_ok=True)  # 既存ディレクトリへの上書き許可
```

### 観察4: `rmtree` のエラーハンドラー

`shutil.rmtree(path, onerror=handler)` で削除エラー時のカスタムハンドラーを設定できる。
Windows での読み取り専用ファイルの削除など、権限エラーが発生する環境で有用。

Python 3.12 以降では `onerror` は非推奨となり `onexc` に統一された。

### 観察5: `get_terminal_size` のフォールバック

CI/CD 環境や pytest 実行時など端末が接続されていない場合、
`shutil.get_terminal_size(fallback=(80, 24))` は指定したフォールバック値を返す。
実際のターミナルが存在する場合は `os.get_terminal_size()` の値が使われる。

---

## nene2-python フレームワークとの統合

- `ErrorHandlerMiddleware` + `RequestIdMiddleware` は問題なく機能
- すべての入力を Pydantic BodyModel で検証（`max_length` 設定）
- `archive` フォーマットは `pattern="^(zip|tar|gztar|bztar)$"` で制限

---

## まとめ

`shutil` は実用的なファイル操作の標準ライブラリで、
バックアップ、デプロイ、テスト用一時ファイル操作など広い用途に使える。
主要な摩擦は `disk_usage()` の `total != used + free`（Linux 予約領域）のみで、
他の機能は直感通りに動作した。
