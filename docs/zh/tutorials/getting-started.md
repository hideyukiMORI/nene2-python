# nene2-python 入门

本教程将帮助您在 5 分钟内使用 nene2-python 启动一个 Notes CRUD API。

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

在浏览器中打开 `http://localhost:8080/docs` 查看 Swagger UI。

## 4. 测试 API

```bash
# 创建笔记
curl -X POST http://localhost:8080/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "我的第一条笔记", "body": "使用 nene2-python 创建"}'

# 获取笔记列表
curl http://localhost:8080/notes
```

## 5. 运行测试

```bash
uv run pytest
```

135 个以上的测试应全部通过。

## 下一步

- [配置参考](../reference/configuration.md) — 通过环境变量配置数据库和身份验证
