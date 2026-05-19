---
layout: home

hero:
  name: "NENE2"
  text: "Python API Framework"
  tagline: FastAPI · Clean Architecture · MCP · mypy --strict · Von Anfang an KI-bereit.
  actions:
    - theme: brand
      text: Loslegen →
      link: /de/tutorials/getting-started
    - theme: alt
      text: Auf GitHub ansehen
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: PHP-Version
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ nativ
    details: Python 3.12 generische Syntax, eingefrorene Dataclasses und Pydantic v2. mypy --strict bei jedem Commit erzwungen.

  - icon: ⚡
    title: FastAPI + async
    details: ASGI-nativ mit AsyncUseCaseProtocol für nicht blockierendes I/O. asyncio.gather für parallele Repository-Aufrufe.

  - icon: 🤖
    title: MCP integriert
    details: UseCases werden über LocalMcpServer als MCP-Werkzeuge bereitgestellt — ohne zusätzliche Konfiguration.

  - icon: 🏛️
    title: Clean Architecture
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy. Jede Schicht mit InMemory-Repositories testbar.

  - icon: 🛡️
    title: Sicherheit zuerst
    details: RFC 9457 Problem Details, Bearer + API Key Authentifizierung, Rate Limiting, Sicherheits-Header — sofort einsatzbereit.

  - icon: 📄
    title: OpenAPI automatisch generiert
    details: Swagger UI und ReDoc unter /docs — keine Konfiguration. Statisches openapi.yaml mit einem Befehl exportieren.
---
