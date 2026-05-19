# Primeiros passos com nene2-python

Este tutorial permite que você inicie uma API CRUD de Notes com nene2-python em 5 minutos.

## Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/) instalado
- Git

## 1. Clonar o repositório

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. Instalar dependências

```bash
uv sync
```

## 3. Iniciar o servidor de desenvolvimento

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

Abra `http://localhost:8080/docs` no navegador para acessar o Swagger UI.

## 4. Testar a API

```bash
# Criar uma nota
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Minha primeira nota", "body": "Criada com nene2-python"}'

# Listar notas
curl http://localhost:8080/notes
```

## 5. Executar os testes

```bash
uv run pytest
```

Mais de 135 testes devem passar com sucesso.

## Próximos passos

- [Referência de configuração](../reference/configuration.md) — Configurar banco de dados e autenticação via variáveis de ambiente
