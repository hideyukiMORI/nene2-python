---
layout: home

hero:
  name: "NENE2"
  text: "Python API フレームワーク"
  tagline: FastAPI · クリーンアーキテクチャ · MCP · mypy --strict · AI ファースト設計
  actions:
    - theme: brand
      text: はじめる →
      link: /ja/tutorials/getting-started
    - theme: alt
      text: GitHub で見る
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: PHP 版
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ ネイティブ
    details: Python 3.12 のジェネリクス構文、frozen dataclass、Pydantic v2 を使用。後方互換 shim なし。mypy --strict を全コミットで強制。

  - icon: ⚡
    title: FastAPI + async 対応
    details: ASGI ネイティブ。AsyncUseCaseProtocol で非同期 I/O をサポート。asyncio.gather による並列リポジトリ呼び出し。

  - icon: 🤖
    title: MCP 内蔵
    details: UseCase を LocalMcpServer 経由で MCP ツールとして公開 — 追加配線不要。Claude と任意の MCP クライアントが API を直接呼び出せる。

  - icon: 🏛️
    title: クリーンアーキテクチャ
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy。各レイヤーを InMemory リポジトリで独立してテスト可能。

  - icon: 🛡️
    title: セキュリティファースト
    details: RFC 9457 Problem Details、Bearer + API Key 認証、レートリミット、セキュリティヘッダー、リクエストサイズ制限 — すべて即使用可能。

  - icon: 📄
    title: OpenAPI 自動生成
    details: Swagger UI と ReDoc を /docs で提供 — 設定ゼロ。1コマンドで静的 openapi.yaml をエクスポート。
---
