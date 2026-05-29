# Premiers pas avec nene2-python

Dans ce tutoriel, vous allez démarrer une API CRUD Notes en moins de 5 minutes.

## Prérequis

- Python 3.12 ou supérieur
- [uv](https://docs.astral.sh/uv/) installé
- Git

## 1. Cloner le dépôt

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. Installer les dépendances

```bash
uv sync
```

## 3. Démarrer le serveur de développement

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

Ouvrez `http://localhost:8080/docs` dans votre navigateur — Swagger UI est prêt.

## 4. Tester l'API

```bash
# Créer une note
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Ma première note", "body": "Créée avec nene2-python"}'

# Lister les notes
curl http://localhost:8080/notes
```

## 5. Exécuter les tests

```bash
uv run pytest
```

Les 167+ tests doivent tous passer.

## Étapes suivantes

- [Implémenter un nouveau domaine](first-domain.md) — parcourir toute la pile de couches avec le domaine Tag
- [Référence de configuration](../reference/configuration.md) — configurer une vraie base de données ou activer l'authentification
