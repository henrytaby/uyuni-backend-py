# 01. Arquitectura y Reglas de Negocio — Commerce

Este documento describe la arquitectura interna, los patrones de diseño y las reglas de negocio críticas implementadas en el módulo `commerce` de **Uyuni Backend**.

---

## 🏛️ Patrón Arquitectónico (DDD-Lite + Clean Architecture)

El módulo sigue una arquitectura desacoplada y orientada al dominio (DDD-Lite) donde cada submódulo encapsula su responsabilidad respetando el principio de inversión de dependencias:

```mermaid
flowchart TD
    Client["Cliente HTTP (Angular / React PWA)"] --> Routers["Routers Layer (app/modules/commerce/*/routers.py)"]
    
    subgraph CommerceDomain ["Dominio Commerce (Ecosistema Comercial)"]
        Routers --> Services["Services Layer (app/modules/commerce/*/service.py)"]
        Services --> Repositories["Repositories Layer (app/modules/commerce/*/repository.py)"]
        Repositories --> Models["Models Layer (app/modules/commerce/*/models.py)"]
        
        Services -.->|Valida| BusinessRules["Reglas de Negocio (Piso Regateo, Mermas, Costos)"]
        Repositories -.->|Hereda de| BaseRepo["BaseRepository genérico"]
    end
    
    Models --> DB[("PostgreSQL / SQLite")]

    classDef clientNode fill:#f0f9ff,stroke:#00b4d8,stroke-width:2px,color:#003865,font-weight:bold;
    classDef routerNode fill:#002b49,stroke:#00b4d8,stroke-width:2px,color:#ffffff,font-weight:bold;
    classDef serviceNode fill:#003865,stroke:#00c2cb,stroke-width:2px,color:#ffffff;
    classDef repoNode fill:#004889,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef ruleNode fill:#f8fafc,stroke:#00b4d8,stroke-width:1.5px,color:#003865;
    classDef dbNode fill:#002b49,stroke:#00c2cb,stroke-width:2.5px,color:#ffffff,font-weight:bold;

    class Client clientNode;
    class Routers routerNode;
    class Services serviceNode;
    class Repositories,Models repoNode;
    class BusinessRules,BaseRepo ruleNode;
    class DB dbNode;
```

### Responsabilidades por Capa:

1. **Routers (`routers.py`):**
   - Manejo de solicitudes y respuestas HTTP.
   - Seguridad mediante dependencias de FastAPI: validación de tokens JWT y permisos RBAC (`PermissionChecker`).
   - Serialización y deserialización a través de esquemas Pydantic v2 (`ProductRead`, `SaleCreate`, etc.).
   - No contienen lógica de negocio ni consultas de base de datos directas.

2. **Services (`service.py`):**
   - Encapsulan toda la lógica de negocio y las reglas de dominio.
   - Coordinan transacciones atómicas (por ejemplo, registrar una venta y descontar stock simultáneamente).
   - Recalculan costos y puntos de equilibrio de lotes de importación.
   - Lanzan excepciones de negocio tipadas (`BadRequestException`, `NotFoundException`).

3. **Repositories (`repository.py`):**
   - Heredan de `BaseRepository[T]`.
   - Aíslan el acceso a datos y encapsulan queries ORM complejas.
   - Implementan búsqueda global multi-campo insensible a mayúsculas (`_apply_search` con joins optimizados).

4. **Models (`models.py`):**
   - Entidades de base de datos declaradas con SQLModel.
   - Heredan de `BaseModel` (que provee UUIDv7 como clave primaria) y `AuditMixin` (captura automática de fechas y usuario creador/modificador).

---

## 💡 Decisión de Diseño Clave: Ficha Maestra vs. Inventario por Lote

Uno de los mayores refinamientos de este backend fue la **separación estricta entre la Ficha Comercial Maestra y el Inventario Físico por Caja**:

```mermaid
classDiagram
    class ProductMaster {
        +UUID id
        +int item_number (1..242)
        +str code ("53", "NOV-053")
        +str name ("Almohadilla Térmica Eléctrica")
        +UUID category_id
        +UUID live_basket_id
        +float official_price (180.0)
        +float minimum_price (140.0)
        +float published_price (160.0)
        +str cover_image_url
        +str external_info_url (computed)
        +str marketplace_url (computed)
        +bool is_reviewed
        +bool is_published_marketplace
    }

    class Product {
        +UUID id
        +UUID master_product_id
        +UUID batch_id
        +str variant_name ("Modelo TK-HP2412")
        +float cost_price (80.0)
        +int initial_quantity (1)
        +int sold_quantity (0)
        +int merma_quantity (0)
        +int available_quantity (1)
        +str status ("AVAILABLE")
        +str physical_condition ("OPERATIONAL")
    }

    class Batch {
        +UUID id
        +str code ("ATAUD-02")
        +float purchase_price
        +float freight_cost
        +float unit_cost
    }

    class ProductMasterImage {
        +UUID id
        +UUID product_master_id
        +UUID product_id
        +str url
        +str public_id
        +str image_type ("CATALOG", "REAL", "MARKETING", "BANNER")
        +str title
        +str original_filename
        +int file_size_bytes
        +int width
        +int height
        +str format ("webp")
        +bool is_cover
        +int sort_order
    }

    class ProductMasterExternalLink {
        +UUID id
        +UUID product_master_id
        +str url
        +str portal ("AMAZON", "EBAY", "ALIBABA", "ALIEXPRESS", "WALMART", "MERCADOLIBRE", "FACEBOOK", "TIKTOK", "OTHER")
        +str link_type ("REFERENCE", "MARKETPLACE")
        +str label ("Amazon UK", "Facebook Marketplace - Liz", "Marketplace - Henry")
        +bool is_primary
        +bool is_public
        +int sort_order
    }

    ProductMaster "1" <-- "*" Product : Referencia de Identidad y Precios
    Batch "1" <-- "*" Product : Procedencia y Costo Físico
    ProductMaster "1" <-- "*" ProductMasterImage : Galería Multimedia y Creativos de Catálogo
    ProductMaster "1" <-- "*" ProductMasterExternalLink : Enlaces de Referencia y Publicaciones en Marketplace
```

### Justificación de Negocio:
1. **El mismo producto puede llegar en diferentes lotes a diferentes costos:** Por ejemplo, la *Almohadilla Térmica* (#53) llegó tanto en la caja `Digital` (fila 53 del Excel original) como en el lote `Ataúd 2` (fila 165). En el modelo anterior, esto obligaba a duplicar la ficha comercial o a sobreescribir los costos.
2. **Coherencia con el Almacén de Medios y Marketing:** En el repositorio o CDN de activos comerciales, cada carpeta o identificador representa un producto comercial (`053-almohadilla-termica-electrica/`) que almacena fotos WebP, videos, investigación y guiones publicitarios. La tabla `commerce_product_master` es el espejo exacto en base de datos de esta estructura intelectual.
3. **Existencias Consolidadas vs. Trazabilidad Física:** Cuando el cliente consulta el catálogo en la PWA o el streamer revisa su canasta en vivo, le interesa saber que hay **2 unidades disponibles en total** (#53). Cuando el operador empaqueta el pedido en almacén, necesita saber exactamente **de qué caja física extraer la unidad** y cuál fue su costo real.

---

## ⚖️ Reglas de Negocio Críticas

### 1. Piso Mínimo de Regateo (`minimum_price`)
- **Regla:** En Bolivia, la venta por Marketplace y streaming implica una alta tasa de regateo por parte de los clientes. Cada producto maestro tiene un `official_price` (precio de lista), un `published_price` (precio en publicidad) y un `minimum_price` (piso absoluto de seguridad que garantiza margen neto positivo).
- **Control en `SaleService`:**
  ```python
  if product.minimum_price > 0 and item_data.unit_price < product.minimum_price and not data.allow_below_minimum:
      raise BadRequestException(
          detail=f"Precio pactado ({item_data.unit_price}) menor al mínimo ({product.minimum_price}) para '{product.name}'. Requiere autorización (allow_below_minimum=True)."
      )
  ```
- **Excepción autorizada:** Un administrador puede vender por debajo del mínimo (por ejemplo, remate de unidad con raspones leves) enviando explícitamente `allow_below_minimum=True` en el payload de la venta.

### 2. Contabilidad de Costos por Lote y Absorción de Mermas
- **Regla:** Al comprar una caja de liquidación cerrada (por ejemplo, $4,000 Bs por la caja + $200 Bs de flete = $4,200 Bs costo total), se recibe una cantidad inicial de productos heterogéneos. Si 2 productos llegan rotos o inservibles (**merma**), el costo de la caja no disminuye; en su lugar, **las unidades vendibles restantes deben absorber el costo de las unidades mermadas**.
- **Fórmula implementada en `BatchService`:**
  $$\text{sellable\_items\_count} = \text{initial\_items\_count} - \text{merma\_items\_count}$$
  $$\text{unit\_cost} = \frac{\text{total\_cost}}{\text{sellable\_items\_count}}$$
- **Cascada automática:** Cada vez que se crea, actualiza o elimina un producto asociado a una caja, o se incrementa su merma (`merma_quantity`), el servicio `BatchService.recalculate_from_products` recalcula automáticamente los conteos, el costo unitario promedio del lote y el estado financiero hacia el punto de equilibrio.

### 3. Transacción Atómica de Ventas (`SaleService`)
- **Regla:** Una venta debe ser indivisible. Si la transacción falla en cualquier punto (por ejemplo, stock insuficiente en el segundo producto de un carrito con 3 ítems), la base de datos revierte completamente la operación sin dejar registros parciales.
- **Flujo de Ejecución Atómica:**

```mermaid
sequenceDiagram
    autonumber
    actor Vendedor as Vendedor / Operador
    participant Router as SaleRouter
    participant Service as SaleService
    participant DB as Base de Datos (PostgreSQL)

    Vendedor->>Router: POST /api/commerce/sales/ (payload)
    Router->>Service: create(data: SaleCreate)
    
    critical Transacción ACID
        Service->>DB: Verificar existencia de cada producto
        Service->>DB: Validar stock disponible (available_quantity >= requested)
        Service->>Service: Validar precio pactado vs. minimum_price
        Service->>Service: Obtener costo del producto (cost_price o batch.unit_cost)
        Service->>DB: Insertar registro Sale (encabezado)
        loop Por cada ítem
            Service->>DB: Insertar SaleItem (unit_price, unit_cost, net_margin)
            Service->>DB: Descontar stock (sold_quantity += q, available_quantity -= q)
            Note over Service,DB: Si available_quantity <= 0 -> status = 'SOLD_OUT'
        end
        Service->>DB: COMMIT Transacción
    end
    
    Service->>Router: Retorna SaleRead con ítems enriquecidos
    Router->>Vendedor: 201 Created (SaleRead JSON)
```

### 4. Búsqueda Inteligente Multi-Criterio
- **En `ProductRepository`:** Al buscar en el inventario físico (`GET /api/commerce/products/?search=reloj`), el repositorio realiza un `LEFT JOIN` transparente con `commerce_product_master` buscando simultáneamente en:
  - Nombre del producto maestro (`name`).
  - Código comercial (`code`).
  - Variante de lote (`variant_name`).
  - Estado y condición física (`status`, `physical_condition`).
  - Número de ítem numérico (`item_number` si el término es numérico).
- **En `ProductMasterRepository`:** Normaliza automáticamente búsquedas con caracteres comunes como `#53`, `NOV-53`, `NOV-053` o simplemente `53`.

---

### 5. Motor de Multi-Fotografía y Gestión Multimedia (Cloudinary Engine)

El subsistema de imágenes implementa un patrón híbrido que combina la normalización relacional para galerías multi-foto con la desnormalización estratégica para lecturas de alto rendimiento:

```mermaid
flowchart TD
    subgraph Storage ["Cloudinary CDN (Almacenamiento Físico)"]
        Dir["uyuni/products/{item_number}/{image_type}/"]
        Dir --> Cat["catalog/ (Web/PWA)"]
        Dir --> Real["real/ (Almacén/Unboxing)"]
        Dir --> Mkt["marketing/ (TikTok/Banners)"]
    end

    subgraph Database ["PostgreSQL (uyuni_prod)"]
        Master["commerce_product_master\ncover_image_url (O(1) lectura rápida)"]
        Images["commerce_product_image\nurl, public_id, image_type, is_cover, sort_order"]
        Master -->|"1:N"| Images
    end

    Images -.->|Sincroniza automáticamente| Master
```

#### Reglas de Implementación en Backend:
1. **Jerarquía Aislada en Cloudinary:**
   - Todo archivo se sube a la ruta: `uyuni/products/{item_number}/{image_type.lower()}/`.
   - Se convierte y sirve automáticamente en formato WebP con compresión inteligente (`quality: auto`, `fetch_format: auto`).
2. **Desnormalización de `cover_image_url`:**
   - La columna `cover_image_url` en `commerce_product_master` actúa como caché de lectura inmediata para alimentar tablas de Angular y la PWA de clientes sin requerir un `JOIN` a la tabla de imágenes.
   - **Inmutabilidad en formulario:** El endpoint `PUT /api/commerce/product-masters/{id}` descarta explícitamente `cover_image_url` (`data.pop("cover_image_url", None)`). La portada se modifica **exclusivamente** mediante las acciones de la galería (`/images`).
3. **Máquina de Estados de Portada:**
   - **Subida:** Si la ficha maestra no tiene portada, la primera foto subida se convierte automáticamente en portada oficial.
   - **Fijar Portada (`set_cover_image`):** Se marca `is_cover = True` en la foto seleccionada, `is_cover = False` en las demás, y se sincroniza `master.cover_image_url`.
   - **Eliminación con Auto-Recuperación (`delete_image`):** Si se borra la foto que era portada, el backend busca la siguiente foto disponible según `sort_order` y la promueve automáticamente como nueva portada. Si no quedan fotos, establece `master.cover_image_url = None`.
   - **Destrucción en Cloudinary:** Cada eliminación física ejecuta `cloudinary.uploader.destroy(public_id)` para asegurar que no queden activos huérfanos ocupando almacenamiento.
   - **Cascada al Eliminar Ficha Maestra:** Si se elimina una ficha maestra (`ProductMasterService.delete`), se purgan de Cloudinary todas las fotos asociadas antes de borrar el registro en base de datos.

---

### 6. Autogeneración Atómica del Identificador (`item_number`)

Para evitar cualquier posibilidad de colisión, duplicados o errores cuando múltiples usuarios crean productos simultáneamente:

1. **Secuencia Nativa en Base de Datos:**
   - Se creó la secuencia atómica en PostgreSQL:
     ```sql
     CREATE SEQUENCE commerce_product_master_item_number_seq;
     ALTER TABLE commerce_product_master 
     ALTER COLUMN item_number SET DEFAULT nextval('commerce_product_master_item_number_seq');
     ```
2. **Consumo Atómico en Memoria:**
   - En PostgreSQL, la llamada `SELECT nextval('commerce_product_master_item_number_seq')` consume la secuencia directamente en memoria compartida con candado por hardware (*spinlock*). Dos peticiones simultáneas en el mismo microsegundo reciben números correlativos consecutivos independientes (ej: 243 y 244).
3. **Inmutabilidad Absoluta:**
   - Ni en `POST` ni en `PUT` el usuario puede definir o alterar `item_number`. Ambos endpoints descartan cualquier valor manual recibido y delegan la numeración a PostgreSQL.
4. **Hook de Auto-Calibración en Arranque (`main.py`):**
   - Al iniciar la aplicación, un hook ejecuta `SELECT setval('commerce_product_master_item_number_seq', COALESCE(MAX(item_number), 0))` para asegurar sincronía perfecta incluso tras restauraciones con Navicat o backups manuales de base de datos.

