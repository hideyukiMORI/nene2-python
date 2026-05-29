# Guide pratique : versionner son API

Séparer les endpoints en `/v1`, `/v2` en utilisant l'`APIRouter` de FastAPI avec le paramètre `prefix`.

---

## Structure de base

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

Le `prefix` d'un `APIRouter` est **ajouté automatiquement** aux chemins à l'intérieur du router.
N'écrivez pas `/v1` dans les chemins internes (cela créerait une duplication).

---

## Partager la couche domaine ; absorber les différences de version dans la couche HTTP

Gardez la logique partagée entre les versions dans la couche domaine, et exprimez les différences
par version dans les modèles Pydantic.

```python
# Couche domaine (indépendante de la version)
@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    age: int

# v1 : fusion en full_name
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

# v2 : séparation first_name/last_name + ajout age + email → contact_email
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

## Schéma OpenAPI

Définir `tags=["v1"]` / `tags=["v2"]` sur chaque `APIRouter` les regroupe par version dans
Swagger UI. `UserResponseV1` / `UserResponseV2` sont définis séparément dans le schéma.

---

## Voir aussi

- FT109 : `docs/field-trials/2026-05-field-trial-109.md`
