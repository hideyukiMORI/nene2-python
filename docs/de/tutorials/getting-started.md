# Erste Schritte mit nene2-python

Dieses Tutorial ermöglicht es Ihnen, in 5 Minuten eine Notes-CRUD-API mit nene2-python zu starten.

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

Öffnen Sie `http://localhost:8080/docs` im Browser für die Swagger UI.

## 4. API testen

```bash
# Notiz erstellen
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Meine erste Notiz", "body": "Erstellt mit nene2-python"}'

# Notizen auflisten
curl http://localhost:8080/notes
```

## 5. Tests ausführen

```bash
uv run pytest
```

Mehr als 167 Tests sollten erfolgreich sein.

## Nächste Schritte

- [Konfigurationsreferenz](../reference/configuration.md) — Datenbank und Authentifizierung über Umgebungsvariablen konfigurieren
