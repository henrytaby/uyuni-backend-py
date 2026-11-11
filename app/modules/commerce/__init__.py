# Import all commerce models for SQLModel relationship registry
# Import catalogs so they auto-register into the global registry
import app.modules.commerce.catalogs  # noqa: F401
from app.modules.commerce.batches.models import Batch  # noqa: F401
from app.modules.commerce.categories.models import Category  # noqa: F401
from app.modules.commerce.channels.models import SalesChannel  # noqa: F401
from app.modules.commerce.live_baskets.models import LiveBasket  # noqa: F401
from app.modules.commerce.product_masters.models import ProductMaster  # noqa: F401
from app.modules.commerce.products.models import Product  # noqa: F401
from app.modules.commerce.rounds.models import InvestmentRound  # noqa: F401
from app.modules.commerce.sales.models import Sale, SaleItem  # noqa: F401
