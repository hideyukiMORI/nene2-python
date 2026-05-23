---
layout: home

hero:
  name: "NENE2"
  text: "Python API Framework"
  tagline: FastAPI · Clean Architecture · MCP · mypy --strict · AI-ready from day one.
  actions:
    - theme: brand
      text: Get Started →
      link: /tutorials/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: PHP Version
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ native
    details: Uses Python 3.12 generic syntax, frozen dataclasses, and Pydantic v2. No legacy shims. mypy --strict enforced on every commit.

  - icon: ⚡
    title: FastAPI + async ready
    details: ASGI-native with async handlers and AsyncUseCaseProtocol for non-blocking I/O. asyncio.gather for concurrent repository calls.

  - icon: 🤖
    title: MCP built-in
    details: UseCases are exposed as MCP tools via LocalMcpServer — no extra wiring. Claude and any MCP client can call your API directly.

  - icon: 🏛️
    title: Clean Architecture
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy. Each layer is testable in isolation with InMemory repositories.

  - icon: 🛡️
    title: Security first
    details: RFC 9457 Problem Details, Bearer + API Key auth, rate limiting, security headers, request size limits — all wired out of the box.

  - icon: 📄
    title: OpenAPI auto-generated
    details: Swagger UI and ReDoc at /docs — zero config. Export a static openapi.yaml with one command. FastAPI does the work.

  - icon: 🧪
    title: 219 field trials
    details: Every stdlib pattern validated in isolated sandbox apps with security audits. Searchable INDEX in docs/field-trials/INDEX.md.
---
