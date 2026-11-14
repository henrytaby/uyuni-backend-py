import html
import re
import urllib.parse
import urllib.request

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# Headers emulando navegador móvil (evita bloqueos de anti-bots en Amazon)
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
)

DEFAULT_HEADERS = {
    "User-Agent": MOBILE_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
}

# Subcadenas no deseadas que suelen ser iconos, banners genéricos o píxeles
IGNORE_IMAGE_SUBSTRINGS = (
    "icon",
    "sprite",
    "pixel",
    "logo",
    "badge",
    "play-button",
    "overlay",
    "transparent",
    "grey-pixel",
    "1x1",
    "spinner",
    "loading",
    "favicon",
    "avatar",
)


class ScrapedImageItem(BaseModel):
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt: str | None = None


class ScrapedMediaResult(BaseModel):
    source_url: str
    platform: str
    images: list[ScrapedImageItem]
    warning: str | None = None


class ExternalMediaScraper:
    """
    Extractor inteligente de imágenes de productos desde URLs externas.
    Soporta plataformas como Amazon, eBay, AliExpress, Alibaba y sitios genéricos.
    """

    def scrape(self, url: str) -> ScrapedMediaResult:
        clean_url = (url or "").strip()
        if not clean_url or not clean_url.startswith(("http://", "https://")):
            return ScrapedMediaResult(
                source_url=clean_url,
                platform="UNKNOWN",
                images=[],
                warning="URL no válida. Debe iniciar con http:// o https://.",
            )

        parsed = urllib.parse.urlparse(clean_url)
        domain = parsed.netloc.lower()

        if "amazon." in domain:
            platform = "AMAZON"
        elif "ebay." in domain:
            platform = "EBAY"
        elif "aliexpress." in domain:
            platform = "ALIEXPRESS"
        elif "alibaba." in domain:
            platform = "ALIBABA"
        else:
            platform = "GENERIC"

        try:
            req = urllib.request.Request(clean_url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=12) as response:
                content_type = response.headers.get("Content-Type", "")
                if (
                    "text/html" not in content_type
                    and "application/xhtml" not in content_type
                ):
                    return ScrapedMediaResult(
                        source_url=clean_url,
                        platform=platform,
                        images=[],
                        warning=(
                            f"La URL respondió con tipo '{content_type}', "
                            "no es una página HTML."
                        ),
                    )
                raw_bytes = response.read()
                html_text = raw_bytes.decode("utf-8", errors="ignore")
                html_text = html.unescape(html_text)
        except urllib.error.HTTPError as exc:
            logger.warning("scrape_http_error", url=clean_url, code=exc.code)
            return ScrapedMediaResult(
                source_url=clean_url,
                platform=platform,
                images=[],
                warning=(
                    f"El sitio externo respondió con error HTTP {exc.code}. "
                    "Puedes descargar las imágenes y arrastrarlas a la galería."
                ),
            )
        except Exception as exc:
            logger.warning("scrape_fetch_failed", url=clean_url, error=str(exc))
            return ScrapedMediaResult(
                source_url=clean_url,
                platform=platform,
                images=[],
                warning=(
                    f"No fue posible conectar con el sitio externo: {str(exc)}. "
                    "Puedes subir las imágenes arrastrándolas a la galería."
                ),
            )

        # Parsear según la plataforma
        if platform == "AMAZON":
            images = self._extract_amazon(html_text)
        elif platform == "EBAY":
            images = self._extract_ebay(html_text)
        elif platform in ("ALIEXPRESS", "ALIBABA"):
            images = self._extract_alibaba(html_text, clean_url)
        else:
            images = self._extract_generic(html_text, clean_url)

        warning_msg = None
        if not images:
            warning_msg = (
                "No se encontraron imágenes en alta resolución en la página. "
                "Puedes descargar las imágenes y arrastrarlas a la galería."
            )

        return ScrapedMediaResult(
            source_url=clean_url,
            platform=platform,
            images=images,
            warning=warning_msg,
        )

    def _extract_amazon(self, html_text: str) -> list[ScrapedImageItem]:
        """Extrae imágenes de Amazon y las convierte a su versión sin compresión."""
        pattern = (
            r"https://(?:m\.media-amazon\.com|images-na\.ssl-images-amazon\.com)"
            r"/images/I/[A-Za-z0-9%_.,-]+\.(?:jpg|jpeg|png|webp)"
        )
        raw_matches = re.findall(pattern, html_text, re.IGNORECASE)

        seen: set[str] = set()
        items: list[ScrapedImageItem] = []

        for raw_url in raw_matches:
            # Transformar URL quitando modificadores de tamaño (ej. ._AC_SL1500_.)
            high_res = re.sub(r"\._[A-Za-z0-9,._-]+_\.", ".", raw_url)
            low_url = high_res.lower()

            if any(bad in low_url for bad in IGNORE_IMAGE_SUBSTRINGS):
                continue

            if high_res not in seen:
                seen.add(high_res)
                thumb = re.sub(
                    r"\.(jpg|jpeg|png|webp)$",
                    r"._AC_SL300_.\1",
                    high_res,
                    flags=re.IGNORECASE,
                )
                items.append(
                    ScrapedImageItem(
                        url=high_res,
                        thumbnail_url=thumb,
                        alt="Amazon Product Photo",
                    )
                )

        return items

    def _extract_ebay(self, html_text: str) -> list[ScrapedImageItem]:
        """Extrae imágenes de eBay y las escala a s-l1600 (alta resolución)."""
        pattern = (
            r"https://i\.ebayimg\.com/(?:images/g/[A-Za-z0-9_-]+/s-l\d+"
            r"|thumbs/images/g/[A-Za-z0-9_-]+/s-l\d+)\.(?:jpg|jpeg|png|webp)"
        )
        raw_matches = re.findall(pattern, html_text, re.IGNORECASE)

        seen: set[str] = set()
        items: list[ScrapedImageItem] = []

        for raw_url in raw_matches:
            high_res = re.sub(r"s-l\d+\.", "s-l1600.", raw_url)
            high_res = high_res.replace("/thumbs/images/", "/images/")
            low_url = high_res.lower()

            if any(bad in low_url for bad in IGNORE_IMAGE_SUBSTRINGS):
                continue

            if high_res not in seen:
                seen.add(high_res)
                thumb = re.sub(r"s-l\d+\.", "s-l300.", raw_url)
                items.append(
                    ScrapedImageItem(
                        url=high_res,
                        thumbnail_url=thumb,
                        alt="eBay Product Photo",
                    )
                )

        return items

    def _extract_alibaba(self, html_text: str, base_url: str) -> list[ScrapedImageItem]:
        """Extrae imágenes de AliExpress / Alibaba."""
        pattern = (
            r"https://(?:sc0[1-4]|ae01|s)\.alicdn\.com/kf/[A-Za-z0-9_-]+"
            r"\.(?:jpg|jpeg|png|webp)"
        )
        raw_matches = re.findall(pattern, html_text, re.IGNORECASE)

        seen: set[str] = set()
        items: list[ScrapedImageItem] = []

        for raw_url in raw_matches:
            high_res = re.sub(
                r"_\d+x\d+.*?\.(jpg|jpeg|png|webp)$",
                r".\1",
                raw_url,
                flags=re.IGNORECASE,
            )
            low_url = high_res.lower()

            if any(bad in low_url for bad in IGNORE_IMAGE_SUBSTRINGS):
                continue

            if high_res not in seen:
                seen.add(high_res)
                items.append(
                    ScrapedImageItem(
                        url=high_res,
                        thumbnail_url=high_res,
                        alt="Alibaba / AliExpress Product Photo",
                    )
                )

        if not items:
            return self._extract_generic(html_text, base_url)
        return items

    def _extract_generic(self, html_text: str, base_url: str) -> list[ScrapedImageItem]:
        """Extrae imágenes mediante meta tags OpenGraph e imágenes <img> estándar."""
        seen: set[str] = set()
        items: list[ScrapedImageItem] = []

        # 1. OpenGraph y Twitter Cards
        og_pattern = (
            r'<meta\s+(?:property|name)=[\'"](?:og:image|og:image:secure_url'
            r'|twitter:image)[\'"]\s+content=[\'"]([^\'"]+)[\'"]'
        )
        og_matches = re.findall(og_pattern, html_text, re.IGNORECASE)
        for og_url in og_matches:
            full_url = urllib.parse.urljoin(base_url, og_url.strip())
            if full_url.startswith(("http://", "https://")) and full_url not in seen:
                seen.add(full_url)
                items.append(
                    ScrapedImageItem(
                        url=full_url,
                        thumbnail_url=full_url,
                        alt="Cover Photo (OG/Twitter)",
                    )
                )

        # 2. Etiquetas <img> del cuerpo
        img_tags = re.findall(
            r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', html_text, re.IGNORECASE
        )
        allowed_exts = (".jpg", ".jpeg", ".png", ".webp", ".avif")
        for src in img_tags:
            src = src.strip()
            if not src or src.startswith("data:"):
                continue
            full_url = urllib.parse.urljoin(base_url, src)
            low_url = full_url.lower()

            if not full_url.startswith(("http://", "https://")):
                continue
            if any(bad in low_url for bad in IGNORE_IMAGE_SUBSTRINGS):
                continue
            if not any(ext in low_url for ext in allowed_exts):
                continue

            if full_url not in seen:
                seen.add(full_url)
                items.append(
                    ScrapedImageItem(
                        url=full_url,
                        thumbnail_url=full_url,
                        alt="Product Photo",
                    )
                )

        return items


media_scraper = ExternalMediaScraper()
