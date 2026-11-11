# 02. Diccionario de Base de Datos — Core & Identity

Todas las tablas del sistema siguen rigurosamente el estándar **Singular Table Naming Convention** (`user`, `role`, `user_role`, etc.) y utilizan identificadores primarios UUID (o códigos slug para recursos estables).

---

## 📊 Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    user ||--o{ user_role : "tiene_asignado"
    role ||--o{ user_role : "define"
    role ||--o{ role_module : "otorga_permisos"
    module ||--o{ role_module : "recurso_protegido"
    module_group ||--o{ module : "agrupa"
    user ||--o{ user_log_login : "registra_accesos"
    user ||--o{ user_revoked_token : "revoca_tokens"

    user {
        uuid id PK "UUIDv7 identificador único"
        string username UK "Nombre de usuario único para login"
        string email UK "Correo electrónico único"
        string first_name "Nombres del usuario"
        string last_name "Apellidos del usuario"
        string phone "Teléfono celular / WhatsApp (formato E.164)"
        string avatar_url "URL pública de imagen de perfil"
        string country "Código de país ISO (ej. BO)"
        string city "Ciudad de residencia o sucursal"
        string address "Dirección física o referencia"
        string notes "Notas administrativas internas"
        string timezone "Zona horaria IANA (ej. America/La_Paz)"
        bool is_verified "Si el correo fue verificado"
        bool is_active "Estado activo / inactivo de la cuenta"
        bool is_superuser "Acceso total bypass RBAC"
        string password_hash "Hash seguro bcrypt"
        int failed_login_attempts "Contador de intentos fallidos"
        datetime locked_until "Fecha/hora hasta la cual está bloqueado"
        datetime last_login_at "Fecha/hora del último acceso exitoso"
        datetime created_at "Auditoría de creación"
        datetime updated_at "Auditoría de última modificación"
        uuid created_by_id "Usuario que creó el registro"
        uuid updated_by_id "Usuario que modificó el registro"
    }

    role {
        uuid id PK "UUIDv7 identificador único"
        string name UK "Nombre descriptivo del rol"
        string slug UK "Identificador en código (ej. admin, seller)"
        string description "Descripción del rol y responsabilidades"
        string icon "Icono PrimeNG / Lucide para menús"
        int sort_order "Posición en desplegables y selectores"
        bool is_active "Estado activo / inactivo"
        datetime created_at "Auditoría de creación"
        datetime updated_at "Auditoría de última modificación"
    }

    user_role {
        uuid id PK "UUIDv7 identificador único"
        uuid user_id FK "user.id"
        string role_slug FK "role.slug"
        bool is_active "Si la asignación está vigente"
        datetime created_at "Auditoría de asignación"
        datetime updated_at "Auditoría de modificación"
    }

    user_log_login {
        uuid id PK "UUIDv7 identificador único"
        uuid user_id FK "user.id (opcional si falló usuario inexistente)"
        string username "Nombre de usuario intentado"
        string ip_address "Dirección IP del cliente"
        string host_info "User-Agent del navegador y sistema operativo"
        bool is_successful "Si el intento fue exitoso o fallido"
        string token "Token JWT generado (privado interno)"
        datetime token_expiration "Fecha de caducidad del token"
        datetime logged_out_at "Fecha/hora en que cerró sesión"
        datetime created_at "Fecha y hora del intento de acceso"
    }

    user_revoked_token {
        uuid id PK "UUIDv7 identificador único"
        string token UK "Token JWT invalidado"
        uuid user_id "ID del usuario dueño del token"
        datetime revoked_at "Fecha y hora de revocación"
    }

    module_group {
        uuid id PK "UUIDv7 identificador único"
        string name UK "Nombre visible del grupo en la barra lateral"
        string slug UK "Slug único (ej. configuration, commerce)"
        string description "Descripción del grupo funcional"
        string icon "Icono para el encabezado del acordeón"
        int sort_order "Orden en el menú lateral"
        bool is_active "Estado de activación"
    }

    module {
        uuid id PK "UUIDv7 identificador único"
        string name UK "Nombre visible del módulo en el menú"
        string slug UK "Slug único protegido por RBAC (ej. users, sales)"
        string group_slug FK "module_group.slug"
        string route "Ruta angular (ej. /users, /commerce/products)"
        string icon "Icono del ítem de navegación"
        int sort_order "Orden relativo dentro del grupo"
        bool is_active "Estado de activación"
    }

    role_module {
        uuid id PK "UUIDv7 identificador único"
        string role_slug FK "role.slug"
        string module_slug FK "module.slug"
        bool can_create "Permiso para crear registros (POST)"
        bool can_update "Permiso para modificar registros (PUT/PATCH)"
        bool can_delete "Permiso para eliminar registros (DELETE)"
        bool scope_all "True: ve todos los registros; False: solo los propios"
        bool is_active "Si la regla de permiso está vigente"
    }
```

---

## 📑 Diccionario Campo por Campo

### 1. Tabla: `user`
Almacena las cuentas de usuario y credenciales del sistema.

| Columna | Tipo | Nulo | Clave | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | No | PK | Identificador único UUIDv7. |
| `username` | `VARCHAR` | No | UK | Nombre de usuario único para el inicio de sesión. |
| `email` | `VARCHAR` | No | UK | Correo electrónico principal de la cuenta. |
| `first_name` | `VARCHAR` | Sí | | Nombres de pila de la persona. |
| `last_name` | `VARCHAR` | Sí | | Apellidos de la persona. |
| `phone` | `VARCHAR(30)` | Sí | | Teléfono celular / WhatsApp (formato E.164). |
| `avatar_url` | `VARCHAR(500)` | Sí | | URL de la imagen de perfil (Cloudinary, R2). |
| `country` | `VARCHAR(10)` | Sí | | Código de país ISO (Default: `"BO"`). |
| `city` | `VARCHAR(100)` | Sí | | Ciudad de residencia o sucursal operativa. |
| `address` | `VARCHAR(255)` | Sí | | Dirección física o referencia de ubicación. |
| `notes` | `TEXT` | Sí | | Notas administrativas y supervisión interna. |
| `timezone` | `VARCHAR(50)` | Sí | | Zona horaria IANA (Default: `"America/La_Paz"`). |
| `password_hash` | `VARCHAR` | No | | Hash seguro bcrypt (nunca retornado en respuestas JSON). |
| `is_verified` | `BOOLEAN` | No | | `true` si el correo ha sido verificado. Default: `false`. |
| `is_active` | `BOOLEAN` | No | | `true` si la cuenta puede iniciar sesión. Default: `true`. |
| `is_superuser` | `BOOLEAN` | No | | `true` si tiene privilegios de superadministrador. Default: `false`. |
| `failed_login_attempts` | `INTEGER` | No | | Contador de fallos consecutivos de autenticación. |
| `locked_until` | `TIMESTAMP` | Sí | | Si no es nulo y es futuro, bloquea cualquier intento de login. |
| `last_login_at` | `TIMESTAMP` | Sí | | Marca temporal del último inicio de sesión exitoso. |
| `created_at` | `TIMESTAMP` | Sí | | Fecha y hora de creación del registro (CDC). |
| `updated_at` | `TIMESTAMP` | Sí | | Fecha y hora de última modificación (CDC). |
| `created_by_id` | `UUID` | Sí | | UUID del usuario creador (CDC). |
| `updated_by_id` | `UUID` | Sí | | UUID del usuario modificador (CDC). |

---

### 2. Tabla: `role`
Catálogo de roles del sistema definidos en el arranque o por dominios.

| Columna | Tipo | Nulo | Clave | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | No | PK | Identificador único UUIDv7. |
| `name` | `VARCHAR` | No | UK | Nombre del rol (ej: `"Administrador Sistema"`). |
| `slug` | `VARCHAR` | No | UK | Clave alfanumérica fija en código (ej: `"admin"`, `"seller"`). |
| `description` | `VARCHAR` | Sí | | Descripción operativa del perfil. |
| `icon` | `VARCHAR` | Sí | | Icono representativo (ej: `"pi pi-user"`). |
| `sort_order` | `INTEGER` | Sí | | Prioridad de visualización en selectores. |
| `is_active` | `BOOLEAN` | No | | Si el rol está habilitado para ser asignado. Default: `true`. |

---

### 3. Tabla: `user_role`
Tabla asociativa muchos a muchos entre usuarios y roles.

| Columna | Tipo | Nulo | Clave | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | No | PK | Identificador único de la asignación. |
| `user_id` | `UUID` | No | FK | Referencia foránea a `user.id`. |
| `role_slug` | `VARCHAR` | No | FK | Referencia foránea a `role.slug`. |
| `is_active` | `BOOLEAN` | No | | `true` si el rol está activo en el usuario; `false` si fue revocado. |

---

### 4. Tabla: `user_log_login`
Bitácora de seguridad y auditoría de accesos.

| Columna | Tipo | Nulo | Clave | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `id` | `UUID` | No | PK | Identificador único del evento de log. |
| `user_id` | `UUID` | Sí | FK | Referencia a `user.id` (nulo si el usuario no existía). |
| `username` | `VARCHAR` | Sí | | Usuario enviado en la petición de login. |
| `ip_address` | `VARCHAR` | No | | Dirección IP de origen de la conexión. |
| `host_info` | `VARCHAR` | No | | User-Agent completo (navegador, versión, sistema operativo). |
| `is_successful` | `BOOLEAN` | No | | `true`: autenticado correctamente. `false`: contraseña errónea o bloqueado. |
| `token` | `VARCHAR` | Sí | | Token generado (privado, nunca expuesto por API). |
| `token_expiration` | `TIMESTAMP` | Sí | | Fecha límite de validez del token. |
| `logged_out_at` | `TIMESTAMP` | Sí | | Fecha/hora en la que se realizó logout voluntario. |
| `created_at` | `TIMESTAMP` | Sí | | Marca temporal del intento de login. |

