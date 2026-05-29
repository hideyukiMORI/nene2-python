# 如何发布到 PyPI

本指南描述经过验证的发布流程：**更新 CHANGELOG → 版本号更新 → 打 tag → 自动发布（TestPyPI → PyPI → GitHub Release）**。自动化流程位于 [`.github/workflows/publish.yml`](../../.github/workflows/publish.yml)，通过 **PyPI Trusted Publishing**（OIDC — 无需长期 Token）在 `v*` tag 上触发。

## 一次性设置（维护者 — 已完成）

发布工作流使用 Trusted Publishing 和 GitHub Environments。**已配置完毕**并可正常运行；此处记录仅供参考和恢复：

1. **PyPI / TestPyPI — Trusted Publisher** 配置 `nene2-python`：
   - Owner：`hideyukiMORI`，Repository：`nene2-python`
   - Workflow：`publish.yml`
   - Environment：`pypi`（pypi.org）和 `testpypi`（test.pypi.org）
   - 注册于 https://pypi.org/manage/account/publishing/ 及 TestPyPI 的对应页面。
2. **GitHub repo → Settings → Environments**：`testpypi` 和 `pypi` 已创建（如需手动审批门，可在 `pypi` 上添加必要的审批人）。

该包**已发布** — `pip install nene2-python` 可直接从 PyPI 安装最新版本（v1.8.163+）。

## 发布流程（每次发布）

1. **更新 `CHANGELOG.md`** — 添加 `## [X.Y.Z] — YYYY-MM-DD` 章节。GitHub Release 步骤通过匹配此标题提取发布说明，因此该章节必须存在，否则发布说明为空。
2. **在 `pyproject.toml` 中更新版本号**并刷新 lock 文件：
   ```bash
   uv lock
   ```
3. **提交 PR**，通过 CI（`package-build` job 验证构建产物），然后合并到 `main`。
4. **打 tag 并推送**：
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` 自动运行：`uv build` → 发布到 **TestPyPI** → 发布到 **PyPI** → 创建带有 CHANGELOG 说明和 dist 产物附件的 **GitHub Release**。

## 本地验证（打 tag 前）

CI 的 `package-build` job 在每个 PR 上运行此验证，您也可以在本地重现：

```bash
uv build                        # sdist + wheel 输出到 dist/
uvx twine check dist/*          # PyPI 元数据有效性检查
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # 干净导入；example/tests 不应可导入
```

从 v1.8.163 起此验证通过：`twine check` 报告 `PASSED`，wheel 在全新 venv 中干净导入，且只包含 `src/nene2`（`example`/`tests` 由 `[tool.hatch.build.targets.wheel] packages = ["src/nene2"]` 排除）。

## 说明

- **版本管理**：`pyproject.toml` 中的 `version` 是权威来源，每次 FT / 功能 / 修复 PR 都会更新。Git 的 `v*` tag 在发布时选择性创建（发布工作流仅在 tag 上触发），因此 `pyproject.toml` 版本会超前于 tag。
- **CHANGELOG 粒度**：每个版本的单行条目记录在 [`docs/todo/current.md`](../todo/current.md) 的里程碑表中；`CHANGELOG.md` 按发布粒度记录聚合条目。
- 本流程对应 **FT7 级"发布流程"试验**（#541）：该流程已完全可用 — v1.8.163 已通过此流程发布到 PyPI，可通过 `pip install nene2-python` 安装。
