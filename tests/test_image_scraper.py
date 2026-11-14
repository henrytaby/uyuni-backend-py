from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.modules.commerce.product_masters.models import ProductMaster
from app.modules.commerce.product_masters.scraper import (
    ExternalMediaScraper,
    media_scraper,
)
from app.modules.commerce.product_masters.service import ProductMasterService


def test_media_scraper_invalid_url():
    result = media_scraper.scrape("invalid-url")
    assert result.platform == "UNKNOWN"
    assert len(result.images) == 0
    assert "no válida" in (result.warning or "")


def test_media_scraper_amazon_extraction():
    img1 = "https://m.media-amazon.com/images/I/61N0yD-OCAL._AC_UF894,1000_QL80_.jpg"
    img2 = "https://m.media-amazon.com/images/I/71b7MTr2-KL._AC_UF894,1000_QL80_.jpg"
    sample_html = f"""
    <html>
      <body>
        <img src="{img1}" />
        <img src="{img2}" />
        <img src="https://m.media-amazon.com/images/I/play-button-overlay.png" />
      </body>
    </html>
    """
    scraper = ExternalMediaScraper()
    items = scraper._extract_amazon(sample_html)
    assert len(items) == 2
    assert items[0].url == "https://m.media-amazon.com/images/I/61N0yD-OCAL.jpg"
    assert (
        items[0].thumbnail_url
        == "https://m.media-amazon.com/images/I/61N0yD-OCAL._AC_SL300_.jpg"
    )
    assert items[1].url == "https://m.media-amazon.com/images/I/71b7MTr2-KL.jpg"


def test_media_scraper_ebay_extraction():
    sample_html = """
    <html>
      <body>
        <img src="https://i.ebayimg.com/images/g/abc123XYZ/s-l500.jpg" />
        <img src="https://i.ebayimg.com/thumbs/images/g/def456UVW/s-l300.webp" />
      </body>
    </html>
    """
    scraper = ExternalMediaScraper()
    items = scraper._extract_ebay(sample_html)
    assert len(items) == 2
    assert items[0].url == "https://i.ebayimg.com/images/g/abc123XYZ/s-l1600.jpg"
    assert items[1].url == "https://i.ebayimg.com/images/g/def456UVW/s-l1600.webp"


def test_media_scraper_generic_opengraph():
    sample_html = """
    <html>
      <head>
        <meta property="og:image" content="https://example.com/products/main.jpg" />
        <meta name="twitter:image" content="https://example.com/products/side.jpg" />
      </head>
      <body>
        <img src="/static/product1.png" />
        <img src="/icons/logo.svg" />
      </body>
    </html>
    """
    scraper = ExternalMediaScraper()
    items = scraper._extract_generic(sample_html, base_url="https://example.com/item/1")
    assert len(items) >= 2
    urls = [i.url for i in items]
    assert "https://example.com/products/main.jpg" in urls
    assert "https://example.com/products/side.jpg" in urls
    assert "https://example.com/static/product1.png" in urls


def test_import_external_images_service(session: Session):
    master = ProductMaster(
        item_number=9999,
        name="Producto Test Import",
        official_price=100.0,
        minimum_price=80.0,
    )
    session.add(master)
    session.commit()
    session.refresh(master)

    service = ProductMasterService(session)

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50
    mock_resp.headers = {"Content-Type": "image/jpeg"}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with patch(
            "app.modules.commerce.product_masters.service.cloudinary_service.upload_image"
        ) as mock_upload:
            mock_upload.return_value = {
                "url": "https://res.cloudinary.com/test/image/upload/v1/prod.jpg",
                "public_id": "test_prod_1",
                "format": "jpg",
                "bytes": 58,
                "width": 800,
                "height": 800,
            }

            created = service.import_external_images(
                master_id=master.id,
                image_urls=["https://example.com/photo1.jpg"],
                image_type="CATALOG",
                set_first_as_cover=True,
            )

            assert len(created) == 1
            assert created[0].product_master_id == master.id
            assert created[0].is_cover is True
            assert master.cover_image_url == created[0].url
