# Manual del Desarrollador: Creación de Módulos (v2.0)

Esta guía describe el flujo de trabajo estándar para añadir una nueva funcionalidad (Módulo) al sistema **FastAPI Enterprise**, asegurando el cumplimiento de los estándares de Calidad, Seguridad y Arquitectura.

## Flujo de Trabajo (Receta Paso a Paso)

```mermaid
flowchart TD
    A[1. Modelo DB (SQLModel + Mixins)] --> B[2. Migración Alembic]
    B --> C[3. Schemas (Pydantic DTOs)]
    C --> D[4. Repositorio (Acceso a Datos)]
    D --> E[5. Servicio (Lógica de Negocio)]
    E --> F[6. Router (API + Inyección)]
    F --> G[7. Registrar Router]
    G --> H[8. Tests (Pytest)]
```

> **Nota**: Para los fundamentos teóricos, consulta:
> *   **[Guía de Arquitectura / Patrones](DESIGN_PATTERNS_GUIDE.md)**
> *   **[Guía de Auditoría](AUDIT_GUIDE.md)**
> *   **[Guía de Calidad](QUALITY_GUIDE.md)**

---

### 1. Definición del Modelo (Base de Datos)

El primer paso es definir la entidad.
**Reglas de Oro**:
1.  Heredar de `SQLModel` y `AuditMixin` (para auditoría automática).
2.  Usar `uuid.UUID` como Primary Key (UUIDv7 default).
3.  Nombre de tabla en **plural** (`__tablename__ = "products"`).

**Archivo**: `app/modules/{nombre_modulo}/models.py`

```python
import uuid
from sqlmodel import Field, SQLModel
from app.models.mixins import AuditMixin
import uuid6 # Librería para UUIDv7

# Heredar de AuditMixin agrega: created_at, updated_at, created_by_id, updated_by_id
class NuevoRecurso(SQLModel, AuditMixin, table=True):
    __tablename__ = "nuevos_recursos"

    id: uuid.UUID = Field(
        default_factory=uuid6.uuid7, 
        primary_key=True,
        description="Identificador único (UUIDv7)"
    )
    nombre: str = Field(index=True)
    activo: bool = Field(default=True)
```

> **Magia de Auditoría**: Gracias a `AuditMixin` y los Hooks del sistema, **NO** necesitas preocuparte por llenar `created_by_id` o `updated_at`. El sistema lo hace solo.

---

### 2. Generar Migración (Alembic)

Registra tu modelo en `alembic/env.py` (si no lo hace automáticamente) y genera el script.

```bash
# 1. Crear la migración
alembic revision --autogenerate -m "add_nuevo_recurso"

# 2. Aplicar cambios a la BD
alembic upgrade head
```

---

### 3. Crear Schemas (DTOs)

Define qué datos entran y salen.
**Regla**: Los schemas son "tontos". No deben tener lógica de base de datos.

**Archivo**: `app/modules/{nombre_modulo}/schemas.py`

```python
import uuid
from pydantic import BaseModel

class NuevoRecursoBase(BaseModel):
    nombre: str
    activo: bool = True

class NuevoRecursoCreate(NuevoRecursoBase):
    pass # ID se genera en backend

class NuevoRecursoRead(NuevoRecursoBase):
    id: uuid.UUID
```

---

### 4. Crear Repositorio

Capa de acceso a datos. Hereda de `BaseRepository`.
**Regla**: Aquí van las consultas SQL (`select`, `where`).

**Archivo**: `app/modules/{nombre_modulo}/repository.py`

```python
from app.core.repository import BaseRepository
from .models import NuevoRecurso

class NuevoRecursoRepository(BaseRepository[NuevoRecurso]):
    def __init__(self, session):
        super().__init__(session, NuevoRecurso)
    
    # Métodos extra si necesitas búsquedas complejas
    def get_by_name(self, name: str):
        statement = select(self.model).where(self.model.nombre == name)
        return self.session.exec(statement).first()
```

---

### 5. Crear Servicio (Lógica de Negocio)

Aquí va la validación y reglas de negocio.
**Regla**: Si necesitas verificar si algo existe, pídeselo al Repositorio. Si falla, lanza `NotFoundException`.

**Archivo**: `app/modules/{nombre_modulo}/service.py`

```python
import uuid
from app.core.exceptions import NotFoundException
from .repository import NuevoRecursoRepository
from .schemas import NuevoRecursoCreate

class NuevoRecursoService:
    def __init__(self, repository: NuevoRecursoRepository):
        self.repository = repository

    def crear(self, data: NuevoRecursoCreate):
        # Ejemplo: Validar unicidad (usando metodo del repo, no SQL directo)
        # if self.repository.get_by_name(data.nombre): ...
        
        # Convertir DTO a Modelo DB
        nuevo_db = NuevoRecurso.model_validate(data)
        
        # Guardar (AuditMixin se llenará solo aquí)
        return self.repository.create(nuevo_db)
```

---

### 6. Crear Router (API)

Expone los endpoints.
**Regla**: Usa Inyección de Dependencias (`Depends`) para obtener el Servicio y el Usuario actual.

**Archivo**: `app/modules/{nombre_modulo}/routers.py`

```python
import uuid
from fastapi import APIRouter, Depends, status
from app.core.db import get_session
from .service import NuevoRecursoService
from .repository import NuevoRecursoRepository
from .schemas import NuevoRecursoCreate, NuevoRecursoRead

router = APIRouter()

# Factoría de dependencias
def get_service(session = Depends(get_session)):
    repo = NuevoRecursoRepository(session)
    return NuevoRecursoService(repo)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=NuevoRecursoRead)
def create_item(
    data: NuevoRecursoCreate, 
    service: NuevoRecursoService = Depends(get_service)
):
    return service.crear(data)
```

---

### 7. Registrar el Módulo

Añade tu nuevo router al archivo principal.

**Archivo**: `app/core/routers.py`

```python
from app.modules.nuevo_recurso.routers import router as nuevo_router

api_router.include_router(nuevo_router, prefix="/nuevos", tags=["Nuevos"])
```

---

### 8. Testing Automatizado

Crea un test de integración. Usa `TestClient`.

**Archivo**: `tests/modules/nuevo_recurso/test_routers.py`

```python
def test_create_nuevo_recurso_ok(client, superuser_token_headers):
    data = {"nombre": "Test 1"}
    response = client.post("/api/nuevos/", json=data, headers=superuser_token_headers)
    
    assert response.status_code == 201
    content = response.json()
    assert content["nombre"] == "Test 1"
    assert "id" in content # UUID generado
```

---

### Checklist de Calidad Final

Antes de `git push`, ejecuta:

```bash
# 1. Formatear y Linting
ruff check --fix .
ruff format .

# 2. Tipado Estático
mypy .

# 3. Tests
pytest
```
