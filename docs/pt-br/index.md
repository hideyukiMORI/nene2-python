---
layout: home

hero:
  name: "NENE2"
  text: "Framework de API Python"
  tagline: FastAPI · Arquitetura Limpa · MCP · mypy --strict · Projetado para IA desde o primeiro dia.
  actions:
    - theme: brand
      text: Começar →
      link: /pt-br/tutorials/getting-started
    - theme: alt
      text: Ver no GitHub
      link: https://github.com/hideyukiMORI/nene2-python
    - theme: alt
      text: Versão PHP
      link: https://hideyukimori.github.io/NENE2/

features:
  - icon: 🐍
    title: Python 3.12+ nativo
    details: Sintaxe genérica do Python 3.12, dataclasses imutáveis e Pydantic v2. mypy --strict aplicado em todos os commits.

  - icon: ⚡
    title: FastAPI + async
    details: ASGI nativo com AsyncUseCaseProtocol para I/O não bloqueante. asyncio.gather para chamadas paralelas.

  - icon: 🤖
    title: MCP integrado
    details: UseCases expostos como ferramentas MCP via LocalMcpServer — sem configuração adicional.

  - icon: 🏛️
    title: Arquitetura Limpa
    details: HTTP Handler → UseCase → RepositoryInterface → SQLAlchemy. Cada camada testável em isolamento.

  - icon: 🛡️
    title: Segurança em primeiro lugar
    details: RFC 9457 Problem Details, autenticação Bearer + API Key, limitação de taxa, cabeçalhos de segurança.

  - icon: 📄
    title: OpenAPI gerado automaticamente
    details: Swagger UI e ReDoc em /docs — sem configuração. Exporte um openapi.yaml estático com um comando.
---
