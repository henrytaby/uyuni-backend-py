# Guía de Calidad de Código (Linting & Typing)

## 1. Introducción

En Uyuni-BackEnd, mantenemos un estándar alto de calidad de código utilizando herramientas automatizadas de última generación. El objetivo es:
1.  **Uniformidad**: Que todo el código parezca escrito por una sola persona.
2.  **Prevención de Errores**: Detectar bugs (variables no usadas, errores de tipo) *antes* de ejecutar el código.
3.  **Velocidad**: Automatizar revisiones triviales para que los Code Reviews se enfoquen en lógica de negocio.

Las herramientas principales son **Ruff** (Linting y Formateo) y **MyPy** (Tipado Estático).

---

## 2. Ruff (Linting y Formateo)

[Ruff](https://docs.astral.sh/ruff/) es un linter y formateador de Python escrito en Rust. Es extremadamente rápido y reemplaza a múltiples herramientas antiguas (Black, Isort, Flake8).

### 2.1. ¿Para qué se usa?
*   **Linting (`ruff check`)**: Analiza el código buscando errores estilísticos (ej. líneas muy largas), imports no usados, variables indefinidas, etc.
*   **Formateo (`ruff format`)**: Reescribe automáticamente tu código para cumplir con el estilo estándar (espacios, comillas, saltos de línea). Equivalente a "Black".

### 2.2. Configuración del Proyecto (`ruff.toml`)

La configuración se encuentra en el archivo `ruff.toml`.

*   **Longitud de línea**: `88` caracteres (Estándar de la industria).
*   **Versión Python**: `3.10`.
*   **Exclusiones**: La carpeta `alembic/` (migraciones autogeneradas) está excluida.

### 2.3. Uso para Desarrolladores

```bash
# Verificar errores (solo lectura)
ruff check .

# Verificar y corregir automáticamente lo que sea posible (Recomendado)
ruff check --fix .

# Formatear código (Reescribir archivos)
ruff format .
```

---

## 3. MyPy (Tipado Estático)

[MyPy](https://mypy.readthedocs.io/) es un verificador de tipos estático.

### 3.1. ¿Para qué se usa?
Para asegurar que si una función espera un `int`, no le pases un `str`. Esto previene `TypeError` en producción.

### 3.2. Uso para Desarrolladores

```bash
mypy .
```

---

## 4. Flujo de Trabajo Recomendado

Antes de hacer `git commit`, ejecuta siempre:

```bash
# 1. Corrige imports y errores simples
ruff check --fix .

# 2. Formatea el código bonito
ruff format .

# 3. Verifica tipos estrictos
mypy .
```

---

## 5. Estándares de Excelencia (Clean Code & Arquitectura)

### 5.1. Convenciones de Nombres (Naming)
*   **Variables y Funciones**: `snake_case` (ej: `create_user`, `is_active`). Deben ser verbos o sustantivos descriptivos.
*   **Clases**: `PascalCase` (ej: `StaffRepository`, `StaffService`).
*   **Constantes**: `UPPER_CASE` (ej: `MAX_LOGIN_ATTEMPTS`).
*   **Archivos**: `snake_case` (ej: `user_service.py`).

#### 5.1.1. Métodos Privados y Encapsulamiento (`_`)
Siguiendo el estándar **PEP 8**, cualquier método o variable que sea de uso **estrictamente interno** de una clase debe comenzar con un guion bajo (`_`).

*   **¿Por qué usar `_nombre`?**: 
    1.  **Encapsulamiento**: Separa la "Cocina" (lógica técnica) de la "Puerta Principal" (acciones que el Router puede invocar).
    2.  **Seguridad**: Indica a otros desarrolladores que ese método no debe ser llamado desde fuera de la clase.
    3.  **Limpia el Autocompletado**: Los IDEs ocultan estos métodos al escribir `service.`, dejando solo las acciones de negocio visibles.

**Ejemplo en Servicios**:
```python
class OrgUnitService:
    # Acción Pública (Lo que el Router ve)
    def get_management_units(self, ...):
        filters = self._get_filters() # Usa el ayudante interno
        return self.repository.get_all(..., extra_filters=filters)

    # Ayudante Privado (Oculto al Router)
    def _get_filters(self):
        return [OrgUnit.type == "MANAGEMENT"]
```

### 5.2. Arquitectura Limpia (Clean Architecture)
El código debe respetar estrictamente la jerarquía de capas:
1.  **Router (Capa HTTP)**: Solo maneja Request/Response, Status Codes y DTOs.
2.  **Service (Capa de Negocio)**: Contiene la lógica del caso de uso.
3.  **Repository (Capa de Datos)**: Abstrae el acceso a la DB.

Riverside
