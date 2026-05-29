# How-to: API-Versionierung

Endpunkte in `/v1`, `/v2` aufteilen mit FastAPIs `APIRouter` + `prefix`.

---

## Grundstruktur

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

Das `prefix` eines `APIRouter` wird **automatisch vorangestellt** an die Pfade innerhalb des Routers. Sie schreiben `/v1` nicht in den router-internen Pfaden (es würde doppelt erscheinen).

---

## Die Domain-Schicht teilen; Versionsunterschiede in der HTTP-Schicht absorbieren

Halten Sie die versionsübergreifend gemeinsame Logik in der Domain-Schicht, und drücken Sie die versionsspezifischen Unterschiede in den Pydantic-Modellen aus.

```python
# Domain-Schicht (versionsunabhängig)
@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    age: int

# v1: zu full_name zusammengeführt
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

# v2: first_name/last_name getrennt + age hinzugefügt + email → contact_email
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

## OpenAPI-Schema

Das Setzen von `tags=["v1"]` / `tags=["v2"]` auf jedem `APIRouter` gruppiert sie pro Version in der Swagger-Oberfläche. `UserResponseV1` / `UserResponseV2` werden separat im Schema definiert.

---

## Siehe auch

- FT109: `docs/field-trials/2026-05-field-trial-109.md`
