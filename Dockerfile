FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY src/ src/

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "src.example.app:app", "--host", "0.0.0.0", "--port", "8080"]
