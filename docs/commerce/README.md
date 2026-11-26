# Ecosistema Commerce — Guía Maestra

Documentación oficial del dominio **Commerce** de **Uyuni Backend**. Este dominio es el motor
transaccional y ERP de importación/comercialización de **Marca Blanca**: control de capital de
inversión, costeo de lotes, existencias físicas, catálogo maestro multicanal, ventas atómicas y
asistente de IA comercial.

> **Base de la API:** `/api` · **Prefijo del dominio:** `/api/commerce`
> **Autenticación:** JWT `Bearer` + RBAC granular (permiso requerido sobre el módulo `commerce`).

---

## 🎯 Propósito del Dominio

El dominio resuelve la operación de importación y venta de lotes de liquidación/retail a través de
remates en vivo (**TikTok Live**), **Facebook Marketplace**, canales de mensajería y entregas
locales o envíos nacionales (flota/courier). Sus desafíos críticos son:

1. **Identidad comercial vs. existencia física:** separa la ficha maestra intelectual
   (`commerce_product_master`) de cada unidad física importada en una caja (`commerce_product`).
2. **Contabilidad de costos por lote:** calcula costo unitario, absorción de mermas y punto de
   equilibrio por caja y por ronda de inversión.
3. **Protección de margen:** bloquea ventas por debajo del piso de regateo (`minimum_price`) salvo
   autorización explícita (`allow_below_minimum=True`).
4. **Ventas atómicas:** crea cabecera, líneas, descuenta stock y calcula utilidad en una sola
   transacción ACID.
5. **Canastas para Live:** agrupa productos en canastas temáticas (`C1`…`C4`, `C+1`, `FONDO`) para
   agilizar el remate.
6. **Catálogos de alto rendimiento:** permite poblar todos los selectores del frontend en una sola
   petición (`POST /api/catalogs/bulk`).

---

## 📚 Índice de la Documentación

| Documento | Audiencia | Contenido principal |
| :--- | :--- | :--- |
| **[01. Arquitectura y Reglas de Negocio](./01_ARCHITECTURE.md)** | Arquitectos, Tech Leads, Backend | DDD-Lite + Clean Architecture, Ficha Maestra vs. Lote, Tri-Precio, modalidades de costeo, ventas atómicas, Cloudinary, secuencias atómicas. |
| **[02. Diccionario de Base de Datos](./02_DATABASE_DICTIONARY.md)** | DBAs, Fullstack, Auditoría | ERD oficial y diccionario campo por campo de las **11 tablas** (tipos, índices, FK, auditoría). |
| **[03. Guía de Integración Frontend](./03_FRONTEND_INTEGRATION_GUIDE.md)** | Frontend (Angular 21 / React PWA) | Contratos REST, catálogos bulk, galería Cloudinary, enlaces externos, lotes, ventas, rondas y TypeScript. |
| **[04. Flujo Operativo y Ciclo de Vida](./04_OPERATIONAL_WORKFLOW.md)** | Operadores, Almacén, Devs | Ciclo de vida didáctico: financiación → desempaque → merma → merchandising → venta → break-even. |
| **[05. Asistente de IA e Inventario](./05_AI_ASSISTANT_GUIDE.md)** | Backend, Frontend | Asistente multi-proveedor (Groq, Mistral, Gemini) con RAG ligero y stock en vivo. |
| **[🛒 Ventas y POS](../sales/README.md)** | Backend, Frontend, Cajeros | Documentación especializada del submódulo de ventas, caja y logística. |
| **[📖 Manual de Rondas y Lotes](../manuales/commerce/01_RONDAS_Y_LOTES_MANUAL_OPERATIVO.md)** | Socios, Administradores | Manual didáctico de rondas de inversión, modalidades de lotes y operación. |

---

## 🧩 Submódulos del Dominio

```text
app/modules/commerce/
├── assistant/         # Copiloto IA (Groq / Mistral / Gemini) con stock en vivo
├── rounds/            # Rondas de inversión y capital desembolsado
├── batches/           # Cajas/lotes importados y costeo
├── categories/        # Categorías de catálogo (CAT-01…)
├── live_baskets/      # Canastas temáticas para Live (C1…C4, C+1, FONDO)
├── channels/          # Canales comerciales (Marketplace, Live, WhatsApp…)
├── product_masters/   # Fichas maestras, galería Cloudinary y enlaces externos
├── products/          # Inventario físico por caja/lote
├── sales/             # Venta atómica y detalle de ítems
├── catalogs/          # Proveedores dinámicos para selectbox y bulk loading
└── routers.py         # Agregador unificado (/api/commerce)
```

Cada submódulo respeta la estructura `routers.py → service.py → repository.py → models.py` y
`schemas.py`, y declara sus permisos/rutas en `manifest.py`.

---

## 🧭 Menú Frontend (Manifiesto Real)

`app/modules/commerce/manifest.py` registra el grupo **Comercio** con estos módulos. Los iconos son
**PrimeIcons** (`pi pi-*`), no Lucide:

| Orden | Módulo | Ruta | Icono | Propósito |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Rondas de Inversión** | `/commerce/rounds` | `pi pi-chart-line` | Capital, lotes asociados y punto de equilibrio. |
| 2 | **Lotes y Cajas** | `/commerce/batches` | `pi pi-box` | Costeo, mermas y costo unitario de cajas. |
| 3 | **Productos** | `/commerce/products` | `pi pi-tags` | Inventario físico, estados y precios. |
| 4 | **Catálogo Maestro** | `/commerce/product-masters` | `pi pi-database` | Fichas técnicas, galería y marketing. |
| 5 | **Ventas** | `/commerce/sales` | `pi pi-shopping-cart` | Registro atómico de ventas y cobros. |
| 6 | **Catálogos** | `/commerce/catalogs` | `pi pi-sliders-h` | Hub de cejas: categorías, canales y canastas Live. |

> **Unified Catalog Hub Pattern:** la barra lateral expone un único acceso de catálogos
> (`/commerce/catalogs`) con pestañas (`p-tabs` de PrimeNG) para datos de baja frecuencia. Las
> **Rondas de Inversión** se promovieron a módulo propio por ser el paso 1 del ciclo operativo.

---

## 🛠️ Stack Tecnológico

- **Framework:** FastAPI (Python 3.14.6), Pydantic v2.
- **ORM:** SQLModel (SQLAlchemy 2).
- **Base de datos:** PostgreSQL (`uyuni_prod` como BD principal y destino de sincronización;
  `an_core` como origen externo de lectura vía `SYNC_DATABASE_URL`) y SQLite en memoria para tests.
- **Migraciones:** Alembic (head actual `469394d3c127`).
- **Seguridad:** JWT (access/refresh), RBAC (`PermissionChecker`) y auditoría CDC (`AuditMixin`).
- **Multimedia:** Cloudinary (WebP, `q_auto`, `f_auto`).
- **IA:** Groq (principal), Mistral (fallback), Gemini (opcional) — configurable por `.env`.
- **Calidad:** Ruff, Mypy y Pytest.

---

## 🔌 Superficie de API (resumen)

| Recurso | Prefijo | Operaciones |
| :--- | :--- | :--- |
| Catálogos dinámicos | `/api/catalogs` | `POST /bulk`, `GET /{catalog_name}` |
| Fichas maestras | `/api/commerce/product-masters` | CRUD, `/by-number/{n}`, `/resolve/{id}`, `/images/*`, `/links/*` |
| Inventario físico | `/api/commerce/products` | CRUD, `/by-sku/{sku}`, `/images/*` |
| Lotes y cajas | `/api/commerce/batches` | CRUD, `/{id}/recalculate`, `/{id}/allocate-relative-costs` |
| Categorías | `/api/commerce/categories` | CRUD |
| Canales | `/api/commerce/channels` | CRUD |
| Canastas Live | `/api/commerce/live-baskets` | CRUD |
| Rondas de inversión | `/api/commerce/rounds` | CRUD, `/{id}/metrics`, `/{id}/recalculate` |
| Ventas | `/api/commerce/sales` | CRUD, `/available-products`, `/count` |
| Asistente IA | `/api/commerce/assistant` | `POST /chat`, `GET /providers` |

Convenciones transversales:

- **Paginación:** `offset` + `limit` (el repositorio acota `limit` entre **1 y 500**; endpoints
  específicos como `/sales/available-products` aplican su propio tope).
- **Ordenamiento:** `sort_by` + `sort_order` (`asc`/`desc`).
- **Búsqueda:** `search` multi-campo (según repositorio de cada entidad).
- **Errores:** `{ "detail": "..." }` con 400/401/403/404/422/500.
- **Auditoría:** todas las tablas incluyen `created_at`, `updated_at`, `created_by_id`, `updated_by_id`.
- **Base de datos:** nombres de tabla en **singular** (`commerce_product`, `commerce_sale`, etc.).

---

## 📖 Glosario Rápido

| Término | Significado en Uyuni |
| :--- | :--- |
| **Ficha Maestra** (`ProductMaster`) | Identidad comercial/intelectual del producto, precios y marketing. |
| **Producto físico** (`Product`) | Unidad concreta de inventario dentro de una caja/lote. |
| **Lote / Caja** (`Batch`) | Compra de importación con costos, mermas y costo unitario. |
| **Ronda** (`InvestmentRound`) | Capital invertido que financia uno o más lotes. |
| **Canasta Live** (`LiveBasket`) | Agrupación temática para remates en TikTok Live. |
| **Tri-Precio** | `official_price` (lista/mercado), `published_price` (venta), `minimum_price` (piso). |
| **Piso de regateo** | Límite mínimo de venta; vender por debajo exige `allow_below_minimum`. |
| **Merma** | Unidad dañada/inservible excluida de la ponderación de costos. |
| **Break-even** | Momento en que las ventas igualan el capital invertido. |
| **RIM** | *Retail Inventory Method*: prorrateo ponderado del costo por valor comercial. |

---

## 📋 Control de la Documentación

| Campo | Valor |
| :--- | :--- |
| **Fuente de verdad** | Código en `app/modules/commerce/` (modelos, schemas, routers y services) |
| **Última verificación** | 2026-11-26 |
| **Cobertura** | 11 tablas · 10 submódulos · 6 documentos |
| **Mantenimiento** | Actualizar este dominio cuando cambien modelos, endpoints o reglas de negocio |
