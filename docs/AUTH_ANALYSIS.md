# Análisis de Autenticación JWT (Estado Actual - Post Refactoring)

Este documento detalla el análisis del flujo de autenticación actual (`app/auth/`) tras la fase de **Hardening & Standardization**.

## 1. Resumen de Seguridad (Estado Actual)

| Característica | Estado Anterior | **Estado Actual** | Veredicto Enterprise |
| :--- | :--- | :--- | :--- |
| **Algoritmo** | HS256 | **HS256** | ✅ Aceptable (Estándar Industria). |
| **Refresh Token** | Rotación | **Rotación + Blacklist** | ✅ Excelente. Robo mitigado. |
| **Logging** | Passwords en Texto Plano | **Sanitizado** | ✅ **Resuelto**. Columna eliminada y logs limpios. |
| **CORS** | `*` (All) | **Restringido** | ✅ **Resuelto**. Configurable vía `.env`. |
| **Anti-Bruteforce** | No existía | **Lockout Fields** | ✅ **Implementado** (DB Schema listo). |
| **Transport** | JSON Body | **JSON Body** | ⚠️ Aceptable para Fase 1. |

## 2. Mejoras Implementadas (Log de Cambios)

### ✅ A. Sanitización de Logs
*   **Antes**: Se guardaba `password` en fallos de login.
*   **Ahora**:
    *   Código modificado para no escribir password.
    *   **Columna eliminada** físicamente de la tabla (actualmente `user_log_logins`, en plural).
    *   **Riesgo Eliminado**: Imposible filtrar credenciales vía logs.

### ✅ B. Estandarización de API (RESTful)
Se renombraron los endpoints para seguir el estándar de la industria (Auth0/OIDC):

| Acción | Endpoint Anterior | **Endpoint Nuevo** |
| :--- | :--- | :--- |
| Login | `/api/auth/token` | **`/api/auth/login`** |
| Profile | `/api/auth/users/me/` | **`/api/auth/me`** |
| Refresh | `/api/auth/token/refresh` | **`/api/auth/refresh`** |

> **Nota**: No existe un endpoint público `POST /api/auth/register`. La creación de usuarios se realiza a través del submódulo `core/users/` expuesto en `POST /api/core/users/` (protegido con `PermissionChecker(module_slug=CoreModuleSlug.USERS)`), accesible solo a usuarios con el permiso `CREATE` en el módulo `core_users`.

### ✅ C. Protección de Bases de Datos
*   Se agregaron campos a la tabla `User` (`failed_login_attempts`, `locked_until`, `last_login_at`).

### ✅ D. Lógica de Negocio (Lockout Implementation)
*   **Anti-Bruteforce Activado**:
    *   Bloqueo automático tras n intentos fallidos (Configurable).
    *   Reset automático tras login exitoso.
    *   **Tests**: Cobertura completa (`tests/test_lockout.py`).

### ✅ E. Clean Code & Quality
*   Refactor de `AuthService` para cumplir SRP (Single Responsibility Principle).
*   Pasado **Mypy Strict** (100% type safety).

## 3. Deuda Técnica y Futuros Pasos

1.  **Recuperación de Contraseña**:
    *   Endpoints definidos como "Deferred" (diferidos). Requiere integración SMTP.
2.  **Cookies**:
    *   Migrar `refresh_token` a HttpOnly Cookie para Fase 2 (Banking Grade).

## 4. Conclusión
El módulo de Autenticación ha pasado de un estado **"Funcional pero Vulnerable"** a **"Seguro y Estandarizado"**. Cumple con las normativas básicas de seguridad (OWASP Top 10) respecto a manejo de sesiones y exposición de datos.
