# Primeiros passos com nene2-python

Neste tutorial, você vai colocar uma API CRUD de Notes em funcionamento em menos de 5 minutos.

## Pré-requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/) instalado
- Git

## 1. Clonar o repositório

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. Instalar as dependências

```bash
uv sync
```

## 3. Iniciar o servidor de desenvolvimento

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

Abra `http://localhost:8080/docs` no navegador — o Swagger UI já está disponível.

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

Todos os 167+ testes devem passar.

## Próximos passos

- [Implementar um novo domínio](first-domain.md) — percorra toda a pilha de camadas usando o domínio Tag
- [Referência de configuração](../reference/configuration.md) — configure um banco de dados real ou habilite autenticação
