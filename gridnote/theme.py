"""Tema azul-escuro (inspirado no OneNote) e ícones desenhados em código."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap

C = {
    "bg0": "#071327",        # barra lateral
    "bg1": "#0B1B36",        # painel de arquivos abertos
    "bg2": "#0F2344",        # área central
    "surface": "#142C55",    # cartões / barras
    "surface2": "#1A3666",
    "grid": "#0D1F3E",
    "grid_alt": "#10264A",
    "gridline": "#1C3762",
    "header": "#17325F",
    "header_on": "#21457F",
    "border": "#22406E",
    "text": "#E8EFFB",
    "muted": "#A3B6D3",
    "faint": "#6C84A8",
    "accent": "#4C9AFF",
    "accent_hover": "#6DAEFF",
    "accent_press": "#3479D6",
    "sel": "#2A5DB0",
    "warn": "#F2C14E",
    "modified": "#4B3F17",
    "danger": "#FF6B6F",
    "ok": "#43D18D",
}

FONT_UI = "Segoe UI"
_ICON_FONTS = ("Segoe Fluent Icons", "Segoe MDL2 Assets")

# Glifos das fontes de ícone do Windows 10/11
G = {
    "folder": "", "folder_open": "", "open_file": "", "save": "",
    "save_as": "", "undo": "", "redo": "", "filter": "", "search": "",
    "add": "", "delete": "", "refresh": "", "link": "", "cancel": "",
    "replace": "", "help": "", "explorer": "", "lightbulb": "", "close": "",
    "check": "", "warning": "", "dock_bottom": "", "dock_left": "", "sort": "",
    "copy": "", "edit": "", "paste": "", "erase": "", "document": "",
}


@lru_cache(maxsize=None)
def _icon_family() -> str | None:
    families = set(QFontDatabase.families())
    for f in _ICON_FONTS:
        if f in families:
            return f
    return None


def glyph_icon(name: str, color: str | None = None, size: int = 32) -> QIcon:
    color = color or C["text"]
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fam = _icon_family()
    if fam:
        f = QFont(fam)
        f.setPixelSize(int(size * 0.72))
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, G[name])
    else:  # sem fonte de ícones: um ponto discreto
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(size / 2, size / 2), size / 8, size / 8)
    p.end()
    icon = QIcon(pm)
    return icon


def glyph_label_font(px: int = 16) -> QFont:
    f = QFont(_icon_family() or FONT_UI)
    f.setPixelSize(px)
    return f


def bars_icon(vertical: bool, color: str | None = None, size: int = 32) -> QIcon:
    """Três barras: verticais = colunas, horizontais = linhas."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color or C["text"]))
    m, gap = size * 0.16, size * 0.08
    span = size - 2 * m
    bar = (span - 2 * gap) / 3
    for i in range(3):
        o = m + i * (bar + gap)
        rect = QRectF(o, m, bar, span) if vertical else QRectF(m, o, span, bar)
        p.drawRoundedRect(rect, bar * 0.25, bar * 0.25)
    p.end()
    return QIcon(pm)


def dot_pixmap(color: str, size: int = 12, hollow: bool = False) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if hollow:
        p.setPen(QPen(QColor(color), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
    p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
    p.end()
    return pm


def app_icon_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    path = QPainterPath()
    path.addRoundedRect(QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92), s * 0.2, s * 0.2)
    p.fillPath(path, QColor("#123A78"))
    # folha com grade
    sheet = QRectF(s * 0.2, s * 0.2, s * 0.6, s * 0.6)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#EAF2FF"))
    p.drawRoundedRect(sheet, s * 0.05, s * 0.05)
    p.setBrush(QColor("#4C9AFF"))
    p.drawRoundedRect(QRectF(sheet.left(), sheet.top(), sheet.width(), s * 0.14), s * 0.05, s * 0.05)
    p.drawRect(QRectF(sheet.left(), sheet.top() + s * 0.07, sheet.width(), s * 0.07))
    pen = QPen(QColor("#9DB9E6"), max(1.0, s * 0.012))
    p.setPen(pen)
    for i in (1, 2):
        x = sheet.left() + sheet.width() * i / 3
        p.drawLine(QPointF(x, sheet.top() + s * 0.14), QPointF(x, sheet.bottom()))
    for i in (1, 2, 3):
        y = sheet.top() + s * 0.14 + (sheet.height() - s * 0.14) * i / 4
        p.drawLine(QPointF(sheet.left(), y), QPointF(sheet.right(), y))
    # bolinha branca de "não salvo"
    p.setPen(QPen(QColor("#123A78"), s * 0.03))
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(s * 0.78, s * 0.78), s * 0.11, s * 0.11)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_icon_pixmap(sz))
    return icon


def apply(app) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_UI, 10))
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: C["bg2"], QPalette.ColorRole.WindowText: C["text"],
        QPalette.ColorRole.Base: C["grid"], QPalette.ColorRole.AlternateBase: C["grid_alt"],
        QPalette.ColorRole.Text: C["text"], QPalette.ColorRole.Button: C["surface"],
        QPalette.ColorRole.ButtonText: C["text"], QPalette.ColorRole.Highlight: C["sel"],
        QPalette.ColorRole.HighlightedText: "#FFFFFF", QPalette.ColorRole.ToolTipBase: C["surface2"],
        QPalette.ColorRole.ToolTipText: C["text"], QPalette.ColorRole.PlaceholderText: C["faint"],
        QPalette.ColorRole.Link: C["accent"],
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(C["faint"]))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(C["faint"]))
    app.setPalette(pal)
    app.setStyleSheet(QSS.format(**C))


QSS = """
QWidget {{ color: {text}; }}
QMainWindow, #Central {{ background: {bg2}; }}
QToolTip {{ background: {surface2}; color: {text}; border: 1px solid {border}; padding: 6px; border-radius: 6px; }}

/* ---------- menus ---------- */
QMenuBar {{ background: {bg0}; color: {muted}; padding: 2px 6px; }}
QMenuBar::item {{ padding: 6px 12px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {surface}; color: {text}; }}
QMenu {{ background: {surface}; border: 1px solid {border}; padding: 6px; border-radius: 8px; }}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {sel}; }}
QMenu::item:disabled {{ color: {faint}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}
QMenu::icon {{ padding-left: 8px; }}

/* ---------- barra lateral ---------- */
#Nav {{ background: {bg0}; }}
#Brand {{ font-size: 17px; font-weight: 700; color: #FFFFFF; }}
#BrandSub {{ color: {faint}; font-size: 11px; }}
#SectionLabel {{ color: {faint}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
#FolderCard {{ background: {bg1}; border: 1px solid {border}; border-radius: 10px; }}
#FolderName {{ font-weight: 600; font-size: 13px; }}
#FolderPath {{ color: {faint}; font-size: 11px; }}
#NavTree, #OpenList {{ background: transparent; border: none; outline: none; }}
#NavTree::item {{ padding: 5px 4px; border-radius: 6px; }}
#NavTree::item:hover {{ background: {bg1}; }}
#NavTree::item:selected {{ background: {surface}; color: #FFFFFF; }}
#OpenPanel {{ background: {bg1}; border-top: 1px solid {border}; }}
#OpenList::item {{ border-radius: 8px; margin: 1px 0px; }}
#OpenList::item:hover {{ background: {surface}; }}
#OpenList::item:selected {{ background: {surface2}; border-left: 3px solid {accent}; }}
#OpenName {{ font-size: 13px; }}
#OpenBadge {{ color: {muted}; background: {bg0}; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: 700; }}
#EmptyHint {{ color: {faint}; font-size: 12px; }}

QTreeView::branch {{ background: transparent; }}

/* ---------- botões ---------- */
QPushButton, QToolButton {{
    background: {surface}; border: 1px solid {border}; border-radius: 7px; padding: 6px 12px;
}}
QPushButton:hover, QToolButton:hover {{ background: {surface2}; border-color: {accent_press}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {bg1}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {faint}; background: {bg1}; border-color: {bg1}; }}
QToolButton::menu-indicator {{ image: none; }}
QPushButton[kind="primary"] {{ background: {accent}; border-color: {accent}; color: #06152C; font-weight: 700; }}
QPushButton[kind="primary"]:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton[kind="primary"]:pressed {{ background: {accent_press}; }}
QPushButton[kind="primary"]:disabled {{ background: {surface}; color: {faint}; border-color: {surface}; }}
QPushButton[kind="danger"] {{ background: transparent; border-color: {danger}; color: {danger}; }}
QPushButton[kind="danger"]:hover {{ background: #3A1D2A; }}
QPushButton[kind="danger"]:disabled {{ color: {faint}; border-color: {border}; }}
QPushButton[kind="ghost"], QToolButton[kind="ghost"] {{ background: transparent; border-color: transparent; }}
QPushButton[kind="ghost"]:hover, QToolButton[kind="ghost"]:hover {{ background: {surface}; border-color: {border}; }}
QToolButton[kind="close"] {{ background: transparent; border: none; padding: 2px; border-radius: 5px; }}
QToolButton[kind="close"]:hover {{ background: #5A2635; }}

/* botões Colunas | Linhas */
#ModeSwitch {{ background: {bg1}; border: 1px solid {border}; border-radius: 9px; }}
#ModeSwitch QToolButton {{ background: transparent; border: none; border-radius: 7px; padding: 6px 14px; font-weight: 600; color: {muted}; }}
#ModeSwitch QToolButton:hover {{ color: {text}; background: {surface}; }}
#ModeSwitch QToolButton:checked {{ background: {accent}; color: #06152C; }}

/* ---------- campos ---------- */
QLineEdit, QComboBox, QSpinBox {{
    background: {bg1}; border: 1px solid {border}; border-radius: 7px; padding: 5px 8px;
    selection-background-color: {sel};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}
QLineEdit#FilterEdit {{ padding-left: 4px; min-width: 150px; }}
QLineEdit[active="true"] {{ border-color: {warn}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {surface}; border: 1px solid {border}; selection-background-color: {sel}; outline: none; padding: 4px; }}
QCheckBox, QRadioButton {{ spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QCheckBox::indicator {{ border: 1px solid {faint}; border-radius: 4px; background: {bg1}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QRadioButton::indicator {{ border: 1px solid {faint}; border-radius: 8px; background: {bg1}; }}
QRadioButton::indicator:checked {{ border-color: {accent};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {accent}, stop:0.45 {accent}, stop:0.55 {bg1}, stop:1 {bg1}); }}

/* ---------- página (editor) ---------- */
#PageTitle {{ font-size: 24px; font-weight: 600; color: #FFFFFF; }}
#PageMeta {{ color: {faint}; font-size: 12px; }}
#TitleRule {{ background: {border}; max-height: 1px; min-height: 1px; }}
#Toolbar {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
#ToolSep {{ background: {border}; min-width: 1px; max-width: 1px; }}
#CountLabel {{ color: {muted}; font-size: 12px; }}
#Tip {{ background: #13345F; border: 1px solid #2A5591; border-radius: 10px; }}
#TipText {{ color: #CFE0FA; }}
#ReplacePanel {{ background: {bg1}; border: 1px solid {accent_press}; border-radius: 12px; }}
#PanelTitle {{ font-weight: 700; font-size: 14px; }}
#ScopeLabel {{ color: {warn}; font-weight: 600; }}
#SelInfo {{ color: {muted}; font-size: 12px; }}

QTableView {{
    background: {grid}; alternate-background-color: {grid_alt}; gridline-color: {gridline};
    border: 1px solid {border}; border-radius: 10px; selection-background-color: {sel};
    selection-color: #FFFFFF;
}}
QTableView QLineEdit {{ border-radius: 0px; border: 2px solid {accent}; padding: 0px 4px; background: #0A1830; }}
QHeaderView {{ background: {header}; border: none; }}
QHeaderView::section {{
    background: {header}; color: {muted}; border: none; border-right: 1px solid {gridline};
    border-bottom: 1px solid {gridline}; padding: 4px 8px;
}}
QHeaderView::section:hover {{ background: {header_on}; color: #FFFFFF; }}
QHeaderView::section:checked {{ background: {accent}; color: #06152C; }}
QHeaderView[focus="true"]::section {{ color: {text}; background: {header_on}; }}
QHeaderView[focus="true"]::section:checked {{ background: {accent}; color: #06152C; }}
QTableCornerButton::section {{ background: {header}; border: none; border-right: 1px solid {gridline}; border-bottom: 1px solid {gridline}; }}

QTabBar#SheetTabs::tab {{ background: {bg1}; color: {muted}; padding: 6px 16px; border: 1px solid {border}; border-top: none;
    border-bottom-left-radius: 7px; border-bottom-right-radius: 7px; margin-right: 3px; }}
QTabBar#SheetTabs::tab:selected {{ background: {surface2}; color: #FFFFFF; border-top: 2px solid {accent}; }}

/* ---------- barra de salvar ---------- */
#SaveBar {{ background: {bg1}; border-top: 1px solid {border}; }}
#SaveBar[dirty="true"] {{ background: #1C2F52; border-top: 2px solid {warn}; }}
#SaveText {{ font-size: 13px; }}
#SaveBar[dirty="true"] #SaveText {{ color: #FFFFFF; font-weight: 600; }}

/* ---------- boas-vindas ---------- */
#Welcome {{ background: {bg2}; }}
#WelcomeTitle {{ font-size: 30px; font-weight: 700; color: #FFFFFF; }}
#WelcomeSub {{ color: {muted}; font-size: 14px; }}
#StepCard {{ background: {surface}; border: 1px solid {border}; border-radius: 14px; }}
#StepNum {{ background: {accent}; color: #06152C; border-radius: 16px; font-weight: 800; font-size: 15px; }}
#StepTitle {{ font-weight: 700; font-size: 14px; }}
#StepText {{ color: {muted}; }}

/* ---------- diálogos ---------- */
QDialog {{ background: {bg2}; }}
#DialogTitle {{ font-size: 18px; font-weight: 700; color: #FFFFFF; }}
#DialogText {{ color: {muted}; }}
#FormatCard {{ background: {surface}; border: 2px solid {border}; border-radius: 12px; text-align: left; padding: 10px; }}
#FormatCard:hover {{ border-color: {accent_press}; }}
#FormatCard:checked {{ border-color: {accent}; background: {surface2}; }}
#FileRow {{ background: {surface}; border-radius: 8px; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle {{ background: {border}; border-radius: 4px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: {faint}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: {border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QMessageBox {{ background: {bg2}; }}
"""
