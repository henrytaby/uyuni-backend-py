# Ecosistema Core (Identidad, Usuarios y Seguridad) — Guía Maestra

Bienvenido a la documentación oficial del dominio **Core** del sistema **Uyuni Backend**. Este dominio actúa como el núcleo de seguridad, gestión de cuentas de usuario, control de acceso basado en roles (RBAC granular), auditoría de sesiones y registro de manifiestos declarativos de navegación.

---

## 🎯 Propósito del Dominio

El dominio `core` resuelve los siguientes desafíos arquitecturales de nivel empresarial:

1. **Gestión Integral de Identidad:** Control de cuentas de usuario (`user`), perfiles, verificación de email y bloqueo reactivo ante ataques de fuerza bruta (`failed_login_attempts`, `locked_until`).
2. **Control de Accesos Basado en Roles (RBAC Granular):** Desacoplamiento entre usuarios y roles a través de `user_role`, con asignación de permisos CRUD y alcance global (`scope_all`) sobre cada módulo vía `role_module`.
3. **Auditoría de Inicios de Sesión (Login History):** Trazabilidad exhaustiva de cada intento de acceso (`user_log_login`) registrando dirección IP, agente de usuario/dispositivo, fecha/hora y estado (éxito o fallo), sin exponer credenciales sensibles.
4. **Catálogos Dinámicos de Sistema:** Exposición de proveedores de datos (`CoreRolesProvider`) para alimentar selectores y combos en el frontend de forma instantánea (`GET /api/catalogs/roles` y `/api/catalogs/bulk`).
5. **Manifiestos Descentralizados:** Sincronización idempotente de grupos, módulos y rutas en el arranque del servidor sin requerir scripts SQL manuales.

---

## 📚 Índice de la Documentación

La documentación se encuentra organizada en 3 volúmenes especializados:

| Documento | Audiencia | Contenido Principal |
| :--- | :--- | :--- |
| **[01. Arquitectura y Seguridad](./01_ARCHITECTURE.md)** | Arquitectos, Tech Leads, Backend Devs | Patrón DDD-Lite, flujo de autenticación, ciclo de vida de usuarios, validaciones y sincronización de permisos. |
| **[02. Diccionario de Base de Datos](./02_DATABASE_DICTIONARY.md)** | DBAs, Fullstack Devs, Auditores | Diagrama Entidad-Relación (ERD) en estricto singular y descripción de las 7 tablas de identidad y seguridad. |
| **[03. Guía de Integración Frontend](./03_FRONTEND_INTEGRATION_GUIDE.md)** | Frontend Devs (Angular, PrimeNG) | Arquitectura de UI con pestañas (`p-tabs`), contratos TypeScript, consumo de endpoints REST, payloads JSON y buenas prácticas. |

---

## 🧩 Resumen de Submódulos y Directorios

El dominio Core está ubicado en `app/modules/core/`:

```text
app/modules/core/
├── __init__.py         # Inicialización e importación de proveedores de catálogo
├── constants.py        # Slugs de módulos Core (USERS = "users")
├── manifest.py         # Manifiesto declarativo (Grupo: Configuración, Módulo: Usuarios)
├── routers.py          # Enrutador agregador unificado (/api/core)
├── catalogs/           # Proveedores de catálogos dinámicos
│   ├── __init__.py     # Registro de "roles" y "core_roles" en global_registry
│   └── providers.py    # CoreRolesProvider (SELECT slug, name, icon FROM role)
└── users/              # Submódulo transaccional de usuarios
    ├── __init__.py
    ├── models.py       # (Entidades importadas de app.models.user)
    ├── schemas.py      # UserCreate, UserUpdate, UserRead, UserReadDetailed, UserLogLoginRead
    ├── repository.py   # UserRepository con selectinload para carga optimizada de roles
    ├── service.py      # UserService (validaciones, hashing bcrypt, roles y logs de login)
    └── routers.py      # Endpoints REST (/api/core/users)
```

---

## 🧭 Menú Frontend y Jerarquía de Navegación

En el frontend de gestión (Angular), el módulo Core se ubica bajo el grupo **Configuración**:

| Módulo | Ruta | Icono PrimeNG / Lucide | Tipo | Propósito |
| :--- | :--- | :--- | :--- | :--- |
| **Usuarios** | `/users` (o `/configuration/users`) | `pi pi-user` / `LucideUser` | Gestión Administrativa | CRUD de cuentas, asignación de roles y visor de historial de accesos. |

---

## 🛠️ Stack Tecnológico

- **Framework:** FastAPI con Python 3.14.6
- **Modelado / ORM:** SQLModel (SQLAlchemy 2.0 + Pydantic v2)
- **Base de Datos:** PostgreSQL en producción (`fastapi_product`), SQLite en memoria para tests
- **Hashing de Contraseñas:** Bcrypt con salting automático
- **Carga Eager:** `selectinload` de SQLAlchemy para resolver relaciones `User -> UserRole -> Role` en una sola consulta
- **Estándar de Nombres:** **Singular Table Naming Convention** (`user`, `role`, `user_role`, `user_log_login`, `role_module`, `module_group`, `module`)

