# 03. Guía de Integración Frontend — Commerce

Esta guía está dirigida a los desarrolladores de frontend encargados de integrar el módulo `commerce` en el panel de administración (**Angular 21 + PrimeNG 21** en `/opt/uyuni/uyuni-frontend-ng`) y la aplicación móvil de catálogo para clientes (**React + Vite PWA** en `/opt/nova/nova-home-tech/apps/catalog-pwa`).

---

## 🔑 Autenticación y Encabezados

Todas las rutas privadas del API requieren un token JWT de tipo `Bearer` en el encabezado `Authorization`:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Manejo Estándar de Errores:
Las respuestas de error siguen el estándar de excepciones tipadas del backend:
- `400 Bad Request`: Error de validación o regla de negocio violada (ej: intentar vender por debajo del mínimo).
- `401 Unauthorized`: Token ausente, expirado o inválido.
- `403 Forbidden`: El usuario no cuenta con los permisos RBAC requeridos.
- `404 Not Found`: El recurso solicitado (producto, lote o venta) no existe.

```json
{
  "detail": "Precio pactado (100.0) menor al mínimo (140.0) para 'Almohadilla Térmica Eléctrica'. Requiere autorización (allow_below_minimum=True)."
}
```

---

## ⚡ 1. Catálogos Dinámicos Masivos (`POST /api/catalogs/bulk`)

> [!TIP]
> **Optimización de Rendimiento:** Nunca realices peticiones HTTP separadas para poblar cada `<p-dropdown>` o `<select>`. Utiliza el endpoint masivo para obtener todos los catálogos en **una sola llamada HTTP**.

### Petición:
```http
POST /api/catalogs/bulk
```

```json
{
  "commerce_categories": {},
  "commerce_live_baskets": {},
  "commerce_batches": {},
  "commerce_product_masters": {},
  "commerce_physical_conditions": {},
  "commerce_product_statuses": {},
  "commerce_sales_channels": {},
  "commerce_payment_methods": {},
  "commerce_delivery_modalities": {}
}
```

### Respuesta Consolidada:
```json
{
  "commerce_categories": [
    { "value": "01a1b8dc-dd82-73cb-8e37-99fb5265bd0e", "label": "💡 Hogar & Iluminación", "extra": null },
    { "value": "01a1b8dc-dd8b-7123-8c42-88ec4152aa11", "label": "🎧 Audio & Sonido", "extra": null }
  ],
  "commerce_live_baskets": [
    { "value": "01a1b8dc-dd9c-7016-a183-d997fb1d90ab", "label": "Canasta 1 - Taller & Auto", "extra": null },
    { "value": "01a1b8dc-dda2-7201-b219-c990ee12ff34", "label": "Canasta +1 - Remate Flash", "extra": null }
  ],
  "commerce_product_masters": [
    { "value": "01a1c784-f9b2-7248-af9c-59a9f3951962", "label": "#1 - Reloj de Pared Vinilo LED RGB", "extra": null },
    { "value": "01a1c785-02b3-7641-bb12-9988aa112233", "label": "#53 - Almohadilla Térmica Eléctrica", "extra": null }
  ],
  "commerce_payment_methods": [
    { "value": "QR", "label": "Pago QR", "extra": null },
    { "value": "CASH", "label": "Efectivo", "extra": null },
    { "value": "TRANSFER", "label": "Transferencia Bancaria", "extra": null }
  ]
}
```

---

## 📦 2. Fichas Maestras (`/api/commerce/product-masters`)

Las fichas maestras representan el catálogo intelectual y comercial de productos.

### A. Listar Fichas Maestras
```http
GET /api/commerce/product-masters/?offset=0&limit=50&category_id=<uuid>&live_basket_id=<uuid>&search=reloj
```

#### Parámetros Query:
- `offset`: Desplazamiento para paginación (default: `0`).
- `limit`: Cantidad de registros por página (default: `100`).
- `sort_by`: Campo de ordenación (`item_number`, `name`, `official_price`, default: `item_number`).
- `sort_order`: `'asc'` o `'desc'`.
- `search`: Búsqueda multi-campo insensible a mayúsculas (`"53"`, `"#53"`, `"NOV-053"`, `"reloj"`, `"almohadilla"`).
- `category_id`: Filtrar por categoría.
- `live_basket_id`: Filtrar por canasta de TikTok Live.
- `is_active`: Filtrar activos (`true`) o archivados (`false`).

#### Respuesta Enriquecida con Existencias Consolidadas:
Cada elemento incluye el consolidado de existencias en tiempo real de todas las cajas:
```json
[
  {
    "id": "01a1c785-02b3-7641-bb12-9988aa112233",
    "item_number": 53,
    "code": "53",
    "name": "Almohadilla Térmica Eléctrica",
    "description": "Almohadilla de calor terapéutico con control de temperatura digital.",
    "category_id": "01a1b8dc-dd82-73cb-8e37-99fb5265bd0e",
    "live_basket_id": "01a1b8dc-dda2-7201-b219-c990ee12ff34",
    "brand": "Genérico",
    "model": "TK-HP2412",
    "official_price": 180.0,
    "minimum_price": 140.0,
    "published_price": 160.0,
    "currency": "BOB",
    "cover_image_url": "https://pub-novabox.r2.dev/products/053/cover.webp",
    "marketplace_url": "https://www.facebook.com/marketplace/item/123456789/",
    "external_info_url": "https://www.amazon.com/dp/B08XYZ123",
    "features": "• 6 niveles de temperatura\n• Auto-apagado a las 2 horas\n• Lavable a máquina",
    "marketing_details": "Ideal para dolores lumbares y menstruales. Resaltar la seguridad del auto-apagado.",
    "is_reviewed": true,
    "is_fb_verified": true,
    "has_video": true,
    "is_published_marketplace": true,
    "is_whatsapp_published": false,
    "is_active": true,
    "total_available_stock": 2,
    "total_sold_stock": 0,
    "total_merma_stock": 0
  }
]
```

### B. Obtener Total de Fichas Maestras
```http
GET /api/commerce/product-masters/count?category_id=<uuid>&search=reloj
```
**Respuesta:**
```json
{
  "total": 240,
  "count": 240
}
```

### C. Obtener por Número Numérico Directo
```http
GET /api/commerce/product-masters/by-number/53
```

---

## 🏷️ 3. Inventario Físico por Caja (`/api/commerce/products`)

Representa las existencias físicas asociadas a una caja o lote de importación.

### A. Listar Inventario Físico
```http
GET /api/commerce/products/?batch_id=<uuid>&master_product_id=<uuid>&status=AVAILABLE
```

#### Propiedades Delegadas Automáticas:
Para evitar que el frontend deba realizar peticiones secundarias, cada producto físico incluye automáticamente las propiedades heredadas de su ficha maestra y su lote:
- `name`: Nombre de la ficha maestra (`master_product.name`).
- `official_price`, `minimum_price`, `published_price`: Precios de referencia.
- `batch_name`: Nombre de la caja física (`batch.name`, ej: `"Ataúd 2"`).

```json
[
  {
    "id": "01a1c786-1122-3344-5566-778899aabbcc",
    "master_product_id": "01a1c785-02b3-7641-bb12-9988aa112233",
    "batch_id": "01a1b8dc-ddb0-71f4-bbec-6966db6633ef",
    "batch_name": "Ataúd 2",
    "name": "Almohadilla Térmica Eléctrica",
    "variant_name": "Modelo TK-HP2412",
    "cost_price": 80.0,
    "initial_quantity": 1,
    "sold_quantity": 0,
    "merma_quantity": 0,
    "available_quantity": 1,
    "status": "AVAILABLE",
    "physical_condition": "OPERATIONAL",
    "defect_detail": null,
    "is_reviewed": true,
    "official_price": 180.0,
    "minimum_price": 140.0,
    "published_price": 160.0
  }
]
```

### B. Registrar Merma o Producto Dañado
Para registrar una unidad defectuosa o actualizar el estado tras una prueba física:
```http
PUT /api/commerce/products/<product_id>
```
```json
{
  "merma_quantity": 1,
  "physical_condition": "DAMAGED_SCRAP",
  "defect_detail": "Conector roto, no enciende."
}
```
*El backend recalcula automáticamente `available_quantity = initial - sold - merma` y si es 0, cambia el estado a `"SCRAPPED"`.*

---

## 💰 4. Transacciones de Venta (`/api/commerce/sales`)

Permite registrar transacciones comerciales atómicas con soporte para logística y pagos bolivianos.

### A. Crear Venta
```http
POST /api/commerce/sales/
```

#### Payload de Ejemplo:
```json
{
  "customer_name": "Gonzalo Morales",
  "customer_phone": "79712345",
  "channel_id": "01a1c1d9-7bd8-7453-a5c3-6bae663dd49e",
  "channel": "TikTok Live",
  "payment_method": "QR",
  "payment_status": "COLLECTED",
  "delivery_modality": "TERMINAL_BUS",
  "delivery_address": "Terminal de Buses CBB - Flota Trans Copacabana a La Paz",
  "delivery_cost": 20.0,
  "delivery_cost_paid_by": "CUSTOMER",
  "delivery_status": "PENDING",
  "total_collected": 160.0,
  "allow_below_minimum": false,
  "observations": "Enviar encomienda a nombre de Gonzalo Morales, CI 4567890 LP.",
  "items": [
    {
      "product_id": "01a1c786-1122-3344-5566-778899aabbcc",
      "quantity": 1,
      "unit_price": 160.0
    }
  ]
}
```

### B. Respuesta de Venta Creada:
El backend genera el código de venta (`VTA-YYYYMMDD-XXXXXX`), asocia el costo unitario del lote, calcula la ganancia neta y descuenta el stock:

```json
{
  "id": "01a1c787-9988-7766-5544-33221100aabb",
  "sale_number": "VTA-20261110-D8E9F0",
  "sale_date": "2026-11-10T20:30:00Z",
  "customer_name": "Gonzalo Morales",
  "customer_phone": "79712345",
  "channel": "TikTok Live",
  "payment_method": "QR",
  "payment_status": "COLLECTED",
  "delivery_modality": "TERMINAL_BUS",
  "delivery_address": "Terminal de Buses CBB - Flota Trans Copacabana a La Paz",
  "delivery_cost": 20.0,
  "delivery_cost_paid_by": "CUSTOMER",
  "delivery_status": "PENDING",
  "total_collected": 160.0,
  "total_cost": 80.0,
  "net_profit": 80.0,
  "currency": "BOB",
  "observations": "Enviar encomienda a nombre de Gonzalo Morales, CI 4567890 LP.",
  "items": [
    {
      "id": "01a1c787-aaaa-bbbb-cccc-ddddeeeeffff",
      "sale_id": "01a1c787-9988-7766-5544-33221100aabb",
      "product_id": "01a1c786-1122-3344-5566-778899aabbcc",
      "product_name": "Almohadilla Térmica Eléctrica",
      "quantity": 1,
      "unit_price": 160.0,
      "unit_cost": 80.0,
      "total_price": 160.0,
      "net_margin": 80.0
    }
  ]
}
```

---

## 🎛️ 5. Módulo Unificado de Catálogos y Parámetros (`/commerce/catalogs`)

### 5.1. Estándar de Industria: Separación de Flujo Operativo vs. Catálogos Maestros
En sistemas ERP de clase mundial (Shopify, Stripe, Odoo, SAP), los elementos de la interfaz se dividen en:
1. **Flujo Transaccional Diario (Alta Frecuencia):** Pantallas como Ventas, Productos y Lotes, accesibles directamente desde la barra lateral.
2. **Datos de Referencia y Catálogos (Baja Frecuencia):** Tablas de parametrización como Categorías, Canales de Venta y Rondas de Inversión, que se configuran esporádicamente.

Para evitar saturar la barra lateral con 8 o 10 accesos directos (*efecto menú sábana*), el módulo `commerce` implementa el **Unified Catalog Hub Pattern**:
- En la barra lateral solo se expone un acceso: **`Catálogos`** (ruta: `commerce/catalogs`, slug: `commerce-catalogs`, icono: `LucideSlidersHorizontal`).
- Al ingresar, la pantalla presenta una interfaz basada en **Pestañas (Cejas / Tabs de PrimeNG 21)** donde cada pestaña gestiona un grupo de datos independiente con su propia tabla y formulario.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Comercio / Catálogos y Parámetros                                     │
├─────────────────┬───────────────────┬──────────────────────────────────┤
│  🏷️ Categorías   │  📢 Canales Venta │  📈 Rondas de Inversión          │
├─────────────────┴───────────────────┴──────────────────────────────────┤
│                                                [+ Nueva Categoría]     │
│  Buscar categoría: [ Q Buscar... ]                                     │
│                                                                        │
│  Nombre             Slug           Estado      Acciones                │
│  ─────────────────────────────────────────────────────────────         │
│  Electrónica        electronica    Activo      [Editar] [Eliminar]     │
│  Hogar y Cocina     hogar-cocina   Activo      [Editar] [Eliminar]     │
│  Herramientas       herramientas   Activo      [Editar] [Eliminar]     │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 5.2. Cejas / Pestañas y sus Endpoints de Backend

Cada pestaña ("ceja") en el componente de Angular se conecta a su propio submódulo CRUD en FastAPI:

#### Ceja 1: Categorías de Producto (`/api/commerce/categories`)
Permite clasificar el catálogo de productos (ej. Electrónica, Iluminación, Hogar, Herramientas):
- **Listar:** `GET /api/commerce/categories/?offset=0&limit=50&search=`
- **Crear:** `POST /api/commerce/categories/`
  ```json
  {
    "name": "Electrónica y Audio",
    "description": "Auriculares, micrófonos, parlantes y adaptadores bluetooth",
    "is_active": true
  }
  ```
- **Editar:** `PUT /api/commerce/categories/{id}`
- **Eliminar:** `DELETE /api/commerce/categories/{id}`

#### Ceja 2: Canales de Venta (`/api/commerce/channels`)
Gestiona los canales comerciales por donde ingresan los pedidos (TikTok Live, Facebook Marketplace, WhatsApp, Tienda Física):
- **Listar:** `GET /api/commerce/channels/?offset=0&limit=50&search=`
- **Crear:** `POST /api/commerce/channels/`
  ```json
  {
    "name": "TikTok Live",
    "description": "Ventas directas durante transmisiones de remate en vivo",
    "is_active": true
  }
  ```
- **Editar:** `PUT /api/commerce/channels/{id}`
- **Eliminar:** `DELETE /api/commerce/channels/{id}`

#### Ceja 3: Canastas Live (`/api/commerce/live-baskets`)
Agrupaciones temáticas de productos para subastas en vivo (C1 Taller & Auto, C2 Cables & Iluminación, C3 Hogar & Cocina, C+1 Flash):
- **Listar:** `GET /api/commerce/live-baskets/?offset=0&limit=50&search=`
- **Crear:** `POST /api/commerce/live-baskets/`
  ```json
  {
    "code": "C1",
    "name": "Taller & Auto",
    "label": "Canasta 1 - Taller & Auto",
    "description": "Herramientas eléctricas y accesorios para vehículo",
    "price_range": "Bs. 40 - 200",
    "target_audience": "Mecánicos, choferes y hobbistas"
  }
  ```
- **Editar:** `PUT /api/commerce/live-baskets/{id}`
- **Eliminar:** `DELETE /api/commerce/live-baskets/{id}`

#### Ceja 4: Rondas de Inversión (`/api/commerce/rounds`)
Control de aportes de capital y socios inversionistas:
- **Listar:** `GET /api/commerce/rounds/?offset=0&limit=50`
- **Crear:** `POST /api/commerce/rounds/`

---

### 5.3. Implementación Estándar en Angular 21 (PrimeNG 21 Tabs)

Ejemplo de implementación recomendada para `CommerceCatalogsComponent` (`src/app/features/commerce/pages/catalogs`):

```html
<div class="card p-6">
  <div class="flex items-center gap-3 mb-6">
    <svg lucideSlidersHorizontal size="28" class="text-brand-500"></svg>
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Catálogos de Comercio</h1>
      <p class="text-sm text-gray-500">Gestión de categorías, canales comerciales, canastas live y rondas</p>
    </div>
  </div>

  <p-tabs value="0">
    <p-tablist>
      <p-tab value="0">
        <i class="pi pi-tags mr-2"></i> Categorías de Producto
      </p-tab>
      <p-tab value="1">
        <i class="pi pi-share-alt mr-2"></i> Canales de Venta
      </p-tab>
      <p-tab value="2">
        <i class="pi pi-video mr-2"></i> Canastas Live
      </p-tab>
      <p-tab value="3">
        <i class="pi pi-chart-line mr-2"></i> Rondas de Inversión
      </p-tab>
    </p-tablist>

    <p-tabpanels>
      <!-- CEJA 1: CATEGORÍAS -->
      <p-tabpanel value="0">
        <app-commerce-categories-tab></app-commerce-categories-tab>
      </p-tabpanel>

      <!-- CEJA 2: CANALES DE VENTA -->
      <p-tabpanel value="1">
        <app-commerce-channels-tab></app-commerce-channels-tab>
      </p-tabpanel>

      <!-- CEJA 3: CANASTAS LIVE -->
      <p-tabpanel value="2">
        <app-commerce-live-baskets-tab></app-commerce-live-baskets-tab>
      </p-tabpanel>

      <!-- CEJA 4: RONDAS DE INVERSIÓN -->
      <p-tabpanel value="3">
        <app-commerce-rounds-tab></app-commerce-rounds-tab>
      </p-tabpanel>
    </p-tabpanels>
  </p-tabs>
</div>
```


