"""Barra lateral estilo OneNote: pasta vinculada (árvore) e arquivos abertos."""
from __future__ import annotations

import os
from pathlib import Path

import subprocess

from PySide6.QtCore import QDir, QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QFileSystemModel, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QPushButton,
    QSplitter, QStyledItemDelegate, QToolButton, QTreeView, QVBoxLayout, QWidget,
)

from . import theme
from .document import path_key
from .fileio import OPEN_EXTS


class DirtyDotDelegate(QStyledItemDelegate):
    """Desenha a bolinha branca nos arquivos da árvore que têm alterações não salvas."""

    def __init__(self, nav: "NavPanel"):
        super().__init__(nav)
        self.nav = nav

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        key = path_key(self.nav.fs.filePath(index))
        if key in self.nav.open_state:
            option.font.setBold(True)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        key = path_key(self.nav.fs.filePath(index))
        if self.nav.open_state.get(key):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            r = option.rect
            painter.drawEllipse(QPointF(r.right() - 12, r.center().y() + 0.5), 4.5, 4.5)
            painter.restore()


class OpenItem(QWidget):
    closeClicked = Signal(str)

    def __init__(self, key: str, name: str, fmt: str, dirty: bool):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 4, 6)
        lay.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(12, 12)
        if dirty:
            dot.setPixmap(theme.dot_pixmap("#FFFFFF", 12))
            dot.setToolTip("Alterações não salvas")
        else:
            dot.setPixmap(theme.dot_pixmap(theme.C["faint"], 12, hollow=True))
            dot.setToolTip("Tudo salvo")
        lay.addWidget(dot)
        label = QLabel(name)
        label.setObjectName("OpenName")
        label.setToolTip(key)
        if dirty:
            label.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        lay.addWidget(label, 1)
        badge = QLabel(fmt.upper())
        badge.setObjectName("OpenBadge")
        lay.addWidget(badge)
        close = QToolButton()
        close.setProperty("kind", "close")
        close.setIcon(theme.glyph_icon("close", theme.C["muted"]))
        close.setIconSize(QSize(12, 12))
        close.setToolTip("Fechar arquivo")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(lambda: self.closeClicked.emit(key))
        lay.addWidget(close)


class NavPanel(QWidget):
    openPath = Signal(str)
    linkFolder = Signal()
    openFileDialog = Signal()
    activateDoc = Signal(str)
    closeDoc = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Nav")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.open_state: dict[str, bool] = {}  # chave -> tem alteração?
        self.folder: Path | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.setChildrenCollapsible(False)
        outer.addWidget(self.split)

        # ---------------- pasta
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(14, 14, 10, 6)
        tl.setSpacing(10)

        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(theme.app_icon_pixmap(34))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        t = QLabel("GridNote")
        t.setObjectName("Brand")
        s = QLabel("Editor de planilhas e textos")
        s.setObjectName("BrandSub")
        names.addWidget(t)
        names.addWidget(s)
        brand.addLayout(names, 1)
        tl.addLayout(brand)

        sec = QLabel("PASTA VINCULADA")
        sec.setObjectName("SectionLabel")
        tl.addWidget(sec)

        card = QFrame()
        card.setObjectName("FolderCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 10, 10)
        cl.setSpacing(6)
        row = QHBoxLayout()
        ficon = QLabel(theme.G["folder"])
        ficon.setFont(theme.glyph_label_font(18))
        ficon.setStyleSheet(f"color: {theme.C['warn']};")
        row.addWidget(ficon)
        self.folder_name = QLabel("Nenhuma pasta")
        self.folder_name.setObjectName("FolderName")
        row.addWidget(self.folder_name, 1)
        self.btn_explorer = QToolButton()
        self.btn_explorer.setProperty("kind", "ghost")
        self.btn_explorer.setIcon(theme.glyph_icon("explorer"))
        self.btn_explorer.setToolTip("Abrir esta pasta no Explorador de Arquivos")
        self.btn_explorer.clicked.connect(self._open_explorer)
        row.addWidget(self.btn_explorer)
        cl.addLayout(row)
        self.folder_path = QLabel("Vincule uma pasta para ver os arquivos aqui.")
        self.folder_path.setObjectName("FolderPath")
        self.folder_path.setWordWrap(True)
        cl.addWidget(self.folder_path)
        btns = QHBoxLayout()
        self.btn_link = QPushButton("Vincular pasta")
        self.btn_link.setIcon(theme.glyph_icon("link"))
        self.btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_link.clicked.connect(self.linkFolder)
        btn_open = QPushButton("Abrir arquivo")
        btn_open.setIcon(theme.glyph_icon("open_file"))
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.clicked.connect(self.openFileDialog)
        btns.addWidget(self.btn_link)
        btns.addWidget(btn_open)
        cl.addLayout(btns)
        tl.addWidget(card)

        self.fs = QFileSystemModel(self)
        self.fs.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.fs.setNameFilters([f"*{e}" for e in OPEN_EXTS])
        self.fs.setNameFilterDisables(False)
        self.tree = QTreeView()
        self.tree.setObjectName("NavTree")
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setItemDelegate(DirtyDotDelegate(self))
        self.tree.clicked.connect(self._tree_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.tree.hide()
        tl.addWidget(self.tree, 1)
        self.tree_empty = QLabel("Os arquivos .csv, .txt, .xlsx e .xls\nda pasta vão aparecer aqui.")
        self.tree_empty.setObjectName("EmptyHint")
        self.tree_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.addWidget(self.tree_empty, 1)
        self.split.addWidget(top)

        # ---------------- abertos
        bottom = QFrame()
        bottom.setObjectName("OpenPanel")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 10, 10)
        bl.setSpacing(6)
        sec2 = QLabel("ABERTOS AGORA")
        sec2.setObjectName("SectionLabel")
        bl.addWidget(sec2)
        self.list = QListWidget()
        self.list.setObjectName("OpenList")
        self.list.currentItemChanged.connect(self._list_changed)
        bl.addWidget(self.list, 1)
        self.list_empty = QLabel("Nenhum arquivo aberto.")
        self.list_empty.setObjectName("EmptyHint")
        bl.addWidget(self.list_empty)
        legend = QLabel("●  = alterações não salvas")
        legend.setObjectName("EmptyHint")
        bl.addWidget(legend)
        self.split.addWidget(bottom)
        self.split.setSizes([520, 220])

    # ---------------------------------------------------------------- pasta
    def set_folder(self, folder: str | None) -> None:
        if not folder or not Path(folder).is_dir():
            self.folder = None
            self.folder_name.setText("Nenhuma pasta")
            self.folder_path.setText("Vincule uma pasta para ver os arquivos aqui.")
            self.btn_link.setText("Vincular pasta")
            self.btn_explorer.setEnabled(False)
            self.tree.hide()
            self.tree_empty.show()
            return
        self.folder = Path(folder)
        self.folder_name.setText(self.folder.name or str(self.folder))
        self.folder_path.setText(str(self.folder))
        self.btn_link.setText("Trocar pasta")
        self.btn_explorer.setEnabled(True)
        root = self.fs.setRootPath(str(self.folder))
        self.tree.setModel(self.fs)
        for c in range(1, self.fs.columnCount()):
            self.tree.hideColumn(c)
        self.tree.setRootIndex(root)
        self.tree.show()
        self.tree_empty.hide()

    def set_orientation(self, bottom: bool) -> None:
        self.split.setOrientation(Qt.Orientation.Horizontal if bottom else Qt.Orientation.Vertical)

    def _open_explorer(self) -> None:
        if self.folder:
            os.startfile(self.folder)  # noqa: S606 - abre o Explorer na pasta do usuário

    def _tree_clicked(self, index) -> None:
        if not self.fs.isDir(index):
            self.openPath.emit(self.fs.filePath(index))

    def _tree_menu(self, pos) -> None:
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        path = self.fs.filePath(index)
        menu = QMenu(self)
        if not self.fs.isDir(index):
            menu.addAction(theme.glyph_icon("open_file"), "Abrir no GridNote", lambda: self.openPath.emit(path))
        menu.addAction(theme.glyph_icon("explorer"), "Mostrar no Explorador",
                       lambda: subprocess.Popen(["explorer", f"/select,{os.path.normpath(path)}"]))  # noqa: S603,S607
        menu.addAction(theme.glyph_icon("copy"), "Copiar caminho",
                       lambda: QGuiApplication.clipboard().setText(os.path.normpath(path)))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # -------------------------------------------------------------- abertos
    def set_open_docs(self, docs: list[tuple[str, str, str, bool]], active: str | None) -> None:
        """docs = [(chave, nome, formato, tem_alteração)]"""
        self.open_state = {k: d for k, _n, _f, d in docs}
        self.list.blockSignals(True)
        self.list.clear()
        for key, name, fmt, dirty in docs:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            widget = OpenItem(key, name, fmt, dirty)
            widget.closeClicked.connect(self._close_clicked)
            item.setSizeHint(QSize(100, 38))
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
            if key == active:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.list_empty.setVisible(not docs)
        self.tree.viewport().update()

    def _list_changed(self, item, _prev) -> None:
        # adiado: a lista é reconstruída em resposta, e não pode ser apagada dentro do próprio sinal
        if item:
            key = item.data(Qt.ItemDataRole.UserRole)
            QTimer.singleShot(0, lambda: self.activateDoc.emit(key))

    def _close_clicked(self, key: str) -> None:
        QTimer.singleShot(0, lambda: self.closeDoc.emit(key))
