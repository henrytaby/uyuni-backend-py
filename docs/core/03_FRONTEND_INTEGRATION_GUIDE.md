# 03. Guía de Integración Frontend — Gestión de Usuarios y Seguridad

Esta guía está dirigida a desarrolladores de Frontend (**Angular 21 + PrimeNG 21**) encargados de implementar la pantalla y el modal/drawer de gestión de usuarios en `/users` o `/configuration/users`.

---

## 🎨 1. Arquitectura de UI Recomendada: Interfaz con Pestañas (`p-tabs`)

Para ofrecer una experiencia ergonómica de nivel corporativo, la vista o diálogo de detalle de un usuario se estructura en **3 pestañas** ("cejas" de PrimeNG):

```text
┌────────────────────────────────────────────────────────────────────────┐
│  👤 Detalle de Usuario: carlos.dev@empresa.com                         │
├────────────────────────────────────────────────────────────────────────┤
│  [ 📝 Datos Generales ]   [ 🛡️ Roles Asignados ]   [ 📜 Historial de Accesos ]│
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  TAB 1 (Datos): Nombre, Apellido, Username, Email, Password,           │
│                 Teléfono / WhatsApp, Avatar URL, País, Ciudad,         │
│                 Dirección, Notas Administrativas, Timezone, Estados    │
│  TAB 2 (Roles): Selector múltiple <p-multiSelect> y lista de roles     │
│  TAB 3 (Logs):  Tabla <p-table> de inicios de sesión y auditoría IP    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 2. Contratos e Interfaces TypeScript

Copia y pega estas interfaces en tu proyecto Angular (ej. `src/app/core/models/user.model.ts`):

```typescript
// --- Catálogos ---
export interface CatalogItem<T = string> {
  value: T;
  label: string;
  extra?: {
    icon?: string;
    description?: string;
    [key: string]: any;
  } | null;
}

// --- Roles ---
export interface RoleSummary {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
}

// --- Usuario ---
export interface UserDetail {
  id: string;
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  notes?: string | null;
  timezone?: string | null;
  is_verified: boolean;
  is_active: boolean;
  is_superuser: boolean;
  role_slugs: string[];
  roles: RoleSummary[];
  created_at?: string | null;
  updated_at?: string | null;
  created_by_id?: string | null;
  updated_by_id?: string | null;
}

// --- Payloads de Creación y Edición ---
export interface UserCreatePayload {
  username: string;
  email: string;
  password: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  notes?: string | null;
  timezone?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  is_verified?: boolean;
  role_slugs?: string[];
}

export interface UserUpdatePayload {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  notes?: string | null;
  timezone?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  is_verified?: boolean;
  role_slugs?: string[];
}

// --- Historial de Login (user_log_login) ---
export interface UserLoginLog {
  id: string;
  created_at: string;
  ip_address: string;
  host_info: string;
  is_successful: boolean;
  logged_out_at?: string | null;
}
```

---

## ⚡ 3. Endpoints de la API REST

Todos los endpoints requieren el encabezado `Authorization: Bearer <access_token>`.

### A. Listado de Usuarios (DataTable Principal)
```http
GET /api/core/users/?offset=0&limit=15&sort_by=created_at&sort_order=desc&search=&is_active=true
```

#### Parámetros de Consulta (Query Params):
- `offset`: Número de registros a omitir (default: `0`).
- `limit`: Tamaño de la página (default: `100`, sugerido UI: `15`).
- `sort_by`: Campo para ordenar (`username`, `email`, `created_at`, `city`).
- `sort_order`: Dirección (`asc` o `desc`).
- `search`: Texto para búsqueda global insensible a mayúsculas en `["username", "email", "first_name", "last_name", "phone", "city"]`.
- `is_active`: Filtrar por usuarios activos (`true`/`false`).
- `is_superuser`: Filtrar por superusuarios (`true`/`false`).

#### Respuesta de Ejemplo:
```json
[
  {
    "id": "01a1cbf8-b99b-7323-8ec2-11ef8412aa01",
    "username": "carlos_admin",
    "email": "carlos@empresa.com",
    "first_name": "Carlos",
    "last_name": "Mamani",
    "phone": "+59170012345",
    "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
    "country": "BO",
    "city": "Santa Cruz",
    "address": "Av. San Martín #450, Equipetrol",
    "notes": "Líder de operaciones sucursal Santa Cruz",
    "timezone": "America/La_Paz",
    "is_verified": true,
    "is_active": true,
    "is_superuser": false,
    "role_slugs": ["admin"],
    "roles": [
      {
        "id": "01a1cbf8-a001-7111-9ec2-888888888888",
        "name": "Administrador Sistema",
        "slug": "admin",
        "icon": "pi pi-user",
        "description": "Acceso administrativo general"
      }
    ],
    "created_at": "2026-11-10T18:20:00",
    "updated_at": "2026-11-11T12:00:00"
  }
]
```

### B. Conteo Total de Usuarios (para Paginador de PrimeNG)
```http
GET /api/core/users/count?search=&is_active=true
```
```json
{
  "total": 42
}
```

---

### C. Crear Usuario con Roles (`POST /api/core/users/`)
Al crear un usuario, puedes enviar directamente la lista de `role_slugs` junto con sus datos de perfil:

```http
POST /api/core/users/
Content-Type: application/json
```
```json
{
  "username": "lucia_vendedora",
  "email": "lucia@empresa.com",
  "first_name": "Lucía",
  "last_name": "Pérez",
  "password": "PasswordSeguro2026*",
  "phone": "+59171234567",
  "avatar_url": "https://avatar.iran.liara.run/public/44",
  "country": "BO",
  "city": "La Paz",
  "address": "Calle 21 de Calacoto, Edif. Titanium Of. 402",
  "notes": "Encargada de ventas presenciales showroom Calacoto",
  "timezone": "America/La_Paz",
  "is_active": true,
  "is_superuser": false,
  "is_verified": true,
  "role_slugs": ["admin"]
}
```

> [!IMPORTANT]
> **Validaciones de Seguridad Estrictas en el Backend:**
> - **Username:** Debe tener entre 3 y 30 caracteres, sin espacios (`\s`), sin caracteres especiales consecutivos (`..`, `__`, `--`), y sin iniciar/terminar con símbolos. Cualquier espacio (como `"henry. taby"`) es rechazado con `422 Unprocessable Entity`. Se normaliza automáticamente a minúsculas (`lowercase`).
> - **Email:** Debe cumplir con el estándar RFC 5322 (`EmailStr`). Se normaliza a minúsculas y se limpian espacios en los extremos.
> - **Password:** Mínimo 6 caracteres.

> [!NOTE]
> Si envías un rol inexistente o inactivo en `role_slugs`, el backend responderá con `400 Bad Request` indicando exactamente: `"Role 'xyz' not found or inactive"`.

---

### D. Actualizar Usuario y Sincronizar Roles (`PATCH /api/core/users/{id}`)
Para modificar datos, campos de perfil o cambiar los roles asignados:

```http
PATCH /api/core/users/01a1cbf8-b99b-7323-8ec2-11ef8412aa01
Content-Type: application/json
```
```json
{
  "first_name": "Lucía Elena",
  "phone": "+59179988776",
  "city": "Cochabamba",
  "address": "Av. América Este #120",
  "notes": "Reubicada a sucursal Cochabamba para expansión",
  "role_slugs": ["admin"]
}
```
*Si no deseas modificar los roles en una actualización simple, omite el campo `role_slugs`.*

---

### E. Endpoints de Asignación Rápida de Rol Individual
Ideales para botones de acción rápida o toggles en la tabla:

- **Asignar Rol:**
  ```http
  POST /api/core/users/{id}/roles/{role_slug}
  ```
- **Revocar Rol:**
  ```http
  DELETE /api/core/users/{id}/roles/{role_slug}
  ```

---

### F. Historial de Inicios de Sesión (Pestaña 3: Seguridad)
Obtiene los accesos del usuario registrados en la tabla `user_log_login`:

```http
GET /api/core/users/{id}/logins?offset=0&limit=10&is_successful=true
```

#### Respuesta de Ejemplo:
```json
[
  {
    "id": "01a1cc01-b4be-7104-a690-3631be03a5b1",
    "created_at": "2026-11-11T14:30:15",
    "ip_address": "192.168.1.50",
    "host_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "is_successful": true,
    "logged_out_at": null
  },
  {
    "id": "01a1cb90-a112-7001-b119-9900ee11ff22",
    "created_at": "2026-11-11T10:14:02",
    "ip_address": "200.105.210.14",
    "host_info": "Mozilla/5.0 (Linux; Android 14) Chrome/120.0.0.0 Mobile",
    "is_successful": false,
    "logged_out_at": null
  }
]
```

#### Conteo de Inicios de Sesión:
```http
GET /api/core/users/{id}/logins/count
```
```json
{
  "total": 15
}
```

---

### G. Catálogo de Roles para Selectores (`GET /api/catalogs/roles`)
Para poblar el `<p-multiSelect>` en el formulario de creación o edición de usuarios:

```http
GET /api/catalogs/roles
```
*(También disponible vía `POST /api/catalogs/bulk` enviando `{"roles": {}}`)*

```json
[
  {
    "value": "admin",
    "label": "pi pi-user Administrador Sistema",
    "extra": {
      "icon": "pi pi-user",
      "description": "Administrador de Sistema"
    }
  }
]
```

---

## 💻 4. Ejemplo de Servicio Angular (`UserService`)

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  UserDetail,
  UserCreatePayload,
  UserUpdatePayload,
  UserLoginLog,
  CatalogItem
} from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);
  private apiUrl = '/api/core/users';
  private catalogUrl = '/api/catalogs';

  // 1. Obtener lista paginada
  getUsers(params: {
    offset?: number;
    limit?: number;
    search?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    isActive?: boolean;
  }): Observable<UserDetail[]> {
    let httpParams = new HttpParams()
      .set('offset', params.offset ?? 0)
      .set('limit', params.limit ?? 15);

    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.sortBy) httpParams = httpParams.set('sort_by', params.sortBy);
    if (params.sortOrder) httpParams = httpParams.set('sort_order', params.sortOrder);
    if (params.isActive !== undefined) httpParams = httpParams.set('is_active', params.isActive);

    return this.http.get<UserDetail[]>(this.apiUrl, { params: httpParams });
  }

  // 2. Conteo total
  countUsers(search?: string, isActive?: boolean): Observable<{ total: number }> {
    let httpParams = new HttpParams();
    if (search) httpParams = httpParams.set('search', search);
    if (isActive !== undefined) httpParams = httpParams.set('is_active', isActive);
    return this.http.get<{ total: number }>(`${this.apiUrl}/count`, { params: httpParams });
  }

  // 3. Obtener detalle por ID
  getUserById(id: string): Observable<UserDetail> {
    return this.http.get<UserDetail>(`${this.apiUrl}/${id}`);
  }

  // 4. Crear usuario
  createUser(payload: UserCreatePayload): Observable<UserDetail> {
    return this.http.post<UserDetail>(this.apiUrl, payload);
  }

  // 5. Actualizar usuario
  updateUser(id: string, payload: UserUpdatePayload): Observable<UserDetail> {
    return this.http.patch<UserDetail>(`${this.apiUrl}/${id}`, payload);
  }

  // 6. Eliminar usuario
  deleteUser(id: string): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`${this.apiUrl}/${id}`);
  }

  // 7. Historial de Logins (Pestaña 3)
  getLoginHistory(
    userId: string,
    offset = 0,
    limit = 10,
    isSuccessful?: boolean
  ): Observable<UserLoginLog[]> {
    let params = new HttpParams()
      .set('offset', offset)
      .set('limit', limit);
    if (isSuccessful !== undefined) {
      params = params.set('is_successful', isSuccessful);
    }
    return this.http.get<UserLoginLog[]>(`${this.apiUrl}/${userId}/logins`, { params });
  }

  countLoginHistory(userId: string, isSuccessful?: boolean): Observable<{ total: number }> {
    let params = new HttpParams();
    if (isSuccessful !== undefined) {
      params = params.set('is_successful', isSuccessful);
    }
    return this.http.get<{ total: number }>(`${this.apiUrl}/${userId}/logins/count`, { params });
  }

  // 8. Catálogo de Roles para Selectbox
  getRolesCatalog(): Observable<CatalogItem[]> {
    return this.http.get<CatalogItem[]>(`${this.catalogUrl}/roles`);
  }
}
```

---

## 💡 5. Buenas Prácticas de UI con PrimeNG

1. **Chips para Roles en la Tabla (`p-tag`):**
   Renderiza los roles del usuario con `<p-tag>` usando el color temático:
   ```html
   <ng-template pTemplate="body" let-user>
     <tr>
       <td>{{ user.first_name }} {{ user.last_name }} (@{{ user.username }})</td>
       <td>{{ user.email }}</td>
       <td>
         <div class="flex gap-1 flex-wrap">
           @for (role of user.roles; track role.slug) {
             <p-tag [value]="role.name" severity="info" [icon]="role.icon || 'pi pi-tag'"></p-tag>
           }
           @empty {
             <span class="text-gray-400 text-sm">Sin rol</span>
           }
         </div>
       </td>
     </tr>
   </ng-template>
   ```

2. **Badges de Éxito / Fallo en el Historial de Logins:**
   ```html
   @if (log.is_successful) {
     <p-tag value="Exitoso" severity="success" icon="pi pi-check"></p-tag>
   } @else {
     <p-tag value="Fallido" severity="danger" icon="pi pi-times"></p-tag>
   }
   ```

3. **Avatar de Usuario con Fallback de Iniciales (`p-avatar`):**
   Muestra la foto de perfil o, si no fue cargada, las iniciales del nombre con color corporativo:
   ```html
   <p-avatar
     [image]="user.avatar_url || ''"
     [label]="!user.avatar_url ? (user.first_name?.[0] || user.username[0] | uppercase) : undefined"
     shape="circle"
     size="large"
     styleClass="bg-teal-50 text-teal-700 font-bold border border-teal-200"
   ></p-avatar>
   ```

4. **Acción Rápida de WhatsApp (`phone`):**
   Si el usuario tiene teléfono registrado, abre directamente el chat de WhatsApp Web/App:
   ```html
   @if (user.phone) {
     <a
       [href]="'https://wa.me/' + user.phone.replace('+', '').replace(' ', '')"
       target="_blank"
       pButton
       icon="pi pi-whatsapp"
       class="p-button-rounded p-button-success p-button-sm p-button-text"
       pTooltip="Contactar por WhatsApp"
     ></a>
   }
   ```

5. **Validación Reactiva de Formulario Espejada con el Backend:**
   Garantiza que la UI capture los errores antes de enviar la petición HTTP:
   ```typescript
   this.userForm = this.fb.group({
     username: [
       '',
       [
         Validators.required,
         Validators.minLength(3),
         Validators.maxLength(30),
         // Sin espacios, sin símbolos consecutivos, debe iniciar y terminar con alfanumérico
         Validators.pattern(/^[a-zA-Z0-9](?!.*[._-]{2})[a-zA-Z0-9._-]{1,28}[a-zA-Z0-9]$/)
       ]
     ],
     email: ['', [Validators.required, Validators.email]],
     password: ['', [Validators.minLength(6)]],
     first_name: [''],
     last_name: [''],
     phone: [''],
     avatar_url: [''],
     city: [''],
     country: ['BO'],
     address: [''],
     notes: [''],
     timezone: ['America/La_Paz'],
     role_slugs: [[]],
     is_active: [true],
     is_verified: [false],
     is_superuser: [false]
   });
   ```

6. **Estructura de Pestañas con PrimeNG (`p-tabs`):**
   ```html
   <p-tabs value="0">
     <p-tablist>
       <p-tab value="0" icon="pi pi-user">Datos Generales</p-tab>
       <p-tab value="1" icon="pi pi-shield">
         Roles y Permisos
         @if (selectedRoles.length > 0) {
           <p-badge [value]="selectedRoles.length" severity="info"></p-badge>
         }
       </p-tab>
       <p-tab value="2" icon="pi pi-history">Historial de Accesos</p-tab>
     </p-tablist>
     <p-tabpanels>
       <!-- TAB 1: DATOS GENERALES Y PERFIL -->
       <p-tabpanel value="0">
         <!-- Inputs de Nombre, Apellido, Username, Email, Password, Teléfono, Ciudad, Switches -->
       </p-tabpanel>

       <!-- TAB 2: ROLES ASIGNADOS -->
       <p-tabpanel value="1">
         <p-multiSelect
           [options]="rolesCatalog"
           optionLabel="label"
           optionValue="value"
           formControlName="role_slugs"
           placeholder="Seleccionar roles asignados"
           display="chip"
           class="w-full"
         ></p-multiSelect>
       </p-tabpanel>

       <!-- TAB 3: HISTORIAL DE LOGINS -->
       <p-tabpanel value="2">
         <p-table [value]="loginHistory" [paginator]="true" [rows]="10" responsiveLayout="scroll">
           <!-- Columnas: Fecha, IP, Dispositivo / User-Agent, Estado -->
         </p-table>
       </p-tabpanel>
     </p-tabpanels>
   </p-tabs>
   ```

