# Guía de Observabilidad y Logging

Esta guía documenta el sistema de "Observabilidad Lite" implementado en `uyuni-backend-py`.

## 1. Introducción: La Filosofía "Zero Guessing"

En un entorno Enterprise, cuando algo falla en producción, no podemos conectarnos al servidor a depurar. Necesitamos que el sistema nos cuente la historia completa a través de sus logs.

**Objetivo**: Transformar logs de texto plano ("impresiones en pantalla") en **Eventos Estructurados (JSON)** que puedan ser ingeridos automáticamente por sistemas de monitoreo (ELK, Datadog, Splunk, CloudWatch).

### ¿Por qué Structlog?
Usamos `structlog` en lugar del `logging` nativo de Python porque nos obliga a pensar en **eventos y contexto** (Key-Value) en lugar de cadenas de texto (Strings).

| Característica | Logging Nativo | Structlog (Enterprise) |
| :--- | :--- | :--- |
| Formato | Texto plano difícil de parsear | JSON nativo fácil de consultar |
| Contexto | Difícil de agregar (requiere filtros) | Contexto enlazado (`bind`) automático |
| Performance | Lento en concatenación de strings | Optimizado para serialización |
| Legibilidad | Buena para humanos, Mala para máquinas | Configurable (Consola vs JSON) |

## 2. Arquitectura de Archivos

La lógica de observabilidad está centralizada y no dispersa:

```text
app/
├── core/
│   ├── config.py       # Define variables de entorno (ENABLE_ACCESS_LOGS, etc)
│   └── logging.py      # Configura structlog, renderers (JSON/Console) y filtros
└── main.py             # Middleware que intercepta CADA petición HTTP
```

### Flujo de un Log
1.  **Middleware (`main.py`)**: Intercepta la petición al entrar.
2.  **Context Binding**: Genera un `request_id` único y lo "ata" al contexto. Todos los logs generados durante esa petición (incluso en funciones profundas) llevarán ese ID.
3.  **Procesamiento**: La petición se ejecuta. Se mide el tiempo (`duration`).
4.  **Filtrado (`main.py`)**: Se decide si se loguea o no basado en `config.py`.
5.  **Renderizado (`logging.py`)**:
    *   **Local**: Se imprime bonito con colores (`ConsoleRenderer`).
    *   **Producción**: Se imprime como JSON compacto (`JSONRenderer`).

## 3. Guía de Uso para Desarrolladores

### ✅ LO QUE DEBES HACER (Do's)

1.  **Usar Structlog siempre**:
    ```python
    import structlog
    logger = structlog.get_logger()
    
    # BIEN: Contexto explicito
    logger.info("user_login_failed", user_id=123, reason="bad_password")
    ```

2.  **Loguear Eventos, no Oraciones**:
    *   ❌ `logger.info("El usuario 123 no pudo entrar porque la contraseña estaba mal")`
    *   ✅ `logger.info("login_failed", user_id=123, error="invalid_password")`

3.  **Confiar en el Middleware**:
    No necesitas loguear "Iniciando petición..." ni "Terminando petición...". El middleware ya lo hace con `request_completed`.

### ❌ LO QUE NO DEBES HACER (Don'ts)

1.  **Usar `print()`**: Jamás. `print` no tiene timestamp, ni nivel de severidad, ni request_id. Es invisible para el monitoreo.
2.  **Concatenar Strings en Logs**:
    *   ❌ `logger.info(f"Usuario {user.id} creado")` (Rompe la estructura JSON)
    *   ✅ `logger.info("user_created", user_id=user.id)`

## 4. Configuración y Control

El sistema es controlable vía variables de entorno (`.env`):

| Variable | Tipo | Default | Descripción |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | str | `local` | `local` = Colores/Texto. `production` = JSON. |
| `ENABLE_ACCESS_LOGS` | bool | `True` | Master switch. `False` silencia todos los logs de tráfico HTTP. |
| `ACCESS_LOGS_ONLY_ERRORS` | bool | `False` | `True` = Solo loguea si status >= 400. Útil para ahorrar espacio. |

### Cómo cambiar el comportamiento en tiempo real
Para producción, se recomienda:
```ini
ENVIRONMENT=production
ENABLE_ACCESS_LOGS=True
ACCESS_LOGS_ONLY_ERRORS=False  # O True si hay demasiado tráfico
```

## 5. Explicación del Código Crítico

### `app/core/logging.py`
Aquí ocurre la magia de "limpiar" los logs de Uvicorn.
*   **Problema**: Uvicorn por defecto imprime logs "verdes" duplicados que no tienen nuestro formato.
*   **Solución**:
    ```python
    # Silencia el logger "access" de uvicorn (porque nosotros ya logueamos el acceso en middleware)
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    ```

### `app/main.py` (Middleware)
Aquí capturamos la duración y el ID.
```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # 1. Generar ID único (Traza)
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    # 2. Medir tiempo
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # 3. Loguear con contexto final
    structlog.get_logger("api.access").info(
        "request_completed",
        path=request.url.path,
        status_code=response.status_code,
        duration=duration,  # <--- Métrica clave de performance
    )
```
