# Guía Maestra: Sistema de Consultas Genéricas y Búsqueda Inteligente

Esta guía está diseñada para desarrolladores que desean entender a fondo cómo funciona el motor de consultas de **Uyuni-BackEnd**. Este sistema automatiza la paginación, el ordenamiento, la búsqueda global y los filtros avanzados, permitiendo que tus DataTables en el frontend sean potentes con muy poco código.

---

## 1. Los 4 Pilares de una Consulta
Cuando el frontend (Angular/PrimeNG) solicita datos, siempre envía estos 5 parámetros base a través del `BaseRepository`:

| Parámetro | Tipo | Descripción |
| :--- | :--- | :--- |
| `offset` | `int` | Número de registros a saltar (Paginación). |
| `limit` | `int` | Cuántos registros traer (Paginación). |
| `sort_by` | `str` | Nombre de la columna por la que ordenar. |
| `sort_order` | `str` | `"asc"` o `"desc"`. |
| `search` | `str` | Término de búsqueda global ("tipo Google"). |

---

## 2. Búsqueda Global Polimórfica (`search`)

Es el filtro que se aplica cuando el usuario escribe en la barra de búsqueda general de la tabla.

### Configuración
En tu repositorio, simplemente define cuáles campos son "buscables":
```python
class FixedAssetRepository(BaseRepository[FixedAsset]):
    # Define qué campos se verán afectados por el parámetro ?search=
    searchable_fields = ["name", "code_saf", "serial_number", "external_id"]
```

### ¿Por qué "Polimórfica"? (Smart Casting)
En bases de datos como PostgreSQL, no puedes usar `ILIKE` (contiene) directamente sobre números. Para solucionar esto y hacer la búsqueda "inteligente", el motor:
1. Detecta si el campo es de texto o número.
2. Si es número (ej. `external_id`), aplica un `CAST(col AS TEXT)` en tiempo de ejecución.
3. **Resultado**: El usuario puede buscar **"10"** y el sistema encontrará tanto el nombre `"Laptop 10"` como el ID `10`.

---

## 3. Filtros Inyectables (`extra_filters`)

Es la capacidad de inyectar condiciones fijas desde el **Servicio** sin tocar el **Repositorio**. Sigue el patrón *Specification*.

### Lógica AND (Lista de predicados)
SQLModel interpreta cada elemento de la lista `extra_filters` como una operación **AND**.

#### Caso 1: Filtro Simple
"Quiero solo unidades del acrónimo FCO".
```python
extra_filters = [OrgUnit.acronym == "FCO"]
```

#### Caso 2: Filtro AND Combinado
"Quiero unidades de FCO que sean de tipo GERENCIA".
```python
extra_filters = [
    OrgUnit.acronym == "FCO",
    OrgUnit.type == "MANAGEMENT"
]
```

---

## 4. "Mezclando Todo": El Gran Poder
El motor combina automáticamente el `search` global con tus `extra_filters`. 

**Escenario**: Vista de "Activos en Mantenimiento" (`status == 'MAINT'`). El usuario busca `"HP"`.
1. El motor aplica el filtro fijo: `WHERE status = 'MAINT'`
2. Y añade el bloque de búsqueda global con un AND: `AND (name ILIKE '%HP%' OR code ILIKE '%HP%')`

---

## 5. Implementación Paso a Paso (Garantizando Consistencia)

Para evitar que el **Listado** y el **Conteo** tengan filtros diferentes (lo que rompería la paginación de PrimeNG), usa siempre **métodos privados de ayuda**.

### Paso A: El Servicio (Service)
Extrae la lógica del filtro a una función que empiece por `_`.

```python
class MyService:
    def get_list(self, acronym, offset, limit, search):
        # 1. Obtenemos filtros del ayudante privado
        filters = self._get_my_filters(acronym)
        # 2. Reutilizamos el motor genérico
        return self.repository.get_all(offset, limit, search=search, extra_filters=filters)

    def count(self, acronym, search):
        # 3. USAMOS EL MISMO AYUDANTE (Garantiza paridad)
        filters = self._get_my_filters(acronym)
        return self.repository.count(search, filters)

    # --- Ayudante Privado (No visible para el Router) ---
    def _get_my_filters(self, acronym):
        return [OrgUnit.acronym == acronym, OrgUnit.type == "OFFICE"]
```

### Paso B: El Controlador (Router)
El Router solo llama a los métodos públicos. No tiene acceso a los privados (`_`).

```python
@router.get("/by-acronym/{acronym}")
def get_list(
    acronym: str,
    search: Optional[str] = Query(None),
    service: MyService = Depends(get_service)
):
    # El Router no sabe nada de _get_my_filters, solo pide la acción de negocio
    return service.get_list(acronym, search=search, ...)
```

---

## 6. Mejores Prácticas

> [!IMPORTANT]
> **Consistencia en el Conteo**: El método `count()` de tu servicio debe recibir **exactamente los mismos** `extra_filters` que el `get_all()`. Si no, el frontend mostrará el total de páginas incorrecto.

> [!TIP]
> **Performance**: Los filtros fijos (`extra_filters`) sobre columnas indexadas son mucho más rápidos que el `search` global. Úsalos siempre que la lógica de la pantalla lo permita.

