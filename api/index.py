# ==========================================
# Entrypoint para Vercel Serverless Functions
# ==========================================
import sys
from pathlib import Path

# Agregar la raíz del proyecto a sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.main import app  # noqa: E402

# Vercel espera la variable 'app' o 'handler'
handler = app

