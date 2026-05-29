# Como fazer release e publicar no PyPI

Este guia descreve o fluxo de release verificado: **CHANGELOG → bump de versão → tag →
publicação automatizada (TestPyPI → PyPI → GitHub Release)**. A automação fica em
[`.github/workflows/publish.yml`](../../.github/workflows/publish.yml) e dispara
em tags `v*` via **PyPI Trusted Publishing** (OIDC — sem tokens de longa duração).

## Configuração inicial (mantenedor — já feito)

O fluxo de publicação usa Trusted Publishing e GitHub Environments. Isso está
**já configurado** e operacional; está registrado aqui para referência e
recuperação:

1. **PyPI / TestPyPI — Trusted Publisher** para `nene2-python`:
   - Owner: `hideyukiMORI`, Repository: `nene2-python`
   - Workflow: `publish.yml`
   - Environment: `pypi` (em pypi.org) e `testpypi` (em test.pypi.org)
   - Registrado em https://pypi.org/manage/account/publishing/ e o equivalente no TestPyPI.
2. **GitHub repo → Settings → Environments**: `testpypi` e `pypi` existem
   (adicione revisores obrigatórios em `pypi` para uma aprovação manual se desejar).

O pacote está **publicado** — `pip install nene2-python` instala a versão mais recente
(v1.8.163+) diretamente do PyPI.

## Procedimento de release (por release)

1. **Atualize o `CHANGELOG.md`** — adicione uma seção `## [X.Y.Z] — YYYY-MM-DD`. A
   etapa do GitHub Release extrai as notas buscando esse header, então a seção deve
   existir ou as notas do release estarão vazias.
2. **Bump da versão** em `pyproject.toml` e atualize o lock:
   ```bash
   uv lock
   ```
3. **Abra um PR**, passe a CI (o job `package-build` valida a distribuição),
   e faça merge para `main`.
4. **Tague e faça push** do release:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` executa automaticamente: `uv build` → publica no **TestPyPI** →
   publica no **PyPI** → cria um **GitHub Release** com notas do CHANGELOG e
   os artefatos dist anexados.

## Verificação local (antes de taggear)

O job `package-build` da CI executa isso em todo PR, mas você pode reproduzir:

```bash
uv build                        # sdist + wheel em dist/
uvx twine check dist/*          # validade dos metadados PyPI
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # import limpo; exemplo/tests NÃO devem ser importáveis
```

A partir da v1.8.163 isso passa: `twine check` reporta `PASSED`, o wheel importa
de forma limpa em um venv novo, e apenas `src/nene2` é enviado (`example`/`tests` são
excluídos por `[tool.hatch.build.targets.wheel] packages = ["src/nene2"]`).

## Notas

- **Versionamento**: a `version` de `pyproject.toml` é a fonte da verdade e é incrementada
  por FT / feature / fix PR. As tags `v*` do Git são criadas seletivamente no momento do release
  (o fluxo de publicação só dispara em tags), então `pyproject` fica à frente das tags.
- **Granularidade do CHANGELOG**: one-liners por versão vivem na tabela de milestones de
  [`docs/todo/current.md`](../todo/current.md); `CHANGELOG.md`
  registra entradas agregadas por release.
- Este procedimento corresponde ao **trial de "fluxo de publicação" estilo FT7** (#541): o
  fluxo está totalmente operacional — v1.8.163 foi publicado no PyPI por ele e está
  instalável via `pip install nene2-python`.
