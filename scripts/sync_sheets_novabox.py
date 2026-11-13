"""
Nova Box Bolivia - Script de Migración y Sincronización ETL
Sincroniza los datos del Google Sheet comercial
hacia la base de datos de Uyuni ERP (PostgreSQL / SQLite).

Uso:
    # Cargar en base de datos SQLite local para pruebas y desarrollo
    venv/bin/python scripts/sync_sheets_novabox.py --sqlite data/novabox.db

    # Cargar en PostgreSQL según .env (DATABASE_URL)
    venv/bin/python scripts/sync_sheets_novabox.py

    # Simular sin escribir en base de datos
    venv/bin/python scripts/sync_sheets_novabox.py --dry-run

    # Refrescar caché desde Google Sheets antes de migrar
    venv/bin/python scripts/sync_sheets_novabox.py --refresh-cache
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import date, datetime
from typing import Any

# Setup import path for the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, SQLModel, create_engine, delete, select

from app.core.config import settings
from app.modules.commerce.batches.models import Batch
from app.modules.commerce.categories.models import Category
from app.modules.commerce.channels.models import SalesChannel
from app.modules.commerce.live_baskets.models import LiveBasket
from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.products.models import Product
from app.modules.commerce.rounds.models import InvestmentRound
from app.modules.commerce.sales.models import Sale, SaleItem

SPREADSHEET_ID = "1FKrYWIZfjAk_uXwyJ8Wi1-2OQlfzzEEkWP8OZHp03sQ"

# Reglas de unificación de duplicados entre lotes
UNIFICATIONS = {
    165: (53, "Modelo TK-HP2412"),
    220: (61, "Sistema Solar K9"),
}
PRIMARY_VARIANTS = {
    53: "Calor Seco y Húmedo",
    61: "Modelo Luna",
}


# ==========================================
# UTILIDADES DE LIMPIEZA Y NORMALIZACIÓN
# ==========================================
def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def clean_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    # Quitar "Bs.", "%", comas de miles y espacios
    s = re.sub(r"[^\d.-]", "", s.replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return default


def clean_int(val: Any, default: int = 0) -> int:
    f = clean_float(val, float(default))
    return int(round(f))


def clean_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("TRUE", "1", "SI", "S", "VERDADERO")


def clean_date(val: Any) -> date | None:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None

    # Probar formatos comunes: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def clean_datetime(val: Any) -> datetime:
    d = clean_date(val)
    if d:
        return datetime.combine(d, datetime.min.time())
    return datetime.now()


def normalize_condition(val: Any) -> str:
    s = clean_str(val).upper()
    if "DAÑ" in s or "MERMA" in s or "DAMAGED" in s:
        return "DAMAGED_SCRAP"
    if "REPUESTO" in s or "PARTS" in s:
        return "FOR_PARTS"
    if "INCOMPLETO" in s or "SIN CAJA" in s:
        return "INCOMPLETE"
    if "REPARADO" in s or "REPAIRED" in s:
        return "REPAIRED"
    return "OPERATIONAL"


def normalize_status(
    raw_val: Any, sold_qty: int, merma_qty: int, avail_qty: int
) -> str:
    s = clean_str(raw_val).upper()
    if "MERMA" in s or "DAÑ" in s or "SCRAP" in s:
        return "SCRAPPED"
    if "RESERV" in s:
        return "RESERVED"
    if "AGOTADO" in s or "VENDIDO" in s or "SOLD" in s:
        return "SOLD_OUT"
    if avail_qty <= 0:
        return "SCRAPPED" if (merma_qty > 0 and sold_qty == 0) else "SOLD_OUT"
    return "AVAILABLE"


def normalize_round_status(val: Any) -> str:
    s = clean_str(val).upper()
    if "GANANCIA" in s or "RECUPERADO" in s:
        return "RECOVERED"
    if "TABLAS" in s or "BREAKEVEN" in s:
        return "NEAR_BREAKEVEN"
    if "RECUPERACI" in s:
        return "IN_RECOVERY"
    return "ACTIVE"


def normalize_payment_status(val: Any) -> str:
    s = clean_str(val).upper()
    if "PENDIENTE" in s:
        return "PENDING"
    if "CORTES" in s or "0 BS" in s or "REGALO" in s or "SORTEO" in s:
        return "COURTESY"
    if "REEMBOLSO" in s or "DEVOLUCI" in s:
        return "REFUNDED"
    return "COLLECTED"


def normalize_delivery_modality(val: Any) -> str:
    s = clean_str(val).upper()
    if "DOMICILIO" in s:
        return "HOME_DELIVERY"
    if "FLOTA" in s or "TERMINAL" in s:
        return "TERMINAL_BUS"
    if "COURIER" in s or "NACIONAL" in s:
        return "NATIONAL_COURIER"
    if "TIQUIPAYA" in s or "RECOJO" in s or "TIENDA" in s:
        return "STORE_PICKUP_TIQUIPAYA"
    if "PAQUETERIA" in s:
        return "PARCEL_SERVICE"
    return "FREE_MEETING_POINT"


def normalize_delivery_paid_by(val: Any) -> str:
    s = clean_str(val).upper()
    if "CLIENTE" in s:
        return "CUSTOMER"
    if "NOVA" in s or "TIENDA" in s:
        return "STORE"
    return "FREE"


def normalize_payment_method(val: Any) -> str:
    s = clean_str(val).upper()
    if "EFECTIVO" in s or "CASH" in s:
        return "CASH"
    if "TRANSF" in s:
        return "TRANSFER"
    if "CORTES" in s or "REGALO" in s:
        return "COURTESY"
    return "QR"


def normalize_delivery_status(val: Any) -> str:
    s = clean_str(val).upper()
    if "PENDIENTE" in s:
        return "PENDING"
    if "FLOTA" in s or "ENVIADO" in s:
        return "SHIPPED"
    return "DELIVERED"


DEFAULT_CHANNELS = [
    ("MARKETPLACE", "Marketplace", "Ventas originadas en Facebook Marketplace"),
    ("TIKTOK_LIVE", "TikTok Live", "Ventas en vivo por streaming de TikTok"),
    (
        "WHATSAPP_STATUS",
        "Estados WhatsApp",
        "Ventas por catálogo en estados de WhatsApp",
    ),
    (
        "WHATSAPP_VIP",
        "Grupo VIP WhatsApp",
        "Ventas al grupo VIP exclusivo de WhatsApp",
    ),
    (
        "FAMILY_FRIENDS",
        "Familia / Amigo",
        "Ventas directas a familiares y círculo cercano",
    ),
    (
        "RESELLER",
        "Revendedor / Distribuidor",
        "Ventas canalizadas a través de revendedores o aliados",
    ),
    ("OTHER", "Otro", "Otros canales no categorizados"),
]


# ==========================================
# EXTRACCIÓN Y CACHÉ
# ==========================================
SHEETS_CONFIG = {
    "categorias_catalogo": "Categorias_Catalogo!A1:Z50",
    "canastas_live": "Canastas_Live!A1:Z50",
    "rondas_inversion": "Rondas_Inversion!A1:Z50",
    "cajas_lotes": "Cajas_Lotes!A1:Z50",
    "inventario_general": "Inventario_General!A1:Z1000",
    "ventas": "Ventas!A1:Z1000",
}


def refresh_cache_from_sheets(cache_dir: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    print(f"📥 Refrescando caché desde Google Sheets ({SPREADSHEET_ID})...")
    for name, sheet_range in SHEETS_CONFIG.items():
        dest = os.path.join(cache_dir, f"{name}.json")
        cmd = [
            "gsheets",
            "readonly",
            "read",
            SPREADSHEET_ID,
            sheet_range,
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"❌ Error al leer {name}: {res.stderr}")
            sys.exit(1)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(res.stdout)
        print(f"  ✓ {name} guardado en {dest}")


def load_cached_sheet(cache_dir: str, name: str) -> list[list[Any]]:
    path = os.path.join(cache_dir, f"{name}.json")
    if not os.path.exists(path):
        print(f"❌ Archivo de caché no encontrado: {path}")
        print("Ejecuta con --refresh-cache para descargarlo.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# ETL: MIGRACIÓN A LA BASE DE DATOS
# ==========================================
def run_migration(cache_dir: str, db_url: str, dry_run: bool = False) -> None:
    print(f"\n🚀 Iniciando Migración ETL hacia: {db_url}")
    if dry_run:
        print("⚠️ MODO DRY-RUN: No se guardarán cambios en la base de datos.")

    # Conectar o crear base de datos
    engine = create_engine(db_url, echo=False)
    SQLModel.metadata.create_all(engine)

    stats = {
        "categories": 0,
        "channels": 0,
        "live_baskets": 0,
        "rounds": 0,
        "batches": 0,
        "products": 0,
        "sales": 0,
        "sale_items": 0,
    }

    category_map: dict[str, uuid.UUID] = {}
    channel_map: dict[str, dict[str, Any]] = {}
    live_basket_map: dict[str, uuid.UUID] = {}
    round_map: dict[str, uuid.UUID] = {}
    batch_map: dict[str, uuid.UUID] = {}
    product_sku_map: dict[str, uuid.UUID] = {}
    product_id_map: dict[int, uuid.UUID] = {}
    product_name_map: dict[str, uuid.UUID] = {}

    with Session(engine) as session:
        # ----------------------------------------------------
        # 1. CATEGORÍAS (Categorias_Catalogo)
        # ----------------------------------------------------
        print("\n[1/6] Migrando Categorías...")
        cat_data = load_cached_sheet(cache_dir, "categorias_catalogo")
        for row in cat_data[1:]:
            if not row or len(row) < 2 or not clean_str(row[0]):
                continue
            code = clean_str(row[0])  # CAT-01
            name = clean_str(row[1])  # Hogar & Iluminación
            icon = clean_str(row[2]) if len(row) > 2 else None
            desc = clean_str(row[3]) if len(row) > 3 else None
            typical = clean_str(row[4]) if len(row) > 4 else None

            existing = session.exec(
                select(Category).where(Category.code == code)
            ).first()
            if not existing:
                category = Category(
                    code=code,
                    name=name,
                    icon=icon,
                    description=desc,
                    typical_products=typical,
                )
                if not dry_run:
                    session.add(category)
                    session.flush()
                cat_id = category.id
            else:
                existing.name = name
                existing.icon = icon
                existing.description = desc
                existing.typical_products = typical
                if not dry_run:
                    session.add(existing)
                    session.flush()
                cat_id = existing.id

            category_map[code.upper()] = cat_id
            category_map[name.strip().lower()] = cat_id
            stats["categories"] += 1

        print(f"  ✓ {stats['categories']} categorías procesadas.")

        # ----------------------------------------------------
        # CANALES DE VENTA (commerce_channel)
        # ----------------------------------------------------
        print("\n[*] Sincronizando Canales de Venta...")
        # Deprecar TIKTOK_GIVEAWAY si existe y no tiene ventas
        deprecated_giveaway = session.exec(
            select(SalesChannel).where(SalesChannel.code == "TIKTOK_GIVEAWAY")
        ).first()
        if deprecated_giveaway and not dry_run:
            if not deprecated_giveaway.sales:
                session.delete(deprecated_giveaway)
                session.flush()

        for ch_code, ch_name, ch_desc in DEFAULT_CHANNELS:
            existing_ch = session.exec(
                select(SalesChannel).where(SalesChannel.code == ch_code)
            ).first()
            if not existing_ch:
                ch = SalesChannel(
                    code=ch_code,
                    name=ch_name,
                    description=ch_desc,
                    is_active=True,
                )
                if not dry_run:
                    session.add(ch)
                    session.flush()
                c_id = ch.id
            else:
                existing_ch.name = ch_name
                existing_ch.description = ch_desc
                if not dry_run:
                    session.add(existing_ch)
                    session.flush()
                c_id = existing_ch.id

            channel_map[ch_name.strip().lower()] = {"id": c_id, "code": ch_code}
            channel_map[ch_code.strip().lower()] = {"id": c_id, "code": ch_code}
            stats["channels"] += 1

        print(f"  ✓ {stats['channels']} canales de venta sincronizados.")

        # ----------------------------------------------------
        # 2. CANASTAS LIVE (Canastas_Live)
        # ----------------------------------------------------
        print("\n[2/6] Migrando Canastas para Live...")
        basket_data = load_cached_sheet(cache_dir, "canastas_live")
        for row in basket_data[1:]:
            if not row or len(row) < 3 or not clean_str(row[0]):
                continue
            code = clean_str(row[0])  # C1
            name = clean_str(row[1])  # Taller & Auto
            label = clean_str(row[2])  # Canasta 1 - Taller & Auto
            desc = clean_str(row[3]) if len(row) > 3 else None
            p_range = clean_str(row[4]) if len(row) > 4 else None
            target = clean_str(row[5]) if len(row) > 5 else None

            existing = session.exec(
                select(LiveBasket).where(LiveBasket.code == code)
            ).first()
            if not existing:
                basket = LiveBasket(
                    code=code,
                    name=name,
                    label=label,
                    description=desc,
                    price_range=p_range,
                    target_audience=target,
                )
                if not dry_run:
                    session.add(basket)
                    session.flush()
                b_id = basket.id
            else:
                existing.name = name
                existing.label = label
                existing.description = desc
                existing.price_range = p_range
                existing.target_audience = target
                if not dry_run:
                    session.add(existing)
                    session.flush()
                b_id = existing.id

            live_basket_map[code.upper()] = b_id
            live_basket_map[name.strip().lower()] = b_id
            live_basket_map[label.strip().lower()] = b_id
            stats["live_baskets"] += 1

        print(f"  ✓ {stats['live_baskets']} canastas live procesadas.")

        # ----------------------------------------------------
        # 3. RONDAS DE INVERSIÓN (Rondas_Inversion)
        # ----------------------------------------------------
        print("\n[3/6] Migrando Rondas de Inversión...")
        round_data = load_cached_sheet(cache_dir, "rondas_inversion")
        round_by_num: dict[int, uuid.UUID] = {}

        # Limpiar ronda fantasma previa si existía por fila de encabezado
        if not dry_run:
            session.exec(
                delete(InvestmentRound).where(
                    InvestmentRound.name == "Ronda de Inversión"
                )
            )
            session.flush()

        for row in round_data:
            if not row or len(row) < 5:
                continue
            name_raw = clean_str(row[1])
            m = re.match(r"^ronda\s+(\d+)", name_raw.strip(), re.IGNORECASE)
            if not m:
                continue

            round_num = int(m.group(1))
            code = f"RONDA-{str(round_num).zfill(2)}"
            disb_date = clean_date(row[3])
            capital = clean_float(row[4])
            raw_status = clean_str(row[10]) if len(row) > 10 else "active"
            status = normalize_round_status(raw_status)
            obs = raw_status if raw_status else None

            existing = session.exec(
                select(InvestmentRound).where(
                    (InvestmentRound.code == code) | (InvestmentRound.name == name_raw)
                )
            ).first()
            if not existing:
                inv_round = InvestmentRound(
                    code=code,
                    name=name_raw,
                    disbursement_date=disb_date,
                    capital_invested=capital,
                    currency="BOB",
                    status=status,
                    observations=obs,
                )
                if not dry_run:
                    session.add(inv_round)
                    session.flush()
                r_id = inv_round.id
            else:
                existing.code = code
                existing.name = name_raw
                existing.disbursement_date = disb_date
                existing.capital_invested = capital
                existing.currency = "BOB"
                existing.status = status
                existing.observations = obs
                if not dry_run:
                    session.add(existing)
                    session.flush()
                r_id = existing.id

            round_map[name_raw.strip().lower()] = r_id
            round_by_num[round_num] = r_id
            stats["rounds"] += 1

        print(f"  ✓ {stats['rounds']} rondas de inversión procesadas.")

        # ----------------------------------------------------
        # 4. CAJAS / LOTES (Cajas_Lotes)
        # ----------------------------------------------------
        print("\n[4/6] Migrando Cajas y Lotes...")
        batch_data = load_cached_sheet(cache_dir, "cajas_lotes")
        for row in batch_data[1:]:
            if not row or len(row) < 7:
                continue
            name = clean_str(row[1])
            if not name or "totales" in name.lower():
                continue

            ronda_name = clean_str(row[2]).lower()
            p_date = clean_date(row[3])
            provider = clean_str(row[4])
            batch_type = clean_str(row[5])
            p_price = clean_float(row[6])
            freight = clean_float(row[7]) if len(row) > 7 else 0.0
            initial_items = clean_int(row[9]) if len(row) > 9 else 0
            merma_items = clean_int(row[10]) if len(row) > 10 else 0
            obs = clean_str(row[23]) if len(row) > 23 else None

            # Asignar código uniforme
            code = (
                name.upper().replace(" ", "-").replace("(", "").replace(")", "").strip()
            )

            # Buscar ronda relacionada (1ra -> Ronda 1, 2da -> Ronda 2, 3ra -> Ronda 3)
            r_id = None
            r_lower = ronda_name.lower()
            b_lower = name.lower()
            if (
                "1" in r_lower
                or "1ra" in r_lower
                or "piloto" in r_lower
                or "digital" in b_lower
            ):
                r_id = round_by_num.get(1)
            elif (
                "2" in r_lower
                or "2da" in r_lower
                or "combo" in r_lower
                or "ataud 1" in b_lower
                or "amazon" in b_lower
            ):
                r_id = round_by_num.get(2)
            elif (
                "3" in r_lower
                or "3ra" in r_lower
                or "re-invers" in r_lower
                or "ataud 2" in b_lower
            ):
                r_id = round_by_num.get(3)

            existing = session.exec(select(Batch).where(Batch.name == name)).first()
            if not existing:
                batch = Batch(
                    code=code,
                    name=name,
                    investment_round_id=r_id,
                    provider=provider,
                    batch_type=batch_type,
                    purchase_date=p_date,
                    purchase_price=p_price,
                    freight_cost=freight,
                    total_cost=round(p_price + freight, 2),
                    currency="BOB",
                    initial_items_count=initial_items,
                    merma_items_count=merma_items,
                    sellable_items_count=max(0, initial_items - merma_items),
                    unit_cost=(
                        round(
                            (p_price + freight) / (initial_items - merma_items),
                            2,
                        )
                        if (initial_items - merma_items) > 0
                        else 0.0
                    ),
                    observations=obs,
                )
                if not dry_run:
                    session.add(batch)
                    session.flush()
                b_id = batch.id
            else:
                existing.investment_round_id = r_id
                existing.purchase_price = p_price
                existing.freight_cost = freight
                existing.total_cost = round(p_price + freight, 2)
                existing.currency = "BOB"
                existing.initial_items_count = initial_items
                existing.merma_items_count = merma_items
                existing.sellable_items_count = max(0, initial_items - merma_items)
                if existing.sellable_items_count > 0:
                    existing.unit_cost = round(
                        existing.total_cost / existing.sellable_items_count,
                        2,
                    )
                existing.observations = obs
                if not dry_run:
                    session.add(existing)
                    session.flush()
                b_id = existing.id

            batch_map[name.strip().lower()] = b_id
            batch_map[code.strip().lower()] = b_id
            stats["batches"] += 1

        print(f"  ✓ {stats['batches']} cajas / lotes procesados.")

        # ----------------------------------------------------
        # 5. INVENTARIO DE PRODUCTOS (Inventario_General)
        # ----------------------------------------------------
        print("\n[5/6] Migrando Catálogo de Productos...")
        inv_data = load_cached_sheet(cache_dir, "inventario_general")
        for row in inv_data[1:]:
            if not row or len(row) < 3 or not clean_str(row[1]):
                continue

            sheet_row_id = clean_int(row[0])
            name = clean_str(row[1])
            caja_origen = clean_str(row[2]).lower()
            categoria_str = clean_str(row[3]).lower()
            marca = clean_str(row[4]) if len(row) > 4 else None
            modelo = clean_str(row[5]) if len(row) > 5 else None
            init_qty = clean_int(row[6]) if len(row) > 6 else 1
            sold_qty = clean_int(row[7]) if len(row) > 7 else 0
            merma_qty = clean_int(row[8]) if len(row) > 8 else 0
            avail_qty = (
                clean_int(row[9])
                if len(row) > 9
                else max(0, init_qty - sold_qty - merma_qty)
            )
            raw_status = row[10] if len(row) > 10 else None
            status = normalize_status(raw_status, sold_qty, merma_qty, avail_qty)

            p_oficial = clean_float(row[11]) if len(row) > 11 else 0.0
            p_minimo = clean_float(row[12]) if len(row) > 12 else p_oficial
            p_pub = clean_float(row[13]) if len(row) > 13 else p_oficial
            condicion = normalize_condition(row[14] if len(row) > 14 else None)
            detalle_falla = clean_str(row[15]) if len(row) > 15 else None
            revisado = clean_bool(row[16]) if len(row) > 16 else False
            fb_verif = clean_bool(row[17]) if len(row) > 17 else False
            video = clean_bool(row[18]) if len(row) > 18 else False
            pub_fb = clean_bool(row[19]) if len(row) > 19 else False
            url_fb = clean_str(row[20]) if len(row) > 20 else None
            url_info = clean_str(row[21]) if len(row) > 21 else None
            specs = clean_str(row[22]) if len(row) > 22 else None
            marketing = clean_str(row[23]) if len(row) > 23 else None
            canasta_str = clean_str(row[24]).lower() if len(row) > 24 else None
            wa_pub = clean_bool(row[25]) if len(row) > 25 else False

            sku = f"NOV-{str(sheet_row_id).zfill(3)}"

            # Resolver batch_id
            batch_id = None
            for b_name, b_uuid in batch_map.items():
                if b_name in caja_origen or caja_origen in b_name:
                    batch_id = b_uuid
                    break

            # Resolver category_id
            category_id = None
            for c_name, c_uuid in category_map.items():
                if c_name in categoria_str or categoria_str in c_name:
                    category_id = c_uuid
                    break

            # Resolver live_basket_id
            basket_id = None
            if canasta_str:
                for bsk_name, bsk_uuid in live_basket_map.items():
                    if bsk_name in canasta_str or canasta_str in bsk_name:
                        basket_id = bsk_uuid
                        break

            # Resolver o crear ProductMaster
            target_master_num = sheet_row_id
            variant_name = PRIMARY_VARIANTS.get(sheet_row_id)
            if sheet_row_id in UNIFICATIONS:
                target_master_num, variant_name = UNIFICATIONS[sheet_row_id]

            master = session.exec(
                select(ProductMaster).where(
                    ProductMaster.item_number == target_master_num
                )
            ).first()

            if not master and not dry_run:
                master = ProductMaster(
                    item_number=target_master_num,
                    code=str(target_master_num),
                    name=name,
                    description=specs,
                    category_id=category_id,
                    live_basket_id=basket_id,
                    brand=marca,
                    model=modelo,
                    official_price=p_oficial,
                    minimum_price=p_minimo,
                    published_price=p_pub,
                    currency="BOB",
                    marketplace_url=url_fb,
                    external_info_url=url_info,
                    features=specs,
                    marketing_details=marketing,
                    is_reviewed=revisado,
                    is_fb_verified=fb_verif,
                    has_video=video,
                    is_published_marketplace=pub_fb,
                    is_whatsapp_published=wa_pub,
                    is_active=True,
                )
                session.add(master)
                session.flush()
            elif master and not dry_run:
                if basket_id:
                    master.live_basket_id = basket_id
                master.marketplace_url = url_fb
                master.is_published_marketplace = pub_fb
                master.is_whatsapp_published = wa_pub
                master.is_fb_verified = fb_verif
                session.add(master)

            master_id = master.id if master else None

            existing = session.exec(
                select(Product).where(Product.sheet_row_id == sheet_row_id)
            ).first()
            if not existing:
                product = Product(
                    master_product_id=master_id,
                    batch_id=batch_id,
                    sheet_row_id=sheet_row_id,
                    variant_name=variant_name,
                    initial_quantity=init_qty,
                    sold_quantity=sold_qty,
                    merma_quantity=merma_qty,
                    available_quantity=avail_qty,
                    status=status,
                    physical_condition=condicion,
                    defect_detail=detalle_falla,
                    is_reviewed=revisado,
                )
                if not dry_run:
                    session.add(product)
                    session.flush()
                p_id = product.id
            else:
                existing.master_product_id = master_id
                existing.batch_id = batch_id
                existing.variant_name = variant_name
                existing.initial_quantity = init_qty
                existing.sold_quantity = sold_qty
                existing.merma_quantity = merma_qty
                existing.available_quantity = avail_qty
                existing.status = status
                existing.physical_condition = condicion
                existing.defect_detail = detalle_falla
                existing.is_reviewed = revisado
                if not dry_run:
                    session.add(existing)
                    session.flush()
                p_id = existing.id
                if not dry_run:
                    session.add(existing)
                    session.flush()
                p_id = existing.id

            product_sku_map[sku] = p_id
            product_id_map[sheet_row_id] = p_id
            product_name_map[name.strip().lower()] = p_id
            stats["products"] += 1

        print(f"  ✓ {stats['products']} productos procesados.")

        # ----------------------------------------------------
        # 6. VENTAS Y DETALLE (Ventas)
        # ----------------------------------------------------
        print("\n[6/6] Migrando Historial Transaccional de Ventas...")
        ventas_data = load_cached_sheet(cache_dir, "ventas")
        for row in ventas_data[1:]:
            if (
                not row
                or len(row) < 4
                or not clean_str(row[0])
                or not clean_str(row[3])
            ):
                continue

            sheet_sale_id = clean_int(row[0])
            sale_date = clean_datetime(row[1]) if len(row) > 1 else datetime.now()
            sheet_prod_id = clean_int(row[2]) if len(row) > 2 else 0
            prod_name = clean_str(row[3])
            qty = clean_int(row[5]) if len(row) > 5 else 1
            customer = clean_str(row[6]) if len(row) > 6 else "Cliente Casual"
            phone = clean_str(row[7]) if len(row) > 7 else None
            channel = clean_str(row[8]) if len(row) > 8 else "Marketplace"
            official_p = clean_float(row[9]) if len(row) > 9 else 0.0
            delivery_mod = (
                clean_str(row[10]) if len(row) > 10 else "Punto de Encuentro Gratis"
            )
            delivery_addr = clean_str(row[11]) if len(row) > 11 else None
            delivery_cost = clean_float(row[12]) if len(row) > 12 else 0.0
            delivery_paid_by = clean_str(row[13]) if len(row) > 13 else "Sin Costo"
            total_collected = clean_float(row[14]) if len(row) > 14 else 0.0
            payment_method = clean_str(row[15]) if len(row) > 15 else "QR"
            payment_status = clean_str(row[16]) if len(row) > 16 else "Cobrado"
            delivery_status = clean_str(row[17]) if len(row) > 17 else "Entregado"
            obs = clean_str(row[18]) if len(row) > 18 else None

            # Resolver canal de venta
            c_clean = channel.strip().lower()
            if "regalo" in c_clean or "sorteo" in c_clean:
                c_clean = "tiktok live"
                if not payment_status or payment_status.strip().lower() == "cobrado":
                    payment_status = "Cortesía / 0 Bs"
            elif (
                "comision" in c_clean
                or "especie" in c_clean
                or "agradecimiento" in c_clean
                or "revendedor" in c_clean
            ):
                c_clean = "revendedor / distribuidor"

            matched_channel_id = None
            matched_channel_code = "MARKETPLACE"
            for ch_key, ch_val in channel_map.items():
                if ch_key in c_clean or c_clean in ch_key:
                    matched_channel_id = ch_val["id"]
                    matched_channel_code = ch_val["code"]
                    break

            norm_pay_status = normalize_payment_status(payment_status)
            norm_del_mod = normalize_delivery_modality(delivery_mod)
            norm_del_paid = normalize_delivery_paid_by(delivery_paid_by)
            norm_pay_method = normalize_payment_method(payment_method)
            norm_del_status = normalize_delivery_status(delivery_status)

            # Resolver producto vendido
            matched_product_id = product_id_map.get(sheet_prod_id)
            if not matched_product_id:
                matched_product_id = product_name_map.get(prod_name.strip().lower())

            if not matched_product_id:
                # Si el producto no existe en el catálogo, no podemos crear la línea
                continue

            product_obj = session.get(Product, matched_product_id)
            unit_cost = 0.0
            if product_obj:
                if product_obj.cost_price is not None:
                    unit_cost = product_obj.cost_price
                elif product_obj.batch_id:
                    b_obj = session.get(Batch, product_obj.batch_id)
                    if b_obj:
                        unit_cost = b_obj.unit_cost

            line_cost = round(unit_cost * qty, 2)
            net_profit = round(total_collected - line_cost, 2)
            unit_price = round(total_collected / qty, 2) if qty > 0 else official_p

            sale_number = f"VTA-{str(sheet_sale_id).zfill(4)}"

            existing_sale = session.exec(
                select(Sale).where(Sale.sale_number == sale_number)
            ).first()
            if not existing_sale:
                sale = Sale(
                    sale_number=sale_number,
                    sheet_sale_id=sheet_sale_id,
                    sale_date=sale_date,
                    customer_name=customer or "Cliente Casual",
                    customer_phone=phone,
                    channel_id=matched_channel_id,
                    channel=matched_channel_code,
                    payment_method=norm_pay_method,
                    payment_status=norm_pay_status,
                    delivery_modality=norm_del_mod,
                    delivery_address=delivery_addr,
                    delivery_cost=delivery_cost,
                    delivery_cost_paid_by=norm_del_paid,
                    delivery_status=norm_del_status,
                    total_collected=total_collected,
                    total_cost=line_cost,
                    net_profit=net_profit,
                    currency="BOB",
                    observations=obs,
                )
                if not dry_run:
                    session.add(sale)
                    session.flush()

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=matched_product_id,
                    quantity=qty,
                    unit_price=unit_price,
                    unit_cost=unit_cost,
                    total_price=total_collected,
                    net_margin=net_profit,
                )
                if not dry_run:
                    session.add(sale_item)
            else:
                existing_sale.customer_name = customer or "Cliente Casual"
                existing_sale.customer_phone = phone
                existing_sale.observations = obs
                existing_sale.sale_date = sale_date
                existing_sale.channel_id = matched_channel_id
                existing_sale.channel = matched_channel_code
                existing_sale.payment_method = norm_pay_method
                existing_sale.payment_status = norm_pay_status
                existing_sale.delivery_modality = norm_del_mod
                existing_sale.delivery_address = delivery_addr
                existing_sale.delivery_cost = delivery_cost
                existing_sale.delivery_cost_paid_by = norm_del_paid
                existing_sale.delivery_status = norm_del_status
                existing_sale.total_collected = total_collected
                existing_sale.total_cost = line_cost
                existing_sale.net_profit = net_profit
                existing_sale.currency = "BOB"
                if not dry_run:
                    session.add(existing_sale)

                # Actualizar también la línea de ítem existente
                existing_item = session.exec(
                    select(SaleItem).where(SaleItem.sale_id == existing_sale.id)
                ).first()
                if existing_item:
                    existing_item.product_id = matched_product_id
                    existing_item.quantity = qty
                    existing_item.unit_price = unit_price
                    existing_item.unit_cost = unit_cost
                    existing_item.total_price = total_collected
                    existing_item.net_margin = net_profit
                    if not dry_run:
                        session.add(existing_item)

            stats["sales"] += 1
            stats["sale_items"] += 1

        print(f"  ✓ {stats['sales']} ventas procesadas.")

        if not dry_run:
            session.commit()
            print("\n💾 Cambios guardados exitosamente en la base de datos.")

    print("\n" + "=" * 55)
    print("📊 RESUMEN DE LA MIGRACIÓN NOVA BOX BOLIVIA")
    print("=" * 55)
    print(f"  • Categorías oficializadas:      {stats['categories']}")
    print(f"  • Canales de venta activos:      {stats['channels']}")
    print(f"  • Canastas de TikTok Live:       {stats['live_baskets']}")
    print(f"  • Rondas de inversión:           {stats['rounds']}")
    print(f"  • Cajas y lotes importados:      {stats['batches']}")
    print(f"  • Productos/SKUs catalogados:    {stats['products']}")
    print(f"  • Ventas transaccionales:        {stats['sales']}")
    print(f"  • Ítems de venta asociados:      {stats['sale_items']}")
    print("=" * 55)
    print("✨ Sincronización completada con éxito.")


def main():
    parser = argparse.ArgumentParser(
        description="Migración ETL de Google Sheets a Uyuni ERP (Nova Box)"
    )
    parser.add_argument(
        "--sqlite",
        type=str,
        default=None,
        help="Ruta a base de datos SQLite (ej: data/novabox.db)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="URL de base de datos. Por defecto settings.DATABASE_URL",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data/sheets_cache",
        help="Directorio de caché JSON local",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Refrescar caché descargando de Google Sheets",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar validación sin escribir en la base de datos",
    )
    args = parser.parse_args()

    if args.refresh_cache:
        refresh_cache_from_sheets(args.cache_dir)

    target_db = args.db_url
    if args.sqlite:
        os.makedirs(os.path.dirname(os.path.abspath(args.sqlite)), exist_ok=True)
        target_db = f"sqlite:///{os.path.abspath(args.sqlite)}"
    elif not target_db:
        target_db = settings.DATABASE_URL

    run_migration(args.cache_dir, target_db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
