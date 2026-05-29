# nene2-python 入门指南

本教程将帮助您在 5 分钟内使用 nene2-python 运行一个 Note CRUD API。

## 前提条件

- Python 3.12 或更高版本
- 已安装 [uv](https://docs.astral.sh/uv/)
- Git

## 1. 克隆仓库

```bash
git clone https://github.com/hideyukiMORI/nene2-python.git
cd nene2-python
```

## 2. 安装依赖

```bash
uv sync
```

## 3. 启动开发服务器

```bash
uv run uvicorn src.example.app:app --reload --port 8080
```

在浏览器中打开 `http://localhost:8080/docs`，Swagger UI 已就绪。

## 4. 调用 API

```bash
# 创建笔记
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "My first note", "body": "Created with nene2-python"}'

# 获取笔记列表
curl http://localhost:8080/notes
```

## 5. 运行测试

```bash
uv run pytest
```

167 个以上的测试应全部通过。

## 下一步

- [实现新领域](first-domain.md) — 以 Tag 领域为例，逐层走通完整的架构栈
- [配置参考](../reference/configuration.md) — 配置真实数据库或启用身份验证
