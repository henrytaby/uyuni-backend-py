# 04. Guía de Integración Frontend — Mi Perfil y Autoservicio (`/api/auth/me`)

Esta guía está dirigida al equipo de Frontend (**Angular 21 + PrimeNG 21**) para la implementación de la pantalla **"Perfil de Usuario"** (`/profile` o `Inicio > Usuario > Perfil`) y el menú desplegable superior del avatar.

---

## 🧭 1. Arquitectura de Seguridad: Autoservicio vs Administración

En el sistema existen dos formas de interactuar con cuentas de usuario, y **nunca** deben mezclarse:

```text
┌───────────────────────────────────────────────┬───────────────────────────────────────────────┐
│  🛡️ GESTIÓN ADMINISTRATIVA (RBAC)            │  👤 AUTOSERVICIO / MI PERFIL (/me)            │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • URL: /api/core/users/{id}                   │ • URL: /api/auth/me                           │
│ • Quién: Administradores con permiso USERS.   │ • Quién: CUALQUIER usuario autenticado.       │
│ • Requiere: ID en URL (ej. UUIDv7).           │ • Requiere: Solo Bearer Token (Cero ID).      │
│ • Alcance: Activar/desactivar, asignar roles, │ • Alcance: Solo sus propios datos personales  │
│   superusuario, notas de supervisión.         │   (nombre, avatar, teléfono, dirección).      │
│ • Seguridad: Prevención de escalado.          │ • Seguridad: Cero IDOR (imposible suplantar). │
└───────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Anti-IDOR Garantizado:** Los endpoints de `/api/auth/me` no reciben ningún `id` ni `username` por parámetro. El backend identifica al usuario inspeccionando la firma criptográfica del token JWT en el encabezado `Authorization: Bearer <token>`.

---

## 📦 2. Contratos e Interfaces TypeScript

Copia y pega estas interfaces en tu proyecto Angular (ej. `src/app/core/models/profile.model.ts`):

```typescript
// --- Respuesta completa de Mi Perfil ---
export interface UserProfileResponse {
  id: string;
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  country?: string | null;      // Default: "BO"
  city?: string | null;
  address?: string | null;
  timezone?: string | null;     // Default: "America/La_Paz"
  is_verified: boolean;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

// --- Payload para editar datos de perfil (PATCH /api/auth/me) ---
export interface UserProfileUpdatePayload {
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  timezone?: string | null;
}

// --- Payload para cambio de contraseña (POST /api/auth/me/change-password) ---
export interface UserChangePasswordPayload {
  current_password: string;
  new_password: string;
}

// --- Respuesta de subida de imagen (POST /api/core/media/upload) ---
export interface MediaUploadResponse {
  url: string;
  public_id: string;
  format: string;
  bytes: number;
  width: number;
  height: number;
}
```

---

## ⚡ 3. Endpoints de la API REST

Todos los endpoints requieren el encabezado `Authorization: Bearer <access_token>`.

### A. Consultar Mi Perfil (`GET /api/auth/me`)
Carga los datos iniciales de la pantalla de perfil del usuario logueado.

```http
GET /api/auth/me
```

#### Respuesta de Ejemplo (200 OK):
```json
{
  "id": "01a1cbf8-b99b-7323-8ec2-11ef8412aa01",
  "username": "musharof.dev",
  "email": "musharof@empresa.com",
  "first_name": "Musharof",
  "last_name": "Chowdhury",
  "phone": "+59170012345",
  "avatar_url": "https://avatar.iran.liara.run/public/33",
  "country": "BO",
  "city": "Santa Cruz",
  "address": "Av. San Martín #450, Equipetrol",
  "timezone": "America/La_Paz",
  "is_verified": true,
  "is_active": true,
  "created_at": "2026-11-10T14:00:00",
  "updated_at": "2026-11-11T16:20:00"
}
```

---

### B. Actualizar Mis Datos Personales (`PATCH /api/auth/me`)
Permite al usuario editar su información personal y de contacto.

```http
PATCH /api/auth/me
Content-Type: application/json
```
```json
{
  "first_name": "Musharof",
  "last_name": "Chowdhury",
  "phone": "+59170012345",
  "avatar_url": "https://avatar.iran.liara.run/public/33",
  "country": "BO",
  "city": "Santa Cruz",
  "address": "Av. San Martín #450, Equipetrol",
  "timezone": "America/La_Paz"
}
```

> [!WARNING]
> **Campos Estrictamente Prohibidos:**
> Si el cliente intenta enviar campos como `is_superuser`, `role_slugs`, `is_active`, `username` o `email`, el backend rechazará la petición inmediatamente con **`422 Unprocessable Entity`**. El usuario no puede auto-asignarse privilegios ni cambiar su correo de forma directa sin flujo de verificación.

---

### C. Cambiar Contraseña (`POST /api/auth/me/change-password`)
Permite al usuario actualizar su credencial de acceso.

```http
POST /api/auth/me/change-password
Content-Type: application/json
```
```json
{
  "current_password": "PasswordActual123*",
  "new_password": "NuevoPasswordSeguro2026*"
}
```

#### Respuestas Posibles:
- **`200 OK`**: Contraseña actualizada correctamente.
  ```json
  {
    "message": "Contraseña actualizada exitosamente"
  }
  ```
- **`400 Bad Request`**: Contraseña actual incorrecta:
  ```json
  {
    "detail": "La contraseña actual es incorrecta"
  }
  ```
- **`400 Bad Request`**: Reutilización de clave:
  ```json
  {
    "detail": "La nueva contraseña no puede ser idéntica a la actual"
  }
  ```
- **`422 Unprocessable Entity`**: Contraseña demasiado corta (mínimo 6 caracteres).

---

### D. Subir Foto / Avatar a la Nube (Cloudinary) (`POST /api/core/media/upload?folder=avatars`)
Sube una imagen física desde el navegador a la nube corporativa de Cloudinary, con optimización y compresión automática a formato WebP.

```http
POST /api/core/media/upload?folder=avatars
Content-Type: multipart/form-data
```
- **Parámetro `folder` (Query Param):** `avatars` (para fotos de perfil), `products` (para catálogo), `categories` o `general`.
- **Form Data:** Clave `file` con los bytes binarios de la imagen (JPG, PNG, WEBP, GIF, máx. 5 MB).

#### Respuesta de Ejemplo (200 OK):
```json
{
  "url": "https://res.cloudinary.com/novalabs-bo/image/upload/v1794440964/uyuni/avatars/file_xyrq22.webp",
  "public_id": "uyuni/avatars/file_xyrq22",
  "format": "webp",
  "bytes": 45120,
  "width": 800,
  "height": 800
}
```

> [!TIP]
> **Flujo de 2 Pasos en Frontend:**
> 1. Al seleccionar la foto en el formulario, el frontend la sube con `POST /api/core/media/upload?folder=avatars`.
> 2. Recibe la `url` en la respuesta y actualiza el usuario mediante `PATCH /api/auth/me` enviando `{"avatar_url": response.url}`.

---

### E. Eliminar Mi Avatar (`DELETE /api/auth/me/avatar`)
Permite al usuario quitar su foto de perfil. El backend se encarga de:
1. Eliminar físicamente el archivo en Cloudinary (cero basura residual).
2. Resetear `avatar_url` a `null` en la base de datos.
3. Retornar el perfil actualizado para que el frontend muestre el avatar por defecto con las iniciales (`p-avatar`).

```http
DELETE /api/auth/me/avatar
```

#### Respuesta de Ejemplo (200 OK):
Retorna el objeto `UserProfileResponse` con `"avatar_url": null`.


---

## 💻 4. Ejemplo de Servicio Angular (`ProfileService`)

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  UserProfileResponse,
  UserProfileUpdatePayload,
  UserChangePasswordPayload,
  MediaUploadResponse,
} from '../models/profile.model';

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private http = inject(HttpClient);
  private authUrl = '/api/auth';
  private mediaUrl = '/api/core/media';

  // 1. Obtener datos del perfil actual
  getMyProfile(): Observable<UserProfileResponse> {
    return this.http.get<UserProfileResponse>(`${this.authUrl}/me`);
  }

  // 2. Actualizar datos de perfil (nombre, teléfono, avatar, ciudad, etc.)
  updateMyProfile(payload: UserProfileUpdatePayload): Observable<UserProfileResponse> {
    return this.http.patch<UserProfileResponse>(`${this.authUrl}/me`, payload);
  }

  // 3. Cambiar contraseña
  changeMyPassword(payload: UserChangePasswordPayload): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.authUrl}/me/change-password`, payload);
  }

  // 4. Subir avatar a Cloudinary
  uploadAvatar(file: File): Observable<MediaUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<MediaUploadResponse>(`${this.mediaUrl}/upload?folder=avatars`, formData);
  }

  // 5. Eliminar foto de perfil (resetea a iniciales y borra de Cloudinary)
  deleteAvatar(): Observable<UserProfileResponse> {
    return this.http.delete<UserProfileResponse>(`${this.authUrl}/me/avatar`);
  }
}
```

---

## 🎨 5. Guía Visual de Componentes PrimeNG para la Pantalla "Perfil"

Siguiendo la plantilla mostrada en las capturas de pantalla de la aplicación:

### A. Tarjeta Cabecera (Avatar y Resumen)
```html
<div class="card p-4 flex items-center justify-between border-round shadow-1">
  <div class="flex items-center gap-4">
    <p-avatar
      [image]="profile.avatar_url || ''"
      [label]="!profile.avatar_url ? (profile.first_name?.[0] || 'U') : undefined"
      size="xlarge"
      shape="circle"
      styleClass="bg-primary-100 text-primary-700 font-bold"
    ></p-avatar>
    <div>
      <h2 class="text-xl font-bold m-0">{{ profile.first_name }} {{ profile.last_name }}</h2>
      <span class="text-500 text-sm">@{{ profile.username }} • {{ profile.city || 'Sin ciudad' }}, {{ profile.country }}</span>
    </div>
  </div>
  <button pButton label="Cambiar Contraseña" icon="pi pi-key" class="p-button-outlined p-button-sm" (click)="openPasswordDialog()"></button>
</div>
```

### B. Tarjeta "Información Personal"
- **Nombre y Apellido**: Inputs editables.
- **Correo Electrónico**: Campo **deshabilitado / de solo lectura** (`[disabled]="true"`), ya que no se puede cambiar libremente.
- **Teléfono / WhatsApp**: Input con prefijo internacional.

### C. Tarjeta "Dirección y Residencia"
- **País**: Selector o texto fijo (default `"BO"` - Bolivia).
- **Ciudad**: Input de texto o selector de sucursales (Santa Cruz, La Paz, Cochabamba, etc.).
- **Dirección**: Input de texto para calle, número o referencias.
- **Zona Horaria**: Desplegable o valor informativo (default `"America/La_Paz"`).

### D. Diálogo Modal de "Cambiar Contraseña" (`p-dialog`)
```html
<p-dialog header="Cambiar mi Contraseña" [(visible)]="displayPasswordModal" [modal]="true" [style]="{ width: '400px' }">
  <form [formGroup]="passwordForm" (ngSubmit)="submitChangePassword()">
    <div class="flex flex-column gap-3 py-2">
      <div class="flex flex-column gap-1">
        <label for="current_password" class="font-medium text-sm">Contraseña Actual *</label>
        <p-password id="current_password" formControlName="current_password" [feedback]="false" [toggleMask]="true" styleClass="w-full" inputStyleClass="w-full"></p-password>
      </div>

      <div class="flex flex-column gap-1">
        <label for="new_password" class="font-medium text-sm">Nueva Contraseña * (min 6)</label>
        <p-password id="new_password" formControlName="new_password" [toggleMask]="true" styleClass="w-full" inputStyleClass="w-full"></p-password>
      </div>
    </div>

    <div class="flex justify-content-end gap-2 mt-4">
      <button pButton type="button" label="Cancelar" class="p-button-text" (click)="displayPasswordModal = false"></button>
      <button pButton type="submit" label="Actualizar Contraseña" icon="pi pi-check" [disabled]="passwordForm.invalid"></button>
    </div>
  </form>
</p-dialog>
```

