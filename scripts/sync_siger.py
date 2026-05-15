import sys
import os
import uuid
import uuid6
from datetime import date
from typing import Optional

# Setup import path for the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel, Field, create_engine, Session, select, update
from app.core.config import settings
from app.core.db import engine as local_engine
from app.modules.core.org_units.models import OrgUnit
from app.modules.core.positions.models import StaffPosition
from app.modules.core.staff.models import Staff

# ==========================================
# EXTERNAL MODELS (an_core)
# ==========================================
class FuncionarioSync(SQLModel, table=True):
    __tablename__ = "funcionario"
    id: int = Field(primary_key=True)
    nombres: str
    primer_apellido: str | None = None
    segundo_apellido: str | None = None
    nombre_completo: str
    fecha_nacimiento: date | None = None
    nro_documento: str
    lugar_emision: str | None = None
    email_interno: str | None = None
    celular: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    estado: str
    tipo: str
    cargo_id: int | None = None
    gerencia_id: int | None = None
    departamento_id: int | None = None
    is_active: bool

class UnidadSync(SQLModel, table=True):
    __tablename__ = "unidad_organizacional"
    id: int = Field(primary_key=True)
    nombre: str
    unidad_general: str
    sigla: str
    parent_id: int | None = None
    tipo: str
    is_active: bool

class CargoSync(SQLModel, table=True):
    __tablename__ = "cargo"
    id: int = Field(primary_key=True)
    nro_item: int | None = None
    nivel: str
    nombre: str
    tipo_puesto: str
    is_active: bool

# ==========================================
# SYNC LOGIC
# ==========================================
def run_sync():
    if not settings.SYNC_DATABASE_URL:
        print("ERROR: SYNC_DATABASE_URL not set in .env")
        sys.exit(1)

    print("Connecting to an_core...")
    external_engine = create_engine(settings.SYNC_DATABASE_URL, echo=False)

    with Session(external_engine) as ext_session, Session(local_engine) as loc_session:
        print("--- Deprecating all existing records (is_active = False) ---")
        loc_session.exec(update(Staff).values(is_active=False))
        loc_session.exec(update(StaffPosition).values(is_active=False))
        loc_session.exec(update(OrgUnit).values(is_active=False))
        loc_session.commit()

        # 1. Sync Cargos
        print("--- Syncing Cargos (StaffPosition) ---")
        cargos = ext_session.exec(select(CargoSync)).all()
        for cargo in cargos:
            local_pos = loc_session.exec(select(StaffPosition).where(StaffPosition.external_id == cargo.id)).first()
            if not local_pos:
                local_pos = StaffPosition(
                    id=uuid6.uuid7(),
                    external_id=cargo.id,
                    item_number=cargo.nro_item,
                    name=cargo.nombre,
                    level=cargo.nivel,
                    position_type=cargo.tipo_puesto,
                    is_active=cargo.is_active
                )
                loc_session.add(local_pos)
            else:
                local_pos.item_number = cargo.nro_item
                local_pos.name = cargo.nombre
                local_pos.level = cargo.nivel
                local_pos.position_type = cargo.tipo_puesto
                local_pos.is_active = cargo.is_active
                loc_session.add(local_pos)
        loc_session.commit()
        print(f"Synced {len(cargos)} cargos.")

        # 2. Sync Unidades Organizacionales
        print("--- Syncing Unidades Organizacionales (OrgUnit) ---")
        unidades = ext_session.exec(select(UnidadSync)).all()
        
        # Pass 1: Upsert all units without parent_id
        for uni in unidades:
            local_uni = loc_session.exec(select(OrgUnit).where(OrgUnit.external_id == uni.id)).first()
            if not local_uni:
                local_uni = OrgUnit(
                    id=uuid6.uuid7(),
                    external_id=uni.id,
                    external_parent_id=uni.parent_id,
                    name=uni.nombre,
                    acronym=uni.sigla,
                    general_unit=uni.unidad_general,
                    type=uni.tipo,
                    is_active=uni.is_active
                )
                loc_session.add(local_uni)
            else:
                local_uni.external_parent_id = uni.parent_id
                local_uni.name = uni.nombre
                local_uni.acronym = uni.sigla
                local_uni.general_unit = uni.unidad_general
                local_uni.type = uni.tipo
                local_uni.is_active = uni.is_active
                loc_session.add(local_uni)
        loc_session.commit()
        
        # Pass 2: Map parent_id
        for uni in unidades:
            if uni.parent_id:
                local_uni = loc_session.exec(select(OrgUnit).where(OrgUnit.external_id == uni.id)).first()
                parent_uni = loc_session.exec(select(OrgUnit).where(OrgUnit.external_id == uni.parent_id)).first()
                if local_uni and parent_uni:
                    local_uni.parent_id = parent_uni.id
                    loc_session.add(local_uni)
        loc_session.commit()
        print(f"Synced {len(unidades)} unidades organizacionales.")

        # 3. Sync Funcionarios
        print("--- Syncing Funcionarios (Staff) ---")
        funcionarios = ext_session.exec(select(FuncionarioSync)).all()
        
        for func in funcionarios:
            # Resolve Position UUID
            position_uuid = None
            if func.cargo_id:
                pos = loc_session.exec(select(StaffPosition).where(StaffPosition.external_id == func.cargo_id)).first()
                if pos:
                    position_uuid = pos.id
            
            # Resolve OrgUnit UUID (Priority: departamento_id, Fallback: gerencia_id)
            org_unit_uuid = None
            external_unit_id = func.departamento_id if func.departamento_id else func.gerencia_id
            if external_unit_id:
                uni = loc_session.exec(select(OrgUnit).where(OrgUnit.external_id == external_unit_id)).first()
                if uni:
                    org_unit_uuid = uni.id

            # Only sync if we resolved the required relationships
            if not position_uuid or not org_unit_uuid:
                print(f"Skipping Funcionario {func.id} due to missing position or org_unit relation in local DB.")
                continue

            local_staff = loc_session.exec(select(Staff).where(Staff.external_id == func.id)).first()
            if not local_staff:
                local_staff = Staff(
                    id=uuid6.uuid7(),
                    external_id=func.id,
                    first_name=func.nombres,
                    last_name_1=func.primer_apellido or "",
                    last_name_2=func.segundo_apellido,
                    full_name=func.nombre_completo,
                    birth_date=func.fecha_nacimiento,
                    document_number=func.nro_documento,
                    document_location=func.lugar_emision,
                    email=func.email_interno,
                    cellphone=func.celular,
                    phone=func.telefono,
                    address=func.direccion,
                    status=func.estado,
                    staff_type=func.tipo,
                    is_active=func.is_active,
                    position_id=position_uuid,
                    org_unit_id=org_unit_uuid
                )
                loc_session.add(local_staff)
            else:
                local_staff.first_name = func.nombres
                local_staff.last_name_1 = func.primer_apellido or ""
                local_staff.last_name_2 = func.segundo_apellido
                local_staff.full_name = func.nombre_completo
                local_staff.birth_date = func.fecha_nacimiento
                local_staff.document_number = func.nro_documento
                local_staff.document_location = func.lugar_emision
                local_staff.email = func.email_interno
                local_staff.cellphone = func.celular
                local_staff.phone = func.telefono
                local_staff.address = func.direccion
                local_staff.status = func.estado
                local_staff.staff_type = func.tipo
                local_staff.is_active = func.is_active
                local_staff.position_id = position_uuid
                local_staff.org_unit_id = org_unit_uuid
                loc_session.add(local_staff)

        loc_session.commit()
        print(f"Synced {len(funcionarios)} funcionarios.")
        print("Data synchronization completed successfully.")

if __name__ == "__main__":
    run_sync()
