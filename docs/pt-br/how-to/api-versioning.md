# Como fazer: versionamento de API

Separe endpoints em `/v1`, `/v2` usando `APIRouter` + `prefix` do FastAPI.

---

## Estrutura básica

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

O `prefix` de um `APIRouter` é **prefixado automaticamente** nos caminhos dentro do
router. Você não escreve `/v1` nos caminhos internos do router (seria duplicado).

---

## Compartilhe a camada de domínio; absorva as diferenças de versão na camada HTTP

Mantenha a lógica compartilhada entre versões na camada de domínio, e expresse as
diferenças por versão nos modelos Pydantic.

```python
# Camada de domínio (independente de versão)
@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    age: int

# v1: concatenado em full_name
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

# v2: first_name/last_name separados + age adicionado + email → contact_email
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

## Schema OpenAPI

Definir `tags=["v1"]` / `tags=["v2"]` em cada `APIRouter` agrupa-os por versão
no Swagger UI. `UserResponseV1` / `UserResponseV2` são definidos separadamente no schema.

---

## Veja também

- FT109: `docs/field-trials/2026-05-field-trial-109.md`
