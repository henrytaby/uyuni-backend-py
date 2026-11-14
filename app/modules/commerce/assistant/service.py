import re
from typing import Any

import structlog
from sqlmodel import Session, and_, col, func, or_, select

from app.modules.commerce.assistant.provider import call_llm
from app.modules.commerce.assistant.schemas import (
    ChatAssistantRequest,
    ChatAssistantResponse,
    MatchedProductContext,
)
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.service import ProductMasterService
from app.modules.commerce.products.models import Product

logger = structlog.get_logger(__name__)

STOP_WORDS = {
    # Preguntas / Pronombres interrogativos
    "cuanto",
    "cuanta",
    "cuantos",
    "cuantas",
    "que",
    "qué",
    "cual",
    "cuál",
    "cuales",
    "cuáles",
    "como",
    "cómo",
    "donde",
    "dónde",
    "cuando",
    "cuándo",
    # Existencia / Stock / Almacén
    "stock",
    "inventario",
    "inventarios",
    "disponible",
    "disponibles",
    "disponibilidad",
    "existencia",
    "existencias",
    "almacen",
    "almacén",
    "deposito",
    "depósito",
    "tienda",
    "bodega",
    "sucursal",
    # Verbos comunes de consulta
    "tenemos",
    "tienen",
    "tiene",
    "tienes",
    "tengo",
    "tenga",
    "tengan",
    "hay",
    "habra",
    "habrá",
    "queda",
    "quedan",
    "cuentas",
    "cuenta",
    "cuentan",
    "contamos",
    "dispones",
    "dispone",
    "disponen",
    "disponemos",
    "ofreces",
    "ofrece",
    "ofrecen",
    "ofrecemos",
    "manejas",
    "maneja",
    "manejan",
    "manejamos",
    "vendes",
    "vende",
    "venden",
    "vendemos",
    "mostrar",
    "muestra",
    "muestrame",
    "muéstrame",
    "ver",
    "listar",
    "lista",
    "dime",
    "saber",
    "buscar",
    "busca",
    "consultar",
    "consulta",
    "quisiera",
    # Entidades de catálogo
    "producto",
    "productos",
    "proyecto",
    "proyectos",
    "catalogo",
    "catálogo",
    "ficha",
    "fichas",
    "item",
    "items",
    "articulo",
    "articulos",
    "artículo",
    "artículos",
    "mercaderia",
    "mercadería",
    "informacion",
    "información",
    "info",
    "dato",
    "datos",
    "detalle",
    "detalles",
    "descripcion",
    "descripción",
    "numero",
    "número",
    "nro",
    "num",
    # Precios y Comercial
    "precio",
    "precios",
    "costo",
    "costos",
    "cuesta",
    "cuestan",
    "vale",
    "valen",
    "venta",
    "ventas",
    "vender",
    "piso",
    "regateo",
    "minimo",
    "mínimo",
    # Cantidades y medidas
    "unidad",
    "unidades",
    "unid",
    "unids",
    "pieza",
    "piezas",
    "cantidad",
    "cantidades",
    # Temporalidad / Totalidad
    "todos",
    "todas",
    "todo",
    "actual",
    "actuales",
    "ahora",
    "hoy",
    # Cortesía
    "hola",
    "buenas",
    "buenos",
    "dias",
    "días",
    "tardes",
    "noches",
    "porfa",
    "porfavor",
    "gracias",
    "favor",
    # Artículos, preposiciones y conectores
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "de",
    "del",
    "para",
    "con",
    "sin",
    "por",
    "sobre",
    "en",
    "me",
    "nos",
    "te",
    "se",
    "le",
    "les",
    "algun",
    "algún",
    "alguno",
    "alguna",
    "algunos",
    "algunas",
    "otro",
    "otra",
    "otros",
    "otras",
}

SYNONYM_GROUPS: dict[str, list[str]] = {
    "auto": [
        "auto",
        "autos",
        "automóvil",
        "automovil",
        "automóviles",
        "automoviles",
        "coche",
        "coches",
        "vehículo",
        "vehiculo",
        "vehículos",
        "vehiculos",
        "carro",
        "carros",
        "automotriz",
        "automotrices",
    ],
    "celular": [
        "celular",
        "celulares",
        "teléfono",
        "telefono",
        "teléfonos",
        "telefonos",
        "smartphone",
        "smartphones",
        "móvil",
        "movil",
        "móviles",
        "moviles",
    ],
    "audifono": [
        "audífono",
        "audifono",
        "audífonos",
        "audifonos",
        "auricular",
        "auriculares",
        "headphone",
        "headphones",
        "earphone",
        "earphones",
        "earbuds",
        "cascos",
    ],
    "cargador": [
        "cargador",
        "cargadores",
        "charger",
        "cargador rápido",
        "adaptador de carga",
    ],
    "foco": [
        "foco",
        "focos",
        "bombilla",
        "bombillas",
        "lámpara",
        "lampara",
        "lámparas",
        "lamparas",
    ],
    "luz": [
        "luz",
        "luces",
        "iluminación",
        "iluminacion",
        "reflector",
        "reflectores",
        "linterna",
        "linternas",
    ],
    "reloj": [
        "reloj",
        "relojes",
        "smartwatch",
        "smartwatches",
        "pulsera inteligente",
    ],
    "laptop": [
        "laptop",
        "laptops",
        "computadora",
        "computadoras",
        "notebook",
        "notebooks",
        "pc",
        "ordenador",
    ],
    "parlante": [
        "parlante",
        "parlantes",
        "altavoz",
        "altavoces",
        "bocina",
        "bocinas",
        "speaker",
        "speakers",
    ],
    "bateria": [
        "batería",
        "bateria",
        "baterías",
        "baterias",
        "pila",
        "pilas",
        "powerbank",
        "power bank",
    ],
    "domotica": [
        "domotica",
        "domótica",
        "smart home",
        "smarthome",
        "casa inteligente",
        "hogar inteligente",
        "inteligente",
        "smart",
        "tuya",
        "zigbee",
        "homekit",
        "alexa",
        "automatización",
        "automatizacion",
    ],
}


class CommerceAssistantService:
    def __init__(self, session: Session):
        self.session = session
        self.master_service = ProductMasterService(session)

    @staticmethod
    def to_stem(word: str) -> str:
        """Obtiene la raíz o forma singular básica en español para búsquedas."""
        w = word.lower().strip()
        if len(w) <= 3:
            return w
        if w.endswith("ces") and len(w) > 4:
            return w[:-3] + "z"
        if w.endswith("es") and len(w) > 4:
            if w[-3] in "rdnzjs" or (w[-3] in "bcdfghjklmnpqrstvwxyz" and w[-3] != "l"):
                return w[:-2]
            return w[:-1]
        if w.endswith("s") and not w.endswith(("is", "us")):
            return w[:-1]
        return w

    @staticmethod
    def extract_item_numbers(text: str) -> list[int]:
        """Detecta referencias a números de catálogo (#XX, item XX, producto XX)."""
        numbers: list[int] = []
        pattern = (
            r"(?:#|item|cat[aá]logo|producto|proyecto|ficha|art[ií]culo|"
            r"n[uú]mero|nro|num|n°)\s*#?\s*(\d+)"
        )
        for match in re.finditer(pattern, text, re.IGNORECASE):
            numbers.append(int(match.group(1)))

        if not numbers:
            for match in re.finditer(r"\b(\d{1,4})\b", text):
                numbers.append(int(match.group(1)))

        return list(dict.fromkeys(numbers))

    def extract_search_terms(self, text: str) -> list[str]:
        """Extrae palabras clave de búsqueda del texto omitiendo stop words."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t.strip() for t in cleaned.split() if len(t.strip()) >= 2]
        keywords = [t for t in tokens if t not in STOP_WORDS]
        return keywords

    def detect_query_intent(self, text: str) -> dict[str, bool]:
        """Clasifica la intención operativa del usuario."""
        q = text.lower()
        wants_all = any(
            term in q
            for term in (
                "todos",
                "todas",
                "todo",
                "catalogo completo",
                "catálogo completo",
                "todo el catalogo",
                "todo el catálogo",
                "lista completa",
                "sin importar stock",
                "tanto disponibles como agotados",
                "activos y no activos",
                "activos y agotados",
            )
        )
        wants_available_only = (
            any(
                term in q
                for term in (
                    "disponible",
                    "disponibles",
                    "hay",
                    "tenemos",
                    "tienen",
                    "queda",
                    "quedan",
                    "stock",
                    "existencia",
                    "existencias",
                    "para vender",
                    "para entrega",
                    "para venta",
                )
            )
            and not wants_all
        )
        return {
            "wants_all": wants_all,
            "wants_available_only": wants_available_only,
        }

    def get_global_inventory_summary(self) -> dict[str, Any]:
        """Calcula el total general de fichas maestras y existencias físicas."""
        total_masters = (
            self.session.exec(
                select(func.count(col(ProductMaster.id))).where(
                    ProductMaster.is_active == True  # noqa: E712
                )
            ).one()
            or 0
        )

        total_available = (
            self.session.exec(
                select(func.coalesce(func.sum(Product.available_quantity), 0))
            ).one()
            or 0
        )

        return {
            "total_product_masters": int(total_masters),
            "total_available_units": int(total_available),
        }

    @classmethod
    def get_synonyms(cls, term: str) -> list[str]:
        """Obtiene sinónimos si el término pertenece a una familia semántica."""
        t = term.lower().strip()
        stem = cls.to_stem(t)
        for key, syns in SYNONYM_GROUPS.items():
            if t == key or stem == key or t in syns or stem in syns:
                return syns
        return [term]

    @classmethod
    def _is_valid_keyword_match(cls, kw: str, m: ProductMaster) -> bool:
        """Descarta falsos positivos por subcadenas (ej. 'auto' en 'automático')."""
        kw_clean = kw.lower().strip()
        stem = cls.to_stem(kw_clean)
        synonyms = cls.get_synonyms(kw_clean)

        fields = " ".join(
            filter(
                None,
                [
                    m.name,
                    m.brand,
                    m.model,
                    m.features,
                    m.description,
                ],
            )
        )

        if stem in ("auto", "autos") or "auto" in synonyms:
            # Término automotriz independiente (auto, coche, vehículo), no 'automático'
            syn_patterns = [rf"\b{re.escape(s)}\b" for s in synonyms]
            pattern = "|".join(syn_patterns)
            return bool(re.search(pattern, fields, re.IGNORECASE))

        # Para términos con sinónimos (ej. celular/teléfono), verificar coincidencia
        if len(synonyms) > 1:
            return any(
                re.search(rf"\b{re.escape(s)}", fields, re.IGNORECASE) for s in synonyms
            )

        return True

    @staticmethod
    def extract_cited_item_numbers(reply: str, candidate_numbers: set[int]) -> set[int]:
        """Extrae números de catálogo que el LLM citó explícitamente en su respuesta."""
        cited: set[int] = set()
        # 1. Referencias explícitas: #102, **#102**, Catálogo #102, Ficha 102, (#102)
        pattern_explicit = (
            r"(?:#|cat[aá]logo\s*#?|item\s*#?|ficha\s*#?|producto\s*#?|\()"
            r"\s*\*?\*?#?(\d+)\*?\*?"
        )
        for m in re.finditer(pattern_explicit, reply, re.IGNORECASE):
            num = int(m.group(1))
            if num in candidate_numbers:
                cited.add(num)

        # 2. Primera columna de tablas Markdown: | 102 |, | #102 |, | **102** |
        for m in re.finditer(r"\|\s*\*?\*?#?(\d+)\*?\*?\s*\|", reply):
            num = int(m.group(1))
            if num in candidate_numbers:
                cited.add(num)

        return cited

    def _execute_keyword_search(
        self,
        base_stmt: Any,
        keywords: list[str],
        limit: int,
    ) -> list[ProductMaster]:
        """Búsqueda de keywords con AND/OR y expansión semántica de sinónimos."""
        and_filters = []
        for kw in keywords[:5]:
            stem = self.to_stem(kw)
            synonyms = self.get_synonyms(kw)
            search_terms = list(dict.fromkeys([kw, stem] + synonyms))

            kw_clauses = []
            for term in search_terms:
                kw_clauses.extend(
                    [
                        col(ProductMaster.name).ilike(f"%{term}%"),
                        col(ProductMaster.brand).ilike(f"%{term}%"),
                        col(ProductMaster.model).ilike(f"%{term}%"),
                        col(ProductMaster.features).ilike(f"%{term}%"),
                        col(ProductMaster.description).ilike(f"%{term}%"),
                    ]
                )
            and_filters.append(or_(*kw_clauses))

        strict_stmt = base_stmt.where(and_(*and_filters)).limit(limit * 2)
        strict_matches = list(self.session.exec(strict_stmt).all())
        valid_strict = [
            m
            for m in strict_matches
            if all(self._is_valid_keyword_match(kw, m) for kw in keywords)
        ]
        if valid_strict:
            return valid_strict[:limit]

        or_filters = []
        for kw in keywords[:5]:
            stem = self.to_stem(kw)
            synonyms = self.get_synonyms(kw)
            search_terms = list(dict.fromkeys([kw, stem] + synonyms))
            for term in search_terms:
                or_filters.extend(
                    [
                        col(ProductMaster.name).ilike(f"%{term}%"),
                        col(ProductMaster.brand).ilike(f"%{term}%"),
                        col(ProductMaster.model).ilike(f"%{term}%"),
                        col(ProductMaster.features).ilike(f"%{term}%"),
                        col(ProductMaster.description).ilike(f"%{term}%"),
                    ]
                )

        relaxed_stmt = base_stmt.where(or_(*or_filters)).limit(limit * 2)
        relaxed_matches = list(self.session.exec(relaxed_stmt).all())
        valid_relaxed = [
            m
            for m in relaxed_matches
            if any(self._is_valid_keyword_match(kw, m) for kw in keywords)
        ]
        return valid_relaxed[:limit] if valid_relaxed else relaxed_matches[:limit]

    def search_relevant_products(
        self,
        query: str,
        limit: int = 15,
        intent: dict[str, bool] | None = None,
    ) -> list[MatchedProductContext]:
        """Busca productos coincidentes en el catálogo y extrae stock en vivo."""
        if intent is None:
            intent = self.detect_query_intent(query)

        item_numbers = self.extract_item_numbers(query)
        keywords = self.extract_search_terms(query)
        statement = select(ProductMaster).where(
            ProductMaster.is_active == True  # noqa: E712
        )

        available_subquery = (
            select(Product.master_product_id)
            .where(Product.available_quantity > 0)
            .distinct()
        )

        if item_numbers:
            statement = statement.where(
                col(ProductMaster.item_number).in_(item_numbers)
            )
            masters = list(self.session.exec(statement.limit(limit)).all())
        elif keywords:
            # Si pide disponibles, filtrar stock directamente en BD
            if intent.get("wants_available_only"):
                avail_stmt = statement.where(
                    col(ProductMaster.id).in_(available_subquery)
                )
                masters = self._execute_keyword_search(avail_stmt, keywords, limit)
                # Si no hay disponibles, buscar en catálogo para reportar agotados
                if not masters:
                    masters = self._execute_keyword_search(statement, keywords, limit)
            else:
                masters = self._execute_keyword_search(statement, keywords, limit)
        elif intent.get("wants_available_only"):
            # Trae DIRECTAMENTE los 'limit' productos con stock físico disponible en BD
            statement = (
                statement.where(col(ProductMaster.id).in_(available_subquery))
                .order_by(col(ProductMaster.item_number).desc())
                .limit(limit)
            )
            masters = list(self.session.exec(statement).all())
        else:
            statement = statement.order_by(col(ProductMaster.item_number).desc()).limit(
                limit
            )
            masters = list(self.session.exec(statement).all())

        results: list[MatchedProductContext] = []
        for m in masters:
            stock = self.master_service.get_stock_summary(m.id)
            results.append(
                MatchedProductContext(
                    item_number=m.item_number,
                    name=m.name,
                    brand=m.brand,
                    model=m.model,
                    available_stock=stock["available"],
                    sold_stock=stock["sold"],
                    official_price=m.official_price,
                    published_price=m.published_price,
                    minimum_price=m.minimum_price,
                    currency=m.currency or "BOB",
                    features=m.features,
                    description=m.description,
                )
            )

        # Priorizar productos que tienen existencias disponibles para venta
        results.sort(
            key=lambda x: (x.available_stock > 0, x.item_number or 0),
            reverse=True,
        )

        return results

    def build_system_prompt(
        self,
        products: list[MatchedProductContext],
        global_summary: dict[str, Any],
        intent: dict[str, bool] | None = None,
        item_numbers: list[int] | None = None,
    ) -> str:
        """Construye un prompt de alta precisión aplicando ingeniería de contexto."""
        intent = intent or {"wants_all": False, "wants_available_only": False}
        wants_avail_only = intent.get("wants_available_only", False)

        tot_m = global_summary.get("total_product_masters", 0)
        tot_u = global_summary.get("total_available_units", 0)

        available_items = [p for p in products if p.available_stock > 0]
        out_of_stock_items = [p for p in products if p.available_stock <= 0]

        lines = [
            "Eres el Asistente Ejecutivo de Inventario y Ventas de Uyuni ERP.",
            "Tu interlocutor es el DUEÑO o GERENTE DE MERCADERÍA del negocio.",
            "Tu rol es proveer información rápida, ejecutiva y estratégica "
            "sobre stock real, precios de lista y pisos de regateo.",
            "",
            "### REGLAS DE ORO DE INVENTARIO Y OPERACIÓN COMERCIAL:",
            "1. RELEVANCIA FUNCIONAL: Analiza la intención real de la consulta.",
            "   - Si piden 'proyector', refiere únicamente a equipos cuya función "
            "principal sea proyectar.",
            "   - Descarta accesorios, repuestos o consumibles (ej: bombillas, "
            "focos, soportes o cables) salvo que se pregunten expresamente.",
            "2. ESTRATEGIA COMERCIAL DE PRECIOS Y MARGEN DE NEGOCIACIÓN:",
            "   - 'P. Publicado' (PRECIO PRINCIPAL DE VENTA AL CLIENTE): Precio",
            "     oficial publicado en Marketplace/redes. Es el monto base a cotizar.",
            "   - 'Piso Regateo' (MÍNIMO PROTEGIDO): Límite mínimo de venta",
            "     autorizado si el cliente pide rebaja sin perder rentabilidad.",
            "     * MARGEN REGATEO = (P. Publicado - Piso Regateo). Indica margen",
            "       para que el operador sepa exactamente cuánto puede ceder.",
            "     * CASO PRECIO FIJO: Si P. Publicado == Piso Regateo (margen = 0),",
            "       aclara explícitamente: 'Precio Fijo / Sin margen de regateo'.",
            "   - 'P. Lista' (REFERENCIA DE MERCADO): Precio investigado en mercado",
            "     local (Bolivia). Ancla referencial para argumentar ahorro.",
            "3. CRITERIO DE RESPUESTA SEGÚN INTENCIÓN:",
            "   - SI PREGUNTAN POR DISPONIBLES O EXISTENCIAS:",
            "     * Si HAY productos con stock disponible: Céntrate 100% en ellos.",
            "       - Si son hasta 10 productos disponibles: Presenta tabla completa:",
            "         Catálogo #, Producto, Stock, P. Publicado, Piso, P. Lista.",
            "       - Si son más de 10 productos: Presenta un resumen ejecutivo ágil "
            "(unidades totales, categorías y rango de precios) con tabla concisa "
            "de los 8 más destacados, e indica al operador que puede explorar la "
            "lista completa en las tarjetas interactivas de abajo.",
            "       NO muestres tablas de productos agotados. Si hay otros modelos "
            "en catálogo, menciónalos solo con nota breve al pie: "
            "'(Nota: Existen X modelos más registrados en catálogo sin stock)'.",
            "     * Si NO HAY stock disponible: Explica con claridad que no hay "
            "unidades físicas en almacén y lista los modelos en catálogo "
            "con Stock: 0 para evaluar compras o preventa.",
            "   - SI PIDEN EXPRESAMENTE TODOS LOS PRODUCTOS O EL CATÁLOGO COMPLETO:",
            "     * Presenta tanto los disponibles como los agotados organizados.",
            "   - REGLA DE REFERENCIA: Al mencionar productos en tablas o texto, "
            "incluye SIEMPRE su número de catálogo con formato #XX (ej: #94) para "
            "sincronizar las tarjetas interactivas de la interfaz.",
            "4. CERO ALUCINACIONES: NUNCA inventes números de catálogo, cantidades "
            "ni precios.",
            "5. ESTILO: Directo, ejecutivo, en Markdown limpio y al punto.",
            "",
            "### RESUMEN GLOBAL DEL ALMACÉN:",
            f"- Total de fichas maestras registradas: {tot_m}",
            f"- Total de unidades físicas disponibles en almacén: {tot_u}",
            "",
            "### DATOS DE INVENTARIO EN TIEMPO REAL:",
        ]

        # Si el operador consultó un número de catálogo específico
        if item_numbers and not products:
            num = item_numbers[0]
            lines.append(
                f"\n--- [CONSULTA POR FICHA #{num}: NO REGISTRADA] ---\n"
                f"El operador consultó información de la Ficha #{num}, pero NO "
                "existe ninguna ficha registrada con ese número en el sistema. "
                f"Infórmale de forma directa y clara que el ítem #{num} no existe."
            )
        elif item_numbers and products:
            num = item_numbers[0]
            lines.append(
                f"\n--- [CONSULTA DIRECTA POR FICHA #{num}: CONFIRMADA EN BD] ---\n"
                f"¡CONFIRMADO EN BASE DE DATOS! La Ficha #{num} SÍ existe en Uyuni.\n"
                "Ignora mensajes previos del historial que dijeran que no existía.\n"
                "Presenta con prioridad la ficha solicitada: nombre completo,\n"
                "specs técnicas, P. Publicado (precio oficial de venta al cliente),\n"
                "Piso Regateo (con margen de rebaja o indicando Precio Fijo),\n"
                "P. Lista (referencia mercado) y stock físico provisto abajo."
            )

        if available_items:
            lines.append("--- [PRODUCTOS CON STOCK DISPONIBLE PARA VENTA] ---")
            for p in available_items:
                item_ref = (
                    f"Catálogo #{p.item_number}" if p.item_number else "Sin número"
                )
                brand_model = f"{p.brand or ''} {p.model or ''}".strip()
                specs = p.features or p.description or "Sin detalles adicionales"
                if len(specs) > 250:
                    specs = specs[:247] + "..."

                pub_val = (
                    p.published_price
                    if p.published_price is not None
                    else p.official_price
                )
                margin = max(0.0, pub_val - p.minimum_price)
                if margin > 0:
                    reg_note = f"Margen regateo: {margin:.2f} {p.currency}"
                else:
                    reg_note = "PRECIO FIJO (Sin margen de rebaja)"

                lines.append(
                    f"* [{item_ref}] {p.name} | "
                    f"Marca: {brand_model or 'N/A'} | "
                    f"DISPONIBLE: {p.available_stock} unid. "
                    f"(Vendidos históricos: {p.sold_stock}) | "
                    f"P. Publicado (Venta Cliente): {pub_val:.2f} {p.currency} | "
                    f"Piso Regateo: {p.minimum_price:.2f} {p.currency} ({reg_note}) | "
                    f"P. Lista (Ref. Mercado): {p.official_price:.2f} {p.currency} | "
                    f"Detalles: {specs}"
                )
        else:
            lines.append("--- [NO HAY PRODUCTOS COINCIDENTES CON STOCK DISPONIBLE] ---")

        if out_of_stock_items:
            # Si el usuario solo pidió disponibles y SÍ tenemos disponibles,
            # no saturar el prompt con la lista exhaustiva de agotados.
            if wants_avail_only and available_items:
                lines.append(
                    f"\n--- [INFORMACIÓN ADICIONAL: Hay {len(out_of_stock_items)} "
                    "modelos en catálogo con Stock 0 "
                    "(No listar en detalle salvo nota breve)] ---"
                )
            else:
                lines.append(
                    "\n--- [PRODUCTOS EN CATÁLOGO ACTUALMENTE AGOTADOS (Stock: 0)] ---"
                )
                for p in out_of_stock_items:
                    item_ref = (
                        f"Catálogo #{p.item_number}" if p.item_number else "Sin número"
                    )
                    brand_model = f"{p.brand or ''} {p.model or ''}".strip()
                    pub_val = (
                        p.published_price
                        if p.published_price is not None
                        else p.official_price
                    )
                    lines.append(
                        f"* [{item_ref}] {p.name} | "
                        f"Marca: {brand_model or 'N/A'} | "
                        f"STOCK: 0 unid. (Agotado) | "
                        f"P. Publicado Ref: {pub_val:.2f} {p.currency} | "
                        f"Piso Mínimo Ref: {p.minimum_price:.2f} {p.currency} | "
                        f"P. Lista Ref: {p.official_price:.2f} {p.currency}"
                    )

        return "\n".join(lines)

    def handle_chat(self, request: ChatAssistantRequest) -> ChatAssistantResponse:
        """Procesa una consulta, busca inventario y consulta al LLM."""
        matched_products: list[MatchedProductContext] = []
        global_summary = self.get_global_inventory_summary()
        intent = self.detect_query_intent(request.message)
        item_numbers = self.extract_item_numbers(request.message)

        # Si se solicita stock o si el usuario pregunta por una ficha específica,
        # consultamos siempre la base de datos para garantizar datos en vivo.
        keywords = self.extract_search_terms(request.message)
        if request.include_stock_data or item_numbers:
            # Para búsquedas semánticas por palabras clave, ampliamos el pool de
            # candidatos (35) para que el LLM disponga de todo el universo relevante.
            candidate_limit = 35 if keywords else 15
            matched_products = self.search_relevant_products(
                request.message, limit=candidate_limit, intent=intent
            )

        system_prompt = self.build_system_prompt(
            matched_products,
            global_summary,
            intent,
            item_numbers=item_numbers,
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Sanitizar historial para no duplicar el mensaje actual
        history = request.history[-8:]
        if (
            history
            and history[-1].role == "user"
            and history[-1].content.strip() == request.message.strip()
        ):
            history = history[:-1]

        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": request.message})

        reply, provider_used, model_used, fallback_occurred = call_llm(
            messages=messages,
            requested_provider=request.provider,
            requested_model=request.model,
        )

        # Sincronización inteligente entre respuesta LLM y tarjetas del front:
        keywords = self.extract_search_terms(request.message)
        candidate_ids = {
            p.item_number for p in matched_products if p.item_number is not None
        }
        cited_ids = self.extract_cited_item_numbers(reply, candidate_ids)
        available_products = [p for p in matched_products if p.available_stock > 0]

        if item_numbers:
            # Si consultó por número de ficha específico, mostrar esa ficha exacta
            ui_products = matched_products
        elif keywords and cited_ids:
            ui_products = [p for p in matched_products if p.item_number in cited_ids]
        elif intent["wants_available_only"] and available_products:
            ui_products = available_products
        else:
            ui_products = matched_products

        return ChatAssistantResponse(
            reply=reply,
            provider_used=provider_used,
            model_used=model_used,
            matched_products=ui_products,
            fallback_occurred=fallback_occurred,
        )
