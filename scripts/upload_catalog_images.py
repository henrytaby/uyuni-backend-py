#!/usr/bin/env python3
"""
Script de sincronización y subida masiva de fotografías de catálogo a Cloudinary
a través del endpoint de Uyuni Backend.

Escanea las carpetas en /opt/nova/nova-home-tech/products/ (ej. NOV-242),
revisa si tienen fotos en assets/fotos_originales/, comprueba si la ficha
maestra existe en la base de datos (por item_number) y sube el lote de imágenes
usando el endpoint:
    POST /api/commerce/product-masters/{master_id}/images

Garantiza que la fotografía identificada como 'portada' (o -01) sea subida
en primer lugar para quedar registrada oficialmente como cover del producto.

Uso:
    # 1. Simulación sin subir nada (inspección y diagnóstico):
    venv/bin/python scripts/upload_catalog_images.py --dry-run

    # 2. Probar con un solo producto específico (ej. NOV-242 o 242):
    venv/bin/python scripts/upload_catalog_images.py --item 242

    # 3. Subir una muestra de los primeros 5 productos:
    venv/bin/python scripts/upload_catalog_images.py --limit 5

    # 4. Subida masiva completa (con soporte para reanudar si se interrumpe):
    venv/bin/python scripts/upload_catalog_images.py --resume
"""

import argparse
import json
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# Extensiones de imagen soportadas por Cloudinary y la API
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}


def get_photo_sort_key(photo_path: Path) -> tuple[int, str]:
    """
    Asigna una prioridad de ordenamiento a cada foto:
    - 0: Contiene explícitamente 'portada' en el nombre
    - 1: Contiene errores tipográficos conocidos ('portda', 'portable')
    - 2: Contiene el índice '-01-' o inicia con '01'
    - 10: Fotos secundarias normales (ordenadas alfabéticamente)
    """
    name = photo_path.name.lower()
    if "portada" in name:
        priority = 0
    elif "portda" in name or "portable" in name:
        priority = 1
    elif re.search(r"[-_ ]01[-_ .]", name) or name.startswith("01") or "-01" in name:
        priority = 2
    else:
        priority = 10
    return (priority, name)


def make_multipart_body(
    fields: dict[str, str],
    files: list[tuple[str, str, bytes, str]],
) -> tuple[bytes, str]:
    """
    Construye un cuerpo HTTP multipart/form-data RFC 7578 nativo
    sin requerir librerías externas de terceros.
    """
    boundary = f"----UyuniUploadBoundary{uuid.uuid4().hex}"
    body = bytearray()

    # Campos de formulario
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        body.extend(f"{value}\r\n".encode("utf-8"))

    # Archivos
    for field_name, filename, content, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type_header


class CatalogImageUploader:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        products_dir: Path,
        progress_file: Path,
        delay: float = 0.3,
        force: bool = False,
        dry_run: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.products_dir = products_dir
        self.progress_file = progress_file
        self.delay = delay
        self.force = force
        self.dry_run = dry_run
        self.token: str | None = None
        self.db_masters: dict[int, dict[str, Any]] = {}
        self.completed_items: set[int] = set()
        self.load_progress()

    def login(self) -> str:
        """Autentica contra la API y devuelve el token de acceso JWT."""
        login_url = f"{self.base_url}/api/auth/login"
        form_data = urllib.parse.urlencode(
            {"username": self.username, "password": self.password}
        ).encode("utf-8")

        req = urllib.request.Request(
            login_url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.token = data["access_token"]
                return self.token
        except urllib.error.URLError as exc:
            print(
                f"\n[ERROR] No se pudo conectar al endpoint de login\n"
                f"({login_url}): {exc}"
            )
            print("Asegúrate de que el backend de Uyuni esté iniciado:")
            print("  venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000\n")
            sys.exit(1)

    def load_db_masters(self) -> None:
        """Carga todas las Fichas Maestras existentes en la BD vía API."""
        if not self.token:
            self.login()

        url = f"{self.base_url}/api/commerce/product-masters?limit=500"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                masters = json.loads(resp.read().decode("utf-8"))
                for m in masters:
                    num = m.get("item_number")
                    if num is not None:
                        self.db_masters[int(num)] = {
                            "id": m["id"],
                            "name": m.get("name", ""),
                            "cover_image_url": m.get("cover_image_url"),
                            "images_count": m.get("images_count", 0),
                        }
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                # Token vencido, reintentar una vez
                self.login()
                return self.load_db_masters()
            raise

    def load_progress(self) -> None:
        """Carga el registro de items completados previamente si existe."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_items = set(data.get("completed_item_numbers", []))
            except Exception:
                self.completed_items = set()

    def save_progress(self, item_number: int) -> None:
        """Registra un producto como completado en el archivo de progreso."""
        self.completed_items.add(item_number)
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "total_completed": len(self.completed_items),
                        "completed_item_numbers": sorted(list(self.completed_items)),
                    },
                    f,
                    indent=2,
                )
        except Exception as exc:
            print(f"  [AVISO] No se pudo guardar progreso: {exc}")

    def scan_folders(self) -> list[dict[str, Any]]:
        """
        Escanea la carpeta de productos y estructura el plan de trabajo.
        Devuelve una lista ordenada por item_number.
        """
        if not self.products_dir.exists():
            print(f"[ERROR] El directorio {self.products_dir} no existe.")
            sys.exit(1)

        items_plan = []
        folder_pattern = re.compile(r"^NOV-(\d+)$")

        for entry in self.products_dir.iterdir():
            if not entry.is_dir():
                continue

            match = folder_pattern.match(entry.name)
            if not match:
                continue

            item_number = int(match.group(1))
            fotos_dir = entry / "assets" / "fotos_originales"

            photos = []
            if fotos_dir.exists() and fotos_dir.is_dir():
                photos = [
                    p
                    for p in fotos_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
                ]
                photos.sort(key=get_photo_sort_key)

            items_plan.append(
                {
                    "folder_name": entry.name,
                    "item_number": item_number,
                    "path": entry,
                    "fotos_dir": fotos_dir,
                    "photos": photos,
                    "photos_count": len(photos),
                }
            )

        items_plan.sort(key=lambda x: int(str(x["item_number"])))
        return items_plan

    def upload_product_images(
        self,
        master_id: str,
        photos: list[Path],
    ) -> list[dict[str, Any]]:
        """
        Sube el lote de fotografías de un producto al endpoint de la API.
        """
        if not self.token:
            self.login()

        url = f"{self.base_url}/api/commerce/product-masters/{master_id}/images"

        # Preparar archivos para multipart
        files_payload = []
        for p in photos:
            content_type, _ = mimetypes.guess_type(str(p))
            if not content_type:
                content_type = "image/jpeg"
            with open(p, "rb") as f:
                content = f.read()
            files_payload.append(("files", p.name, content, content_type))

        fields = {
            "image_type": "CATALOG",
            "is_cover": "true",
        }

        body, content_type_header = make_multipart_body(fields, files_payload)

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type_header,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data: list[dict[str, Any]] = json.loads(
                    resp.read().decode("utf-8")
                )
                return data
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                # Token expirado, renovar y reintentar
                self.login()
                return self.upload_product_images(master_id, photos)
            err_msg = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {err_msg}") from exc

    def execute(
        self,
        target_item: int | None = None,
        limit: int | None = None,
        resume: bool = False,
    ) -> None:
        """Ejecuta el flujo completo de escaneo, validación y subida."""
        print("=" * 72)
        print(" Sincronizador Masivo de Fotos de Catálogo -> Uyuni Backend")
        print("=" * 72)
        print(f"Directorio fuente : {self.products_dir}")
        print(f"Endpoint API      : {self.base_url}")
        dry_str = "ACTIVADO (Sin cambios)" if self.dry_run else "DESACTIVADO (Subida)"
        print(f"Modo Dry-Run      : {dry_str}")
        print(f"Reanudar previo   : {'SÍ' if resume else 'NO'}")
        print(f"Fuerza re-subida  : {'SÍ' if self.force else 'NO'}")

        # 1. Autenticación y precarga de BD
        print("\n[1/3] Conectando a la API y cargando Fichas Maestras de la BD...")
        self.login()
        self.load_db_masters()
        print(
            f"  -> Conexión exitosa. Se encontraron {len(self.db_masters)} "
            "fichas maestras en la BD."
        )

        if resume:
            self.load_progress()
            print(
                f"  -> Se cargaron {len(self.completed_items)} "
                "productos previamente completados."
            )

        # 2. Escaneo de carpetas
        print("\n[2/3] Escaneando carpetas de productos...")
        plan = self.scan_folders()
        print(f"  -> Total de carpetas encontradas: {len(plan)}")

        # Filtrar por item específico si se solicitó
        if target_item is not None:
            plan = [item for item in plan if item["item_number"] == target_item]
            if not plan:
                print(
                    f"[ERROR] No se encontró la carpeta para el "
                    f"item_number {target_item}."
                )
                return

        # 3. Procesamiento
        print("\n[3/3] Procesando productos...")
        stats = {
            "total_folders": len(plan),
            "uploaded": 0,
            "skipped_no_photos": 0,
            "skipped_not_in_db": 0,
            "skipped_already_done": 0,
            "errors": 0,
            "photos_uploaded": 0,
        }

        processed_count = 0

        for item in plan:
            num = item["item_number"]
            folder = item["folder_name"]
            photos = item["photos"]

            # Validación 1: ¿Tiene fotos?
            if not photos:
                print(
                    f"  [OMITIDO - SIN FOTOS] {folder} (item {num}): "
                    "Carpeta de fotos vacía."
                )
                stats["skipped_no_photos"] += 1
                continue

            # Validación 2: ¿Existe en BD?
            db_master = self.db_masters.get(num)
            if not db_master:
                print(
                    f"  [OMITIDO - NO EN BD]  {folder} (item {num}): "
                    "No existe ficha maestra en la BD."
                )
                stats["skipped_not_in_db"] += 1
                continue

            # Validación 3: ¿Ya fue completado en sesión previa?
            if resume and num in self.completed_items and not self.force:
                print(
                    f"  [OMITIDO - RESUME]    {folder} (item {num}): "
                    "Ya completado anteriormente."
                )
                stats["skipped_already_done"] += 1
                continue

            # Validación 4: ¿Ya tiene fotos en la BD?
            if not self.force and db_master["images_count"] > 0:
                print(
                    f"  [OMITIDO - YA EN BD]  {folder} (item {num}): "
                    f"Ya cuenta con {db_master['images_count']} foto(s) en BD."
                )
                stats["skipped_already_done"] += 1
                continue

            # Límite alcanzado
            if limit and processed_count >= limit:
                print(f"\n[INFO] Límite de {limit} productos alcanzado.")
                break

            processed_count += 1
            portada_name = photos[0].name
            master_id = db_master["id"]
            master_name = db_master["name"][:40]

            print(
                f"  [{processed_count}] {folder} (item {num}) -> {len(photos)} foto(s) "
                f"| Portada: '{portada_name}' | Ficha: {master_name}..."
            )

            if self.dry_run:
                stats["uploaded"] += 1
                stats["photos_uploaded"] += len(photos)
                continue

            # Subida real a Cloudinary vía API
            start_time = time.time()
            try:
                uploaded = self.upload_product_images(master_id, photos)
                elapsed = time.time() - start_time
                print(
                    f"      [OK] Subidas {len(uploaded)} fotos a Cloudinary "
                    f"y registradas en BD ({elapsed:.1f}s)"
                )
                stats["uploaded"] += 1
                stats["photos_uploaded"] += len(uploaded)
                self.save_progress(num)
                time.sleep(self.delay)
            except Exception as exc:
                print(f"      [ERROR] Falló la subida para {folder}: {exc}")
                stats["errors"] += 1

        # Resumen final
        print("\n" + "=" * 72)
        print(" RESUMEN DE EJECUCIÓN")
        print("=" * 72)
        print(f"Carpetas inspeccionadas       : {stats['total_folders']}")
        print(f"Productos procesados con éxito: {stats['uploaded']}")
        print(f"Fotografías subidas           : {stats['photos_uploaded']}")
        print(f"Omitidos por falta de fotos   : {stats['skipped_no_photos']}")
        print(f"Omitidos por no existir en BD : {stats['skipped_not_in_db']}")
        print(f"Omitidos por ya estar en BD   : {stats['skipped_already_done']}")
        print(f"Errores durante la subida     : {stats['errors']}")
        print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sincronizador masivo de fotografías de catálogo hacia Uyuni Backend"
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="URL base del backend de Uyuni (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Usuario con permisos para autenticación (default: admin)",
    )
    parser.add_argument(
        "--password",
        default="taby2022",
        help="Contraseña para autenticación (default: taby2022)",
    )
    parser.add_argument(
        "--products-dir",
        type=Path,
        default=Path("/opt/nova/nova-home-tech/products"),
        help="Ruta al directorio de productos (default: /opt/nova/.../products)",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=Path(__file__).parent / "upload_progress.json",
        help="Archivo JSON para persistir productos completados",
    )
    parser.add_argument(
        "--item",
        type=str,
        default=None,
        help="Procesar solo un producto específico (ej. 242 o NOV-242)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limitar la cantidad de productos a procesar",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fuerza la subida incluso si el producto ya cuenta con fotos en la BD",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda omitiendo los productos registrados en el archivo de progreso",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la inspección y matching sin subir archivos a Cloudinary",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Pausa en segundos entre subidas para balancear la carga (default: 0.3s)",
    )

    args = parser.parse_args()

    target_item = None
    if args.item:
        clean_item = args.item.upper().replace("NOV-", "").strip()
        try:
            target_item = int(clean_item)
        except ValueError:
            print(
                f"[ERROR] Formato de item inválido: '{args.item}'. "
                "Usa un número como 242 o NOV-242."
            )
            sys.exit(1)

    uploader = CatalogImageUploader(
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        products_dir=args.products_dir,
        progress_file=args.progress_file,
        delay=args.delay,
        force=args.force,
        dry_run=args.dry_run,
    )

    uploader.execute(
        target_item=target_item,
        limit=args.limit,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
