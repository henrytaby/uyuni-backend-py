# Manual de Replicación y Despliegue para Nuevas Empresas (Modelo Single-Tenant Marca Blanca)

Este manual documenta el procedimiento estándar paso a paso para desplegar una nueva instancia independiente y aislada de **Uyuni Backend / Ecosistema Comercial** para una empresa o unidad de negocio (como **Nova Labs / Nova Box** o futuros clientes comerciales).

---

## 🏛️ Filosofía de Arquitectura: Aislamiento Total por Empresa

A diferencia de un sistema multi-inquilino tradicional donde todos los clientes comparten la misma base de datos, este modelo implementa **Instancias Dedicadas Replicables (Single-Tenant)**:

```mermaid
flowchart TD
    %% ==========================================
    %% MODELO SINGLE-TENANT REPLICABLE
    %% ==========================================
    
    subgraph DevMaster ["👨‍💻 Desarrollador / Repositorio Maestro"]
        REPO["GitHub Privado del Desarrollador<br/>(henrytaby/uyuni-backend-py)<br/>Propiedad Intelectual Protegida"]
    end

    subgraph Client1 ["🏢 Empresa 1: Nova Labs (novabo.app@gmail.com)"]
        GH1["GitHub: novalabs-bo (Solo Lectura)"]
        NEON1[("Neon Postgres (1 GB Dedicado)")]
        SERVER1["Vercel Serverless (Backend API)"]
        CLD1["Cloudinary (Fotos Nova Box)"]
        R2_1["Cloudflare R2 (Facturas Nova Labs)"]
        PAGES1["Cloudflare Pages (Frontend Admin)"]
    end

    subgraph Client2 ["🏭 Empresa 2: Futuro Cliente (cliente2@empresa.com)"]
        GH2["GitHub: cliente2-app (Solo Lectura)"]
        NEON2[("Neon Postgres (1 GB Dedicado)")]
        SERVER2["Vercel Serverless (Backend API)"]
        CLD2["Cloudinary (Fotos Cliente 2)"]
        R2_2["Cloudflare R2 (Facturas Cliente 2)"]
        PAGES2["Cloudflare Pages (Frontend Admin)"]
    end

    REPO -->|Acceso Colaborador Read| GH1
    REPO -->|Acceso Colaborador Read| GH2

    GH1 --> SERVER1 <--> NEON1
    SERVER1 --> CLD1
    SERVER1 --> R2_1
    PAGES1 --> SERVER1

    GH2 --> SERVER2 <--> NEON2
    SERVER2 --> CLD2
    SERVER2 --> R2_2
    PAGES2 --> SERVER2

    %% Estilos Corporativos Uyuni
    classDef devNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef c1Node fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865;
    classDef c2Node fill:#fdf4ff,stroke:#c084fc,stroke-width:1.5px,color:#581c87;

    class REPO devNode;
    class GH1,NEON1,SERVER1,CLD1,R2_1,PAGES1 c1Node;
    class GH2,NEON2,SERVER2,CLD2,R2_2,PAGES2 c2Node;
```

### 🌟 Beneficios Estratégicos:
1. **Seguridad y Confidencialidad Absoluta**: Los datos, clientes, ventas y facturas de una empresa jamás se mezclan con los de otra.
2. **Multiplicación de la Capa Gratuita ($0.00 / mes)**: Cada empresa abre sus propias cuentas gratuitas (1 GB en Neon + 10 GB en R2 + 25 créditos en Cloudinary + Vercel Serverless). Tú como desarrollador no pagas un servidor gigante para alojar a todos juntos.
3. **Propiedad Intelectual Protegida**: El código fuente reside en tu repositorio privado. La empresa cliente solo recibe permisos de lectura para que su infraestructura compile y despliegue la aplicación.
4. **Soberanía del Cliente**: Si la empresa crece o un día quiere transferir sus sistemas a su propio equipo de TI, ellos ya son dueños de sus cuentas, datos y activos.

---

## 📋 Checklist de Cuentas por Empresa (Ejemplo: Nova Labs)

Para cada empresa se utiliza un correo corporativo dedicado (ej: `novabo.app@gmail.com`):

| # | Servicio | Cuenta / Nombre sugerido | Propósito | Costo |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **GitHub** | `novalabs-bo` (o `empresa-app`) | Acceso de lectura al código para despliegues | $0.00 |
| **2** | **Neon.tech** | `uyuni-novalabs-prod` | Base de datos PostgreSQL 16 dedicada (1 GB SSD) | $0.00 |
| **3** | **Vercel** | `uyuni-backend-novalabs` | Servidor FastAPI Serverless (Edge Anycast Global) | $0.00 |
| **4** | **Cloudinary** | Cloud Name: `novabox-bo` | Almacenamiento y optimización de fotos de catálogo | $0.00 |
| **5** | **Cloudflare** | Cuenta `novabo.app@gmail.com` | R2 (Facturas/Videos) y Pages (Frontend Angular) | $0.00 |

---

## 🚀 Paso a Paso: Desplegar un Nuevo Cliente en 15 Minutos

### Paso 1: Crear la Identidad Corporativa en GitHub
1. Abre una ventana de incógnito en tu navegador.
2. Ingresa a **[GitHub.com](https://github.com/signup)** y crea una cuenta con el correo del cliente (ej. `novabo.app@gmail.com`).
3. Elige un nombre de usuario institucional representativo (ej: `novalabs-bo`).
4. Confirma el correo de verificación.

---

### Paso 2: Otorgar Acceso de Lectura desde tu Cuenta Principal
1. Entra a tu cuenta personal de GitHub (dueña del código).
2. Ve al repositorio maestro: `https://github.com/henrytaby/uyuni-backend-py`.
3. Ve a **Settings > Collaborators > Add people**.
4. Busca al usuario de la empresa (ej: `novalabs-bo`) y envíale la invitación con rol **Read** (Lectura).
5. En la ventana de la empresa, acepta la invitación.
   *(A partir de este momento, las plataformas cloud de la empresa podrán desplegar el código automáticamente sin que el cliente pueda modificar o borrar tu repositorio principal).*

---

### Paso 3: Crear la Base de Datos en Neon.tech
1. Con la sesión de la empresa abierta, ingresa a **[Neon.tech](https://neon.tech)**.
2. Haz clic en **"Sign Up"** y selecciona **"Continue with GitHub"** (iniciará sesión como `novalabs-bo`).
3. Haz clic en **"Create Project"**:
   * **Name**: `novabox-production` (o el nombre de la empresa).
   * **Region**: `US East (N. Virginia u Ohio)`.
4. Copia la cadena de conexión generada con pooling activado:
   ```text
   postgresql://usuario:password@ep-xyz.us-east-2.aws.neon.tech/novabox-production?sslmode=require
   ```

---

### Paso 4: Inicializar Estructura y Usuario Admin desde tu Terminal
Desde tu máquina de desarrollo, apunta temporalmente a la base de datos del nuevo cliente para construir las tablas y crear su usuario administrador:

```bash
# 1. Crear todas las tablas en la base de datos del cliente
DATABASE_URL="cadena_de_neon_del_cliente" venv/bin/alembic upgrade head

# 2. Poblar módulos, roles y menús de la interfaz
DATABASE_URL="cadena_de_neon_del_cliente" venv/bin/python -m seeds.seed_create_modules

# 3. Dar de alta al administrador de la empresa con contraseña segura
DATABASE_URL="cadena_de_neon_del_cliente" venv/bin/python -c '
from sqlmodel import Session, create_engine, select
from app.models.user import User
from app.auth.utils import get_password_hash
import os

engine = create_engine(os.environ["DATABASE_URL"])
with Session(engine) as s:
    if not s.exec(select(User).where(User.username == "admin")).first():
        admin = User(
            username="admin",
            email="admin@novabox.bo",
            password_hash=get_password_hash("PasswordSuperSeguro2026!"),
            is_superuser=True,
            is_active=True
        )
        s.add(admin)
        s.commit()
        print("✅ Superusuario creado exitosamente para la empresa!")
'
```

---

### Paso 5: Desplegar el Backend Serverless en Vercel

El backend corre en arquitectura **100% Serverless** a través de la red global de Vercel (CDN Anycast), garantizando **cero mantenimiento de servidores**, alta disponibilidad y sin necesidad de servicios externos para mantenerlo despierto.

#### 🧩 Arquitectura Serverless de Uyuni en Vercel:
El repositorio ya está 100% preparado y optimizado para Vercel con los siguientes archivos nativos:
* [`vercel.json`](file:///opt/uyuni/uyuni-backend-py/vercel.json): Configura el enrutamiento inteligente redirigiendo todas las peticiones entrantes (`/(.*)`) al handler ASGI de Python.
* [`api/index.py`](file:///opt/uyuni/uyuni-backend-py/api/index.py): Punto de entrada Serverless (*handler* de FastAPI) que inyecta la ruta raíz del backend a `sys.path` y expone `handler = app`.
* [`requirements.txt`](file:///opt/uyuni/uyuni-backend-py/requirements.txt): Detectado automáticamente por el runtime `@vercel/python` para empaquetar e instalar las dependencias en la nube.

Puedes desplegar en Vercel utilizando cualquiera de los dos métodos siguientes:

---

#### 🖥️ Método 1: Despliegue Visual desde la Interfaz Web (Vercel Dashboard)
*Recomendado para una configuración rápida o para entregar al cliente:*

1. Ingresa a **[Vercel.com](https://vercel.com)** e inicia sesión con el GitHub de la empresa (`novalabs-bo` o la cuenta corporativa creada).
2. En el Dashboard principal, haz clic en **"Add New..." > "Project"**.
3. En la lista de repositorios importables, selecciona el repositorio compartido `henrytaby/uyuni-backend-py`.
4. **Configuración del Proyecto:**
   * **Framework Preset**: Selecciona **Other** (Vercel detecta automáticamente el archivo `vercel.json` y la carpeta `api/`).
   * **Root Directory**: `./` (la raíz del proyecto).
   * **Build and Output Settings**: Déjalos por defecto (no necesitas definir build command, Vercel gestiona Python automáticamente).
5. **Variables de Entorno (Environment Variables):**
   Despliega el acordeón de *Environment Variables* y agrega:

   | Variable | Valor | Nota Crítica |
   | :--- | :--- | :--- |
   | `DATABASE_URL` | `postgresql://usuario:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/novabox-production?sslmode=require` | ⚠️ **Obligatorio usar `-pooler`**: En arquitecturas Serverless, múltiples funciones concurrentes se levantan efímeramente. El endpoint Pooled de Neon (PgBouncer) evita saturar el límite de conexiones de PostgreSQL. |
   | `SECRET_KEY` | `openssl rand -hex 32` | Tu clave criptográfica para los JWT. |
   | `PROJECT_NAME` | `"Uyuni ERP - Nova Box Bolivia"` | Nombre comercial de la empresa. |
   | `ENVIRONMENT` | `production` | Modo producción. |
   | `BACKEND_CORS_ORIGINS` | `["*"]` | O especifica `["https://admin.novabox.bo", "https://catalogo.novabox.bo"]`. |
   | `CLOUDINARY_*` | *(Opcionales si usa fotos)* | `CLOUDINARY_CLOUD_NAME`, `API_KEY`, etc. |
   | `R2_*` | *(Opcionales si usa docs/videos)* | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, etc. |

6. Haz clic en **"Deploy"**.
7. En 45 a 60 segundos, Vercel compilará las dependencias y generará tu URL pública con SSL automático y CDN mundial:
   👉 `https://uyuni-backend-novalabs.vercel.app`

---

#### 💻 Método 2: Despliegue desde la Terminal con Vercel CLI
*Ideal para desarrolladores, integración continua (CI) o despliegues automatizados en segundos:*

1. **Instalar Vercel CLI globalmente:**
   ```bash
   npm install -g vercel
   # O si prefieres no instalar globalmente: npx vercel
   ```

2. **Iniciar sesión en la cuenta del cliente:**
   ```bash
   vercel login
   ```
   *(Selecciona continuar con GitHub o ingresa el correo corporativo novabo.app@gmail.com).*

3. **Vincular el proyecto local con Vercel:**
   Desde la raíz de `/opt/uyuni/uyuni-backend-py`:
   ```bash
   vercel link
   ```
   * Responde `Y` para configurar el proyecto.
   * Selecciona el scope/cuenta del cliente (ej: `novalabs-bo`).
   * Link to existing project? `N`.
   * Project name: `uyuni-backend-novalabs`.
   * Directory: `./`.

4. **Configurar las variables de entorno en producción vía CLI:**
   ```bash
   # Base de datos con Pooling activado
   echo "postgresql://usuario:password@ep-xyz-pooler.us-east-2.aws.neon.tech/novabox-prod?sslmode=require" | vercel env add DATABASE_URL production

   # Clave secreta JWT
   echo "$(openssl rand -hex 32)" | vercel env add SECRET_KEY production

   # Metadatos del sistema
   echo "Uyuni ERP - Nova Box Bolivia" | vercel env add PROJECT_NAME production
   echo "production" | vercel env add ENVIRONMENT production
   echo '["*"]' | vercel env add BACKEND_CORS_ORIGINS production
   ```

5. **Desplegar directamente a producción:**
   ```bash
   vercel --prod
   ```
   *Vercel compilará y publicará la función Serverless, entregando en consola la URL productiva.*

---

#### 🧪 Cómo Probar Localmente el Entorno Vercel (`vercel dev`):
Si deseas probar cómo se comporta FastAPI bajo el emulador de funciones serverless de Vercel antes de desplegar:
```bash
vercel dev
```
La API estará disponible en `http://localhost:3000` con recarga en caliente y emulando las reglas de `vercel.json`.

---

### Paso 6: Desplegar el Frontend (Angular 21) en Cloudflare Pages
1. Entra a Cloudflare con el correo de la empresa.
2. Conecta el repositorio del frontend (`uyuni-frontend-ng`) en **Workers & Pages > Pages**.
3. En variables de entorno configura:
   * `API_URL` = `https://uyuni-backend-novalabs.vercel.app/api`
4. Despliega la aplicación. El frontend quedará publicado en `https://uyuni-admin.pages.dev` o vinculado a su propio dominio (`admin.novabox.bo`).

---

## 🔄 ¿Cómo se aplican actualizaciones cuando mejoras el código?

Al tener el repositorio maestro centralizado en tu cuenta personal:

1. Tú programas mejoras, corriges errores o agregas funciones en tu máquina.
2. Haces `git push origin main` a tu repositorio principal.
3. **Magia de la nube**: Las plataformas de todas las empresas conectadas (Vercel para Nova Labs, etc.) detectan el nuevo commit y **re-despliegan automáticamente en 60 segundos**, sin que tengas que entrar a cada servidor manualmente.
4. Si hay migraciones de base de datos nuevas (`alembic upgrade head`), ejecutas el comando apuntando a la `DATABASE_URL` de cada cliente y listo.

---

## 📝 Ficha de Registro para Nuevos Clientes (Plantilla para copiar y guardar)

Guarda una ficha como esta en un gestor de contraseñas seguro (como Bitwarden o 1Password) para cada empresa:

```text
=====================================================
FICHA DE CLIENTE: [NOMBRE DE LA EMPRESA]
=====================================================
Correo Corporativo:      [cliente@gmail.com]
Usuario GitHub:          [cliente-app]
Proyecto Neon:           [uyuni-cliente-prod]
Neon DATABASE_URL:       [postgresql://...]
URL Backend (Vercel):    [https://api-cliente.vercel.app]
URL Frontend (Pages):    [https://admin.cliente.bo]
Cloudinary Cloud Name:   [cliente-media]
Cloudflare R2 Bucket:    [cliente-documentos]
Admin Username:          admin
Admin Password:          [PasswordSeguroGenerado]
=====================================================
```

