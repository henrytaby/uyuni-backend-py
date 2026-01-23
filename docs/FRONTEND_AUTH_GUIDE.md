# Guía de Integración de Autenticación (Frontend / Angular)

Esta guía detalla el consumo de los servicios de autenticación definidos en `app/auth/routers.py`. El sistema utiliza **JWT (JSON Web Tokens)** con tokens de acceso (corto plazo) y tokens de refresco (largo plazo con rotación).

## Base URL
Todas las rutas son relativas a `/api/auth`.

---

## 1. Login (Inicio de Sesión)

Obtiene el par de tokens (Access + Refresh).

- **Endpoint**: `POST /api/auth/login`
- **Content-Type**: `application/x-www-form-urlencoded` (Estándar OAuth2)

### Request Body (Form Data)
| Param | Tipo | Requerido | Descripción |
|---|---|---|---|
| `username` | string | Sí | Nombre de usuario |
| `password` | string | Sí | Contraseña |

### Respuesta Exitosa (200 OK)
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "refresh_token": "def50200..."
}
```

### Respuestas de Error

## Conceptos de Seguridad (Contexto para Frontend)

El sistema implementa mecanismos robustos de defensa. Es importante conocerlos para entender el "por qué" de ciertos requisitos.

### 1. Lista Negra (Blacklist) y Logout
Cuando un usuario cierra sesión, simplemente "borrar" el token en el navegador no es suficiente (el token sigue siendo válido en el servidor).
*   **Mecanismo**: El backend almacena el `refresh_token` en una tabla de `UserRevokedToken`.
*   **Consecuencia**: Cualquier intento futuro de usar ese token devolverá `401 Unauthorized`.
*   **Requisito Frontend**: Por eso es **obligatorio** enviar el `refresh_token` en el endpoint de Logout. Si no se envía, la sesión queda "zombie" en el servidor hasta que expira naturalmente (días).

### 2. Rotación de Tokens
Para minimizar el riesgo de robo de sesiones, los Refresh Tokens son de **un solo uso**.
*   **Flujo**: Cuando llamas a `/refresh`, obtienes un **nuevo** Refresh Token. El anterior es invalidado inmediatamente (pasa a la Blacklist).
*   **Requisito Frontend**: Debes reemplazar tu refresh token almacenado **cada vez** que consumas el endpoint de refresh. No reutilices el antiguo.

---

## 1. Login (Inicio de Sesión)

#### 401 Unauthorized (Credenciales Inválidas)
```json
{
  "detail": "Incorrect username or password"
}
```

#### 403 Forbidden (Cuenta Bloqueada)
⚠️ **Implementación Crítica**: Si el usuario excede los intentos fallidos, se bloquea.
La respuesta incluye cabeceras y cuerpo estructurado.

**Headers**:
- `Retry-After`: Segundos a esperar (ej. `900`).

**Body (JSON)**:
```json
{
  "detail": {
    "message": "Account is locked due to too many failed attempts.",
    "code": "ACCOUNT_LOCKED",
    "unlock_at": "2023-10-27T10:15:30.123456",
    "wait_seconds": 900,
    "max_attempts": 5,
    "lockout_minutes": 15
  }
}
```

---

## 2. Refresh Token (Renovar Sesión)

Usa el token de refresco para obtener un nuevo token de acceso.

- **Endpoint**: `POST /api/auth/refresh?refresh_token=...`
- **Query Param**: `refresh_token` (string)

**Nota**: Aunque se envía como query param en la implementación actual, se recomienda revisar si su cliente prefiere enviarlo en el body. Actualmente el backend lo espera como **Query Parameter**.

### Respuesta Exitosa (200 OK)
Devuelve un nuevo par de tokens. **El refresh token anterior queda invalidado (rotación).**
```json
{
  "access_token": "nuevo_access_token...",
  "token_type": "bearer",
  "refresh_token": "nuevo_refresh_token..."
}
```

---

## 3. Logout (Cerrar Sesión)

Revoca los tokens actuales.

- **Endpoint**: `POST /api/auth/logout`
- **Header**: `Authorization: Bearer <access_token>`
- **Content-Type**: `application/json`

### Request Body (JSON)
Es opcional, pero recomendado enviar el refresh token para revocarlo explícitamente también.
```json
{
  "refresh_token": "token_actual..."
}
```

### Respuesta Exitosa (200 OK)
```json
{
  "msg": "Successfully logged out"
}
```

---

## 4. Get User Profile (Mi Perfil)

Obtiene datos del usuario actual.

- **Endpoint**: `GET /api/auth/me`
- **Header**: `Authorization: Bearer <access_token>`

### Respuesta Exitosa (200 OK)
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "first_name": "Admin",
  "last_name": "User",
  "is_verified": true
}
```

---

## 5. Get User Roles (Roles)

Lista los roles activos del usuario.

- **Endpoint**: `GET /api/auth/me/roles`
- **Header**: `Authorization: Bearer <access_token>`

### Respuesta Exitosa (200 OK)
```json
[
  {
    "id": 1,
    "name": "Super Admin",
    "icon": "shield"
  },
  {
    "id": 2,
    "name": "Vendedor",
    "icon": "shopping-cart"
  }
]
```

---

## 6. Get Dynamic Menu (Menú Dinámico)

Obtiene la estructura del menú basada en un rol específico.

- **Endpoint**: `GET /api/auth/me/menu/{role_id}`
- **Header**: `Authorization: Bearer <access_token>`

### Respuesta Exitosa (200 OK)
```json
[
  {
    "group_name": "Catálogo",
    "slug": "catalog",
    "icon": "list",
    "sort_order": 1,
    "modules": [
      {
        "name": "Productos",
        "slug": "products",
        "route": "/catalog/products",
        "permissions": {
          "module_slug": "products",
          "can_create": true,
          "can_update": true,
          "can_delete": false,
          "can_read": true
        }
      }
    ]
  }
]
```

---

## Implementación en Angular (Ejemplo)

### Interfaces TypeScript

```typescript
// auth.interfaces.ts

export interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_verified: boolean;
}

export interface LockoutError {
  message: string;
  code: 'ACCOUNT_LOCKED';
  unlock_at: string;
  wait_seconds: number;
  max_attempts: number;
  lockout_minutes: number;
}

// Ejemplo de manejo de error en servicio o interceptor
```

### AuthService (Snippet)

```typescript
import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private apiUrl = '/api/auth';

  constructor(private http: HttpClient) {}

  login(username: string, password: string) {
    // IMPORTANTE: OAuth2 usa form-urlencoded, no JSON
    const body = new URLSearchParams();
    body.set('username', username);
    body.set('password', password);

    return this.http.post<TokenResponse>(
      `${this.apiUrl}/login`,
      body.toString(),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }
    );
  }

  refreshToken(token: string) {
    // El backend espera query param
    const params = new HttpParams().set('refresh_token', token);
    return this.http.post<TokenResponse>(`${this.apiUrl}/refresh`, {}, { params });
  }
}
```
