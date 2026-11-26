# 03. Guía de Integración Frontend — Commerce

Esta guía está dirigida a los desarrolladores de frontend encargados de integrar el módulo `commerce` en el panel de administración (**Angular 21 + PrimeNG 21**) y aplicaciones cliente (**React + Vite PWA** o móviles).

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

El cuerpo es un mapa `{ "nombre_catalogo": { parámetros } }`. Cada valor es un objeto de filtros
del proveedor; `{}` significa "sin filtros".

### Petición:
```http
POST /api/catalogs/bulk
```

```json
{
  "commerce_categories": {},
  "commerce_live_baskets": {},
  "commerce_investment_rounds": {},
  "commerce_batches": {},
  "commerce_product_masters": {},
  "commerce_physical_conditions": {},
  "commerce_product_statuses": {},
  "commerce_sales_channels": {},
  "commerce_payment_methods": {},
  "commerce_payment_statuses": {},
  "commerce_delivery_modalities": {},
  "commerce_delivery_paid_by": {},
  "commerce_delivery_statuses": {}
}
```

### Catálogos registrados en Commerce

| Clave | Origen | Notas |
| :--- | :--- | :--- |
| `commerce_categories` | `commerce_category` | Label con emoji + nombre. |
| `commerce_live_baskets` | `commerce_live_basket` | Label comercial de la canasta. |
| `commerce_investment_rounds` | `commerce_investment_round` | Label `CODE - Nombre`. |
| `commerce_batches` | `commerce_batch` | Label `Nombre (Código)`. |
| `commerce_product_masters` | `commerce_product_master` | Solo activos; label `#N - Nombre`. |
| `commerce_physical_conditions` | Enum estático | `OPERATIONAL`, `DAMAGED_SCRAP`, `FOR_PARTS`, `INCOMPLETE`, `REPAIRED`. |
| `commerce_product_statuses` | Enum estático | `AVAILABLE`, `SOLD_OUT`, `SCRAPPED` (además de `RESERVED`, expuesto por catálogo pero no generado automáticamente por el backend actual). |
| `commerce_sales_channels` | `commerce_channel` | Solo canales activos. |
| `commerce_payment_methods` | Enum estático | `QR`, `CASH`, `TRANSFER`, `COURTESY`. |
| `commerce_payment_statuses` | Enum estático | `COLLECTED`, `PENDING`, `COURTESY`, `REFUNDED`. |
| `commerce_delivery_modalities` | Enum estático | `FREE_MEETING_POINT`, `HOME_DELIVERY`, `TERMINAL_BUS`, `NATIONAL_COURIER`, `STORE_PICKUP`, `PARCEL_SERVICE`. |
| `commerce_delivery_paid_by` | Enum estático | `FREE`, `CUSTOMER`, `STORE`. |
| `commerce_delivery_statuses` | Enum estático | `DELIVERED`, `PENDING`. |

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
- `search`: Búsqueda multi-campo insensible a mayúsculas (`"53"`, `"#53"`, `"NOV-053"`, `"reloj"`, `"almohadilla"`). Busca en `code`, `name`, `brand`, `model`, `description` y `features`.
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
    "code": null,
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
    "cover_image_url": "https://pub-cdn.empresa.com/products/053/cover.webp",
    "marketplace_url": "https://www.facebook.com/marketplace/item/123456789/",
    "external_info_url": "https://www.amazon.com/dp/B08XYZ123",
    "features": "- **Fuente de Energía:** Enchufe 220V\n- **Instrucciones:** 1. Conectar cable. 2. Regular temperatura...",
    "marketing_details": null,
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

### B. Crear Nueva Ficha Maestra (`POST /api/commerce/product-masters/`)

> [!IMPORTANT]
> **Autogeneración Atómica del Identificador:**
> 1. **`item_number`**: **NO debe ser enviado por el frontend**. El backend asigna automáticamente el siguiente correlativo entero atómico (`nextval` en PostgreSQL) sin posibilidad de colisión ni saltos. En la UI del frontend, este campo debe mostrarse como un badge o etiqueta informativa: `Ficha Maestra (Autogenerada)`.
> 2. **`code`**: Es **opcional (`string | null`)**. Está pensado para almacenar el **código de barras** escaneado del producto (EAN-13, UPC) o un SKU de fábrica. Si el producto no tiene código de barras (ej. viene en bolsa sellada sin etiqueta), debe enviarse como `null` o vaciarse.
> 3. **`description`**: Breve resumen comercial (1-2 párrafos) para tarjetas web y catálogo PWA.
> 4. **`features`**: Viñetas con especificaciones técnicas, modo de uso y cuidados en formato Markdown.
> 5. **`marketing_details`**: Guion de venta rápida / TikTok Live (opcional, para copys de venta).

#### Petición (Creación limpia):
```http
POST /api/commerce/product-masters/
Content-Type: application/json
```
```json
{
  "name": "Cámara Exterior PTZ 4G Solar",
  "code": "7751234567890",
  "description": "Cámara de seguridad autónoma con panel solar y conectividad SIM 4G.",
  "features": "- **Fuente de Energía:** Panel Solar + Batería 18650\n- **Instrucciones:** 1. Insertar chip SIM...",
  "marketing_details": "Enfatizar que no requiere WiFi ni electricidad. Ideal para fincas y depósitos.",
  "category_id": "01a1b8dc-dd82-73cb-8e37-99fb5265bd0e",
  "official_price": 550.0,
  "minimum_price": 480.0,
  "published_price": 520.0,
  "currency": "BOB"
}
```

> **Enlaces iniciales opcionales:** `marketplace_url` y `external_info_url` pueden enviarse en la
> creación. El backend los convierte automáticamente en `commerce_product_master_external_link`
> (`MARKETPLACE` / `REFERENCE`, primarios) con **`is_public=True` forzado**. No uses estos campos
> para URLs de proveedores mayoristas o información confidencial: para eso usa
> `POST /api/commerce/product-masters/{id}/links` con `is_public: false`.

### C. Actualizar Ficha Maestra (`PUT /api/commerce/product-masters/{id}`)

* **`item_number`**: **Es inmutable**. No se puede modificar una vez creada la ficha.
* **`cover_image_url`**: **Es de solo lectura**. No se edita por este endpoint ni se escribe a mano; se sincroniza automáticamente desde la galería multimedia (`/images`) mediante la subida de fotos o el botón "Fijar como portada" para garantizar consistencia total con Cloudinary.
* **`code`**: Se puede actualizar con un nuevo código de barras o limpiar a `null`.

```http
PUT /api/commerce/product-masters/01a1c785-02b3-7641-bb12-9988aa112233
Content-Type: application/json
```
```json
{
  "official_price": 190.0,
  "minimum_price": 150.0,
  "code": "0848061058498"
}
```

### D. Obtener Total de Fichas Maestras
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

### E. Obtener por Número Numérico Directo
```http
GET /api/commerce/product-masters/by-number/53
```

### F. Resolver Flexiblemente por Número, Código o SKU
```http
GET /api/commerce/product-masters/resolve/NOV-053
GET /api/commerce/product-masters/resolve/53
GET /api/commerce/product-masters/resolve/7751234567890
```

---

## 📸 3. Gestión Multi-Fotografía y Galería Multimedia (`/api/commerce/product-masters/{id}/images`)

El sistema cuenta con un motor completo de multi-fotografía conectado a Cloudinary con compresión WebP automática, categorización por tipo y carpetas estructuradas.

### A. Estructura de Carpetas en Cloudinary
Las imágenes se guardan de forma aislada y ordenada:
```
uyuni/products/{item_number}/{image_type}/
```
- **`CATALOG`** (`uyuni/products/242/catalog/`): Fotos de alta calidad para e-commerce / PWA y catálogo web (editadas, fondo blanco o ambientadas).
- **`REAL`** (`uyuni/products/242/real/`): Fotos tomadas en almacén (unboxing, producto real, estado físico) para consultas de clientes.
- **`MARKETING`** (`uyuni/products/242/marketing/`): Creativos para redes sociales generados por NovaBox (TikTok, Facebook, historias).
- **`BANNER`** (`uyuni/products/242/banner/`): Creativos panorámicos o banners publicitarios.

---

### B. Subida Masiva de Fotografías (Drag & Drop)
Soporta subir de 1 a 10+ fotos simultáneamente en una sola llamada multipart:

```http
POST /api/commerce/product-masters/{id}/images
Content-Type: multipart/form-data
```

#### Parámetros del Formulario (`multipart/form-data`):
- `files`: Lista de archivos binarios (JPG, PNG, WEBP, GIF, AVIF, máx 10 MB por archivo).
- `image_type`: `"CATALOG"` (default), `"REAL"`, `"MARKETING"`, o `"BANNER"`.
- `is_cover`: `true` | `false`. Solo las imágenes `CATALOG` pueden ser portada. Si es `true`, o si la
  ficha aún no tiene portada `CATALOG`, la primera imagen de esta tanda se asigna como portada.
- `product_id`: `UUID | null` (opcional: si se desea vincular la foto a una unidad física específica de lote).

#### Ejemplo de Respuesta:
```json
[
  {
    "id": "01a1c787-1234-5678-90ab-cdef12345678",
    "product_master_id": "01a1c785-02b3-7641-bb12-9988aa112233",
    "product_id": null,
    "url": "https://res.cloudinary.com/novalabs-bo/image/upload/v1794590000/uyuni/products/53/catalog/IMG_01.webp",
    "public_id": "uyuni/products/53/catalog/IMG_01",
    "image_type": "CATALOG",
    "title": "IMG_01.jpg",
    "original_filename": "IMG_01.jpg",
    "file_size_bytes": 145890,
    "width": 1200,
    "height": 1200,
    "format": "webp",
    "is_cover": true,
    "sort_order": 1,
    "created_at": "2026-11-13T16:00:00Z",
    "updated_at": "2026-11-13T16:00:00Z"
  }
]
```

---

### C. Listar Galería de la Ficha Maestra
```http
GET /api/commerce/product-masters/{id}/images?image_type=CATALOG
```
Retorna todas las imágenes ordenadas por `sort_order ASC, created_at ASC`.

> [!NOTE]
> Al consultar la Ficha Maestra individual (`GET /api/commerce/product-masters/{id}` o `/by-number/{item_number}`), la respuesta ya incluye directamente el arreglo `images: list[ProductImageRead]` y el contador `images_count: int`.

---

### D. Definir Fotografía como Portada Oficial
```http
PATCH /api/commerce/product-masters/{id}/images/{image_id}/cover
```
Marca la imagen seleccionada como `is_cover=True`, desmarca las demás y sincroniza automáticamente `ProductMaster.cover_image_url`.

---

### E. Reordenar Imágenes (Drag & Drop)
Para guardar el nuevo orden tras arrastrar imágenes en la interfaz de Angular/PrimeNG:
```http
PUT /api/commerce/product-masters/{id}/images/reorder
Content-Type: application/json
```
```json
[
  { "id": "01a1c787-1234-5678-90ab-cdef12345678", "sort_order": 1 },
  { "id": "01a1c787-9999-5678-90ab-cdef12345678", "sort_order": 2 }
]
```

---

### F. Actualizar Metadatos de Imagen
```http
PATCH /api/commerce/product-masters/{id}/images/{image_id}
Content-Type: application/json
```
```json
{
  "title": "Fotografía en ángulo de 45°",
  "image_type": "CATALOG"
}
```

---

### G. Eliminar Fotografía
```http
DELETE /api/commerce/product-masters/{id}/images/{image_id}
```
Elimina el archivo físico de Cloudinary (usando su `public_id`) y el registro de la base de datos. Si la foto eliminada era la portada oficial, el backend reasigna automáticamente la siguiente foto disponible como portada.

---

### H. Ejemplo de Implementación en PrimeNG 21 (Angular)
```html
<!-- Subida Masiva con Drag & Drop en pestaña Marketing y Redes -->
<p-fileupload 
    mode="advanced" 
    name="files" 
    [url]="uploadUrl" 
    [multiple]="true" 
    accept="image/*" 
    maxFileSize="10485760"
    (onUpload)="onUploadSuccess($event)">
</p-fileupload>

<!-- Galería con badges y acciones (control flow nativo de Angular 21) -->
<div class="grid grid-cols-4 gap-4 mt-4">
  @for (img of master.images; track img.id) {
    <div class="relative group border rounded-lg overflow-hidden">
      <img [src]="img.url" [alt]="img.title" class="w-full h-36 object-cover" />
      @if (img.is_cover) {
        <span class="absolute top-2 left-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full font-bold">
          Portada
        </span>
      }
      <span class="absolute top-2 right-2 bg-slate-800/80 text-white text-xs px-1.5 py-0.5 rounded">
        {{ img.image_type }}
      </span>
      <div class="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        @if (!img.is_cover) {
          <button (click)="setAsCover(img)" class="p-button-sm p-button-secondary" title="Fijar como portada">★</button>
        }
        <button (click)="deleteImage(img)" class="p-button-sm p-button-danger" title="Eliminar">🗑</button>
      </div>
    </div>
  }
</div>
```

---

### I. Extracción e Importación de Imágenes Externas (Scraping)

**1. Previsualizar imágenes de una URL** (Amazon, eBay, Alibaba o web genérica):

```http
POST /api/commerce/product-masters/{id}/images/scrape-preview
Content-Type: application/json
```
```json
{ "url": "https://www.amazon.com/dp/B08XYZ123" }
```
```json
{
  "source_url": "https://www.amazon.com/dp/B08XYZ123",
  "platform": "AMAZON",
  "images": [
    { "url": "https://m.media-amazon.com/images/I/...jpg", "thumbnail_url": null, "width": 1600, "height": 1600, "alt": null }
  ],
  "warning": null
}
```

**2. Importar las imágenes seleccionadas a Cloudinary** (servidor-a-servidor):

```http
POST /api/commerce/product-masters/{id}/images/import-external
Content-Type: application/json
```
```json
{
  "image_urls": ["https://m.media-amazon.com/images/I/...jpg"],
  "image_type": "CATALOG",
  "set_first_as_cover": true
}
```

**3. Eliminación masiva atómica** (también disponible para la ficha maestra):

```http
POST /api/commerce/product-masters/{id}/images/bulk-delete
Content-Type: application/json
```
```json
{ "image_ids": ["01a1d6b6-bb2c-7326-9164-1b3172dc5669"] }
```

---

## 🔗 3.1 Gestión de Enlaces Externos y Publicaciones de Marketplace (`/api/commerce/product-masters/{id}/links`)

Permite almacenar tanto enlaces de portales internacionales de referencia técnica (Amazon UK, Amazon ES, eBay, Alibaba, AliExpress, Walmart, MercadoLibre, YouTube, TikTok, etc.) como publicaciones comerciales propias activas (Facebook Marketplace, MercadoLibre propio, TikTok Shop, etc.). Soporta múltiples publicaciones por producto (por ejemplo, publicaciones simultáneas de diferentes miembros del equipo como Liz y Henry).

### 🏷️ Tipos de Enlace (`link_type`)
- **`REFERENCE`** (default): Enlaces de especificaciones técnicas, videos, reseñas y fichas de fabricantes o proveedores mayoristas.
- **`MARKETPLACE`**: Enlaces directos a publicaciones de venta comercial activas en Facebook Marketplace, MercadoLibre, grupos de venta, etc.
  - Al agregar un enlace de tipo `MARKETPLACE`, el sistema activa automáticamente `is_published_marketplace = true` en la ficha maestra.

### 🧠 Clasificación Automática de la Industria (Zero-Boilerplate)
**El usuario NO necesita seleccionar el portal de una lista desplegable**: Al pegar cualquier URL externa, el backend analiza la estructura del enlace y clasifica automáticamente el portal y la etiqueta amigable:
- `https://www.facebook.com/marketplace/item/...` ➔ `portal: "FACEBOOK"`, `label: "Facebook Marketplace"`
- `https://www.amazon.co.uk/...` ➔ `portal: "AMAZON"`, `label: "Amazon UK"`
- `https://www.amazon.es/...` ➔ `portal: "AMAZON"`, `label: "Amazon España"`
- `https://www.ebay.com/...` ➔ `portal: "EBAY"`, `label: "eBay"`
- `https://spanish.alibaba.com/...` ➔ `portal: "ALIBABA"`, `label: "Alibaba"`
- `https://es.aliexpress.com/...` ➔ `portal: "ALIEXPRESS"`, `label: "AliExpress"`
- `https://www.walmart.com/...` ➔ `portal: "WALMART"`, `label: "Walmart"`
- `https://articulo.mercadolibre...` ➔ `portal: "MERCADOLIBRE"`, `label: "MercadoLibre"`
- `https://www.youtube.com/...` ➔ `portal: "YOUTUBE"`, `label: "YouTube"`
- `https://www.tiktok.com/...` ➔ `portal: "TIKTOK"`, `label: "TikTok"`
- Cualquier otro dominio ➔ `portal: "OTHER"`, `label: "<Dominio>"`

El usuario puede opcionalmente sobrescribir el `label` con etiquetas operativas clave (ej: *"Marketplace - Liz (La Paz)"*, *"Marketplace - Henry (Central)"*, *"Alibaba Proveedor Directo"*).

---

### A. Agregar Enlace Externo / Publicación
```http
POST /api/commerce/product-masters/{id}/links
Content-Type: application/json
```
```json
{
  "url": "https://www.facebook.com/marketplace/item/999111/",
  "link_type": "MARKETPLACE",
  "label": "Marketplace - Liz (La Paz)",
  "is_primary": true,
  "is_public": true
}
```
*Si es el primer enlace de su tipo (`REFERENCE` o `MARKETPLACE`), se marcará automáticamente como enlace principal de esa categoría y se reflejará en `ProductMaster.external_info_url` o `ProductMaster.marketplace_url`.*  
*Si el enlace es un proveedor mayorista privado (Alibaba, 1688), configurar `is_public: false` para que nunca se exponga en la PWA a clientes.*

#### Ejemplo de Respuesta:
```json
{
  "id": "01932456-789a-7b3c-8d1e-2f3a4b5c6d7e",
  "product_master_id": "019323c0-bf22-77e8-b710-bb2bb4e2baee",
  "url": "https://www.facebook.com/marketplace/item/999111/",
  "portal": "FACEBOOK",
  "link_type": "MARKETPLACE",
  "label": "Marketplace - Liz (La Paz)",
  "is_primary": true,
  "is_public": true,
  "sort_order": 1,
  "created_at": "2026-11-13T18:30:00Z",
  "updated_at": "2026-11-13T18:30:00Z"
}
```

---

### B. Listar Enlaces con Filtros
```http
GET /api/commerce/product-masters/{id}/links?link_type=MARKETPLACE&only_public=false
```
- `link_type`: `'REFERENCE'` o `'MARKETPLACE'` (opcional, sin este parámetro retorna ambos).
- `only_public=true`: Retorna únicamente los enlaces marcados como visibles para clientes (ideal para la PWA de catálogo).
- `only_public=false` (default): Retorna todos los enlaces.

> [!NOTE]
> Al obtener la Ficha Maestra (`GET /api/commerce/product-masters/{id}`), el objeto ya incluye directamente:
> - `reference_links`: Lista de enlaces de referencia técnica (`ProductMasterExternalLinkRead`).
> - `reference_links_count`: Cantidad de enlaces de referencia.
> - `marketplace_links`: Lista de publicaciones comerciales activas (`ProductMasterExternalLinkRead`).
> - `marketplace_links_count`: Cantidad de publicaciones registradas.
> - `external_links`: Todos los enlaces juntos.
> - `external_info_url`: URL del enlace principal de referencia activa.
> - `marketplace_url`: URL de la publicación principal activa en Marketplace.

---

### C. Designar Enlace como Principal
```http
PATCH /api/commerce/product-masters/{id}/links/{link_id}/primary
```
Marca este enlace como `is_primary: true`, desmarca los demás y actualiza inmediatamente la propiedad `external_info_url` de la ficha.

---

### D. Reordenar Enlaces (Drag & Drop)
```http
PUT /api/commerce/product-masters/{id}/links/reorder
Content-Type: application/json
```
```json
[
  { "id": "01932456-789a-7b3c-8d1e-2f3a4b5c6d7e", "sort_order": 1 },
  { "id": "01932456-9999-7b3c-8d1e-2f3a4b5c6d7e", "sort_order": 2 }
]
```

---

### E. Actualizar Metadatos de Enlace
```http
PATCH /api/commerce/product-masters/{id}/links/{link_id}
Content-Type: application/json
```
```json
{
  "label": "Ficha Oficial Proveedor Shenzhen",
  "url": "https://spanish.alibaba.com/p-detail/sample.html",
  "is_public": false
}
```

---

### F. Eliminar Enlace Externo
```http
DELETE /api/commerce/product-masters/{id}/links/{link_id}
```
Si el enlace eliminado era el principal de su categoría (`REFERENCE` o `MARKETPLACE`), el backend promueve automáticamente el siguiente enlace disponible en la secuencia como principal.

---

### G. Implementación UI Recomendada en Angular (PrimeNG 21)

Para mantener la interfaz intuitiva en el diálogo de Ficha Maestra:
1. En la pestaña **"Marketing y Redes"**, separar dos bloques organizados o un sub-tab:
   - **"Publicaciones Activas en Marketplace"** (`marketplace_links`):
     - Muestra un tag con el portal (Facebook / MercadoLibre), la etiqueta asignada (ej. *"Liz - La Paz"*, *"Henry - Central"*), y la fecha de publicación (`created_at`).
     - Botón directo para abrir el enlace en una nueva pestaña del navegador.
     - Botón para designar publicación principal.
     - Formulario rápido: pegar URL, etiqueta (opcional) y botón *"Agregar Publicación"*.
   - **"Referencias y Especificaciones de Fabricante"** (`reference_links`):
     - Muestra los enlaces de Amazon, eBay, Alibaba con badges de portal.
     - Switch de visibilidad pública (`is_public`) para ocultar proveedores mayoristas confidenciales.
     - Estrella para designar el enlace principal de especificaciones.

---

## 🖼️ 3.2 Optimización de Rendimiento con Cloudinary (Transformaciones Dinámicas en Frontend)

Las fotos subidas a Cloudinary se almacenan en resolución original (1600×1600 o 2048×2048). **Nunca se debe renderizar la URL cruda en tablas o miniaturas pequeñas**, ya que consume ancho de banda y ralentiza la aplicación.

### A. Pipe de Angular Reutilizable (`CloudinaryPipe`)
Crear en `src/app/shared/pipes/cloudinary.pipe.ts`:

```typescript
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'cloudinary',
  standalone: true,
})
export class CloudinaryPipe implements PipeTransform {
  transform(
    url: string | null | undefined,
    size: 'thumb' | 'card' | 'zoom' | 'original' = 'card'
  ): string {
    if (!url) return 'assets/images/no-image.png';
    if (!url.includes('cloudinary.com') || size === 'original') return url;

    const transformations: Record<string, string> = {
      // 100x100 px, recorte inteligente centrado en el objeto, auto WebP/AVIF (ideal para tablas)
      thumb: 'w_100,h_100,c_fill,g_auto,q_auto,f_auto',
      // 400x400 px, ajustado proporcionalmente (ideal para tarjetas y galerías modales)
      card: 'w_400,h_400,c_pad,b_white,q_auto,f_auto',
      // 1200 px máx, alta resolución optimizada (para visor a pantalla completa o zoom)
      zoom: 'w_1200,c_limit,q_auto,f_auto',
    };

    return url.replace('/image/upload/', `/image/upload/${transformations[size]}/`);
  }
}
```

### B. Uso en Templates de Angular
```html
<!-- En la tabla de catálogo (miniatura rápida de 48px que pesa ~3 KB en vez de 400 KB) -->
<img [src]="master.cover_image_url | cloudinary:'thumb'" class="w-10 h-10 rounded object-cover shadow-sm" />

<!-- En la galería de fotos del modal de Ficha Maestra -->
<img [src]="img.url | cloudinary:'card'" class="w-full h-44 object-contain rounded" />

<!-- En visor a pantalla completa / zoom -->
<img [src]="selectedImage.url | cloudinary:'zoom'" class="max-h-[85vh] object-contain mx-auto" />
```

---

## 🧾 4. Lotes y Cajas (`/api/commerce/batches`)

`Batch` representa una caja, palet o lote importado. El backend calcula y mantiene:

- `total_cost = purchase_price + freight_cost`
- `sellable_items_count = max(0, initial_items_count - merma_items_count)`
- `unit_cost = total_cost / sellable_items_count` (o `0.0` si no hay vendibles)
- `financial_status`: `EN_RECUPERACION`, `CASI_TABLAS` (≥ 80 % recuperado) o `RECUPERADO`.
- `status`: `active`, `liquidated`, `archived` (operativo).

### A. CRUD

```http
GET    /api/commerce/batches/?offset=0&limit=50&sort_by=code&sort_order=asc&search=amazon
GET    /api/commerce/batches/count?search=amazon
GET    /api/commerce/batches/{id}
POST   /api/commerce/batches/
PUT    /api/commerce/batches/{id}
DELETE /api/commerce/batches/{id}
```

#### Crear lote (payload mínimo)

```json
{
  "name": "Caja Amazon Next",
  "investment_round_id": "019324a1-b8dc-73cb-8e37-99fb5265bd0e",
  "costing_method": "WEIGHTED_RETAIL",
  "purchase_price": 4000.0,
  "freight_cost": 300.0,
  "initial_items_count": 50,
  "merma_items_count": 2,
  "currency": "BOB"
}
```

> `code` es opcional: si se omite, el backend genera `CAJA-01`, `CAJA-02`, etc. Si se envía, se
> normaliza a mayúsculas. `costing_method` canónico: `WEIGHTED_RETAIL`, `SPECIFIC_ITEM`,
> `FLAT_AVERAGE` (los alias `ON_DEMAND`/`WHOLESALE` se tratan como costeo directo por ítem).

> [!IMPORTANT]
> **Protecciones del backend:**
> - `DELETE` se rechaza con `400` si el lote tiene productos asociados.
> - Si el lote ya tiene productos, `PUT` ignora `initial_items_count`, `merma_items_count`,
>   `sellable_items_count`, `unit_cost` y `financial_status`: se derivan de la tabla de productos.
> - `total_cost` nunca se acepta del cliente; siempre se recalcula.

### B. Recalcular conteos y costos desde los productos

```http
POST /api/commerce/batches/{id}/recalculate?revalue_sales=true&force_product_counts=false
```

- `revalue_sales`: revalúa `commerce_sale_item.unit_cost`, `net_margin` y la cabecera de ventas.
- `force_product_counts`: si `true`, sobreescribe los conteos del lote con la suma real de productos.

### C. Prorratear costos relativos (Retail Inventory Method)

```http
POST /api/commerce/batches/{id}/allocate-relative-costs?basis=published_price&revalue_sales=true
```

- `basis`: `published_price` (default), `official_price` o `minimum_price`.
- Excluye productos con `physical_condition = DAMAGED_SCRAP`.
- Reconcilia centavos en el último producto para que la suma de costos iguale `total_cost`.
- Si `revalue_sales=true`, actualiza las ventas históricas del lote.

---

## 🏷️ 5. Inventario Físico por Caja (`/api/commerce/products`)

Representa las existencias físicas reales de cada producto dentro de un lote o caja de importación específica.

### A. Listar Inventario Físico
```http
GET /api/commerce/products/?offset=0&limit=50&batch_id=<uuid>&master_product_id=<uuid>&status=AVAILABLE&search=reloj
```

#### Parámetros Query:
- `offset`: Desplazamiento para paginación (default: `0`).
- `limit`: Cantidad por página (default: `100`, con protección backend clamped entre 1 y 500).
- `sort_by`: Campo de ordenación (`created_at`, `status`, etc.).
- `sort_order`: `'asc'` o `'desc'`.
- `search`: Búsqueda insensible a mayúsculas en `ProductMaster.name`, `ProductMaster.code`,
  `brand`, `model`, `Product.variant_name`, `status`, `physical_condition`, `defect_detail` y
  `#item_number`/`sheet_row_id` numéricos. No busca por código de lote.
- `batch_id`: Filtrar por caja/lote de importación específico.
- `master_product_id`: Filtrar todas las unidades de una ficha maestra en diferentes cajas.
- `status`: Filtrar por estado: `'AVAILABLE'`, `'SOLD_OUT'`, `'SCRAPPED'`.

#### Propiedades Enriquecidas Automáticas (`ProductRead`):
Cada producto físico incluye automáticamente las propiedades calculadas y delegadas de su Ficha Maestra y de su Lote para poblar tablas y tarjetas sin llamadas adicionales:

```json
[
  {
    "id": "01a1c786-1122-3344-5566-778899aabbcc",
    "master_product_id": "01a1c785-02b3-7641-bb12-9988aa112233",
    "batch_id": "01a1b8dc-ddb0-71f4-bbec-6966db6633ef",
    "name": "Aspiradora de Mano Inalámbrica Plegable, Alta Succión, Portátil",
    "item_number": 149,
    "master_code": null,
    "image_url": "https://res.cloudinary.com/test/image/upload/v1/uyuni/products/149/catalog/aud.webp",
    "category_name": "🚗 Accesorios para Autos & Taller",
    "batch_name": "Ataúd 2",
    "batch_code": "BOX-02",
    "currency": "BOB",
    "variant_name": "Color Negro",
    "cost_price": 52.98,
    "published_price": 120.0,
    "minimum_price": 100.0,
    "official_price": 120.0,
    "estimated_margin": 67.02,
    "discount_margin": 20.0,
    "initial_quantity": 1,
    "sold_quantity": 0,
    "merma_quantity": 0,
    "available_quantity": 1,
    "status": "AVAILABLE",
    "physical_condition": "OPERATIONAL",
    "defect_detail": null,
    "is_reviewed": true
  }
]
```

> [!NOTE]
> **Tri-Precio y Rentabilidad:**
> - `published_price`: Precio oficial de venta publicado al público (cotización de entrada).
> - `minimum_price`: Piso mínimo protegido de negociación (no se permite vender por debajo sin autorización).
> - `official_price`: Precio de lista referencial investigado en mercado local (Bolivia).
> - `cost_price`: Costo real unitario asignado.
> - `estimated_margin` = `published_price - cost_price` (Ganancia bruta estimada).
> - `discount_margin` = `published_price - minimum_price` (Margen máximo de rebaja autorizado).

---

### B. Búsqueda Directa por SKU / Código de Barras

```http
GET /api/commerce/products/by-sku/7751234567890
```

Retorna el primer `Product` físico cuyo `ProductMaster.code` coincide. Útil para escaneo en
almacén o POS. Para el conteo paginado usa `GET /api/commerce/products/count` (respuesta:
`{ "total": N }`).

---

### C. Editar Datos y Registrar Merma (`PUT /api/commerce/products/{id}`)

```http
PUT /api/commerce/products/<product_id>
```

#### Reglas de Edición en el Frontend:

| Campo | ¿Editable? | Regla de Negocio / Comportamiento |
| :--- | :---: | :--- |
| `published_price` | ✅ Sí | Permite fijar un precio publicado menor específico para este lote físico (ej. si llegó con empaque abierto). |
| `minimum_price` | ✅ Sí | Piso protegido de regateo para esta unidad física. |
| `cost_price` | ⚠️ Condicional | **Bloqueado** en lotes `WEIGHTED_RETAIL` y `FLAT_AVERAGE` (derivado del lote). **Editable** en `SPECIFIC_ITEM` y alias `ON_DEMAND`/`WHOLESALE`. |
| `initial_quantity`| ✅ Sí | Cantidad física recibida en almacén. |
| `merma_quantity` | ✅ Sí | Cantidad declarada rota o defectuosa. |
| `sold_quantity` | ❌ No | **Solo lectura**: Administrado automáticamente por transacciones atómicas de venta (`commerce_sale_item`). |
| `available_quantity`| ❌ No | **Auto-calculado**: `initial_quantity - sold_quantity - merma_quantity`. |
| `status` | ❌ No | **Auto-calculado**: `AVAILABLE` si `available > 0`; `SOLD_OUT` si `available == 0` y `sold > 0`; `SCRAPPED` si `available == 0` y `sold == 0`. |
| `physical_condition`| ✅ Sí | `OPERATIONAL`, `DAMAGED_SCRAP`, `FOR_PARTS`, `INCOMPLETE`, `REPAIRED`. |
| `defect_detail` | ✅ Sí | Texto descriptivo de la falla, rasguño o accesorio faltante. |
| `is_reviewed` | ✅ Sí | Checkbox de prueba física en mesa de trabajo antes de exhibir. |

```json
{
  "published_price": 110.0,
  "minimum_price": 95.0,
  "merma_quantity": 0,
  "physical_condition": "INCOMPLETE",
  "defect_detail": "Llegó sin cargador USB-C, funciona con cualquier cargador estándar.",
  "is_reviewed": true
}
```

---

### D. Fotografías Reales de Almacén (`/api/commerce/products/{id}/images`)

Permite capturar y adjuntar fotografías reales de desempaque, estado físico o prueba de banco a un producto físico específico. Se almacenan en Cloudinary bajo la jerarquía: `uyuni/products/{item_number}/real/`.

#### 1. Listar Fotos Reales del Producto
```http
GET /api/commerce/products/{id}/images
```

#### 2. Subir Fotos Reales (Multipart)
```http
POST /api/commerce/products/{id}/images
Content-Type: multipart/form-data
```
- `files`: Archivos de imagen (`JPG`, `PNG`, `WEBP`, `AVIF`, máx 10MB).
- `is_public`: (Opcional, `boolean`, default: `false`).
  - `false`: Fotografía privada para uso interno (reclamos, inspección, o para compartir manualmente a clientes por WhatsApp).
  - `true`: Fotografía autorizada para exhibirse en el catálogo público de clientes.

#### 3. Conmutar Visibilidad Pública o Título (`PATCH`)
```http
PATCH /api/commerce/products/{id}/images/{image_id}
Content-Type: application/json
```
```json
{
  "is_public": true,
  "title": "Foto real de unboxing en almacén"
}
```

#### 4. Reordenar Secuencia (Drag & Drop)
```http
PUT /api/commerce/products/{id}/images/reorder
Content-Type: application/json
```
```json
[
  { "id": "01a1d6b6-bb2c-7326-9164-1b3172dc5669", "sort_order": 1 },
  { "id": "01a1d6b6-c249-7110-bde2-688e19332615", "sort_order": 2 }
]
```

#### 5. Eliminar Fotografía Individual
```http
DELETE /api/commerce/products/{id}/images/{image_id}
```
*Destruye el recurso en Cloudinary mediante su `public_id` y remueve el registro de la base de datos.*

#### 6. Eliminación Masiva en Lote (`POST .../bulk-delete`)
> [!TIP]
> **Recomendado para el botón «Eliminar (X)» del frontend:** En lugar de lanzar múltiples peticiones `DELETE` paralelas en `forkJoin`, utiliza este endpoint para eliminar todas las fotos seleccionadas en **una sola llamada HTTP y una sola transacción atómica**.

```http
POST /api/commerce/products/{id}/images/bulk-delete
Content-Type: application/json
```
```json
{
  "image_ids": [
    "01a1d6b6-bb2c-7326-9164-1b3172dc5669",
    "01a1d6b6-c249-7110-bde2-688e19332615"
  ]
}
```
*(También disponible para Fichas Maestras en: `POST /api/commerce/product-masters/{id}/images/bulk-delete`)*

---

## 💰 6. Transacciones de Venta (`/api/commerce/sales`)

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
El backend asigna el **correlativo entero** (`sale_number`) desde
`commerce_sale_sale_number_seq`, asocia el costo unitario del lote, calcula la ganancia neta y
descuenta el stock:

```json
{
  "id": "01a1c787-9988-7766-5544-33221100aabb",
  "sale_number": 30,
  "sale_date": "2026-11-10T20:30:00Z",
  "customer_name": "Gonzalo Morales",
  "customer_phone": "79712345",
  "channel_id": "01a1c1d9-7bd8-7453-a5c3-6bae663dd49e",
  "channel": "TikTok Live",
  "channel_name": "TikTok Live",
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

### C. Consultar y Gestionar Ventas

```http
GET    /api/commerce/sales/?offset=0&limit=50&sort_by=sale_number&sort_order=desc
GET    /api/commerce/sales/count?search=&channel=&payment_status=&delivery_status=
GET    /api/commerce/sales/{id}
PUT    /api/commerce/sales/{id}
DELETE /api/commerce/sales/{id}
```

- Filtros de lista: `search`, `channel`, `payment_status`, `delivery_status`.
- Orden por defecto: `sale_number desc` (más reciente primero).
- `PUT /sales/{id}` puede reemplazar `items`; el servicio devuelve el stock de los ítems anteriores y
  reaplica la venta en una transacción.
- `DELETE /sales/{id}` restaura el stock y recalcula lote/ronda afectados.

### D. Catálogo POS de Productos Disponibles

```http
GET /api/commerce/sales/available-products?search=%2353&limit=50&offset=0
```

`search` admite nombre, código, marca, modelo, variante o `#item_number`. Solo retorna
`status = AVAILABLE` con `available_quantity > 0`. Cada ítem incluye `display_name`,
`batch_code`, `batch_name`, `published_price`, `minimum_price`, `official_price`,
`discount_margin` e `image_url` para pintar la barra del Tri-Precio.

---

## 🎛️ 7. Módulo Unificado de Catálogos y Parámetros (`/commerce/catalogs`)

### 7.1. Estándar de Industria: Separación de Flujo Operativo vs. Catálogos Maestros
En sistemas ERP de clase mundial (Shopify, Stripe, Odoo, SAP), los elementos de la interfaz se dividen en:
1. **Flujo Transaccional Diario (Alta Frecuencia):** Pantallas como Ventas, Productos y Lotes, accesibles directamente desde la barra lateral.
2. **Datos de Referencia y Catálogos (Baja Frecuencia):** Tablas de parametrización como Categorías, Canales de Venta y Canastas Live, que se configuran esporádicamente.

Para evitar saturar la barra lateral con accesos directos (*efecto menú sábana*), el módulo `commerce` implementa el **Unified Catalog Hub Pattern**:
- En la barra lateral se expone **`Catálogos`** (ruta: `commerce/catalogs`, slug: `commerce-catalogs`, icono PrimeIcons `pi pi-sliders-h`). Las Rondas de Inversión se exponen aparte en `/commerce/rounds` por ser el paso 1 del ciclo.
- Al ingresar, la pantalla presenta una interfaz basada en **Pestañas (Cejas / Tabs de PrimeNG 21)** donde cada pestaña gestiona un grupo de datos independiente con su propia tabla y formulario.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Comercio / Catálogos y Parámetros                                     │
├─────────────────┬───────────────────┬──────────────────────────────────┤
│  🏷️ Categorías   │  📢 Canales Venta │  🎥 Canastas Live                │
├─────────────────┴───────────────────┴──────────────────────────────────┤
│                                                [+ Nueva Categoría]     │
│  Buscar categoría: [ Q Buscar... ]                                     │
│                                                                        │
│  Código   Nombre               Icono   Acciones                        │
│  ─────────────────────────────────────────────────────────────         │
│  CAT-01   Hogar & Iluminación    💡    [Editar] [Eliminar]             │
│  CAT-02   Audio & Sonido         🎧    [Editar] [Eliminar]             │
│  CAT-03   Accesorios Auto        🚗    [Editar] [Eliminar]             │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 7.2. Cejas / Pestañas y sus Endpoints de Backend

Cada pestaña ("ceja") en el componente de Angular se conecta a su propio submódulo CRUD en FastAPI.
El módulo de Rondas (independiente del Hub) se documenta al final de esta sección:

#### Ceja 1: Categorías de Producto (`/api/commerce/categories`)
Permite clasificar el catálogo de productos (ej. Electrónica, Iluminación, Hogar, Herramientas):
- **Listar:** `GET /api/commerce/categories/?offset=0&limit=50&search=`
- **Crear:** `POST /api/commerce/categories/` (`code` requerido)
  ```json
  {
    "code": "CAT-10",
    "name": "Electrónica y Audio",
    "icon": "🎧",
    "description": "Auriculares, micrófonos, parlantes y adaptadores bluetooth",
    "typical_products": "Audífonos TWS, barras de sonido, micrófonos"
  }
  ```
- **Editar:** `PUT /api/commerce/categories/{id}`
- **Eliminar:** `DELETE /api/commerce/categories/{id}`

#### Ceja 2: Canales de Venta (`/api/commerce/channels`)
Gestiona los canales comerciales por donde ingresan los pedidos (TikTok Live, Facebook Marketplace, WhatsApp, Tienda Física):
- **Listar:** `GET /api/commerce/channels/?offset=0&limit=50&search=`
- **Crear:** `POST /api/commerce/channels/` (`code` requerido)
  ```json
  {
    "code": "TIKTOK_LIVE",
    "name": "TikTok Live",
    "description": "Ventas directas durante transmisiones de remate en vivo",
    "is_active": true
  }
  ```
- **Editar:** `PUT /api/commerce/channels/{id}`
- **Eliminar:** `DELETE /api/commerce/channels/{id}`

#### Ceja 3: Canastas Live (`/api/commerce/live-baskets`)
Agrupaciones temáticas de productos para subastas en vivo (`C1` Taller & Auto, `C2` Cables &
Regletas, `C3` Hogar & Cocina, `C4` Salud & Belleza, `C+1` Flash, `FONDO`/`NONE` sin canasta):
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

#### Módulo: Rondas de Inversión (`/api/commerce/rounds`)

Gestión y control de fondos de inversión, aportes de capital y retorno financiero (Break-Even).

> [!NOTE]
> **Ubicación en UI y Arquitectura:**  
> La Ronda es el **Paso 1 del ciclo de vida** (Ronda → Lotes → Productos → Ventas). Por ello el
> `manifest.py` la expone como **módulo propio** en la barra lateral: `/commerce/rounds`
> (`pi pi-chart-line`, orden 1). El Hub de Catálogos (`/commerce/catalogs`) queda para categorías,
> canales y canastas Live. Si tu frontend conserva una pestaña heredada de Rondas dentro de
> Catálogos, puede seguir consumiendo los mismos endpoints.

##### Endpoints y Contrato de API:

- **1. Listar Rondas (con paginación, búsqueda y orden):**
  ```http
  GET /api/commerce/rounds/?offset=0&limit=50&sort_by=code&sort_order=asc&search=bazar
  ```
  **Respuesta:**
  ```json
  [
    {
      "id": "019324a1-b8dc-73cb-8e37-99fb5265bd0e",
      "code": "RND-04",
      "name": "Ronda 4 (Campaña Fin de Año)",
      "disbursement_date": "2026-11-01",
      "capital_invested": 2250.0,
      "currency": "BOB",
      "status": "ACTIVE",
      "observations": "Campaña de liquidación navideña y bazar familiar"
    }
  ]
  ```
  > `InvestmentRoundRead` expone `id`, `code`, `name`, `disbursement_date`, `capital_invested`,
  > `currency`, `status` y `observations`. No incluye `created_at`/`updated_at`; si el frontend los
  > necesita para auditoría, debe solicitarlos a un endpoint de auditoría o extender el schema.

- **2. Crear Ronda de Inversión:**
  ```http
  POST /api/commerce/rounds/
  ```
  ```json
  {
    "code": "RND-05",
    "name": "Ronda 5 (Bazar Cosas Usadas y Artesanías)",
    "disbursement_date": "2026-11-14",
    "capital_invested": 0.0,
    "currency": "BOB",
    "status": "ACTIVE",
    "observations": "Ronda abierta para bazar familiar a costo cero y consignaciones"
  }
  ```
  *Nota:* `code` es opcional; si se omite, el backend genera `RONDA-01`, `RONDA-02`, etc.
  `capital_invested` puede crearse en `0.0` y se sincronizará automáticamente cuando se vinculen
  lotes o se recalculen productos. `status` por defecto es `ACTIVE`.

- **3. Conteo de Rondas:**
  ```http
  GET /api/commerce/rounds/count?search=bazar
  ```
  **Respuesta:** `{ "total": N }`

- **4. Obtener Detalle por ID:**
  ```http
  GET /api/commerce/rounds/{id}
  ```

- **5. Actualizar Ronda:**
  ```http
  PUT /api/commerce/rounds/{id}
  ```
  ```json
  {
    "name": "Ronda 5 - Actualizada",
    "status": "LIQUIDATED",
    "observations": "Ronda totalmente liquidada con ganancia"
  }
  ```

- **6. Eliminar Ronda (con Validación de Seguridad Obligatoria):**
  ```http
  DELETE /api/commerce/rounds/{id}
  ```
  > [!IMPORTANT]
  > **Regla de Integridad Referencial:**
  > - **Si la ronda tiene 0 lotes asociados:** La eliminación procede limpiamente retornando HTTP `200 OK`:
  >   `{ "message": "Investment round deleted successfully" }`.
  > - **Si la ronda tiene 1 o más lotes asociados (`commerce_batch`):** El backend **rechaza** la eliminación con HTTP `400 Bad Request` para proteger la trazabilidad financiera:
  >   ```json
  >   {
  >     "detail": "No se puede eliminar la ronda 'Ronda 4' (RND-04) porque tiene 2 lote(s) asociado(s). Desvincule o elimine los lotes primero."
  >   }
  >   ```
  > El Frontend debe capturar `err?.error?.detail` y mostrarlo directamente en un Toast de alerta roja (`severity: 'error'`).

- **7. Consultar Métricas Financieras y Break-Even en Tiempo Real:**
  ```http
  GET /api/commerce/rounds/{id}/metrics
  ```
  **Respuesta Enriquecida:**
  ```json
  {
    "round_id": "019324a1-b8dc-73cb-8e37-99fb5265bd0e",
    "code": "RND-04",
    "name": "Ronda 4 (Campaña Fin de Año)",
    "status": "IN_RECOVERY",
    "capital_invested": 2250.0,
    "capital_recovered": 1400.0,
    "net_profit": -850.0,
    "break_even_progress_percent": 62.22,
    "is_break_even": false,
    "batches_count": 2,
    "total_items": 45,
    "available_items": 20,
    "sold_items": 23,
    "merma_items": 2
  }
  ```
  **Estados Financieros Posibles (`status`):**
  - `"ACTIVE"`: Ronda recién creada sin recaudación de ventas aún.
  - `"IN_RECOVERY"`: Recuperación iniciada pero aún por debajo del 80 % del capital invertido.
  - `"NEAR_BREAKEVEN"`: Próximo al equilibrio ($\ge 80\%$ y $< 100\%$ recuperado).
  - `"RECOVERED"`: **Punto de equilibrio alcanzado** ($\ge 100\%$ recuperado; toda venta posterior es ganancia pura).
  - `"LIQUIDATED"`: Capital recuperado y **todo el inventario vendido** (`available_items == 0`).

- **8. Forzar Recálculo Manual:**
  ```http
  POST /api/commerce/rounds/{id}/recalculate
  ```

---

##### Modelos e Interfaces TypeScript Recomendados:

```typescript
export interface CommerceRound {
  id: string;
  code: string;
  name: string;
  disbursement_date: string | null;
  capital_invested: number;
  currency: string;
  status: 'ACTIVE' | 'IN_RECOVERY' | 'NEAR_BREAKEVEN' | 'RECOVERED' | 'LIQUIDATED';
  observations: string | null;
}

export interface CommerceRoundCreate {
  code?: string; // Si se omite, el backend genera RONDA-XX
  name: string;
  disbursement_date?: string | null;
  capital_invested?: number;
  currency?: string;
  status?: string;
  observations?: string | null;
}

export interface CommerceRoundMetrics {
  round_id: string;
  code: string;
  name: string;
  status: string;
  capital_invested: number;
  capital_recovered: number;
  net_profit: number;
  break_even_progress_percent: number;
  is_break_even: boolean;
  batches_count: number;
  total_items: number;
  available_items: number;
  sold_items: number;
  merma_items: number;
}
```

---

##### Estado Actual del Menú Lateral

Rondas de Inversión **ya está promovido** en `app/modules/commerce/manifest.py` como módulo
independiente. No se requiere configuración adicional en el backend:

```python
ModuleDefinition(
    name="Rondas de Inversión",
    slug="investment-rounds",
    description="Fondos de inversión, aportes de capital y punto de equilibrio",
    group_slug="commerce",
    sort_order=1,  # Paso 1 antes de Lotes
    icon="pi pi-chart-line",
    route="commerce/rounds",
    is_active=True,
)
```

En Angular solo debes asegurar la ruta `commerce/rounds` en `commerce.routes.ts`, protegida por
`authGuard`, y consumir los endpoints `/api/commerce/rounds`.

---

### 7.3. Implementación Estándar en Angular 21 (PrimeNG 21 Tabs)

Ejemplo de implementación recomendada para `CommerceCatalogsComponent` (`src/app/features/commerce/pages/catalogs`):

```html
<div class="card p-6">
  <div class="flex items-center gap-3 mb-6">
    <svg lucideSlidersHorizontal size="28" class="text-brand-500"></svg>
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Catálogos de Comercio</h1>
      <p class="text-sm text-gray-500">Gestión de categorías, canales comerciales y canastas Live</p>
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
    </p-tabpanels>
  </p-tabs>
</div>
```


