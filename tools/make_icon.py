"""Gera assets/gridnote.ico a partir do ícone desenhado em código."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from gridnote.theme import app_icon_pixmap  # noqa: E402

app = QGuiApplication([])
out = ROOT / "assets" / "gridnote.ico"
out.parent.mkdir(exist_ok=True)
if not app_icon_pixmap(256).save(str(out), "ICO"):
    sys.exit("falha ao gravar o ícone")
print(out)
