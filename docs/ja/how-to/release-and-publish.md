# リリースと PyPI 公開の手順

検証済みのリリースフロー — **CHANGELOG → バージョン更新 → タグ → 自動公開
（TestPyPI → PyPI → GitHub Release）** を説明する。自動化は
[`.github/workflows/publish.yml`](../../../.github/workflows/publish.yml) にあり、
`v*` タグを契機に **PyPI Trusted Publishing**（OIDC・長期トークン不要）で動く。

## 一度だけの設定（メンテナ作業・設定済み）

publish ワークフローは Trusted Publishing と GitHub Environments を使う。これは
**既に構成済み・稼働中**で、参照・復旧用に記録する:

1. **PyPI / TestPyPI の Trusted Publisher**（`nene2-python`）:
   - Owner: `hideyukiMORI`、Repository: `nene2-python`
   - Workflow: `publish.yml`
   - Environment: `pypi`（pypi.org）と `testpypi`（test.pypi.org）
   - https://pypi.org/manage/account/publishing/ と TestPyPI の同等画面で登録済み。
2. **GitHub repo → Settings → Environments**: `testpypi` と `pypi` 作成済み
   （`pypi` に必須レビュアーを設定すれば手動承認ゲートになる）。

パッケージは**公開済み**で、`pip install nene2-python` で最新リリース（v1.8.163 以降）
を PyPI から直接取得できる。

## リリース手順（毎回）

1. **`CHANGELOG.md` を更新** — `## [X.Y.Z] — YYYY-MM-DD` セクションを追加。
   GitHub Release ステップはこのヘッダーでノートを抽出するため、無いとリリース
   ノートが空になる。
2. **バージョンを更新**（`pyproject.toml`）し lock を再生成:
   ```bash
   uv lock
   ```
3. **PR を作成**し CI を通す（`package-build` ジョブが配布物を検証）→ `main` にマージ。
4. **タグを切って push**:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` が自動実行: `uv build` → **TestPyPI** 公開 → **PyPI** 公開 →
   CHANGELOG からノートを抽出し配布物を添付して **GitHub Release** を作成。

## ローカル検証（タグ前）

CI の `package-build` ジョブが PR ごとに実行するが、手元でも再現できる:

```bash
uv build                        # dist/ に sdist + wheel
uvx twine check dist/*          # PyPI メタデータ妥当性
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # クリーン import。example/tests は import 不可であること
```

v1.8.163 時点で通過する: `twine check` は `PASSED`、wheel はクリーン venv で
import 可能、配布物は `src/nene2` のみ（`example`/`tests` は
`[tool.hatch.build.targets.wheel] packages = ["src/nene2"]` により除外）。

## 補足

- **バージョン管理**: `pyproject.toml` の `version` が真実の源で、FT / 機能 / 修正 PR
  ごとに更新する。Git `v*` タグはリリース時に選択的に作成（publish はタグ時のみ発火）
  するため、pyproject がタグより先行する。
- **CHANGELOG の粒度**: 版ごとの一行サマリーは
  [`docs/todo/current.md`](../../todo/current.md) のマイルストーン表に、
  `CHANGELOG.md` にはリリース粒度の集約エントリを記録する。
- 本手順は **FT7 相当の「公開フロー」トライアル**（#541）に対応する。フローは完全稼働済みで、
  v1.8.163 を本フローで PyPI に公開済み（`pip install nene2-python` で取得可能）。
