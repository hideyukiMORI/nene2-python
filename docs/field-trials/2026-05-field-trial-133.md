# Field Trial 133: contextlib の高度な活用

## テーマ

`suppress`, `redirect_stdout`, `ExitStack`, `asynccontextmanager` を使った
リソース管理・エラー抑制・動的コンテキストマネージャーを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft133-contextlib/` に以下を実装:

- `contextlib.suppress` — `ValueError`/`ZeroDivisionError` をサイレントに抑制
- `contextlib.redirect_stdout` — `print()` 出力を `StringIO` にキャプチャ
- `contextlib.ExitStack` — 複数リソースを動的に管理（逆順クローズ確認）
- `contextlib.asynccontextmanager` — 非同期DB接続の生存期間管理
- 16 テスト通過

## テスト結果

全 16 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `contextlib.suppress` で例外を宣言的にサイレントにできる

```python
with contextlib.suppress(ValueError, TypeError):
    return int(value)
return None
```

`try/except: pass` より意図が明確で、複数例外を一行で列挙できる。
FastAPI エンドポイントでの入力パース・型変換に使いやすい。

### O2: `ExitStack` で動的な数のリソースを管理できる

```python
with contextlib.ExitStack() as stack:
    resources = [stack.enter_context(FakeResource(name)) for name in names]
    # ここで例外が起きても全リソースがクローズされる
# with ブロックを抜けると全リソースが LIFO 順でクローズ
```

リソースの数が実行時まで決まらない場合（設定ファイルから読む、ユーザー指定など）に有用。
クローズ順は **登録の逆順**（LIFO）= 「後から開いたものを先に閉じる」。

### O3: `asynccontextmanager` で非同期リソースのライフサイクルを管理できる

```python
@contextlib.asynccontextmanager
async def managed_db_connection() -> AsyncGenerator[AsyncDatabase, None]:
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()

# 使い方
async with managed_db_connection() as db:
    rows = await db.execute("SELECT 1")
# with ブロックを抜けると disconnect() が呼ばれる
```

`yield` の前後に接続・切断を書くだけで非同期コンテキストマネージャーが作れる。
`try/finally` で確実にクリーンアップされる。

### O4: `redirect_stdout` でテスト中の print() 出力をキャプチャできる

```python
output = io.StringIO()
with contextlib.redirect_stdout(output):
    print("hello")
captured = output.getvalue()  # "hello\n"
```

テストで副作用（print の出力）をキャプチャするときに有用。
本番コードでは `logging` を使うべきだが、既存の print ベースのライブラリをラップする際に使える。

## まとめ

FT133 は摩擦ゼロ確認。`contextlib` の各機能を FastAPI エンドポイントで活用するパターンを確認した。
特に `ExitStack` による動的リソース管理の LIFO クローズ順と、
`asynccontextmanager` による非同期接続ライフサイクル管理は実用的なパターンとして記録する。
