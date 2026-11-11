# Manual de Despliegue Serverless — Uyuni Backend & Ecosistema Nova Box

Esta guía detalla el procedimiento paso a paso para desplegar **todo el sistema en la nube moderna (Serverless)**, eliminando por completo la necesidad de mantener, pagar o configurar servidores VPS en Linux.

---

## 🏛️ Topología del Ecosistema Serverless ($0.00 / mes)

```mermaid
flowchart TB
    %% ==========================================
    %% TOPOLOGÍA SERVERLESS UYUNI
    %% ==========================================
    
    subgraph ClientsLayer ["🌐 1. Clientes & Frontends (Cloudflare Pages)"]
        SPA["Frontend de Gestión (Angular 21)<br/>admin.tudominio.com"]
        PWA["PWA Clientes (React + Vite)<br/>catalogo.tudominio.com"]
    end

    subgraph BackendCompute ["⚡ 2. Cómputo Backend Serverless (Vercel)"]
        FASTAPI["FastAPI Engine (Python Serverless Functions)<br/>Red Anycast Edge Global (+300 ciudades)<br/>https://uyuni-api.vercel.app"]
    end

    subgraph ManagedData ["🛡️ 3. Datos & Almacenamiento Seguro"]
        NEON[("Neon.tech PostgreSQL 16<br/>1 GB SSD NVMe (Inmortal & Auto-Backup)")]
        CLOUDINARY["Cloudinary Media<br/>Fotos de Productos (Auto WebP / Miniaturas)"]
        R2["Cloudflare R2 (10 GB Gratis)<br/>Facturas PDF, Excel, Word y Videos MP4"]
    end

    ClientsLayer -->|Peticiones REST / JWT| FASTAPI
    FASTAPI <-->|Consultas ACID / UUIDv7 (Pooled)| NEON
    FASTAPI -->|Sube fotos de catálogo| CLOUDINARY
    FASTAPI -->|Sube facturas privadas & videos| R2

    %% Estilos Corporativos Uyuni
    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865,font-weight:bold;
    classDef backendNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef dbNode fill:#003865,stroke:#00c2cb,stroke-width:2.5px,color:#ffffff,font-weight:bold;
    classDef mediaNode fill:#004889,stroke:#38bdf8,stroke-width:2px,color:#ffffff;

    class SPA,PWA clientNode;
    class FASTAPI backendNode;
    class NEON dbNode;
    class CLOUDINARY,R2 mediaNode;
```

---

## 📋 Resumen de Cuentas Gratuitas Necesarias

| Servicio | Rol | Plan Gratuito | ¿Pide Tarjeta? |
| :--- | :--- | :--- | :--- |
| **[Neon.tech](https://neon.tech)** | Base de datos PostgreSQL 16 | 1 GB de almacenamiento SSD | **NO** |
| **[Vercel.com](https://vercel.com)** | Backend FastAPI Serverless | Ejecuciones serverless en Edge global | **NO** |
| **[Cloudinary.com](https://cloudinary.com)** | Fotos de productos optimizadas | 25 créditos mensuales (~25 GB) | **NO** |
| **[Cloudflare.com](https://dash.cloudflare.com)** | R2 (Archivos privados/videos) y Pages (Angular) | 10 GB R2 ($0 egress) + Pages ilimitado | Requiere verificación |

---

## 🚀 PASO 1: Crear la Base de Datos en Neon.tech (2 minutos)

1. Ingresa a **[https://neon.tech](https://neon.tech)** y haz clic en **"Sign Up"** (puedes iniciar sesión directamente con tu cuenta de GitHub).
2. Haz clic en **"Create Project"**:
   * **Project name**: `uyuni-production`
   * **Postgres version**: `16`
   * **Region**: Selecciona **US East (N. Virginia)** o **US East (Ohio)** (son las más cercanas y de menor latencia para Sudamérica/Bolivia).
3. Haz clic en **"Create Project"**.
4. En el panel principal verás la sección **"Connection Details"**.
   * Asegúrate de que esté seleccionado **PostgreSQL** y activa la opción **"Pooled connection"** (o conexión directa).
   * Copia tu cadena de conexión que tendrá esta forma:
     ```text
     postgresql://uyuni_owner:npg_X1Y2Z3A4B5@ep-quiet-star-123456.us-east-2.aws.neon.tech/uyuni-production?sslmode=require
     ```
   * *¡Guarda esta cadena en un bloc de notas seguro!*

---

## 🚀 PASO 2: Inicializar Tablas y Datos (Migraciones y Seeds)

Antes de levantar el backend en la nube, inicializaremos la estructura en la base de datos de Neon desde tu terminal local:

1. Abre tu terminal en tu máquina donde tienes el proyecto `uyuni-backend-py`.
2. Ejecuta las migraciones de Alembic apuntando directamente a Neon (reemplaza por tu URL de Neon):
   ```bash
   DATABASE_URL="postgresql://uyuni_owner:npg_X1Y2Z3A4B5@ep-quiet-star-123456.us-east-2.aws.neon.tech/uyuni-production?sslmode=require" venv/bin/alembic upgrade head
   ```
   *Verás que Alembic crea todas las tablas de roles, usuarios, staff, activos fijos y el dominio comercial en Neon.*

3. Puebla la estructura de navegación y permisos para el frontend:
   ```bash
   DATABASE_URL="postgresql://uyuni_owner:npg_X1Y2Z3A4B5@ep-quiet-star-123456.us-east-2.aws.neon.tech/uyuni-production?sslmode=require" venv/bin/python -m seeds.seed_create_modules
   ```

4. Crea tu usuario administrador con tu contraseña segura personalizada:
   ```bash
   DATABASE_URL="postgresql://uyuni_owner:npg_X1Y2Z3A4B5@ep-quiet-star-123456.us-east-2.aws.neon.tech/uyuni-production?sslmode=require" venv/bin/python -c '
   from sqlmodel import Session, create_engine, select
   from app.models.user import User
   from app.auth.utils import get_password_hash
   import os

   engine = create_engine(os.environ["DATABASE_URL"])
   with Session(engine) as s:
       existing = s.exec(select(User).where(User.username == "admin")).first()
       if not existing:
           admin = User(
               username="admin",
               email="admin@novabox.bo",
               password_hash=get_password_hash("TuPasswordSuperSeguro2026!"),
               is_superuser=True,
               is_active=True
           )
           s.add(admin)
           s.commit()
           print("✅ Superusuario admin creado con éxito en Neon!")
       else:
           print("ℹ️ El usuario admin ya existe.")
   '
   ```
   *¡Listo! Tu base de datos en Neon ya está 100% estructurada, con roles, módulos y tu usuario creados.*

---

## 🚀 PASO 3: Desplegar el Backend en Vercel (100% Serverless)

El backend de FastAPI se ejecuta de forma nativa en la infraestructura Serverless de Vercel. **No requiere servidores, no necesita UptimeRobot (no se suspende por inactividad) y cuenta con CDN global Anycast**.

El repositorio ya incluye los archivos de configuración nativos:
* [`vercel.json`](file:///opt/uyuni/uyuni-backend-py/vercel.json): Reglas de reescritura que redirigen todas las peticiones al handler de Python.
* [`api/index.py`](file:///opt/uyuni/uyuni-backend-py/api/index.py): Punto de entrada Serverless (*handler = app*).
* [`requirements.txt`](file:///opt/uyuni/uyuni-backend-py/requirements.txt): Detectado automáticamente por `@vercel/python`.

---

### Opción 3.A: Despliegue desde la Interfaz Web (Vercel Dashboard)
*Recomendado:*

1. Entra a **[https://vercel.com](https://vercel.com)** con tu cuenta de GitHub.
2. Haz clic en **"Add New..." > "Project"** e importa `uyuni-backend-py`.
3. **Configuración del Proyecto:**
   * **Framework Preset**: `Other` (Vercel detecta automáticamente `vercel.json` y la carpeta `api/`).
   * **Root Directory**: `./` (la raíz del proyecto).
4. **Environment Variables (Variables de Entorno):**
   * `DATABASE_URL` = Cadena de Neon (⚠️ **Obligatorio usar endpoint con `-pooler`** para no agotar conexiones en serverless).
   * `SECRET_KEY` = Tu clave secreta aleatoria (`openssl rand -hex 32`).
   * `PROJECT_NAME` = `"Uyuni ERP"`
   * `ENVIRONMENT` = `production`
   * `BACKEND_CORS_ORIGINS` = `["*"]` *(o el dominio de tu frontend)*
5. Haz clic en **"Deploy"**. En 60 segundos obtendrás tu URL global:
   👉 **`https://uyuni-backend-tu-usuario.vercel.app`**

Puedes probar inmediatamente en tu navegador:
`https://uyuni-backend-tu-usuario.vercel.app/health`

---

### Opción 3.B: Despliegue Rápido desde la Terminal (Vercel CLI)
```bash
# 1. Instalar CLI
npm install -g vercel

# 2. Iniciar sesión y vincular
vercel login
vercel link

# 3. Configurar variables de entorno
vercel env add DATABASE_URL production
vercel env add SECRET_KEY production
vercel env add PROJECT_NAME production
vercel env add ENVIRONMENT production
vercel env add BACKEND_CORS_ORIGINS production

# 4. Desplegar a producción
vercel --prod
```

---

## 🚀 PASO 4: Desplegar el Frontend (Angular 21) en Cloudflare Pages

Para tu frontend de administración (`uyuni-frontend-ng`):

1. Entra a tu panel de **[Cloudflare](https://dash.cloudflare.com/)**.
2. En el menú lateral izquierdo ve a **Compute (Workers) > Workers & Pages > Create application**.
3. Selecciona la pestaña **Pages** y haz clic en **"Connect to Git"**.
4. Selecciona tu repositorio de Angular `uyuni-frontend-ng`.
5. En la configuración de compilación (*Build Settings*):
   * **Framework preset**: `Angular`
   * **Build command**: `npm run build`
   * **Build output directory**: `dist/uyuni-frontend-ng/browser` (o la ruta donde tu Angular emite la carpeta compilada).
6. En **Environment variables**, agrega la URL de tu backend en Vercel:
   * `API_URL` = `https://uyuni-backend-tu-usuario.vercel.app/api`
7. Haz clic en **"Save and Deploy"**.

En 1 minuto tendrás tu frontend publicado en una URL global de alta velocidad:
👉 **`https://uyuni-frontend.pages.dev`** (al cual le puedes vincular tu dominio como `admin.novabox.bo` con 1 solo clic).

---

## 🚀 PASO 5: Multimedia (Cloudinary para Fotos y Cloudflare R2 para Documentos)

### 1. Fotos de Productos (Cloudinary)
1. Crea tu cuenta en **[Cloudinary.com](https://cloudinary.com)**.
2. En tu Dashboard copia tus tres credenciales:
   * `CLOUDINARY_CLOUD_NAME`
   * `CLOUDINARY_API_KEY`
   * `CLOUDINARY_API_SECRET`
3. Agrégalas como variables de entorno en Vercel (Project Settings > Environment Variables).

### 2. Documentos Privados y Videos (Cloudflare R2)
1. En tu panel de Cloudflare, ve a **R2 Object Storage**.
2. Haz clic en **"Create bucket"** y nómbralo `novabox-documents`.
3. En la pestaña **Settings**, genera un **API Token** con permisos de lectura y escritura.
4. Obtendrás tus claves S3:
   * `R2_ACCESS_KEY_ID`
   * `R2_SECRET_ACCESS_KEY`
   * `R2_ENDPOINT_URL` (ej: `https://<account_id>.r2.cloudflarestorage.com`)
5. Agrégalas en las variables de entorno de Vercel.

---

## ✅ Resumen del Flujo de Trabajo a partir de hoy

| Operación | ¿Cómo se hace ahora? |
| :--- | :--- |
| **Actualizar el backend** | Solo haces `git push origin main` en tu computadora. Vercel lo detecta y lo actualiza en el Edge automáticamente en 45 segundos. |
| **Actualizar el frontend** | Solo haces `git push` en tu repositorio de Angular. Cloudflare Pages lo compila y lo despliega solo. |
| **Hacer backup de tu base de datos** | Neon realiza copias automáticas continuas (*Point-in-Time Restore*). O puedes correr `pg_dump` directo a tu PC cuando quieras. |
| **Descargar todas las fotos y facturas a tu PC** | Conectas **Cyberduck** o **FileZilla** a Cloudflare R2 y descargas todo a tu disco duro con un clic sin costo. |
| **Costo total de operación** | **$0.00 / mes**. |
| **Actualizar el frontend** | Solo haces `git push` en tu repositorio de Angular. Cloudflare Pages lo compila y lo despliega solo. |
| **Hacer backup de tu base de datos** | Neon realiza copias automáticas continuas (*Point-in-Time Restore*). O puedes correr `pg_dump` directo a tu PC cuando quieras. |
| **Descargar todas las fotos y facturas a tu PC** | Conectas **Cyberduck** o **FileZilla** a Cloudflare R2 y descargas todo a tu disco duro con un clic sin costo. |
| **Costo total de operación** | **$0.00 / mes**. |

