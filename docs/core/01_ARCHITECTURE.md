# 01. Arquitectura y Reglas de Negocio — Core & Identity

Este documento detalla los principios de diseño, la estructura modular y las reglas de negocio críticas implementadas en el módulo **Core** para la gestión de usuarios, seguridad y control de acceso.

---

## 🏛️ Arquitectura Modular DDD-Lite

El módulo sigue la arquitectura en capas estricta del backend:

```text
Routers (API REST) ──► Services (Reglas de Negocio) ──► Repositories (Data Access) ──► Models / Database
```

```mermaid
flowchart TD
    subgraph Client ["Cliente Frontend (Angular / Postman)"]
        REQ["Petición HTTP con JWT Bearer Token"]
    end

    subgraph Security ["Capa de Seguridad Transversal"]
        AUTH["Auth Middleware / JWT Validator"]
        RBAC["PermissionChecker(USERS, Action)"]
    end

    subgraph CoreLayer ["Capa de Aplicación (Core Domain)"]
        ROUTER["UsersRouter (/api/core/users)"]
        SERVICE["UserService (Hashing, Roles & Logins)"]
        REPO["UserRepository (selectinload Eager Loading)"]
    end

    subgraph Persistence ["Capa de Persistencia (PostgreSQL)"]
        T_USER[("user")]
        T_ROLE[("role")]
        T_USER_ROLE[("user_role")]
        T_LOG[("user_log_login")]
    end

    REQ --> AUTH --> RBAC --> ROUTER
    ROUTER --> SERVICE
    SERVICE --> REPO
    REPO --> T_USER
    REPO --> T_USER_ROLE
    REPO --> T_ROLE
    SERVICE --> T_LOG
```

---

## 🔐 Reglas de Negocio Críticas

### 1. Unicidad, Formato e Inmutabilidad de Identidad
- **Username (Nombre de Usuario):**
  - **Sin espacios:** Se rechaza cualquier espacio intermedio, inicial o final (ej: `"henry. taby"` es rechazado con error 422).
  - **Longitud:** Obligatoriamente entre 3 y 30 caracteres.
  - **Caracteres permitidos:** Alfanuméricos, punto (`.`), guion (`-`) y guion bajo (`_`).
  - **Sin caracteres especiales consecutivos:** No se permite `..`, `--`, `__` ni combinaciones consecutivas.
  - **Sin iniciar ni terminar en signos:** Debe empezar y terminar con un carácter alfanumérico.
  - **Normalización:** Se convierte automáticamente a minúsculas (`lowercase`), evitando problemas de duplicidad como `Admin` vs `admin`.
- **Email (Correo Electrónico):**
  - Validador estricto RFC 5322 (`EmailStr`): Obliga a tener un formato de email real con dominio y TLD válido.
  - Normalización: Se limpia de espacios y se normaliza a minúsculas automáticamente (`lower().strip()`).
- **Contraseña:** Mínimo 6 caracteres tanto en creación como en actualización.
- **Nombres y Apellidos:** Se limpian automáticamente de espacios innecesarios (`strip()`).
- **Hashing Obligatorio:** Las contraseñas en texto plano nunca tocan la base de datos ni los logs de auditoría. Se procesan siempre mediante `get_password_hash` (bcrypt con salt seguro).

### 2. Perfil Operativo y Campos Estándar de la Industria
Para soportar casos de uso reales de ERP comercial, CRM de clientes y comunicación directa con el equipo o clientes, la entidad `user` incorpora campos normalizados de la industria:
- **`phone` (Teléfono / WhatsApp):** Almacena el número en formato internacional o local (hasta 30 caracteres, indexado para búsquedas rápidas). Permite al frontend renderizar botones de acción directa con WhatsApp (`https://wa.me/<phone>`) o llamadas telefónicas.
- **`avatar_url` (Foto de Perfil):** Enlace seguro (Cloudinary, AWS S3, Cloudflare R2 o CDN) para mostrar avatares personalizados en barras de navegación, tablas y comentarios.
- **`country` (País):** Código estándar ISO 3166-1 alpha-2 (por defecto `"BO"`), facilitando prefijos telefónicos, localización y cumplimiento fiscal.
- **`city` (Ciudad / Sucursal):** Ciudad operativa o sucursal donde presta servicios el usuario (hasta 100 caracteres, indexado en búsquedas).
- **`address` (Dirección):** Ubicación física, calle o referencia de domicilio/oficina.
- **`notes` (Notas Administrativas):** Campo de texto libre para observaciones de supervisión, motivos de contratación o historial interno (sin límite de tamaño).
- **`timezone` (Zona Horaria):** Identificador IANA (por defecto `"America/La_Paz"`) para conversiones locales de timestamps y auditorías.
- **Búsqueda Global Multicampo en Repositorio (`UserRepository`):**
  El parámetro `search` del endpoint `GET /api/core/users/` busca de manera insensible a mayúsculas/minúsculas en los siguientes campos simultáneamente:
  `["username", "email", "first_name", "last_name", "phone", "city"]`.

### 3. Gestión Atómica de Roles (`user_role`)
- Al crear o actualizar un usuario, el cliente puede enviar una lista de identificadores (`role_slugs: ["admin", "vendedor"]`).
- **Validación Preventiva:** Cada rol enviado debe existir previamente en la tabla `role` y tener `is_active = True`. De lo contrario, se rechaza la transacción completa con `400 Bad Request`.
- **Sincronización Inteligente (`_sync_user_roles`):**
  - Si un rol ya fue asignado previamente y se desmarcó, se marca `is_active = False` (preservando el historial de auditoría CDC).
  - Si un rol inactivo vuelve a seleccionarse, se reactiva con `is_active = True`.
  - Si es un rol nuevo, se inserta una nueva tupla en `user_role`.
- **Endpoints Atómicos Dedicados:** Adicionalmente al array `role_slugs` en el payload principal, se proveen `POST /api/core/users/{id}/roles/{role_slug}` y `DELETE /api/core/users/{id}/roles/{role_slug}` para activación y desactivación granular de roles individuales sin necesidad de enviar todo el objeto usuario.

### 4. Trazabilidad y Auditoría de Inicios de Sesión (`user_log_login`)
- Cada llamada al endpoint de login (`POST /api/auth/login`) genera un registro inmutable en `user_log_login`.
- Registra:
  - `user_id`: Identificador del usuario (o `null` si el usuario no existía).
  - `username`: Nombre de usuario ingresado en el formulario.
  - `ip_address`: Dirección IP de origen (capturada desde encabezados `X-Forwarded-For` o conexión directa).
  - `host_info`: User-Agent del navegador y sistema operativo cliente.
  - `is_successful`: `true` si las credenciales fueron válidas; `false` si falló la contraseña o el usuario estaba bloqueado.
  - `logged_out_at`: Se actualiza cuando el usuario consume `POST /api/auth/logout`.
- **Regla de Privacidad:** En los endpoints públicos o de consulta de usuarios (`GET /api/core/users/{id}/logins`), **nunca** se retorna el token JWT generado ni hashes de seguridad.

### 5. Protección contra Fuerza Bruta
- La entidad `user` mantiene los contadores `failed_login_attempts` y `locked_until`.
- Tras superar el umbral configurado de intentos erróneos, la cuenta se bloquea automáticamente por un tiempo determinado, impidiendo nuevos accesos aun cuando se ingrese la contraseña correcta posteriormente.

---

## 🔄 Ciclo de Vida: Creación y Asignación de Roles

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrador (Angular)
    participant API as UsersRouter (/api/core/users)
    participant Service as UserService
    participant Repo as UserRepository
    participant DB as PostgreSQL

    Admin->>API: POST /api/core/users/ (Payload con role_slugs: ["admin"])
    API->>Service: create(user_obj, password, role_slugs)
    Service->>DB: Validar que username y email no existan
    Service->>DB: Validar que cada role_slug exista y esté activo en 'role'
    alt Rol no existe o inactivo
        Service-->>API: 400 Bad Request ("Role 'xyz' not found or inactive")
        API-->>Admin: Error descriptivo
    else Validación Exitosa
        Service->>Service: Hash de contraseña (bcrypt)
        Service->>Repo: create(user_obj)
        Repo->>DB: INSERT INTO "user" (...)
        loop Para cada role_slug
            Service->>DB: INSERT INTO "user_role" (user_id, role_slug, is_active=True)
        end
        Service->>DB: COMMIT Transacción
        Service->>Repo: get_by_id(user_id) con selectinload
        Repo->>DB: SELECT "user" JOIN "user_role" JOIN "role"
        Repo-->>Service: User con roles activos resueltos
        Service-->>API: UserReadDetailed (con roles y role_slugs)
        API-->>Admin: 200 OK (Usuario creado con roles)
    end
```

