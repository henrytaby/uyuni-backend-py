# Manual de Despliegue en Render.com (Docker Container)

Esta guía detalla el procedimiento paso a paso para desplegar **Uyuni Backend** en **[Render.com](https://render.com)** como un contenedor Docker completo de Python 3.14, sin requerir verificación por SMS compleja y con despliegues automáticos en cada `git push`.

---

## 🏛️ Topología en Render.com ($0.00 / mes)

```mermaid
flowchart TD
    %% ==========================================
    %% TOPOLOGÍA RENDER.COM UYUNI
    %% ==========================================
    
    subgraph ClientsLayer ["🌐 1. Frontends & Monitoreo"]
        SPA["Frontend de Gestión (Angular 21)<br/>Cloudflare Pages"]
        PING["UptimeRobot (Ping cada 5 min)<br/>Evita suspensión de 15 min"]
    end

    subgraph RenderCompute ["⚡ 2. Cómputo Backend (Render.com)"]
        DOCKER["Contenedor Docker (Python 3.14)<br/>FastAPI Engine + Uvicorn<br/>https://uyuni-backend-novalabs.onrender.com"]
    end

    subgraph ManagedData ["🛡️ 3. Datos & Archivos"]
        NEON[("Neon.tech PostgreSQL 16<br/>1 GB SSD NVMe")]
        CLOUDINARY["Cloudinary (Fotos de Catálogo)"]
        R2["Cloudflare R2 (Facturas y Documentos)"]
    end

    SPA -->|Peticiones REST / JWT| DOCKER
    PING -.->|Mantiene despierto 24/7| DOCKER
    DOCKER <-->|Consultas ACID| NEON
    DOCKER -->|Sube fotos| CLOUDINARY
    DOCKER -->|Sube facturas| R2

    %% Estilos Corporativos Uyuni
    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865,font-weight:bold;
    classDef pingNode fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#78350f,font-weight:bold;
    classDef backendNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef dbNode fill:#003865,stroke:#00c2cb,stroke-width:2.5px,color:#ffffff,font-weight:bold;
    classDef mediaNode fill:#004889,stroke:#38bdf8,stroke-width:2px,color:#ffffff;

    class SPA clientNode;
    class PING pingNode;
    class DOCKER backendNode;
    class NEON dbNode;
    class CLOUDINARY,R2 mediaNode;
```

---

## 📋 Archivos de Soporte Nativos en el Repositorio

El proyecto ya cuenta con soporte nativo para Render:
* [`Dockerfile`](file:///opt/uyuni/uyuni-backend-py/Dockerfile): Imagen `python:3.14-slim` que instala dependencias compiladas y ejecuta Uvicorn en el puerto `${PORT:-8000}`.
* [`render.yaml`](file:///opt/uyuni/uyuni-backend-py/render.yaml): Blueprint de infraestructura como código para auto-aprovisionar el servicio con un solo clic.

---

## 🚀 Paso a Paso: Desplegar en Render en 3 Minutos

### Paso 1: Iniciar Sesión en Render con GitHub
1. Ingresa a **[https://render.com](https://render.com)**.
2. Haz clic en **"GET STARTED FOR FREE"** o **"Sign In"**.
3. Selecciona **"Continue with GitHub"** (utiliza la cuenta corporativa `novalabs-bo` o la cuenta donde tengas acceso al repositorio).
4. Confirma la autorización en GitHub.

---

### Paso 2: Crear el Web Service
1. En el Dashboard principal de Render, haz clic en el botón azul **"New +"** (arriba a la derecha).
2. Selecciona la opción **"Web Service"**.
3. En la sección *Connect a repository*:
   * Si ya ves el repositorio `henrytaby/uyuni-backend-py`, haz clic en **"Connect"**.
   * Si no aparece, haz clic en *Configure account* de GitHub y dale permiso a Render para acceder al repositorio.

---

### Paso 3: Configurar los Parámetros del Servicio

En el formulario de configuración:

| Campo | Valor Recomendado | Explicación |
| :--- | :--- | :--- |
| **Name** | `uyuni-backend-novalabs` | Nombre único que definirá tu URL pública. |
| **Region** | `Ohio (US East)` | Misma región que tu base de datos de Neon para menor latencia (<40ms). |
| **Branch** | `main` | Rama principal del proyecto. |
| **Runtime** | `Docker` | Render compilará automáticamente el `Dockerfile` de Python 3.14. |
| **Instance Type** | `Free` ($0.00 / mes) | 0.1 CPU, 512 MB RAM. |

---

### Paso 4: Cargar Variables de Entorno (Environment Variables)

Haz clic en **"Add Environment Variable"** y añade una por una:

| Key (Nombre) | Value (Valor) |
| :--- | :--- |
| `DATABASE_URL` | Tu cadena de Neon con `?sslmode=require` (ej: `postgresql://novabox_owner:pass@ep-xyz.us-east-2.aws.neon.tech/novabox-production?sslmode=require`) |
| `SECRET_KEY` | Tu clave aleatoria segura de 64 caracteres hex (`openssl rand -hex 32`) |
| `PROJECT_NAME` | `Uyuni ERP - Nova Box Bolivia` |
| `ENVIRONMENT` | `production` |
| `BACKEND_CORS_ORIGINS` | `["*"]` *(o el dominio de tu frontend)* |

---

### Paso 5: Configurar Health Check (Avanzado)
1. Despliega la pestaña **"Advanced"** al final del formulario.
2. En el campo **Health Check Path**, escribe:
   ```text
   /health
   ```
   *(Esto permite a Render verificar que FastAPI arrancó correctamente antes de dirigirle el tráfico).*
3. Haz clic en **"Deploy Web Service"** (botón azul al final).

---

### Paso 6: Verificación del Despliegue
Render iniciará la compilación del contenedor Docker en tiempo real:
1. Verás los logs de compilación: descarga de Python 3.14, instalación de dependencias con pip y arranque de Uvicorn.
2. En aproximadamente **90 a 120 segundos**, el estado cambiará a **`Live`** (en verde).
3. En la parte superior verás tu URL pública segura:
   👉 **`https://uyuni-backend-novalabs.onrender.com`**

#### Comprueba que responde de inmediato:
* **Health Check**: `https://uyuni-backend-novalabs.onrender.com/health`
* **Documentación Swagger**: `https://uyuni-backend-novalabs.onrender.com/docs`
* **ReDoc**: `https://uyuni-backend-novalabs.onrender.com/redoc`

---

## ⏱️ Keep-Alive 24/7 con UptimeRobot (Evitar Modo Reposo)

En el plan gratuito de Render, el contenedor entra en suspensión automática si no recibe ninguna petición durante 15 minutos (y tarda ~30 segundos en "despertar" en la siguiente visita).

Para mantenerlo **caliente y respondiendo en <50 milisegundos 24/7/365**:

1. Ingresa a **[https://uptimerobot.com](https://uptimerobot.com)** y crea una cuenta gratuita.
2. Haz clic en **"+ Add New Monitor"**:
   * **Monitor Type**: `HTTP(s)`
   * **Friendly Name**: `Uyuni Backend Live (Render)`
   * **URL (or IP)**: `https://uyuni-backend-novalabs.onrender.com/health`
   * **Monitoring Interval**: `Every 5 minutes`
3. Haz clic en **"Create Monitor"**.

> [!TIP]
> Al recibir un ping HTTP cada 5 minutos en el endpoint `/health`, Render detecta actividad continua y **mantiene el contenedor activo 24 horas al día sin costo adicional**.

---

## 🔄 Despliegues Continuos Automáticos (CI/CD)

Cada vez que hagas un cambio en tu código y ejecutes:
```bash
git push origin main
```
Render detectará el commit en GitHub, reconstruirá el contenedor Docker y publicará la nueva versión en producción automáticamente en 60 segundos con cero tiempo de inactividad.

