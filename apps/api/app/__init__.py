"""Bootstrap do backend: configura sys.path para importar o engine.

Executa ANTES de qualquer submódulo (`schemas`, `route_service`, etc.),
então todos podem fazer `from core.* import ...` com segurança.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = REPO_ROOT / "apps" / "engine"

if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))
