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
        KOYEB1["Koyeb Backend (Instancia 1)"]
        CLD1["Cloudinary (Fotos Nova Box)"]
        R2_1["Cloudflare R2 (Facturas Nova Labs)"]
        PAGES1["Cloudflare Pages (Frontend Admin)"]
    end

    subgraph Client2 ["🏭 Empresa 2: Futuro Cliente (cliente2@empresa.com)"]
        GH2["GitHub: cliente2-app (Solo Lectura)"]
        NEON2[("Neon Postgres (1 GB Dedicado)")]
        KOYEB2["Koyeb Backend (Instancia 2)"]
        CLD2["Cloudinary (Fotos Cliente 2)"]
        R2_2["Cloudflare R2 (Facturas Cliente 2)"]
        PAGES2["Cloudflare Pages (Frontend Admin)"]
    end

    REPO -->|Acceso Colaborador Read| GH1
    REPO -->|Acceso Colaborador Read| GH2

    GH1 --> KOYEB1 <--> NEON1
    KOYEB1 --> CLD1
    KOYEB1 --> R2_1
    PAGES1 --> KOYEB1

    GH2 --> KOYEB2 <--> NEON2
    KOYEB2 --> CLD2
    KOYEB2 --> R2_2
    PAGES2 --> KOYEB2

    %% Estilos Corporativos Uyuni
    classDef devNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef c1Node fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865;
    classDef c2Node fill:#fdf4ff,stroke:#c084fc,stroke-width:1.5px,color:#581c87;

    class REPO devNode;
    class GH1,NEON1,KOYEB1,CLD1,R2_1,PAGES1 c1Node;
    class GH2,NEON2,KOYEB2,CLD2,R2_2,PAGES2 c2Node;
```

### 🌟 Beneficios Estratégicos:
1. **Seguridad y Confidencialidad Absoluta**: Los datos, clientes, ventas y facturas de una empresa jamás se mezclan con los de otra.
2. **Multiplicación de la Capa Gratuita ($0.00 / mes)**: Cada empresa abre sus propias cuentas gratuitas (1 GB en Neon + 10 GB en R2 + 25 créditos en Cloudinary + Koyeb). Tú como desarrollador no pagas un servidor gigante para alojar a todos juntos.
3. **Propiedad Intelectual Protegida**: El código fuente reside en tu repositorio privado. La empresa cliente solo recibe permisos de lectura para que su infraestructura compile y despliegue la aplicación.
4. **Soberanía del Cliente**: Si la empresa crece o un día quiere transferir sus sistemas a su propio equipo de TI, ellos ya son dueños de sus cuentas, datos y activos.

---

## 📋 Checklist de Cuentas por Empresa (Ejemplo: Nova Labs)

Para cada empresa se utiliza un correo corporativo dedicado (ej: `novabo.app@gmail.com`):

| # | Servicio | Cuenta / Nombre sugerido | Propósito | Costo |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **GitHub** | `novalabs-bo` (o `empresa-app`) | Acceso de lectura al código para despliegues | $0.00 |
| **2** | **Neon.tech** | `uyuni-novalabs-prod` | Base de datos PostgreSQL 16 dedicada (1 GB SSD) | $0.00 |
| **3** | **Koyeb** | `uyuni-backend-novalabs` | Servidor FastAPI serverless en contenedor | $0.00 |
| **4** | **UptimeRobot** | Monitor `NovaBox API Live` | Ping cada 5 min a `/health` para mantenerlo 24/7 | $0.00 |
| **5** | **Cloudinary** | Cloud Name: `novabox-bo` | Almacenamiento y optimización de fotos de catálogo | $0.00 |
| **6** | **Cloudflare** | Cuenta `novabo.app@gmail.com` | R2 (Facturas/Videos) y Pages (Frontend Angular) | $0.00 |

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

### Paso 5: Desplegar el Backend en Koyeb
1. Ingresa a **[Koyeb.com](https://www.koyeb.com)** con la cuenta de GitHub de la empresa (`novalabs-bo`).
2. Haz clic en **"Create Service"** > **"GitHub"**.
3. Selecciona el repositorio compartido `henrytaby/uyuni-backend-py`.
4. **Configuración del Servicio:**
   * **Builder**: `Dockerfile` (lo toma automáticamente del repo).
   * **Instance type**: `Free` (512 MB RAM).
   * **Region**: `Washington, D.C. (US)`.
5. **Variables de Entorno (Environment Variables):**
   * `DATABASE_URL` = La cadena de conexión de Neon del cliente.
   * `SECRET_KEY` = Clave aleatoria (ej: `openssl rand -hex 32`).
   * `PROJECT_NAME` = `"Uyuni ERP - Nova Box Bolivia"` (personalizado con el nombre de la empresa).
   * `ENVIRONMENT` = `production`
   * `PORT` = `8000`
   * `BACKEND_CORS_ORIGINS` = `["*"]` *(luego puedes poner el dominio del cliente)*.
6. Haz clic en **Deploy**.
7. En 90 segundos tendrás la URL viva de la empresa:
   👉 `https://uyuni-backend-novalabs.koyeb.app`

---

### Paso 6: Activar el Monitor Keep-Alive 24/7 en UptimeRobot
1. Entra a **[UptimeRobot.com](https://uptimerobot.com)** con el correo de la empresa.
2. Agrega un monitor tipo HTTP apuntando a `https://uyuni-backend-novalabs.koyeb.app/health` cada 5 minutos.
3. *Resultado:* La instancia nunca entra en suspensión y responde de inmediato a clientes y empleados.

---

### Paso 7: Desplegar el Frontend (Angular 21) en Cloudflare Pages
1. Entra a Cloudflare con el correo de la empresa.
2. Conecta el repositorio del frontend (`uyuni-frontend-ng`) en **Workers & Pages > Pages**.
3. En variables de entorno configura:
   * `API_URL` = `https://uyuni-backend-novalabs.koyeb.app/api`
4. Despliega la aplicación. El frontend quedará publicado en `https://uyuni-admin.pages.dev` o vinculado a su propio dominio (`admin.novabox.bo`).

---

## 🔄 ¿Cómo se aplican actualizaciones cuando mejoras el código?

Al tener el repositorio maestro centralizado en tu cuenta personal:

1. Tú programas mejoras, corriges errores o agregas funciones en tu máquina.
2. Haces `git push origin main` a tu repositorio principal.
3. **Magia de la nube**: Las plataformas de todas las empresas conectadas (Koyeb para Nova Labs, Koyeb para el Cliente 2, etc.) detectan el nuevo commit y **re-despliegan automáticamente en 60 segundos**, sin que tengas que entrar a cada servidor manualmente.
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
URL Backend (Koyeb):     [https://api-cliente.koyeb.app]
URL Frontend (Pages):    [https://admin.cliente.bo]
Cloudinary Cloud Name:   [cliente-media]
Cloudflare R2 Bucket:    [cliente-documentos]
Admin Username:          admin
Admin Password:          [PasswordSeguroGenerado]
=====================================================
```

