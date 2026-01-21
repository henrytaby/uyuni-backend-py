# Guía de Autenticación y Seguridad (Developer Internal Guide)

**"The Auth Bible"**: Todo lo que necesitas saber para trabajar con el módulo de seguridad (`app/auth/`).

---

## 1. Mapa de Estructura y Responsabilidades
¿Dónde está cada cosa? Usa este mapa para no perderte.

```bash
app/auth/
├── routers.py       # 🚦 API Endpoints (/login, /register, /me). Solo definición de rutas.
├── service.py       # 🧠 Lógica de Negocio (Validaciones, creación de usuario, armado de menú).
├── schemas.py       # 📦 Modelos Pydantic (DTOs). Define qué entra y qué sale de la API.
├── utils.py         # 🔧 Herramientas (Hash password, Decode JWT, `get_current_user`).
└── __init__.py      # Exposes (mantiene limpio el import).

app/models/
├── user.py          # 🗄️ Tablas: User, UserRole, UserLogLogin, UserRevokedToken.
├── role.py          # 🗄️ Tablas: Role, RoleModule.
└── module.py        # 🗄️ Tablas: Module, ModuleGroup.

app/core/
├── config.py        # ⚙️ Configuración (SECRET_KEY, ALGORITHM, EXPIRE_MINUTES).
└── ...
```

---

## 2. Flujo de Autenticación (The "Happy Path")

El sistema usa **JWT con Refresh Rotation + Blacklist**. Esto es nivel bancario.

1.  **Login (`POST /api/auth/login`)**:
    *   Recibe `username` + `password`.
    *   Devuelve `access_token` (15 min) + `refresh_token` (7 días).
2.  **Uso (`Authorization: Bearer <token>`)**:
    *   El frontend envía el `access_token` en el header.
    *   El backend verifica firma y expiración.
3.  **Renovación (`POST /api/auth/refresh`)**:
    *   Cuando el `access_token` muere, el frontend envía el `refresh_token`.
    *   El backend valida, **quema (blacklist)** el refresh token usado y entrega un PAR nuevo.
    *   *Si alguien robó tu refresh token viejo, ya no sirve.*
4.  **Logout (`POST /api/auth/logout`)**:
    *   El backend mete el `access_token` y `refresh_token` en la `UserRevokedToken` (Blacklist).
    *   Nadie puede usar esos tokens nunca más.

---

## 3. Configuración (Lo que debes tocar)

Todo se maneja desde variables de entorno (`.env`). **No toques el código para cambiar configuración.**

| Variable | Default (Dev) | Producción Recomendada | Descripción |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | "secret" | **Generar random de 64 chars** | Firma criptográfica. Si se pierde, todos los tokens mueren. |
| `ALGORITHM` | "HS256" | "HS256" | Algoritmo de firma. |
| `ACCESS_TOKEN_EXPIRE` | 30 (min) | 15 (min) | Vida útil corta para seguridad. |
| `REFRESH_TOKEN_EXPIRE`| 7 (dias) | 1 (día) | Vida útil para "Recordarme". |
| `BACKEND_CORS_ORIGINS`| `*` | `["https://miapp.com"]` | Quién puede llamar a tu API. |

---

## 4. Guía de Implementación (How-To)

### 🛡️ Caso A: Quiero proteger mi Endpoint
*Quiero que solo usuarios logueados puedan ver los productos.*

Usa la dependencia `get_current_user` en `routers.py`:

```python
from fastapi import APIRouter, Depends
from app.auth.utils import get_current_user
from app.auth.schemas import User

router = APIRouter()

# ✅ FORMA CORRECTA
@router.get("/secure-data")
def get_secure_data(current_user: User = Depends(get_current_user)):
    return {"msg": f"Hola {current_user.username}, eres VIP."}
```

### 🔓 Caso B: Endpoint Público
*Quiero un endpoint de salud o registro público.*

Simplemente no inyectes `get_current_user`.

```python
# ✅ PÚBLICO
@router.get("/status")
def health_check():
    return {"status": "ok"}
```

### 👮 Caso C: Permisos por Rol (RBAC)
*Quiero verificar si el usuario tiene permiso para este módulo.*

```python
from app.auth.service import AuthService, get_auth_service

@router.post("/crear-producto")
def create_product(
    data: ProductCreate, 
    current_user: User = Depends(get_current_user), # 1. Autenticado
    service: AuthService = Depends(get_auth_service) # 2. Lógica Auth
):
    # Validar manualmente (por ahora)
    # Futuro: Implementar decorador @requires_permission("products", "create")
    if not service.check_permission(current_user, "products", "create"):
        raise HTTPException(403, "No tienes poder aquí.")
        
    return product_service.create(data)
```

---

## 5. Do's and Don'ts (Best Practices)

### ✅ DO (Haz esto)
*   **Usa `get_current_user`**: Es la única forma segura de obtener el usuario. Valida token, expiración y blacklist en una sola línea.
*   **Confía en `schemas.User`**: El objeto `current_user` ya tiene los datos limpios.
*   **Usa logs auditables**: Si algo crítico pasa, usa `structlog`.

### ❌ DON'T (No hagas esto)
*   **Nunca loguees passwords**: Ni en `print`, ni en `logger.info`. NUNCA. (Ya lo sanitizamos, no lo reintroduzcas).
*   **No inventes tu propio JWT decode**: Usa `utils.decode_token`. Crypto es difícil de hacer bien.
*   **No toques `UserLogLogin` manualmente**: El servicio de Auth ya lo hace por ti.

---

## 6. Diagramas para Entender

### Login Flow
```mermaid
graph LR
    User -->|User+Pass| API[/login]
    API -->|Validar| DB[(Usuarios)]
    DB -->|OK| API
    API -->|Log OK| DB[(AuditLog)]
    API -->|Tokens| User
```

### Protected Request
```mermaid
graph TD
    User -->|Bearer Token| API[/endpoint]
    API -->|Decode| Utils
    Utils -->|Check Blacklist| DB[(RevokedToken)]
    DB -->|Clean| API
    API -->|Data| User
```
