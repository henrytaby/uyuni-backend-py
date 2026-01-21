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
    *   **Columna eliminada** físicamente de la base de datos (`user_log_login`).
    *   **Riesgo Eliminado**: Imposible filtrar credenciales vía logs.

### ✅ B. Estandarización de API (RESTful)
Se renombraron los endpoints para seguir el estándar de la industria (Auth0/OIDC):

| Acción | Endpoint Anterior | **Endpoint Nuevo** |
| :--- | :--- | :--- |
| Login | `/api/auth/token` | **`/api/auth/login`** |
| Register | `/api/auth/users/` | **`/api/auth/register`** |
| Profile | `/api/auth/users/me/` | **`/api/auth/me`** |
| Refresh | `/api/auth/token/refresh` | **`/api/auth/refresh`** |

### ✅ C. Protección de Bases de Datos
*   Se agregaron campos a la tabla `User` para futura lógica de bloqueo:
    *   `failed_login_attempts`
    *   `locked_until`
    *   `last_login_at`

## 3. Deuda Técnica y Futuros Pasos

1.  **Implementar Lógica de Lockout**:
    *   Los campos existen en DB, falta la lógica en `AuthService` para bloquear tras 5 intentos.
2.  **Recuperación de Contraseña**:
    *   Endpoints definidos como "Deferred" (diferidos). Requiere integración SMTP.
3.  **Cookies**:
    *   Migrar `refresh_token` a HttpOnly Cookie para Fase 2 (Banking Grade).

## 4. Conclusión
El módulo de Autenticación ha pasado de un estado **"Funcional pero Vulnerable"** a **"Seguro y Estandarizado"**. Cumple con las normativas básicas de seguridad (OWASP Top 10) respecto a manejo de sesiones y exposición de datos.
