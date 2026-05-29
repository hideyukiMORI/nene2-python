# Erste Schritte mit nene2-python

In diesem Tutorial starten Sie in weniger als 5 Minuten eine Notes-CRUD-API.

## Voraussetzungen

- Python 3.12 oder höher
- [uv](https://docs.astral.sh/uv/) installiert
- Git

## 1. Repository klonen

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. Abhängigkeiten installieren

```bash
uv sync
```

## 3. Entwicklungsserver starten

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

Öffnen Sie `http://localhost:8080/docs` im Browser — die Swagger-Oberfläche ist bereit.

## 4. API ausprobieren

```bash
# Notiz erstellen
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "My first note", "body": "Created with nene2-python"}'

# Notizen auflisten
curl http://localhost:8080/notes
```

## 5. Tests ausführen

```bash
uv run pytest
```

Alle 167+ Tests sollten erfolgreich sein.

## Nächste Schritte

- [Eine neue Domain implementieren](first-domain.md) — vollständiger Schritt-für-Schritt-Durchlauf des Layer-Stacks anhand der Tag-Domain
- [Konfigurationsreferenz](../reference/configuration.md) — echte Datenbank konfigurieren oder Authentifizierung aktivieren
