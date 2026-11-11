# Guía de Desarrollo: Sistema de Catálogos Dinámicos Modulares

El sistema de **Catálogos Dinámicos Modulares** de Uyuni Backend es una solución de alto rendimiento diseñada para poblar selectores (dropdowns, combos y filtros) en el frontend de manera dinámica, desacoplada e independiente.

Esta guía está diseñada didácticamente para que **desarrolladores de todos los niveles (desde Junior hasta Senior)** puedan entender la lógica, arquitectura, flujo de ejecución y cómo extenderla sin fricción.

---

## 🎯 ¿Qué problema resuelve?

En sistemas empresariales complejos, un solo formulario de registro puede requerir cargar múltiples listados auxiliares (ej. *categorías de productos, canales de venta, métodos de pago, etc.*). 

*   **El Enfoque Tradicional (Malo):** El frontend realiza 10 llamadas HTTP individuales concurrentes a 10 endpoints distintos. Esto satura el pool de conexiones, incrementa la latencia de carga y genera un código de enrutamiento repetitivo (*boilerplate*) en el backend.
*   **Nuestro Enfoque Híbrido (Óptimo):** Centralizamos las llamadas de red mediante un **único punto de entrada global** que expone consultas individuales (`GET /api/catalogs/{name}`) y consultas masivas en lote (`POST /api/catalogs/bulk`). Con una sola petición HTTP, el frontend puede poblar un formulario completo de golpe, delegando la obtención de datos a proveedores especializados en el backend.

---

## 🏛️ Diseño Arquitectónico (Para Seniors)

El sistema se basa en el patrón de **Registro Desacoplado con Auto-registro** (Decoupled Registration with Self-Registration). Cada módulo de dominio (Commerce, Tasks, etc.) es el dueño absoluto de sus consultas de catálogos y se encarga de registrarlas de manera autónoma.

### Mapa de Capas del Sistema

```mermaid
graph TD
    Client["Frontend / Client"] -->|"GET /api/catalogs/{name}"| GlobalRouter["Global Catalogs Router"]
    Client -->|"POST /api/catalogs/bulk"| GlobalRouter
    GlobalRouter -->|"1. Resolve name"| Registry["CatalogRegistry Singleton"]
    GlobalRouter -->|"2. Exec Query"| Provider["CatalogProvider Implementation"]
    Registry -.->|"Stores Instances of"| Provider
    
    subgraph CommerceDomain ["Domain Module - Commerce Domain"]
        DomainModule["app/modules/commerce/catalogs/__init__.py"] -->|"Registers"| Categories["CommerceCategoriesProvider"]
        DomainModule -->|"Registers"| Channels["CommerceSalesChannelsProvider"]
    end
```

### Componentes Clave y Rutas de Archivos Relativas

1.  **El Protocolo (`CatalogProvider`)** en [base.py](../../app/core/catalogs/base.py):
    Define la "firma" o interfaz de programación. Cualquier clase que implemente `get_items(self, session: Session, **kwargs)` es considerada un proveedor de catálogo válido.
2.  **El DTO Estándar (`CatalogItemSchema`)** en [schemas.py](../../app/core/catalogs/schemas.py):
    Estructura JSON unificada que retorna la API:
    *   `value`: El identificador de la base de datos (generalmente un `UUID` o `int`).
    *   `label`: El texto amigable legible por el usuario (ej. *"Gerencia de TI"*).
    *   `extra`: Metadatos auxiliares opcionales (`dict[str, Any]`).
3.  **La Libreta de Contactos (`CatalogRegistry`)** en [registry.py](../../app/core/catalogs/registry.py):
    Un diccionario en memoria que empareja una clave de texto (`slug`) con su proveedor respectivo en Python. Expone el objeto único `global_registry`.
4.  **El Enrutador Central (`routers.py`)** en [routers.py](../../app/core/catalogs/routers.py):
    Expone los endpoints públicos `/api/catalogs/...` y resuelve dinámicamente las consultas haciendo búsquedas en `global_registry`.

---

## 🔄 Flujo de Trabajo e Inicialización (Para Juniors)

Si te preguntas *"¿cómo sabe el backend qué clase de Python ejecutar cuando mando una palabra en el JSON?"*, aquí tienes la explicación detallada de cómo se asocia en memoria:

### 🔍 La analogía del "Directorio Telefónico" (Cómo se asocia el JSON al Código)

Imagina que el sistema tiene una libreta de contactos en memoria llamada `global_registry`. Esta libreta asocia un **nombre de catálogo (String)** con una **instancia del proveedor (Clase Python)**.

1. **El Registro en memoria (Startup):** Al arrancar el servidor, el archivo `app/modules/commerce/catalogs/__init__.py` inscribe las relaciones:
   ```python
   global_registry.register("commerce_categories", CommerceCategoriesProvider())
   global_registry.register("commerce_sales_channels", CommerceSalesChannelsProvider())
   ```
   Nuestra "libreta de contactos" (`global_registry._providers`) queda guardada en memoria exactamente así:
   ```python
   {
       "commerce_categories": CommerceCategoriesProvider(),
       "commerce_sales_channels": CommerceSalesChannelsProvider()
   }
   ```

2. **El viaje del JSON en el Router:** Cuando envías una petición en lote (Bulk) con este cuerpo JSON:
   ```json
   {
     "commerce_categories": {},
     "commerce_sales_channels": {}
   }
   ```
   FastAPI recibe este JSON y lo convierte en un diccionario de Python. El enrutador global en `app/core/catalogs/routers.py` recorre este diccionario llave por llave:
   ```python
   for catalog_name, params in request_data.items():
       provider = global_registry.get_provider(catalog_name)
       result[catalog_name] = provider.get_items(session, **params)
   ```

3. **Resolución dinámica:**
   * **Iteración 1:** Toma la llave `"commerce_categories"`. Llama a `global_registry.get_provider("commerce_categories")` y obtiene el objeto `CommerceCategoriesProvider()`. Ejecuta su método `.get_items(session)` y guarda los resultados.
   * **Iteración 2:** Toma la llave `"commerce_sales_channels"`. Llama a `global_registry.get_provider("commerce_sales_channels")` y obtiene el objeto `CommerceSalesChannelsProvider()`. Ejecuta su método `.get_items(session)` y guarda los resultados.

4. **Control de Errores e Inexistencias:** ¿Qué pasa si mandas por error una llave inexistente como `"categories_invalid"`? El método `get_provider("categories_invalid")` valida si la clave existe en el diccionario en memoria. Al no encontrarla, lanza de forma segura una excepción `NotFoundException` que responde al cliente con un HTTP 404: `"Catalog 'categories_invalid' not found"` evitando errores de ejecución imprevistos.

---

### 1. Inicialización y Auto-registro en el Startup de la App

Cuando inicias FastAPI, el servidor importa los routers de los módulos. Al importar el router agregador de Core ([routers.py](../../app/modules/core/routers.py)), se gatilla un import silencioso del submódulo de catálogos ([__init__.py](../../app/modules/core/catalogs/__init__.py)).

```mermaid
sequenceDiagram
    participant App as FastAPI Startup
    participant R as Core Router
    participant I as app/modules/commerce/catalogs/__init__.py
    participant Reg as global_registry (Singleton)
    
    App->>R: Import app.modules.commerce.routers
    R->>I: Import app.modules.commerce.catalogs (Trigger self-registration)
    I->>Reg: register("commerce_categories", CommerceCategoriesProvider())
    I->>Reg: register("commerce_sales_channels", CommerceSalesChannelsProvider())
    Reg-->>I: Guardados en diccionario interno
    I-->>R: Registro dinámico completado
```

### 2. Consulta de un Catálogo Genérico Simple (GET)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend
    participant Route as GET /api/catalogs/{name}
    participant Reg as global_registry
    participant DB as PostgreSQL Database
    
    Client->>Route: GET /api/catalogs/commerce_categories
    Route->>Reg: get_provider("commerce_categories")
    Reg-->>Route: Retorna la instancia CommerceCategoriesProvider
    Route->>Route: Invoca get_items(session)
    Route->>DB: SELECT id, name FROM commerce_category WHERE is_active = true
    DB-->>Route: Retorna registros SQL
    Route-->>Client: HTTP 200 list[CatalogItemSchema]
```

### 3. Consulta de Carga Masiva (POST Bulk)

Si el frontend necesita cargar ambos dropdowns en una sola petición:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend
    participant Route as POST /api/catalogs/bulk
    participant Reg as global_registry
    participant DB as PostgreSQL Database
    
    Client->>Route: POST con {"commerce_categories": {}, "commerce_sales_channels": {}}
    loop Por cada elemento del JSON recibido
        Route->>Reg: get_provider(nombre_catalogo)
        Reg-->>Route: Retorna el Provider correspondiente
        Route->>Route: Invoca get_items(session, **params)
        Route->>DB: SQL Query correspondiente
        DB-->>Route: Resultados SQL
    end
    Route-->>Client: HTTP 200 unificado dict[str, list[CatalogItemSchema]]
```

---

## 💻 Manual Práctico: Cómo crear un nuevo catálogo paso a paso

Para incorporar un nuevo catálogo al sistema (por ejemplo, un listado de **Cargos Ocupacionales / Positions**), sigue estos 3 simples pasos:

### Paso 1: Crea el Proveedor (`providers.py`)
Escribe tu clase de consulta en el archivo de proveedores del módulo de negocio correspondiente. 

*Ruta:* [app/modules/core/catalogs/providers.py](../../app/modules/core/catalogs/providers.py)

```python
from sqlmodel import Session, select
from app.core.catalogs.base import CatalogProvider
from app.core.catalogs.schemas import CatalogItemSchema
from app.modules.core.positions.models import Position  # Tu modelo de DB

class CargosProvider(CatalogProvider):
    def get_items(self, session: Session, **kwargs) -> list[CatalogItemSchema]:
        """
        Recupera todos los cargos ocupacionales activos de la empresa.
        """
        # 1. Armamos el SELECT trayendo únicamente los campos necesarios
        query = select(Position.id, Position.name).where(
            Position.is_active == True
        ).order_by(Position.name)
        
        # 2. Ejecutamos la consulta en la DB
        results = session.exec(query).all()
        
        # 3. Retornamos mapeando al esquema estándar
        return [CatalogItemSchema(value=r[0], label=r[1]) for r in results]
```

### Paso 2: Registrar el Proveedor en el inicializador (`__init__.py`)
Abre el constructor de catálogos de tu módulo de dominio e inscribe tu clase en la libreta global.

*Ruta:* [app/modules/core/catalogs/__init__.py](../../app/modules/core/catalogs/__init__.py)

```python
from app.core.catalogs.registry import global_registry
from app.modules.core.catalogs.providers import (
    CommerceCategoriesProvider,
    CommerceSalesChannelsProvider,
    CommercePaymentMethodsProvider,  # 1. Importas tu proveedor
)

# 2. Lo agregas al registry global asignándole un identificador de texto único
global_registry.register("commerce_categories", CommerceCategoriesProvider())
global_registry.register("commerce_sales_channels", CommerceSalesChannelsProvider())
global_registry.register("commerce_payment_methods", CommercePaymentMethodsProvider())  # <-- ¡Agregado!
```

### Paso 3: Disparar el Auto-registro
Asegúrate de que el router agregador del módulo importe silenciosamente el paquete de catálogos para que Python ejecute la carga de `__init__.py` al levantar el servidor.

*Ruta:* [app/modules/commerce/routers.py](../../app/modules/commerce/routers.py)

```python
from fastapi import APIRouter

# Importación silenciosa indispensable
import app.modules.commerce.catalogs  # noqa: F401
...
```

¡Eso es todo! Sin tocar controladores de red, código HTTP ni validaciones de rutas, tu catálogo ya está expuesto en los endpoints globales.

---

## 🧪 Pruebas Unitarias

Siempre debes agregar pruebas para asegurar la estabilidad de la API. Escribe tu caso de prueba dentro de [test_catalogs.py](../../tests/test_catalogs.py):

```python
def test_get_commerce_categories_success(client: TestClient, superuser_token_headers: dict):
    # Probamos la consulta individual (GET)
    response = client.get("/api/catalogs/commerce_categories", headers=superuser_token_headers)
    assert response.status_code == 200
    
    # Probamos la consulta masiva (POST Bulk)
    payload = {"commerce_categories": {}}
    response = client.post("/api/catalogs/bulk", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    assert "commerce_categories" in response.json()
```

Para correr las pruebas locales:
```bash
venv/bin/pytest tests/test_catalogs.py
```

---

## 📋 Ejemplos de Intercambio de Datos (REST API)

### 1. Consulta GET Simple
*   **Request:** `GET /api/catalogs/commerce_categories`
*   **Response (HTTP 200):**
    ```json
    [
      {
        "value": "019e2c7a-cc93-73bd-b877-623043fe07ef",
        "label": "Smartphones & Accesorios",
        "extra": null
      }
    ]
    ```

### 2. Consulta POST Bulk (En lote)
*   **Request:** `POST /api/catalogs/bulk`
*   **Request Body:**
    ```json
    {
      "commerce_categories": {},
      "commerce_sales_channels": {}
    }
    ```
*   **Response (HTTP 200):**
    ```json
    {
      "commerce_categories": [
        {
          "value": "019e2c7a-cc93-73bd-b877-623043fe07ef",
          "label": "Smartphones & Accesorios",
          "extra": null
        }
      ],
      "commerce_sales_channels": [
        {
          "value": "019e2c7a-cc94-7c12-a6c0-bcc390f8fbd3",
          "label": "UNIDAD JURÍDICA",
          "extra": null
        }
      ]
    }
    ```
