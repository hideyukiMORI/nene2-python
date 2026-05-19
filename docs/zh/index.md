---
layout: home

hero:
  name: "NENE2"
  text: "Python API 框架"
  tagline: FastAPI · 整洁架构 · MCP · mypy --strict · 从第一天起就为 AI 而设计。
  actions:
    - theme: brand
      text: 开始使用 →
      link: /zh/tutorials/getting-started
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: PHP 版本
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ 原生
    details: 使用 Python 3.12 泛型语法、冻结 dataclass 和 Pydantic v2。每次提交都强制执行 mypy --strict。

  - icon: ⚡
    title: FastAPI + 异步支持
    details: ASGI 原生，通过 AsyncUseCaseProtocol 支持非阻塞 I/O。使用 asyncio.gather 进行并发仓库调用。

  - icon: 🤖
    title: 内置 MCP
    details: 通过 LocalMcpServer 将 UseCase 作为 MCP 工具公开 — 无需额外配置。

  - icon: 🏛️
    title: 整洁架构
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy。每层都可使用 InMemory 仓库独立测试。

  - icon: 🛡️
    title: 安全优先
    details: RFC 9457 Problem Details、Bearer + API Key 认证、速率限制、安全标头，开箱即用。

  - icon: 📄
    title: 自动生成 OpenAPI
    details: 在 /docs 提供 Swagger UI 和 ReDoc — 零配置。一条命令导出静态 openapi.yaml。
---
