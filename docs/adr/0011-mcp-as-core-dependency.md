# ADR-0011: MCP をコア依存として含める

## ステータス

承認済み (2026-05-20)

## コンテキスト

外部レビューで「`mcp>=1.0` をコア依存に含めると、MCP を使わない利用者まで FastMCP の依存ツリーを背負う」という指摘を受けた。`nene2[mcp]` optional extras に分離する案が提示された。

## 決定

`mcp>=1.0` はコア依存として `pyproject.toml` の `dependencies` に置く。optional extras には分離しない。

### 理由

**1. MCP はフレームワークの設計思想の中核**

`CLAUDE.md` の設計哲学に「LLM delivery ready: API・MCP・認証・DB・引き継ぎドキュメントを整合させる」と明記している。MCP は認証・DB と同列のファーストクラス機能であり、"optional な付加機能" ではない。

**2. UseCase アーキテクチャとの直結**

`nene2.use_case` の `UseCaseProtocol[I, O]` は HTTP と MCP の両方から呼ばれることを前提に設計されている（ADR-0002）。UseCase を MCP ツールとして公開する経路が常に存在することがフレームワークの価値のひとつであり、その経路を extras 依存にすることはアーキテクチャの前提に反する。

**3. extras 化のコスト**

optional extras にすると `nene2.mcp` モジュール全体の import が条件分岐になる:

```python
try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError("Install nene2[mcp] to use MCP features.")
```

フィールドトライアルのたびに MCP を使うため、このパターンを随所に書くことは単なる負債になる。

**4. 現在の採用者像**

nene2-python の想定ユーザーは「AI エージェント連携を見据えた API バックエンドを構築したい開発者」であり、MCP を使わない利用者は現時点で想定外のユースケースに属する。

## 将来の見直し条件

以下のいずれかが発生した場合、optional extras 化を検討する:

- FastMCP の依存ツリーが著しく肥大化し、インストール時間・容量が問題視される
- 「認証・DB・ページネーションだけ使いたい、MCP は不要」という実際の利用者フィードバックが複数件寄せられる
- MCP SDK のライセンスや破壊的変更がコア依存として許容できなくなる

その際は `nene2[mcp]` extras として分離し、`nene2.mcp` モジュールのインポートを条件分岐化する。

## 代替案

| 案 | 却下理由 |
|---|---|
| `nene2[mcp]` optional extras | 設計思想と不整合・extras 化のコストが現状では割に合わない |
| MCP モジュールを別パッケージ (`nene2-mcp`) に分離 | フレームワークの一体感が失われる・インストール手順が増える |

## 結果

- `uv add nene2-python` 一発で MCP 機能を含む完全なスタックが手に入る
- フィールドトライアルで MCP を毎回インストールする手間がない
- 将来的に extras 分離が必要になった場合は ADR を更新してこの決定を覆す
