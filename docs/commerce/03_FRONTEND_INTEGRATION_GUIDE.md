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
- `is_cover`: `true` | `false` (si es `true`, o si la ficha aún no tiene foto de portada, la primera imagen de esta tanda se asigna automáticamente como portada oficial).
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

<!-- Galería con badges y acciones -->
<div class="grid grid-cols-4 gap-4 mt-4">
  <div *ngFor="let img of master.images" class="relative group border rounded-lg overflow-hidden">
    <img [src]="img.url" [alt]="img.title" class="w-full h-36 object-cover" />
    <span *ngIf="img.is_cover" class="absolute top-2 left-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full font-bold">
      Portada
    </span>
    <span class="absolute top-2 right-2 bg-slate-800/80 text-white text-xs px-1.5 py-0.5 rounded">
      {{ img.image_type }}
    </span>
    <div class="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button *ngIf="!img.is_cover" (click)="setAsCover(img)" class="p-button-sm p-button-secondary" title="Fijar como portada">★</button>
      <button (click)="deleteImage(img)" class="p-button-sm p-button-danger" title="Eliminar">🗑</button>
    </div>
  </div>
</div>
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

## 🏷️ 4. Inventario Físico por Caja (`/api/commerce/products`)
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

## 💰 5. Transacciones de Venta (`/api/commerce/sales`)

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

## 🎛️ 6. Módulo Unificado de Catálogos y Parámetros (`/commerce/catalogs`)

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

Gestión y control de fondos de inversión, aportes de capital y retorno financiero (Break-Even).

> [!NOTE]
> **Ubicación en UI y Arquitectura:**  
> Por diseño del sistema (*Unified Catalog Hub Pattern*), las Rondas de Inversión se gestionan actualmente dentro del módulo **Catálogos** (`/commerce/catalogs`), en la **pestaña 4 ("Rondas de Inversión")**, para evitar saturar la barra lateral con catálogos auxiliares.  
> Sin embargo, dado que en la operativa comercial la Ronda es el **Paso 1 del ciclo de vida** (Ronda $\rightarrow$ Lotes $\rightarrow$ Productos $\rightarrow$ Ventas), esta guía detalla tanto el uso dentro del Hub de Catálogos como los pasos para promoverlo a un módulo independiente en el Sidebar si el equipo de Frontend/Producto así lo requiere.

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
      "observations": "Campaña de liquidación navideña y bazar familiar",
      "created_at": "2026-11-01T10:00:00Z",
      "updated_at": "2026-11-14T10:30:00Z"
    }
  ]
  ```

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
  *Nota:* `capital_invested` puede crearse en `0.0`. Se sincronizará automáticamente cuando se vinculen lotes o se recalculen productos.

- **3. Obtener Detalle por ID:**
  ```http
  GET /api/commerce/rounds/{id}
  ```

- **4. Actualizar Ronda:**
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

- **5. Eliminar Ronda (con Validación de Seguridad Obligatoria):**
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

- **6. Consultar Métricas Financieras y Break-Even en Tiempo Real:**
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
  - `"IN_RECOVERY"`: En proceso de recuperación de capital ($< 80\%$ del capital recuperado).
  - `"NEAR_BREAKEVEN"`: Próximo al equilibrio ($\ge 80\%$ y $< 100\%$ recuperado).
  - `"RECOVERED"`: **Punto de equilibrio alcanzado** ($\ge 100\%$ recuperado; toda venta posterior es ganancia pura).
  - `"LIQUIDATED"`: Capital recuperado y **todo el inventario vendido** (`available_items == 0`).

- **7. Forzar Recálculo Manual:**
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
  created_at: string;
  updated_at: string;
}

export interface CommerceRoundCreate {
  code: string;
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

##### Guía para Promover "Rondas de Inversión" al Menú Lateral (Sidebar)

Si el equipo de Frontend y Producto decide que las Rondas de Inversión deben tener su propio botón directo en el Menú Lateral (`/commerce/rounds`), se deben seguir estos 3 pasos:

1. **Registrar el submódulo en el Manifiesto Backend (`app/modules/commerce/manifest.py`):**
   ```python
   ModuleDefinition(
       name="Rondas de Inversión",
       slug="investment-rounds",
       description="Control de aportes de capital, lotes asociados y punto de equilibrio",
       group_slug="commerce",
       sort_order=1,  # Paso 1 antes de Lotes
       icon="pi pi-chart-line",
       route="commerce/rounds",
       is_active=True,
   )
   ```
2. **Definir la Ruta en Angular (`src/app/features/commerce/commerce.routes.ts`):**
   ```typescript
   {
     path: 'rounds',
     loadChildren: () => import('./rounds/rounds.routes').then(m => m.ROUNDS_ROUTES),
     canActivate: [authGuard]
   }
   ```
3. **Consumir los Servicios:** Reutilizar el servicio existente `CommerceCatalogService` o crear un `RoundService` dedicado consumiendo los endpoints `/api/commerce/rounds`.

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


