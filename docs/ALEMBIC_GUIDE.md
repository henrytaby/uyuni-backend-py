# Guía de Migraciones con Alembic

Esta guía explica cómo gestionar las migraciones de base de datos en el proyecto usando Alembic. Su objetivo es prevenir errores comunes como `UndefinedTable`.

## ⚠️ Regla Crítica: Registra Tus Modelos

**Antes de generar una migración**, DEBES registrar tus clases SQLModel en `alembic/env.py`.

Alembic necesita "ver" tus modelos para detectar cambios. Si no los importas en `env.py`, Alembic pensará que las tablas no existen o no detectará tus nuevos modelos, resultando en migraciones vacías o tablas faltantes.

**Archivo:** `alembic/env.py`
```python
# Importa todos los modelos para poblar SQLModel.metadata
from app.models.user import User, UserRole, UserRevokedToken, UserLogLogin
from app.models.role import Role, RoleModule
from app.models.module import Module, ModuleGroup
from app.models.audit import AuditLog
# Domain models
from app.modules.core.staff.models import Staff
from app.modules.core.org_units.models import OrgUnit
from app.modules.core.positions.models import StaffPosition
from app.modules.assets.assets.models import FixedAsset
from app.modules.assets.areas.models import Area
from app.modules.assets.groups.models import AssetGroup
from app.modules.assets.statuses.models import AssetStatus
from app.modules.assets.institutions.models import Institution
from app.modules.assets.acts.models import Act, AssetActLink
from app.modules.tasks.models import Task
# [NUEVO] Agrega tu modelo aquí:
```

---

## 👨‍💻 Recetas para Desarrolladores

### Receta 1: Agregando un Nuevo Módulo (Nuevas Tablas)
Has creado una nueva carpeta de módulo `app/modules/assets/inventory` y definido un modelo `Product` en `app/modules/assets/inventory/models.py`.

**Pasos:**
1.  **Definir el Modelo:** Asegúrate de que tu clase herede de `BaseModel` (o `SQLModel`) y tenga `table=True`.
    ```python
    class Product(BaseModel, table=True):
        # ID (UUIDv7) y campos de auditoría (created_at, etc.) son automáticos.
        name: str
        price: float
    ```
2.  **Registrar en `env.py`:** abre `alembic/env.py` y agrega:
    ```python
    from app.modules.inventory.models import Product
    ```
3.  **Generar Migración:**
    Ejecuta el siguiente comando en tu terminal (asegúrate de que el entorno virtual esté activo):
    ```bash
    ./venv/bin/alembic revision --autogenerate -m "Agregar tabla de productos de inventario"
    ```
4.  **Verificar Migración:**
    Revisa el archivo generado en `alembic/versions/`.
    *   ✅ **Bien:** Ves `op.create_table('product', ...)` con columnas `id` (UUID) y `created_at` (DateTime) automáticas.
    *   ❌ **Mal:** Ves `def upgrade(): pass` (Migración vacía). **Solución:** Vuelve al Paso 2.
5.  **Aplicar Migración:**
    ```bash
    ./venv/bin/alembic upgrade head
    ```

### Receta 2: Modificando un Modelo Existente
Quieres agregar una columna `stock_count` al modelo existente `Product`.

**Pasos:**
1.  **Modificar el Código:**
    En `app/modules/assets/inventory/models.py`:
    ```python
    stock_count: int = Field(default=0)
    ```
2.  **Generar Migración:**
    ```bash
    ./venv/bin/alembic revision --autogenerate -m "Agregar stock_count a producto"
    ```
3.  **Verificar y Aplicar:**
    Revisa el archivo buscando `op.add_column(...)` y ejecuta `./venv/bin/alembic upgrade head`.

### Error Común: `UndefinedTable`
Si ves un error como `psycopg2.errors.UndefinedTable: relation "product" does not exist`, significa:
1.  Definiste la clase en Python.
2.  **PERO** olvidaste ejecutar la migración (u olvidaste registrarla en `env.py` antes de generarla).
    
**Solución:** Revisa `alembic/env.py`, regenera la migración si es necesario, y ejecuta `alembic upgrade head`.
### Error Común: `NameError: name 'sqlmodel' is not defined`
Al generar una revisión (`autogenerate`), Alembic a veces crea código que utiliza `sqlmodel` (por ejemplo, para definir tipos de columnas) pero no añade la importación automáticamente.

**Síntoma:**
Al ejecutar `alembic upgrade head`, falla con `NameError`.

**Solución Automatizada (Implementada):**
Hemos modificado la plantilla `alembic/script.py.mako` para que incluya `import sqlmodel` por defecto en todas las nuevas migraciones.

Si por alguna razón se regenerara el entorno y se perdiera este cambio:
1. Edita `alembic/script.py.mako`.
2. Agrega `import sqlmodel` debajo de `import sqlalchemy as sa`.

**Solución Manual (Legacy):**
1. Abre el archivo de migración generado en `alembic/versions/xxxx_descripcion.py`.
2. Añade manualmente `import sqlmodel` al principio del archivo.

```python
from alembic import op
import sqlalchemy as sa
import sqlmodel # <--- AGREGAR ESTO
```
