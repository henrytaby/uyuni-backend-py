<p align="center">
  <img src="app/static/logo-01.png" alt="Uyuni Logo" width="360" />
</p>

<h1 align="center">Uyuni Backend System</h1>

<p align="center">
  <strong>Plataforma Transaccional Empresarial de Alto Rendimiento</strong><br>
  <em>Arquitectura Modular DDD-Lite &bull; Seguridad Basada en Roles (RBAC) &bull; Auditoría CDC Transversal</em>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-v0.139+-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.14.6-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://sqlmodel.tiangolo.com/"><img src="https://img.shields.io/badge/SQLModel-SQLAlchemy-0284C7?logo=pydantic&logoColor=white" alt="SQLModel" /></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-v16+-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" /></a>
  <img src="https://img.shields.io/badge/Architecture-DDD--Lite%20%7C%20Clean-003865" alt="Clean Architecture" />
  <img src="https://img.shields.io/badge/Quality-Ruff%20%7C%20Mypy%20%7C%20Pytest-10B981" alt="Quality" />
  <img src="https://img.shields.io/badge/License-MIT-7BB661" alt="License" />
</p>

---

Bienvenido a **Uyuni Backend**, una plataforma transaccional de nivel empresarial construida con **FastAPI**, **Python 3.14**, **SQLModel** y **PostgreSQL**. Diseñada bajo los principios de **Clean Architecture** y **DDD-Lite (Domain-Driven Design)**, incorpora autenticación JWT con rotación de tokens, control de acceso granular basado en roles (**RBAC** con personificación dinámica), auditoría transversal de cambios de datos (**CDC**), catálogos dinámicos masivos y dominios transaccionales para **Comercio Electrónico / Nova Box Bolivia**, **Gestión de Usuarios y Accesos** y **Gestión Operativa de Tareas**.

---

## 📋 Tabla de Contenidos

1. [Capacidades del Sistema](#-capacidades-del-sistema)
2. [Arquitectura y Principios de Diseño](#-arquitectura-y-principios-de-diseño)
3. [Módulos de Negocio (Dominios)](#-módulos-de-negocio-dominios)
4. [Stack Tecnológico](#-stack-tecnológico)
5. [Instalación y Puesta en Marcha](#-instalación-y-puesta-en-marcha)
6. [Testing y Calidad de Código](#-testing-y-calidad-de-código)
7. [Despliegue en Producción (VPS Ubuntu)](#-despliegue-en-producción-vps-ubuntu)
8. [Documentación para Desarrolladores](#-documentación-para-desarrolladores)
9. [Scripts y Utilidades](#-scripts-y-utilidades)
10. [Licencia](#-licencia)

---

## 🚀 Capacidades del Sistema

* **Seguridad y Control de Acceso (RBAC)**: Autenticación JWT con rotación continua de tokens, revocación/logout, protección contra fuerza bruta (bloqueo temporal de cuentas) y permisos granulares por módulo con soporte para agregación de roles o personificación (`X-Active-Role`).
* **Auditoría Transversal (CDC)**: Captura automática de contexto HTTP mediante Middleware y registro histórico de cambios (Creación, Modificación, Eliminación) a través de Hooks de SQLAlchemy.
* **Patrón Repositorio Genérico**: Abstracción `BaseRepository[T]` con paginación, ordenamiento dinámico, búsqueda global polimórfica y filtros inyectables seguros (`extra_filters`).
* **Catálogos Dinámicos Masivos**: Protocolo `CatalogProvider` de auto-registro que expone endpoints individuales (`GET /api/catalogs/{name}`) y un optimizador en lote (**`POST /api/catalogs/bulk`**) para alimentar selectboxes del frontend en una única petición HTTP.
* **Motor Transaccional de Comercio**: Gestión de SKUs, lotes de liquidación, punto de equilibrio, protección de precios mínimos y ventas atómicas multicanal.
* **Sincronización ETL Idempotente**: Scripts de sincronización (Upsert + Soft-Delete) para mapear entidades externas con llaves foráneas locales UUIDv7.

---

## 🏛️ Arquitectura y Principios de Diseño

El sistema implementa una **Arquitectura Modular (DDD-Lite)** apoyada en el **Patrón Repositorio**, **Inyección de Dependencias** y un **Modelo Transversal de Auditoría (CDC)**:

```mermaid
flowchart TB
    %% ==========================================
    %% UYUNI ARCHITECTURE - CORPORATE BRAND THEME
    %% ==========================================
    
    subgraph Clients["🌐 Capas de Consumo / Clientes"]
        SPA["Frontend de Gestión (Angular 21)"]
        PWA["PWA Comercial (React + Vite)"]
        CLI["Scripts ETL / Mobile / API Clients"]
    end

    subgraph Gateway["🚪 Capa de Entrada, Middleware & Seguridad"]
        API["FastAPI 0.139 Engine (/api)"]
        AUDIT_MW["Audit Middleware (RequestID & Context)"]
        AUTH["Control de Acceso RBAC (Tokens JWT & X-Active-Role)"]
    end

    subgraph BusinessDomains["📦 Dominios Modulares de Negocio (DDD-Lite)"]
        direction TB
        
        subgraph Commerce["🛒 Módulo Commerce (Nova Box Bolivia)"]
            direction LR
            C_R["Routers (SKUs, Lotes)"] --> C_S["Service (Ventas, Piso Mínimo)"] --> C_RP["Commerce Repositories"]
        end

        subgraph Core["👥 Módulo Core (Seguridad, Usuarios & Configuración)"]
            direction LR
            U_R["Routers (Users, Auth)"] --> U_S["Service (Roles & Manifests)"] --> U_RP["Core Repositories"]
        end

        subgraph Tasks["📋 Módulo Tasks (Operaciones)"]
            direction LR
            T_R["Routers (Tasks)"] --> T_S["Service (Seguimiento)"] --> T_RP["Task Repository"]
        end
    end

    subgraph SharedCore["⚙️ Infraestructura Transversal (app/core)"]
        BASE_REPO["BaseRepository[T] (Paginación, Búsqueda, Filtros)"]
        CATALOG_REG["Catálogos Dinámicos (Global Registry)"]
        EXC_HANDLER["Manejo Centralizado de Excepciones"]
    end

    subgraph DataPersistence["💾 Capa de Persistencia & Auditoría"]
        ORM["SQLModel / SQLAlchemy 2.0 ORM"]
        DB[("PostgreSQL 16 (19 Tablas Singulares)")]
        CDC["SQLAlchemy Event Hooks (CDC Audit Logs)"]
    end

    %% Relaciones de Flujo
    Clients --> API
    API --> AUDIT_MW
    AUDIT_MW --> AUTH
    AUTH --> BusinessDomains

    Commerce -.-> BASE_REPO
    Core -.-> BASE_REPO
    Tasks -.-> BASE_REPO
    Commerce -.-> CATALOG_REG

    C_RP --> ORM
    U_RP --> ORM
    T_RP --> ORM

    ORM --> DB
    DB -.->|Captura CDC| CDC
    CDC -.->|Inserta historial| DB

    %% ==========================================
    %% ESTILOS CORPORATIVOS UYUNI
    %% ==========================================
    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:1.5px,color:#003865,font-weight:bold;
    classDef gatewayNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef commerceNode fill:#003865,stroke:#00c2cb,stroke-width:2px,color:#ffffff;
    classDef coreNode fill:#004889,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef tasksNode fill:#0f172a,stroke:#67e8f9,stroke-width:2px,color:#ffffff;
    classDef sharedNode fill:#f8fafc,stroke:#00b4d8,stroke-width:1.5px,color:#003865;
    classDef dbNode fill:#002b49,stroke:#00c2cb,stroke-width:2.5px,color:#ffffff,font-weight:bold;

    class SPA,PWA,CLI clientNode;
    class API,AUTH,AUDIT_MW gatewayNode;
    class C_R,C_S,C_RP commerceNode;
    class U_R,U_S,U_RP coreNode;
    class T_R,T_S,T_RP tasksNode;
    class BASE_REPO,CATALOG_REG,EXC_HANDLER sharedNode;
    class ORM,DB,CDC dbNode;
```

### Componentes de Cada Dominio (`app/modules/`)
Cada módulo de negocio está aislado en su propio submódulo para garantizar alta cohesión y bajo acoplamiento:
* `routers.py`: Exposición de contratos RESTful, endpoints y políticas de seguridad RBAC.
* `service.py`: Lógica de negocio pura, validaciones de dominio y transacciones atómicas.
* `repository.py`: Consultas optimizadas, filtros especializados y operaciones sobre la base de datos.
* `models.py`: Entidades relacionales mapeadas con SQLModel/SQLAlchemy.
* `schemas.py`: Contratos de validación de entrada/salida tipados con Pydantic v2.

---

## 🗄️ Módulos de Negocio (Dominios)

El backend organiza sus capacidades en los siguientes módulos principales:

### 1. `commerce` (Motor Comercial & Nova Box Bolivia)
Plataforma transaccional para control de inventarios, lotes y facturación de ventas:
* **Fichas Maestras y SKUs (`product_masters`, `products`)**: Catálogo maestro de 240+ SKUs, control de condición (*nuevo, usado, caja abierta*), precio oficial y regla crítica de **precio mínimo (`minimum_price`)**.
* **Lotes de Importación (`batches`)**: Control de cajas (Ataúd 1, Ataúd 2, Amazon Next, etc.), costos de flete, seguros e impuestos, cálculo del **punto de equilibrio** y margen neto.
* **Ventas Atómicas (`sales`)**: Registro seguro de transacciones con métodos de pago bolivianos (QR Simple, Efectivo, Flota/Transferencia), cálculo automático de ganancias y cambio de estado a `vendido` en la misma transacción.
* **Catálogo Público Cacheado (`api/public/catalog`)**: Endpoint de alta velocidad para alimentar la PWA de clientes en tiempo real sin reconstrucción de frontend.

### 2. `core` (Seguridad, Usuarios & Configuración)
* **Usuarios y Cuentas**: Gestión de cuentas de usuario, verificación, reseteo y lockout defensivo.
* **Control de Acceso (RBAC)**: Roles (`role`), módulos (`module`), grupos de módulos (`module_group`) y permisos de acción (`role_module`).
* **Manifiestos Descentralizados**: Sincronización declarativa e idempotente de menús y permisos de cada dominio.

### 3. `tasks` (Seguimiento Operativo)
* Gestión y monitoreo de tareas operativas y administrativas.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Lenguaje** | **Python 3.14.6** | Tipado estático estricto y alto rendimiento |
| **Framework Web** | **FastAPI 0.139+** | API REST asíncrona, validación automática y OpenAPI 3.1 |
| **ORM / Datos** | **SQLModel + SQLAlchemy 2.0+** | Combinación declarativa de SQLAlchemy con modelos Pydantic |
| **Base de Datos** | **PostgreSQL 16+** | PostgreSQL en producción / SQLite en memoria para tests |
| **Migraciones** | **Alembic** | Control de versiones y evolución de esquema relacional |
| **Seguridad** | **PyJWT + Passlib (bcrypt)** | Tokens JWT Bearer con rotación, RBAC y lockout defensivo |
| **Logging** | **Structlog** | Trazabilidad estructurada JSON con `request_id` contextual |
| **Linter & Formato** | **Ruff** | Herramienta ultra-rápida de linting y formateo de código |
| **Type Checking** | **Mypy** | Análisis estático de tipos estricto (`--ignore-missing-imports`) |
| **Testing** | **Pytest** | Suite automatizada de pruebas de integración unitarias |

---

## ⚙️ Instalación y Puesta en Marcha

> [!IMPORTANT]
> **Convención del Entorno Virtual**: Este proyecto requiere el uso del entorno virtual `venv/`. Siempre ejecute las herramientas con el prefijo `venv/bin/<herramienta>` (ej. `venv/bin/python`, `venv/bin/alembic`, `venv/bin/pytest`).

### 1. Requisitos Previos
* **Python 3.14.6** (En Ubuntu/Debian se instala con `sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt install -y python3.14 python3.14-venv python3.14-dev`)
* **PostgreSQL 16+**
* **Git**

### 2. Clonar el Repositorio
```bash
git clone git@github.com:henrytaby/uyuni-backend-py.git
cd uyuni-backend-py
```

### 3. Configurar el Entorno Virtual
```bash
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configurar Base de Datos y Variables de Entorno
Crea la base de datos en PostgreSQL:
```bash
sudo -u postgres createdb uyuni_admin
```

Copia la plantilla de entorno y edítala:
```bash
cp .env.example .env
```

Configura tus credenciales en `.env`:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/uyuni_admin"
SECRET_KEY="tu_clave_secreta_generada_aleatoriamente"
ENVIRONMENT="development"
PORT=8000
```

### 5. Ejecutar Migraciones de Base de Datos
Aplica las migraciones de Alembic para crear la estructura completa de tablas:
```bash
venv/bin/alembic upgrade head
```

### 6. Poblar Datos Iniciales (Seeds)
Ejecuta los scripts de inicialización para crear los módulos, roles y el usuario administrador:
```bash
venv/bin/python seeds/seed_create_modules.py
venv/bin/python seeds/seed_users.py
```

*Credenciales por defecto de desarrollo: `admin` / `admin123`*

> [!CAUTION]
> **Seguridad en Producción**: La contraseña `admin123` es exclusiva para pruebas locales. Debe cambiarse inmediatamente antes de desplegar en producción.

### 7. Iniciar el Servidor de Desarrollo
```bash
venv/bin/fastapi dev app/main.py
```

El portal y la documentación interactiva estarán disponibles en:
* **Portal Gateway Web**: `http://localhost:8000/`
* **Swagger UI Interactivo**: `http://localhost:8000/docs`
* **ReDoc Technical Docs**: `http://localhost:8000/redoc`
* **Health Check**: `http://localhost:8000/health`

---

## 🧪 Testing y Calidad de Código

El proyecto cuenta con una batería de pruebas automatizadas y estándares estrictos de **Clean Code** y **SOLID**:

```bash
# 1. Ejecutar suite de pruebas con base de datos en memoria (SQLite)
venv/bin/pytest

# 2. Análisis estático de tipos
venv/bin/mypy app/ --ignore-missing-imports

# 3. Linter y formateo automático
venv/bin/ruff check app/ tests/ --fix
venv/bin/ruff format app/ tests/
```

---

## 🚀 Opciones de Despliegue en Producción

El proyecto incluye una suite completa de guías de infraestructura y puesta en producción centralizada en [`docs/deployment/`](docs/deployment/README.md):

1. 🏢 **[Manual de Replicación para Nuevas Empresas (Marca Blanca)](docs/deployment/CLIENT_REPLICATION_PLAYBOOK.md)**: **Recomendado**. Guía paso a paso para desplegar instancias independientes y aisladas para nuevas empresas (como **Nova Labs** o futuros clientes comerciales) con sus propios correos, cuentas gratuitas y protección de propiedad intelectual.
2. 🟣 **[Despliegue en Render.com (Contenedor Docker)](docs/deployment/RENDER_DEPLOYMENT_GUIDE.md)**: Manual paso a paso para desplegar en Render con Docker (Python 3.14), base de datos Neon y monitor Keep-Alive 24/7 con UptimeRobot.
3. ☁️ **[Despliegue Serverless en la Nube (Sin Servidores)](docs/deployment/SERVERLESS_DEPLOYMENT_GUIDE.md)**: Arquitectura moderna sin Linux con Neon.tech, Vercel/Render, fotos en Cloudinary y documentos en Cloudflare R2. Costo $0.00/mes.
4. 🖥️ **[Despliegue Tradicional en Servidor VPS Ubuntu](docs/deployment/UBUNTU_VPS_DEPLOYMENT_GUIDE.md)**: Despliegue en tu propio servidor Linux con **Systemd**, **Nginx como Reverse Proxy** y certificados SSL de **Let's Encrypt**.

---

## 📚 Documentación para Desarrolladores

El proyecto incluye una completa suite de guías técnicas en el directorio [`docs/`](docs/README.md):

| Documento | Descripción |
| :--- | :--- |
| 🚀 **[Suite de Despliegue & Infraestructura](docs/deployment/README.md)** | Índice maestro de producción, serverless, Render, VPS y marca blanca |
| 🏢 **[Replicación para Nuevas Empresas](docs/deployment/CLIENT_REPLICATION_PLAYBOOK.md)** | Procedimiento de despliegue dedicado por empresa / marca blanca (Nova Labs y clientes) |
| 🟣 **[Despliegue en Render.com](docs/deployment/RENDER_DEPLOYMENT_GUIDE.md)** | Manual paso a paso para contenedores Docker en Render.com (Python 3.14) |
| ☁️ **[Despliegue Serverless](docs/deployment/SERVERLESS_DEPLOYMENT_GUIDE.md)** | Manual completo en la nube: Neon + Vercel/Render + Cloudflare + Cloudinary |
| 🖥️ **[Despliegue VPS Ubuntu](docs/deployment/UBUNTU_VPS_DEPLOYMENT_GUIDE.md)** | Manual paso a paso para servidores privados virtuales con Systemd y Nginx |
| **[Módulo Commerce (Guía Maestra)](docs/COMMERCE_MODULE_GUIDE.md)** | Visión general del ecosistema comercial, SKUs, lotes y ventas |
| **[Arquitectura Commerce](docs/commerce/01_ARCHITECTURE.md)** | Diagramas de componentes, flujos transaccionales y entidades |
| **[Diccionario de Base de Datos](docs/commerce/02_DATABASE_DICTIONARY.md)** | Tablas, campos, restricciones, llaves y tipos de datos de Commerce |
| **[Guía de Integración Frontend](docs/commerce/03_FRONTEND_INTEGRATION_GUIDE.md)** | Endpoints, contratos de petición/respuesta y ejemplos de consumo |
| **[Flujos Operativos y Reglas de Negocio](docs/commerce/04_OPERATIONAL_WORKFLOW.md)** | Flujo de lotes, punto de equilibrio, ventas atómicas y mermas |
| **[Manual del Desarrollador](docs/DEVELOPER_GUIDE.md)** | Guía paso a paso para crear nuevos submódulos |
| **[Guía de RBAC y Permisos](docs/RBAC_GUIDE.md)** | Modelo de seguridad, slugs, roles y personificación |
| **[Guía de Migraciones (Alembic)](docs/ALEMBIC_GUIDE.md)** | Procedimientos para versionar y aplicar cambios de esquema |
| **[Guía de Catálogos Dinámicos](docs/developer_guide/02_sistema_catalogos_dinamicos.md)** | Protocolo `CatalogProvider` y carga masiva (`/api/catalogs/bulk`) |
| **[Guía de Búsqueda y Filtros](docs/QUERY_SYSTEM_GUIDE.md)** | Motor polimórfico de búsqueda y filtros inyectables |
| **[Guía de Auditoría (CDC)](docs/AUDIT_GUIDE.md)** | Registro contextual y trazabilidad de cambios en base de datos |
| **[Estándar de AI Agents (.agents/)](.agents/README.md)** | Skills, personas y memoria para agentes de inteligencia artificial |

---

## 🛠️ Scripts y Utilidades

Ubicados en la carpeta `scripts/` para tareas de mantenimiento y administración:

* **Sincronización ETL SIGER**:
  ```bash
  venv/bin/python scripts/sync_siger.py
  ```
* **Archivado de Auditoría**:
  ```bash
  venv/bin/python scripts/archive_audit.py --days 90 --dir archive
  ```
* **Reinicio de Esquema DB (Desarrollo)**:
  ```bash
  venv/bin/python scripts/reset_db_schema.py
  ```
* **Demo Interactivo de Auditoría**:
  ```bash
  venv/bin/python scripts/demo_audit.py
  ```

---

## 📜 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más información.
