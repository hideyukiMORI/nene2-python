# 操作指南：API 版本管理

使用 FastAPI 的 `APIRouter` + `prefix` 将 endpoint 分割到 `/v1`、`/v2` 中。

---

## 基本结构

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()

v1_router = APIRouter(prefix="/v1", tags=["v1"])
v2_router = APIRouter(prefix="/v2", tags=["v2"])

@v1_router.get("/users")
def list_users_v1() -> list[UserResponseV1]:
    ...

@v2_router.get("/users")
def list_users_v2() -> list[UserResponseV2]:
    ...

app.include_router(v1_router)
app.include_router(v2_router)
```

`APIRouter` 的 `prefix` 会**自动拼接**到 router 内部路径之前。在 router 内部的路径中不要写 `/v1`（否则会重复）。

---

## 在领域层共享逻辑；在 HTTP 层吸收版本差异

将各版本共享的逻辑保留在领域层，通过 Pydantic 模型表达各版本的差异。

```python
# 领域层（与版本无关）
@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    age: int

# v1：合并为 full_name
class UserResponseV1(BaseModel):
    user_id: int
    full_name: str
    email: str

    @classmethod
    def from_domain(cls, user: User) -> "UserResponseV1":
        return cls(
            user_id=user.user_id,
            full_name=f"{user.first_name} {user.last_name}",
            email=user.email,
        )

# v2：拆分 first_name/last_name + 增加 age + email → contact_email
class UserResponseV2(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    contact_email: str
    age: int

    @classmethod
    def from_domain(cls, user: User) -> "UserResponseV2":
        return cls(
            user_id=user.user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            contact_email=user.email,
            age=user.age,
        )
```

---

## OpenAPI schema

在各 `APIRouter` 上设置 `tags=["v1"]` / `tags=["v2"]`，Swagger UI 中会按版本分组显示。`UserResponseV1` / `UserResponseV2` 在 schema 中分别定义。

---

## 参阅

- FT109: `docs/field-trials/2026-05-field-trial-109.md`
