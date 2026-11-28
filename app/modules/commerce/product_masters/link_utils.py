import re
import urllib.parse
from urllib.parse import urlparse

_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
_DIGITS_ID_RE = re.compile(r"^\d{4,30}$")
_IG_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{5,30}$")
_DIRECT_VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")


def detect_portal(url: str) -> tuple[str, str]:
    """Clasifica automáticamente el portal y genera una etiqueta amigable."""
    cleaned = (url or "").strip().lower()
    if not cleaned:
        return "OTHER", "Enlace Externo"

    if "amazon.co.uk" in cleaned:
        return "AMAZON", "Amazon UK"
    if "amazon.es" in cleaned:
        return "AMAZON", "Amazon España"
    if "amazon.com.mx" in cleaned:
        return "AMAZON", "Amazon México"
    if "amazon.de" in cleaned:
        return "AMAZON", "Amazon Alemania"
    if "amazon.fr" in cleaned:
        return "AMAZON", "Amazon Francia"
    if "amazon.it" in cleaned:
        return "AMAZON", "Amazon Italia"
    if "amazon.com.au" in cleaned:
        return "AMAZON", "Amazon Australia"
    if "amazon.nl" in cleaned:
        return "AMAZON", "Amazon Países Bajos"
    if "amazon.ca" in cleaned:
        return "AMAZON", "Amazon Canadá"
    if "amazon.co.jp" in cleaned:
        return "AMAZON", "Amazon Japón"
    if "amazon." in cleaned:
        return "AMAZON", "Amazon"
    if "ebay." in cleaned:
        return "EBAY", "eBay"
    if "aliexpress." in cleaned:
        return "ALIEXPRESS", "AliExpress"
    if "alibaba." in cleaned:
        return "ALIBABA", "Alibaba"
    if "walmart." in cleaned:
        return "WALMART", "Walmart"
    if "mercadolibre." in cleaned or "articulo.mercadolibre" in cleaned:
        return "MERCADOLIBRE", "MercadoLibre"
    if "youtube.com" in cleaned or "youtu.be" in cleaned:
        if "/shorts/" in cleaned:
            return "YOUTUBE", "YouTube Shorts"
        return "YOUTUBE", "YouTube"
    if "tiktok.com" in cleaned:
        return "TIKTOK", "TikTok"
    if any(k in cleaned for k in ("facebook.com", "fb.com", "fb.me", "fb.watch")):
        if "marketplace" in cleaned:
            return "FACEBOOK", "Facebook Marketplace"
        if "/reel/" in cleaned:
            return "FACEBOOK", "Facebook Reels"
        if "/watch" in cleaned or "/videos/" in cleaned or "fb.watch" in cleaned:
            return "FACEBOOK", "Facebook Video"
        return "FACEBOOK", "Facebook"
    if "instagram.com" in cleaned:
        if "/reel/" in cleaned or "/reels/" in cleaned:
            return "INSTAGRAM", "Instagram Reels"
        return "INSTAGRAM", "Instagram"
    if "vimeo.com" in cleaned:
        return "VIMEO", "Vimeo"
    if "res.cloudinary.com" in cleaned and (
        "/video/upload/" in cleaned
        or urlparse(cleaned).path.endswith(_DIRECT_VIDEO_EXTS)
    ):
        return "CLOUDINARY", "Video Cloudinary"
    if urlparse(cleaned).path.endswith(_DIRECT_VIDEO_EXTS):
        return "DIRECT_VIDEO", "Video Directo"
    if "wa.me" in cleaned or "whatsapp.com" in cleaned:
        return "WHATSAPP", "WhatsApp"
    if "shein." in cleaned:
        return "SHEIN", "SHEIN"
    if "temu." in cleaned:
        return "TEMU", "Temu"

    try:
        domain = urlparse(url).netloc.replace("www.", "")
        label = domain.split(".")[0].capitalize() if domain else "Sitio Oficial"
        return "OTHER", label
    except Exception:
        return "OTHER", "Sitio Oficial"


def resolve_video_embed(url: str) -> tuple[str | None, str]:
    """Construye una URL segura de embed y determina el modo de reproducción.

    Solo genera URLs de embed contra una allow-list estricta de plataformas
    confiables para prevenir inyección en iframes.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return None, "EXTERNAL_ONLY"

    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        return None, "EXTERNAL_ONLY"

    host = parsed.netloc.lower().split(":")[0]
    path = parsed.path or ""
    path_parts = [p for p in path.split("/") if p]

    # 1. YouTube / YouTube Shorts
    if host in ("youtu.be", "www.youtu.be") and path_parts:
        short_id = path_parts[0]
        if _YT_ID_RE.match(short_id):
            return f"https://www.youtube-nocookie.com/embed/{short_id}", "EMBED_IFRAME"

    if host in (
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    ):
        yt_id: str | None = None
        if path == "/watch" or path.startswith("/watch/"):
            qs = urllib.parse.parse_qs(parsed.query)
            v_params = qs.get("v")
            yt_id = v_params[0] if v_params else None
        elif len(path_parts) >= 2 and path_parts[0] in ("shorts", "embed", "live"):
            yt_id = path_parts[1]
        if yt_id and _YT_ID_RE.match(yt_id):
            return f"https://www.youtube-nocookie.com/embed/{yt_id}", "EMBED_IFRAME"

    # 2. TikTok (solo enlaces completos con /video/{id} o /embed/v2/{id})
    if host in ("tiktok.com", "www.tiktok.com", "m.tiktok.com"):
        if "video" in path_parts:
            idx = path_parts.index("video")
            if idx + 1 < len(path_parts) and _DIGITS_ID_RE.match(path_parts[idx + 1]):
                return (
                    f"https://www.tiktok.com/embed/v2/{path_parts[idx + 1]}",
                    "EMBED_IFRAME",
                )
        if (
            len(path_parts) >= 3
            and path_parts[0] == "embed"
            and path_parts[1] == "v2"
            and _DIGITS_ID_RE.match(path_parts[2])
        ):
            return f"https://www.tiktok.com/embed/v2/{path_parts[2]}", "EMBED_IFRAME"

    # 3. Instagram Reels / Posts
    if host in ("instagram.com", "www.instagram.com") and len(path_parts) >= 2:
        kind, code = path_parts[0], path_parts[1]
        if kind in ("reel", "reels") and _IG_CODE_RE.match(code):
            return f"https://www.instagram.com/reel/{code}/embed", "EMBED_IFRAME"
        if kind == "p" and _IG_CODE_RE.match(code):
            return f"https://www.instagram.com/p/{code}/embed", "EMBED_IFRAME"

    # 4. Facebook Reels / Watch / Videos
    if host in ("facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"):
        is_fb_video = (
            host == "fb.watch"
            or "/reel/" in path
            or "/videos/" in path
            or path.startswith("/watch")
        )
        if is_fb_video:
            encoded = urllib.parse.quote(cleaned, safe="")
            return (
                f"https://www.facebook.com/plugins/video.php"
                f"?href={encoded}&show_text=false",
                "EMBED_IFRAME",
            )

    # 5. Vimeo
    if host in ("vimeo.com", "www.vimeo.com") and path_parts:
        vimeo_id = path_parts[-1]
        if _DIGITS_ID_RE.match(vimeo_id):
            return f"https://player.vimeo.com/video/{vimeo_id}", "EMBED_IFRAME"
    if (
        host == "player.vimeo.com"
        and len(path_parts) >= 2
        and path_parts[0] == "video"
        and _DIGITS_ID_RE.match(path_parts[1])
    ):
        return f"https://player.vimeo.com/video/{path_parts[1]}", "EMBED_IFRAME"

    # 6. Video directo HTML5 (MP4/WebM/MOV o Cloudinary video)
    lower_path = path.lower()
    if lower_path.endswith(_DIRECT_VIDEO_EXTS) or (
        host == "res.cloudinary.com" and "/video/upload/" in lower_path
    ):
        return cleaned, "HTML5_VIDEO"

    return None, "EXTERNAL_ONLY"
