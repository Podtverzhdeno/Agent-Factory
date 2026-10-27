import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / 'services'
for name in ('agent-builder', 'agent-runtime', 'litellm-adapter'):
    sys.path.insert(0, str(ROOT / name))
