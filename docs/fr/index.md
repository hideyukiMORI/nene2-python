---
layout: home

hero:
  name: "NENE2"
  text: "Framework API Python"
  tagline: FastAPI · Architecture propre · MCP · mypy --strict · Conçu pour l'IA dès le premier jour.
  actions:
    - theme: brand
      text: Commencer →
      link: /fr/tutorials/getting-started
    - theme: alt
      text: Voir sur GitHub
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: Version PHP
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ natif
    details: Syntaxe générique Python 3.12, dataclasses gelées et Pydantic v2. mypy --strict appliqué à chaque commit.

  - icon: ⚡
    title: FastAPI + async
    details: ASGI natif avec AsyncUseCaseProtocol pour les I/O non bloquants. asyncio.gather pour les appels parallèles.

  - icon: 🤖
    title: MCP intégré
    details: Les UseCases sont exposés comme outils MCP via LocalMcpServer — sans configuration supplémentaire.

  - icon: 🏛️
    title: Architecture propre
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy. Chaque couche est testable en isolation.

  - icon: 🛡️
    title: Sécurité d'abord
    details: RFC 9457 Problem Details, authentification Bearer + API Key, limitation de débit, en-têtes de sécurité.

  - icon: 📄
    title: OpenAPI auto-généré
    details: Swagger UI et ReDoc à /docs — sans configuration. Export d'un openapi.yaml statique en une commande.
---
