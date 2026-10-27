import sys
from pathlib import Path
base = Path(__file__).resolve().parents[2] / "services"
sys.path.insert(0, str(base / "evaluation"))
sys.path.insert(0, str(base / "gepard-optimizer"))
