# Ecosistema Commerce — Guía Maestra

Bienvenido a la documentación oficial del módulo **Commerce** del sistema **Uyuni Backend**. Este módulo funciona como el motor transaccional, ERP de costos de importación, control de existencias físicas y gestor de catálogo comercial multicanal (Marca Blanca).

---

## 🎯 Propósito del Módulo

El módulo está diseñado para la importación y comercialización de lotes de productos o liquidaciones minoristas, comercializados a través de remates por streaming en vivo (**TikTok Live**), publicaciones en **Marketplace**, canales de mensajería directa y entregas locales o envíos nacionales.

El módulo `commerce` resuelve los siguientes desafíos críticos de negocio:

1. **Separación de Identidad vs. Lote Físico:** Diferencia la ficha comercial e intelectual de un producto (`commerce_product_master`) de sus existencias físicas importadas en diferentes cajas o lotes (`commerce_product`).
2. **Contabilidad de Costos por Lote y Punto de Equilibrio:** Calcula el costo real unitario de cada producto considerando precio de compra de la caja, flete y absorción de mermas/unidades defectuosas.
3. **Protección de Margen y Piso de Regateo:** Bloquea ventas por debajo del precio mínimo de venta (`minimum_price`) a menos que medie autorización explícita.
4. **Ventas Atómicas:** Descuenta stock, actualiza estados y calcula ganancias netas en una única transacción ACID.
5. **Canastas de Venta en Vivo (TikTok Live):** Organiza los productos por canastas temáticas (`C1 Taller`, `C2 Cables`, `C3 Hogar`, `C4 Belleza`, `C+1 Flash`) para agilizar la interacción del streamer y el registro de pedidos en tiempo real.
6. **Catálogos Dinámicos de Alto Rendimiento:** Permite a los frontends (Angular y React PWA) poblar todos los selectores del sistema en una única petición HTTP (`/api/catalogs/bulk`).

---

## 📚 Índice de la Documentación

La documentación se encuentra organizada en 4 volúmenes especializados según el rol del lector:

| Documento | Audiencia | Contenido Principal |
| :--- | :--- | :--- |
| **[01. Arquitectura y Reglas de Negocio](./01_ARCHITECTURE.md)** | Arquitectos, Tech Leads, Backend Devs | Patrón DDD-Lite, Clean Architecture, separación Ficha Maestra vs. Lote, reglas de negocio críticas, transacciones y diagramas de flujo. |
| **[02. Diccionario de Base de Datos](./02_DATABASE_DICTIONARY.md)** | DBAs, Fullstack Devs, Auditores | Diagrama Entidad-Relación (ERD) completo y descripción detallada campo por campo de las 9 tablas, tipos, índices y claves foráneas. |
| **[03. Guía de Integración Frontend](./03_FRONTEND_INTEGRATION_GUIDE.md)** | Frontend Devs (Angular, React) | Consumo de la API REST, autenticación, carga masiva de catálogos (`/api/catalogs/bulk`), búsqueda inteligente, filtros y ejemplos de payloads JSON. |
| **[04. Flujo Operativo y Ciclo de Vida](./04_OPERATIONAL_WORKFLOW.md)** | Operadores, Gestores de Almacén, Devs | Ciclo de vida didáctico paso a paso: desde el desempaque de una caja de liquidación, inspección y merma, hasta la venta en live y el cierre de lote. |

---

## 🧩 Resumen de Submódulos y Navegación Frontend

El dominio se encuentra estructurado en 8 submódulos desacoplados dentro de `app/modules/commerce/`:

```text
app/modules/commerce/
├── rounds/            # Rondas de inversión y capital desembolsado
├── batches/           # Lotes y cajas importadas con control de costos
├── categories/        # Categorías generales de catálogo (CAT-01..09)
├── live_baskets/      # Canastas temáticas para Live Streaming (C1..C4, C+1, FONDO)
├── channels/          # Canales comerciales (Marketplace, Live, Tienda física)
├── product_masters/   # Fichas comerciales e intelectuales (#1..242)
├── products/          # Inventario físico específico por caja/lote
├── sales/             # Transacciones de venta y detalle de ítems vendidos
├── catalogs/          # Proveedores dinámicos para selectbox y bulk loading
└── routers.py         # Enrutador agregador unificado (/api/commerce)
```

### 🧭 Menú Frontend y Unified Catalog Hub Pattern

Para mantener la barra lateral limpia y ergonómica, el menú de **Comercio** en Angular (`manifest.py`) expone los siguientes módulos:

| Módulo | Ruta | Icono Lucide | Tipo | Propósito |
| :--- | :--- | :--- | :--- | :--- |
| **Productos** | `/commerce/products` | `LucideTag` | Operativo | Catálogo de SKUs, stock físico y precios. |
| **Lotes y Cajas** | `/commerce/batches` | `LucideBoxes` | Operativo | Control de costos de cajas y punto de equilibrio. |
| **Ventas** | `/commerce/sales` | `LucideShoppingCart` | Operativo | Registro instantáneo de pedidos, cobros QR y despachos. |
| **Catálogo Maestro** | `/commerce/product-masters` | `LucideDatabase` | Maestro | Fichas técnicas maestras, especificaciones y fotos WebP. |
| **Catálogos** | `/commerce/catalogs` | `LucideSlidersHorizontal` | Catálogos (Tabs) | **Unified Hub con Cejas**: Categorías, Canales, Canastas Live y Rondas. |

---

## 🛠️ Stack Tecnológico

- **Framework:** FastAPI con Python 3.14.6
- **ORM / Modelado:** SQLModel (SQLAlchemy 2 + Pydantic v2)
- **Base de Datos:** PostgreSQL en producción y desarrollo (`fastapi_product`), SQLite en memoria para tests
- **Migraciones:** Alembic (historial unificado y limpio en `c0e81b83d91f`)
- **Seguridad y Permisos:** JWT (Bearer) con RBAC granular (`PermissionChecker`) y CDC (`AuditMixin`)
- **Calidad de Código:** Ruff (Linter & Formatter), Mypy (Tipado estático 100% verificado), Pytest

