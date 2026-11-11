# Módulo Commerce (Nova Box Bolivia) — Acceso Rápido

La documentación completa, modular y profesional del módulo de **Commerce** se encuentra en la carpeta especializada [`docs/commerce/`](./commerce/README.md).

---

## 📚 Documentos Disponibles:

1. **[Guía Maestra y Visión General](./commerce/README.md):**
   - Contexto del negocio de Nova Box Bolivia y problemas que resuelve.
   - Resumen de submódulos y stack tecnológico.

2. **[01. Arquitectura y Reglas de Negocio](./commerce/01_ARCHITECTURE.md):**
   - Clean Architecture y patrón DDD-Lite.
   - Separación entre Ficha Comercial Maestra (`ProductMaster`) e Inventario Físico (`Product`).
   - Reglas críticas: piso mínimo de regateo (`minimum_price`), costeo por lote, absorción de mermas y ventas atómicas.

3. **[02. Diccionario de Base de Datos](./commerce/02_DATABASE_DICTIONARY.md):**
   - Diagrama Entidad-Relación (ERD) oficial en Mermaid.
   - Diccionario exhaustivo campo por campo de las 9 tablas, tipos, índices, claves foráneas y columnas de auditoría.

4. **[03. Guía de Integración Frontend](./commerce/03_FRONTEND_INTEGRATION_GUIDE.md):**
   - Consumo de API para Angular 21 y React PWA.
   - Carga masiva de catálogos en una sola petición (`POST /api/catalogs/bulk`).
   - Endpoints, parámetros query, contratos JSON y respuestas enriquecidas con existencias consolidadas.

5. **[04. Flujo Operativo y Ciclo de Vida](./commerce/04_OPERATIONAL_WORKFLOW.md):**
   - Ciclo de vida didáctico paso a paso: financiamiento, importación, pruebas en mesa, mermas, publicación en TikTok Live y Facebook Marketplace, cobro por QR, despacho por flota y punto de equilibrio (*Break-Even*).

