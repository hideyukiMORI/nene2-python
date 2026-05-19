# はじめての nene2-python

このチュートリアルでは、nene2-python を使って Note の CRUD API を 5 分で起動します。

## 前提条件

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/) がインストール済み
- Git

## 1. リポジトリを clone する

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. 依存関係をインストールする

```bash
uv sync
```

## 3. 開発サーバーを起動する

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

起動後、ブラウザで `http://localhost:8080/docs` を開くと Swagger UI が表示されます。

## 4. API を試す

```bash
# Note を作成する
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "はじめてのノート", "body": "nene2-python で作成しました"}'

# Note 一覧を取得する
curl http://localhost:8080/notes
```

## 5. テストを実行する

```bash
uv run pytest
```

135 件以上のテストがすべて通ることを確認してください。

## 次のステップ

- [新しいドメインを実装する](first-domain.md) — Tag ドメインの実装を通じてフレームワークの構造を理解する
- [設定リファレンス](../reference/configuration.md) — 環境変数で DB や認証を設定する
