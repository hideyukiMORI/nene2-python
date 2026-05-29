# Veröffentlichen und auf PyPI publizieren

Dieser Leitfaden beschreibt den verifizierten Veröffentlichungsablauf: **CHANGELOG → Versionserhöhung → Tag → automatisiertes Publizieren (TestPyPI → PyPI → GitHub Release)**. Die Automatisierung befindet sich in [`.github/workflows/publish.yml`](../../.github/workflows/publish.yml) und wird bei `v*`-Tags über **PyPI Trusted Publishing** (OIDC — keine langlebigen Tokens) ausgelöst.

## Einmalige Einrichtung (Maintainer — bereits erledigt)

Der Publish-Workflow verwendet Trusted Publishing und GitHub Environments. Dies ist **bereits konfiguriert** und betriebsbereit; es wird hier zur Referenz und Wiederherstellung festgehalten:

1. **PyPI / TestPyPI — Trusted Publisher** für `nene2-python`:
   - Owner: `hideyukiMORI`, Repository: `nene2-python`
   - Workflow: `publish.yml`
   - Environment: `pypi` (auf pypi.org) und `testpypi` (auf test.pypi.org)
   - Registriert unter https://pypi.org/manage/account/publishing/ und dem TestPyPI-Äquivalent.
2. **GitHub-Repo → Settings → Environments**: `testpypi` und `pypi` existieren (fügen Sie bei Bedarf erforderliche Reviewer auf `pypi` für ein manuelles Genehmigungstor hinzu).

Das Paket ist **veröffentlicht** — `pip install nene2-python` installiert die neueste Version (v1.8.163+) direkt von PyPI.

## Veröffentlichungsablauf (pro Release)

1. **`CHANGELOG.md` aktualisieren** — einen `## [X.Y.Z] — YYYY-MM-DD`-Abschnitt hinzufügen. Der GitHub-Release-Schritt extrahiert Notizen durch Abgleich dieser Überschrift, daher muss der Abschnitt existieren, sonst sind die Release-Notizen leer.
2. **Version erhöhen** in `pyproject.toml` und Lock aktualisieren:
   ```bash
   uv lock
   ```
3. **PR öffnen**, CI bestehen (der `package-build`-Job validiert die Distribution) und in `main` mergen.
4. **Tag und Push** des Releases:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` läuft automatisch: `uv build` → auf **TestPyPI** publizieren → auf **PyPI** publizieren → **GitHub Release** mit Notizen aus CHANGELOG und angehängten dist-Artefakten erstellen.

## Lokale Verifizierung (vor dem Tagging)

Der CI-`package-build`-Job führt dies bei jedem PR aus, aber Sie können es reproduzieren:

```bash
uv build                        # sdist + wheel in dist/
uvx twine check dist/*          # PyPI-Metadaten-Gültigkeit
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # sauberer Import; example/tests dürfen NICHT importierbar sein
```

Ab v1.8.163 besteht dies: `twine check` meldet `PASSED`, das Wheel importiert sauber in einer frischen venv, und nur `src/nene2` wird ausgeliefert (`example`/`tests` werden durch `[tool.hatch.build.targets.wheel] packages = ["src/nene2"]` ausgeschlossen).

## Hinweise

- **Versionierung**: `pyproject.toml` `version` ist die einzige Quelle der Wahrheit und wird pro FT / Feature / Fix-PR erhöht. Git-`v*`-Tags werden selektiv zum Release-Zeitpunkt erstellt (der Publish-Workflow wird nur bei Tags ausgelöst), sodass `pyproject` den Tags voraus läuft.
- **CHANGELOG-Granularität**: Pro-Version-Einzeiler befinden sich in der [`docs/todo/current.md`](../todo/current.md)-Meilenstein-Tabelle; `CHANGELOG.md` enthält auf Release zusammengefasste Einträge.
- Dieses Verfahren entspricht dem **FT7-Klassen-"publish flow"-Trial** (#541): Der Ablauf ist vollständig betriebsbereit — v1.8.163 wurde darüber auf PyPI veröffentlicht und ist über `pip install nene2-python` installierbar.
