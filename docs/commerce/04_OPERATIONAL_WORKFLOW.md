# 04. Flujo Operativo y Ciclo de Vida — Commerce

Este documento describe de manera **didáctica y paso a paso** el ciclo de vida completo de un producto en el ecosistema comercial: desde que los inversionistas desembolsan el capital para adquirir una caja o lote de importación hasta que el producto es vendido, despachado y se cierra el retorno de inversión del lote.

---

## 🔄 Visión General del Ciclo de Vida

```mermaid
flowchart TD
    Fase1["1. Financiación e Importación\nRonda de Inversión + Compra de Caja"] --> Fase2["2. Desempaque y Clasificación\nFicha Maestra vs. Existencia Física"]
    Fase2 --> Fase3["3. Control de Calidad y Pruebas\nInspección Física y Registro de Merma"]
    Fase3 --> Fase4["4. Merchandising y Publicación\nAsignación a Canasta Live + Redes"]
    Fase4 --> Fase5["5. Venta y Despacho\nNegociación, Pago QR y Envío Flota"]
    Fase5 --> Fase6["6. Cierre Financiero\nPunto de Equilibrio (Break-Even)"]
```

---

## 📋 Las 6 Fases Operativas Paso a Paso

### Fase 1: Financiación y Adquisición del Lote

Esta es la **receta inicial obligatoria** antes de desempaque o ventas:

1. **Paso 1: Apertura de la Ronda de Inversión (`InvestmentRound`):**
   - Se crea en el módulo de Catálogos (`/commerce/catalogs` $\rightarrow$ Pestaña *Rondas de Inversión*) o vía `POST /api/commerce/rounds/`.
   - **Caso Importación de Cajas:** `RONDA-02` con capital inicial previsto (ej: Bs. 15,000).
   - **Caso Bazar / Cosas Propias de Socios:** Se crea con `capital_invested = 0.0`. No hay deuda inicial que cubrir; el sistema irá sumando de abajo hacia arriba solo si se añaden compromisos de pago.
2. **Paso 2: Registro del Lote o Caja (`Batch`):**
   - Se crea en `/commerce/batches` asociándole la ronda creada (`investment_round_id`).
   - Se define la **modalidad de costeo (`costing_method`)**:
     - `WEIGHTED_RETAIL`: Cajas sorpresa o liquidaciones de Amazon con costo fijo global adelantado (ej. compra 4.000 Bs + flete 300 Bs = 4.300 Bs), cuyo costo se distribuye ponderadamente según el precio comercial de los productos buenos.
     - `SPECIFIC_ITEM`: Lotes abiertos dinámicos (bazar familiar, compras a pedido, artesanías/manufactura) con costo de compra inicial de 0 Bs, donde cada producto nuevo ingresado suma su propio costo o costo nominal.
     - `FLAT_AVERAGE`: Lotes mayoristas homogéneos repartidos en partes iguales entre las unidades vendibles.
   - Estado financiero inicial: `ACTIVE` o `IN_RECOVERY`.

---

### Fase 2: Desempaque, Clasificación e Inventariado
Al abrir la caja física en el almacén, el operador saca cada producto y realiza una doble verificación:

1. **¿El producto ya existe en el catálogo maestro? (`ProductMaster`):**
   - **Caso A (Producto Nuevo):** Se crea una nueva Ficha Maestra con su número correlativo limpio asignado atómicamente (`item_number: 243`), nombre oficial, categoría y precios de referencia (`official_price: 180`, `minimum_price: 140`). Se suben las fotos y creativos directamente a Cloudinary organizados en su jerarquía (`uyuni/products/243/catalog/`, `real/`, `marketing/`).
   - **Caso B (Producto Repetido):** Si el producto ya existía de una importación anterior (por ejemplo, el producto `#53 - Almohadilla Térmica`), **NO** se duplica la ficha maestra. Se utiliza la ficha existente `#53`.
2. **Registro de la Unidad Física en el Lote (`Product`):**
   - Se crea el registro de inventario físico vinculándolo a la ficha maestra (`master_product_id`) y a la caja de donde salió (`batch_id`).
   - Se indica la variante física específica si aplica (ej: `variant_name: "Color Gris"` o `"Modelo TK-HP2412"`).

---

### Fase 3: Control de Calidad, Pruebas y Tratamiento de Merma
Los productos de liquidación provienen de devoluciones o excedentes de tiendas estadounidenses; por tanto, **cada unidad debe ser probada individualmente en mesa de trabajo**:

1. **Inspección Operativa:**
   - Se conecta a la corriente y se comprueba que encienda, caliente o sincronice correctamente.
   - Si funciona al 100%: Se marca `is_reviewed = True` y `physical_condition = "OPERATIONAL"`.
2. **Tratamiento de Defectos o Merma:**
   - **Daño Estético Menor:** Si funciona pero tiene un raspón, se registra en `defect_detail: "Pequeño raspón en la esquina trasera"` y permanece como disponible.
   - **Unidad Insensible o Inservible (Merma):**
     - Si el producto llegó roto o quemado, se actualiza el producto con `merma_quantity = 1` y `physical_condition = "DAMAGED_SCRAP"`.
     - El stock disponible pasa a 0 (`available_quantity = 0`) y el estado a `"SCRAPPED"`.
     - **Efecto Financiero:** El servicio `BatchService` recalcula automáticamente el costo unitario de la caja:
       - Si la caja costó Bs. 4,300 y llegaron 50 ítems, pero 2 fueron merma, ahora hay **48 ítems vendibles**.
       - El costo unitario de cada producto vendible se eleva automáticamente a:
         $$\text{unit\_cost} = \frac{4,300}{48} = \text{Bs. } 89.58$$
       - De esta manera, **el negocio nunca pierde dinero por unidades rotas**, ya que su costo queda distribuido de forma transparente en las unidades buenas.

---

### Fase 4: Merchandising para TikTok Live y Redes Sociales
Antes de la transmisión en vivo, el equipo organiza los productos para facilitar la dinámica de subasta y venta rápida:

1. **Asignación de Canasta (`live_basket_id`):**
   - Cada producto maestro tiene asignada una canasta temática según su tipo y rango de precio:
     - `C1 Taller & Auto`: Linternas mecánicas, cargadores de batería, compresores portátiles.
     - `C2 Cables & Regletas`: Hubs USB, cables blindados, cargadores GaN.
     - `C3 Hogar & Cocina`: Afiladores eléctricos, luces solares, almohadillas térmicas.
     - `C4 Salud & Belleza`: Masajeadores, secadores iónicos, perfiladores.
     - `C+1 Remate Flash`: Productos especiales para dinamizar el live en momentos de alto tráfico.
2. **Publicación Multicanal:**
   - Se publican las fotos WebP en Facebook Marketplace (`is_published_marketplace = True`) y en catálogos de WhatsApp.
   - Los clientes pueden ver el catálogo público en tiempo real mediante la **PWA de Clientes** (`/apps/catalog-pwa`), la cual consulta directamente los productos con stock disponible sin necesidad de recompilar la web.

---

### Fase 5: Negociación, Regateo y Venta Atómica
Durante el live o por chat de Marketplace, un cliente expresa interés en un producto:

1. **Negociación y Piso de Regateo:**
   - El precio de publicación es de Bs. 160 (`published_price`).
   - El cliente ofrece Bs. 140. El vendedor acepta porque el piso protegido (`minimum_price`) es Bs. 140.
   - Si el cliente ofreciera Bs. 120, el sistema bloquearía el registro a menos que un supervisor active `allow_below_minimum = True`.
2. **Registro de la Venta (`POST /api/commerce/sales`):**
   - El operador selecciona el método de pago boliviano acordado:
     - `QR`: Pago inmediato por Simple QR.
     - `CASH`: Efectivo en punto de entrega.
     - `TRANSFER`: Transferencia bancaria (BNB, BCP, Banco Unión).
   - Selecciona la logística de entrega:
     - `FREE_MEETING_POINT`: Punto neutro sin costo (ej: Plaza Colón, Correo).
     - `HOME_DELIVERY`: Delivery con moto a domicilio.
     - `TERMINAL_BUS`: Envío por flota interdepartamental (Trans Copacabana, Bolívar) para clientes de La Paz, Santa Cruz u Oruro.
3. **Ejecución Atómica en Base de Datos:**
   - Se descuenta la unidad del inventario físico (`available_quantity = 0`, `status = "SOLD_OUT"`).
   - Se calcula el margen neto en el acto:
     $$\text{net\_margin} = \text{precio pactado (140)} - \text{costo del lote (89.58)} = \text{Bs. } +50.42$$

---

### Fase 6: Cierre Financiero y Retorno de Inversión (Break-Even)
1. **Seguimiento del Lote:**
   - Con cada venta registrada, el sistema suma el capital recuperado de esa caja específica.
2. **Punto de Equilibrio (*Break-Even*):**
   - En cuanto las ventas de la caja superan los Bs. 4,300 iniciales, el campo `financial_status` del lote cambia a `"RECUPERADO"`.
3. **Distribución de Utilidades:**
   - A partir de ese momento, cada venta subsiguiente de esa caja representa **100% utilidad neta**, permitiendo a los administradores generar los reportes de liquidación para los inversionistas de la ronda.

