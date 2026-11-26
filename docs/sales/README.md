# Módulo de Ventas y Transacciones Comerciales (`commerce/sales`) — Guía Maestra

Bienvenido a la documentación oficial del módulo de **Ventas, Facturación y Control de Caja (POS)** del sistema **Uyuni Backend**. 

Este submódulo opera como el corazón de liquidación y salida comercial del ERP, gestionando de forma atómica el cobro multicanal, control de arqueo de caja física, despacho logístico y cálculo de rentabilidad neta en tiempo real.

---

## 🎯 Propósitos y Capacidades del Módulo

1. **Venta Atómica Transaccional (ACID):**
   * En una sola transacción de base de datos se crea el encabezado de venta, se registran las líneas de detalle, se deduce el stock físico disponible (`available_quantity`), se actualiza la cantidad vendida (`sold_quantity`) y se conmuta el estado del producto a `SOLD_OUT` si se agotan las existencias.
2. **Correlativo Atómico Legible (`#1`, `#2`, `#29`):**
   * Secuencia numérica entera respaldada por PostgreSQL (`commerce_sale_sale_number_seq`), permitiendo numeración limpia, legible e indexada para tickets físicos, boletaje y búsqueda instantánea con `#`.
3. **Punto de Venta (POS) y Control de Efectivo:**
   * Registro del monto recibido (`amount_tendered`) y cálculo exacto de cambio/vuelto (`change_given`), evitando valores nulos en auditoría de caja.
4. **Estrategia Comercial del Tri-Precio (Precios Inteligentes):**
   * El vendedor dispone en pantalla del **Precio Publicado** (cotización de entrada), **Piso Mínimo de Regateo** (límite no negociable para proteger margen) y **Precio de Referencia de Mercado** (ancla de ahorro frente a la competencia).
5. **Catálogo POS Desacoplado con Búsqueda Híbrida (`/available-products`):**
   * Endpoint optimizado bajo el contexto de ventas que no requiere permisos de inventario (`commerce_products`), filtrando únicamente existencias vendibles (`AVAILABLE` con `stock > 0`) y admitiendo búsqueda en servidor con debounce.
6. **Separación de Logística y Estado:**
   * Distinción clara entre la **Modalidad de Entrega** (Punto de Encuentro, Envío por Flota, Delivery a Domicilio) y el **Ciclo de Entrega** simplificado (`DELIVERED` vs `PENDING`).
7. **Deducción de Fletes Asumidos por la Tienda:**
   * Descuento automático de costos de transporte del margen neto (`net_profit`) cuando la tienda asume el envío (`STORE`).

---

## 📚 Índice de la Documentación Especializada

La documentación se divide en 4 volúmenes según el rol del profesional o usuario:

| Documento | Audiencia | Contenido Principal |
| :--- | :--- | :--- |
| **[01. Arquitectura y Lógica Backend](./01_ARCHITECTURE_BACKEND.md)** | Backend Devs, Tech Leads, Arquitectos | Patrón DDD-Lite, Service/Repository, secuencia atómica PostgreSQL, transacciones ACID, deducción financiera, control de permisos RBAC y algoritmos de búsqueda. |
| **[02. Diccionario de Base de Datos](./02_DATABASE_DICTIONARY.md)** | DBAs, Fullstack Devs, Auditores | Diagrama Entidad-Relación (ERD) oficial, tablas `commerce_sale` y `commerce_sale_item`, tipos de datos, índices, secuencias, claves foráneas y queries de mantenimiento. |
| **[03. Guía de Integración Frontend](./03_FRONTEND_INTEGRATION_GUIDE.md)** | Frontend Devs (Angular 21 / PrimeNG) | Contratos REST, interfaces TypeScript, Opción C híbrida de búsqueda reactiva con debounce de 300ms, barra del Tri-Precio, cálculo de cambio POS y templates. |
| **[04. Manual de Usuario Operativo y Cajeros](./04_MANUAL_USUARIO_OPERATIVO.md)** | Vendedores, Cajeros, Administradores | Guía práctica paso a paso: creación de ventas, cobro en efectivo y QR, cómo negociar con el Tri-Precio, modalidades de despacho y búsqueda rápida por `#`. |

---

## 🗺️ Mapa Rápido de Endpoints

Todos los endpoints están agrupados bajo el prefijo `/api/commerce/sales`:

| Método | Endpoint | Permiso Requerido | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/commerce/sales/` | `commerce:create` | Crea una venta atómica, descuenta stock y calcula utilidades. |
| `GET` | `/api/commerce/sales/` | `commerce:read` | Lista paginada de ventas con filtros de canal, estado y búsqueda. |
| `GET` | `/api/commerce/sales/count` | `commerce:read` | Conteo total de transacciones para paginación de tablas. |
| `GET` | `/api/commerce/sales/available-products` | `commerce:read` | **Catálogo POS:** Productos vendibles con stock y Tri-Precio comercial. |
| `GET` | `/api/commerce/sales/{id}` | `commerce:read` | Obtiene el detalle completo de una venta con sus ítems. |
| `PUT` | `/api/commerce/sales/{id}` | `commerce:update` | Actualiza datos de cliente, canal, método de pago o logística. |
| `DELETE`| `/api/commerce/sales/{id}` | `commerce:delete` | Elimina una venta del sistema con registro de auditoría CDC. |
