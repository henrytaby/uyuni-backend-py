# Manual de Despliegue Serverless — Uyuni Backend & Ecosistema Nova Box

Esta guía detalla el procedimiento paso a paso para desplegar **todo el sistema en la nube moderna (Serverless)**, eliminando por completo la necesidad de mantener, pagar o configurar servidores VPS en Linux.

---

## 🏛️ Topología del Ecosistema Serverless ($0.00 / mes)

```mermaid
flowchart TB
    %% ==========================================
    %% TOPOLOGÍA SERVERLESS UYUNI
    %% ==========================================
    
    subgraph ClientsLayer ["🌐 1. Clientes & Frontends (Cloudflare Pages / Vercel)"]
        SPA["Frontend de Gestión (Angular 21)<br/>admin.tudominio.com"]
        PWA["PWA Clientes (React + Vite)<br/>catalogo.tudominio.com"]
    end

    subgraph MonitoringLayer ["⏱️ 2. Keep-Alive 24/7 (UptimeRobot)"]
        PING["Monitor Ping (Cada 5 min)<br/>GET /health (Evita modo reposo)"]
    end

    subgraph BackendCompute ["⚡ 3. Cómputo Backend (Koyeb / Vercel)"]
        FASTAPI["FastAPI Engine (Python 3.14 MicroVM o Vercel Serverless)<br/>Koyeb o Vercel"]
    end

    subgraph ManagedData ["🛡️ 4. Datos & Almacenamiento Seguro"]
        NEON[("Neon.tech PostgreSQL 16<br/>1 GB SSD NVMe (Inmortal & Auto-Backup)")]
        CLOUDINARY["Cloudinary Media<br/>Fotos de Productos (Auto WebP / Miniaturas)"]
        R2["Cloudflare R2 (10 GB Gratis)<br/>Facturas PDF, Excel, Word y Videos MP4"]
    end

    ClientsLayer -->|Peticiones REST / JWT| FASTAPI
    PING -.->|Mantiene despierto 24/7| FASTAPI
    FASTAPI <-->|Consultas ACID / UUIDv7| NEON
    FASTAPI -->|Sube fotos de catálogo| CLOUDINARY
    FASTAPI -->|Sube facturas privadas & videos| R2

    %% Estilos Corporativos Uyuni
    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865,font-weight:bold;
    classDef pingNode fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#78350f,font-weight:bold;
    classDef backendNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef dbNode fill:#003865,stroke:#00c2cb,stroke-width:2.5px,color:#ffffff,font-weight:bold;
    classDef mediaNode fill:#004889,stroke:#38bdf8,stroke-width:2px,color:#ffffff;

    class SPA,PWA clientNode;
    class PING pingNode;
    class FASTAPI backendNode;
    class NEON dbNode;
    class CLOUDINARY,R2 mediaNode;
```

---

## 📋 Resumen de Cuentas Gratuitas Necesarias

| Servicio | Rol | Plan Gratuito | ¿Pide Tarjeta? |
| :--- | :--- | :--- | :--- |
| **[Neon.tech](https://neon.tech)** | Base de datos PostgreSQL 16 | 1 GB de almacenamiento SSD | **NO** |
| **[Koyeb.com](https://www.koyeb.com)** / **[Vercel.com](https://vercel.com)** | Alojamiento del Backend FastAPI | MicroVM 512 MB (Koyeb) o Serverless Anycast (Vercel) | **NO** |
| **[UptimeRobot.com](https://uptimerobot.com)** | Mantener el backend despierto 24/7 | 50 monitores con pings cada 5 min | **NO** |
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

## 🚀 PASO 3: Desplegar el Backend (Elige entre Koyeb o Vercel)

El proyecto soporta tanto contenedores Docker tradicionales (Koyeb/Render) como ejecución 100% Serverless en el Edge (Vercel).

---

### 🟢 Opción 3.A: Desplegar en Koyeb (Contenedor Docker MicroVM)
Ideal si quieres un contenedor completo siempre activo ejecutando Python 3.14 nativo:

El repositorio ya cuenta con un archivo [`Dockerfile`](file:///opt/uyuni/uyuni-backend-py/Dockerfile) optimizado para Python 3.14.

1. Asegúrate de haber subido los cambios a tu repositorio de GitHub:
   ```bash
   git add .
   git commit -m "feat: add Dockerfile and serverless configuration"
   git push origin main
   ```
2. Entra a **[https://www.koyeb.com](https://www.koyeb.com)** y crea tu cuenta con GitHub.
3. En el panel de Koyeb, haz clic en **"Create App"** o **"Create Service"**.
4. Selecciona **"GitHub"** como fuente de despliegue y elige tu repositorio `uyuni-backend-py`.
5. En la configuración del servicio:
   * **Builder**: Selecciona **Dockerfile** (lo detectará automáticamente).
   * **Instance type**: Selecciona **Free** (Nano / 512 MB RAM).
   * **Regions**: Selecciona **Washington, D.C. (US)** (para que esté al lado de tu base de datos de Neon).
6. En la sección **"Environment variables"**, agrega las siguientes variables:
   * `DATABASE_URL` = La URL de conexión de Neon (ej: `postgresql://uyuni_owner:...@ep-xyz.neon.tech/uyuni-production?sslmode=require`)
   * `SECRET_KEY` = Tu clave secreta aleatoria (puedes generarla con `openssl rand -hex 32`)
   * `ENVIRONMENT` = `production`
   * `PORT` = `8000`
   * `BACKEND_CORS_ORIGINS` = `["*"]` *(luego podrás restringirlo a tu dominio de frontend)*
7. En la sección **"Ports"**, asegúrate de que el puerto interno sea **`8000`** con protocolo **HTTP**.
8. Haz clic en **"Deploy"**.

En aproximadamente 90 segundos, Koyeb compilará la imagen de Docker y te proporcionará tu URL pública segura:
👉 **`https://uyuni-backend-tu-usuario.koyeb.app`**

Puedes probar inmediatamente en tu navegador:
`https://uyuni-backend-tu-usuario.koyeb.app/health`

---

### ▲ Opción 3.B: Desplegar en Vercel (Serverless Python Functions)
Ideal si quieres máxima velocidad de respuesta a través de CDN global y **no tener que usar UptimeRobot** (despierta instantáneamente bajo demanda):

El repositorio ya incluye los archivos de configuración nativos:
* [`vercel.json`](file:///opt/uyuni/uyuni-backend-py/vercel.json): Reglas de rewrite hacia el handler.
* [`api/index.py`](file:///opt/uyuni/uyuni-backend-py/api/index.py): Punto de entrada Serverless (*handler = app*).
* [`requirements.txt`](file:///opt/uyuni/uyuni-backend-py/requirements.txt): Empaquetado automático por `@vercel/python`.

#### Método con Vercel Web Dashboard:
1. Entra a **[https://vercel.com](https://vercel.com)** con tu GitHub.
2. Haz clic en **"Add New..." > "Project"** e importa `uyuni-backend-py`.
3. **Configuración:**
   * **Framework Preset**: `Other`
   * **Root Directory**: `./`
4. **Environment Variables:**
   * `DATABASE_URL` = Cadena de Neon (⚠️ **Obligatorio usar endpoint con `-pooler`** para no agotar conexiones en serverless).
   * `SECRET_KEY` = Tu clave aleatoria (`openssl rand -hex 32`).
   * `PROJECT_NAME` = `"Uyuni ERP"`
   * `ENVIRONMENT` = `production`
   * `BACKEND_CORS_ORIGINS` = `["*"]`
5. Haz clic en **"Deploy"**. En 60 segundos obtendrás:
   👉 **`https://uyuni-backend-tu-usuario.vercel.app`**

#### Método rápido con Vercel CLI:
```bash
npm install -g vercel
vercel login
vercel link
vercel env add DATABASE_URL production
vercel env add SECRET_KEY production
vercel --prod
```

---

## 🚀 PASO 4: Activar el Keep-Alive 24/7 en UptimeRobot (Solo para Koyeb o Render)

> [!NOTE]
> **Si desplegaste en Vercel (Opción 3.B):** Puedes saltarte este paso por completo. Las funciones serverless de Vercel no se suspenden por inactividad.

Para garantizar que el servicio de Koyeb (o Render) nunca entre en modo de reposo y responda siempre en menos de 50 milisegundos:

1. Entra a **[https://uptimerobot.com](https://uptimerobot.com)** y crea una cuenta gratuita.
2. Haz clic en **"+ Add New Monitor"**:
   * **Monitor Type**: `HTTP(s)`
   * **Friendly Name**: `Uyuni Backend Live`
   * **URL (or IP)**: `https://uyuni-backend-tu-usuario.koyeb.app/health`
   * **Monitoring Interval**: `Every 5 minutes`
3. Haz clic en **"Create Monitor"**.

> [!TIP]
> Al recibir una petición HTTP cada 5 minutos al endpoint `/health`, la plataforma detecta actividad continua y **mantiene el contenedor caliente y despierto 24 horas al día, 365 días al año**, sin ningún costo.

---

## 🚀 PASO 5: Desplegar el Frontend (Angular 21) en Cloudflare Pages

Para tu frontend de administración (`uyuni-frontend-ng`):

1. Entra a tu panel de **[Cloudflare](https://dash.cloudflare.com/)**.
2. En el menú lateral izquierdo ve a **Compute (Workers) > Workers & Pages > Create application**.
3. Selecciona la pestaña **Pages** y haz clic en **"Connect to Git"**.
4. Selecciona tu repositorio de Angular `uyuni-frontend-ng`.
5. En la configuración de compilación (*Build Settings*):
   * **Framework preset**: `Angular`
   * **Build command**: `npm run build`
   * **Build output directory**: `dist/uyuni-frontend-ng/browser` (o la ruta donde tu Angular emite la carpeta compilada).
6. En **Environment variables**, agrega la URL de tu backend:
   * `API_URL` = `https://uyuni-backend-tu-usuario.koyeb.app/api`
7. Haz clic en **"Save and Deploy"**.

En 1 minuto tendrás tu frontend publicado en una URL global de alta velocidad:
👉 **`https://uyuni-frontend.pages.dev`** (al cual le puedes vincular tu dominio como `admin.novabox.bo` con 1 solo clic).

---

## 🚀 PASO 6: Multimedia (Cloudinary para Fotos y Cloudflare R2 para Documentos)

### 1. Fotos de Productos (Cloudinary)
1. Crea tu cuenta en **[Cloudinary.com](https://cloudinary.com)**.
2. En tu Dashboard copia tus tres credenciales:
   * `CLOUDINARY_CLOUD_NAME`
   * `CLOUDINARY_API_KEY`
   * `CLOUDINARY_API_SECRET`
3. Agrégalas como variables de entorno en tu servicio de Koyeb.

### 2. Documentos Privados y Videos (Cloudflare R2)
1. En tu panel de Cloudflare, ve a **R2 Object Storage**.
2. Haz clic en **"Create bucket"** y nómbralo `novabox-documents`.
3. En la pestaña **Settings**, genera un **API Token** con permisos de lectura y escritura.
4. Obtendrás tus claves S3:
   * `R2_ACCESS_KEY_ID`
   * `R2_SECRET_ACCESS_KEY`
   * `R2_ENDPOINT_URL` (ej: `https://<account_id>.r2.cloudflarestorage.com`)
5. Agrégalas en las variables de entorno de Koyeb.

---

## ✅ Resumen del Flujo de Trabajo a partir de hoy

| Operación | ¿Cómo se hace ahora? |
| :--- | :--- |
| **Actualizar el backend** | Solo haces `git push origin main` en tu computadora. Koyeb lo detecta y lo actualiza en la nube automáticamente en 60 segundos. |
| **Actualizar el frontend** | Solo haces `git push` en tu repositorio de Angular. Cloudflare Pages lo compila y lo despliega solo. |
| **Hacer backup de tu base de datos** | Neon realiza copias automáticas continuas (*Point-in-Time Restore*). O puedes correr `pg_dump` directo a tu PC cuando quieras. |
| **Descargar todas las fotos y facturas a tu PC** | Conectas **Cyberduck** o **FileZilla** a Cloudflare R2 y descargas todo a tu disco duro con un clic sin costo. |
| **Costo total de operación** | **$0.00 / mes**. |

