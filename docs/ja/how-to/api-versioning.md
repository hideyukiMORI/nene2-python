# How-to: API バージョニング

FastAPI の `APIRouter` + `prefix` でエンドポイントを `/v1`, `/v2` に分離するパターン。

---

## 基本構成

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

`APIRouter` の `prefix` はルーター内のパスに **自動的に付加**される。
ルーター内のパスに `/v1` を書く必要はない（二重にならない）。

---

## ドメイン層は共有、HTTP 層でバージョン差分を吸収

バージョン間の共有ロジックはドメイン層に置き、各バージョンの Pydantic モデルで差分を表現する。

```python
# ドメイン層（バージョン非依存）
@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    age: int

# v1: full_name に結合
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

# v2: first_name/last_name を分離 + age を追加 + email → contact_email
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

## OpenAPI スキーマ

`tags=["v1"]` / `tags=["v2"]` を `APIRouter` に指定すると Swagger UI でバージョンごとに
グループ化される。スキーマには `UserResponseV1` / `UserResponseV2` が個別に定義される。

---

## 参照

- FT109: `docs/field-trials/2026-05-field-trial-109.md`
