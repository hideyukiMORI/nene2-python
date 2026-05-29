# Guide pour publier une release sur PyPI

Ce guide décrit le flux de release vérifié : **CHANGELOG → bump de version → tag →
publication automatisée (TestPyPI → PyPI → GitHub Release)**. L'automatisation se trouve dans
[`.github/workflows/publish.yml`](../../.github/workflows/publish.yml) et se déclenche sur
les tags `v*` via **PyPI Trusted Publishing** (OIDC — sans tokens à longue durée de vie).

## Configuration initiale (mainteneur — déjà fait)

Le workflow de publication utilise Trusted Publishing et les GitHub Environments. C'est
**déjà configuré** et opérationnel ; cela est enregistré ici pour référence et récupération :

1. **PyPI / TestPyPI — Trusted Publisher** pour `nene2-python` :
   - Owner : `hideyukiMORI`, Repository : `nene2-python`
   - Workflow : `publish.yml`
   - Environment : `pypi` (sur pypi.org) et `testpypi` (sur test.pypi.org)
   - Enregistré sur https://pypi.org/manage/account/publishing/ et l'équivalent TestPyPI.
2. **Dépôt GitHub → Settings → Environments** : `testpypi` et `pypi` existent
   (ajoutez des reviewers requis sur `pypi` pour une porte d'approbation manuelle si souhaité).

Le package est **publié** — `pip install nene2-python` installe la dernière version
(v1.8.163+) directement depuis PyPI.

## Procédure de release (par release)

1. **Mettre à jour `CHANGELOG.md`** — ajouter une section `## [X.Y.Z] — YYYY-MM-DD`. L'étape
   GitHub Release extrait les notes en correspondant à cet en-tête, donc la section doit exister
   sinon les notes de release seront vides.
2. **Bumper la version** dans `pyproject.toml` et rafraîchir le lock :
   ```bash
   uv lock
   ```
3. **Ouvrir une PR**, passer la CI (le job `package-build` valide la distribution), et merger
   dans `main`.
4. **Tagger et pousser** la release :
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` s'exécute automatiquement : `uv build` → publication sur **TestPyPI** →
   publication sur **PyPI** → création d'une **GitHub Release** avec les notes du CHANGELOG et
   les artefacts dist attachés.

## Vérification locale (avant le tag)

Le job CI `package-build` l'exécute à chaque PR, mais vous pouvez le reproduire :

```bash
uv build                        # sdist + wheel dans dist/
uvx twine check dist/*          # validité des métadonnées PyPI
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # import propre ; example/tests ne doivent PAS être importables
```

À partir de v1.8.163, cela passe : `twine check` rapporte `PASSED`, le wheel s'importe
proprement dans un venv vierge, et seul `src/nene2` est livré (`example`/`tests` sont exclus
par `[tool.hatch.build.targets.wheel] packages = ["src/nene2"]`).

## Notes

- **Versioning** : `version` dans `pyproject.toml` est la source de vérité et est incrémentée
  par FT / feature / fix PR. Les tags Git `v*` sont créés sélectivement au moment de la release
  (le workflow de publication se déclenche uniquement sur les tags), donc `pyproject` avance
  avant les tags.
- **Granularité du CHANGELOG** : les one-liners par version vivent dans le tableau de jalons de
  [`docs/todo/current.md`](../todo/current.md) ; `CHANGELOG.md` enregistre les entrées agrégées
  au niveau de la release.
- Cette procédure correspond au **trial "flux de publication" de classe FT7** (#541) : le flux
  est pleinement opérationnel — v1.8.163 a été publiée sur PyPI via lui et est installable
  via `pip install nene2-python`.
