"""Página central: título, botões Colunas/Linhas, filtro, Substituir e a grade."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu, QPushButton, QRadioButton, QSizePolicy, QStyledItemDelegate, QTabBar, QTableView, QToolButton,
    QVBoxLayout, QWidget,
)

from . import dialogs, theme
from .document import Document
from .model import MATCHES, TableModel, replace_function

TIPS = {
    "cols": "Modo Colunas: clique em uma célula ou no número no topo para selecionar a coluna inteira. "
            "Depois use Substituir para trocar os valores dela. Segure Ctrl para escolher várias colunas.",
    "rows": "Modo Linhas: clique em uma célula ou no número à esquerda para selecionar a linha inteira. "
            "O filtro mostra só as linhas que têm o texto digitado.",
    "cells": "Modo Célula: cada clique seleciona só uma célula, para corrigir valores um a um. "
             "Arraste ou use Shift/Ctrl para marcar várias; digitar preenche todas as marcadas.",
}
FILL_HINT = "  —  digite um valor para preencher todas"

# (chave, texto no menu)
SPLITS = [
    ("cells", "Células da planilha (original)"),
    ("char", "Cada caractere em uma coluna"),
    (";", "Por ponto e vírgula  ( ; )"),
    (",", "Por vírgula  ( , )"),
    ("\t", "Por tabulação"),
    ("|", "Por barra vertical  ( | )"),
    ("line", "Linha inteira em uma coluna"),
]
SPLIT_SHORT = {"cells": "Planilha", "char": "Por caractere", ";": "Por  ;", ",": "Por  ,", "\t": "Por tabulação",
               "|": "Por  |", "line": "Linha inteira"}


class FillSelectionDelegate(QStyledItemDelegate):
    """Ao terminar de digitar numa célula que faz parte de uma seleção maior, grava o valor em toda a seleção."""

    def __init__(self, page: "DocumentEditor"):
        super().__init__(page)
        self.page = page

    def setModelData(self, editor, model, index):
        page = self.page
        sm = page.view.selectionModel()
        if isinstance(editor, QLineEdit) and sm and sm.isSelected(index) and page.selection_size() > 1:
            value = editor.text()
            model.set_cells({cell: value for cell in page.selected_cells()})
            page.sel_info.setText(f"✓ \"{value}\" aplicado em {page.selection_size()} célula(s)  —  Ctrl+Z desfaz")
            return
        super().setModelData(editor, model, index)


def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("ToolSep")
    f.setFixedHeight(26)
    return f


def _tool(text: str, icon: str, tip: str) -> QToolButton:
    b = QToolButton()
    b.setText(text)
    b.setIcon(theme.glyph_icon(icon))
    b.setToolTip(tip)
    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b.setProperty("kind", "ghost")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class GridView(QTableView):
    """QTableView que devolve o foco para a grade depois de editar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(True)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().setDefaultSectionSize(28)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setHighlightSections(True)
        self.horizontalHeader().setMinimumSectionSize(28)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)


class DocumentEditor(QWidget):
    dirtyChanged = Signal()
    historyChanged = Signal()

    def __init__(self, doc: Document, parent=None, show_tips: bool = True):
        super().__init__(parent)
        self.doc = doc
        self.mode = "cols"
        self.sheet = 0
        self._show_tips = show_tips
        self._filter_timer = QTimer(self, singleShot=True, interval=250)
        self._filter_timer.timeout.connect(self.apply_filter)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 18, 28, 10)
        root.setSpacing(10)

        # ---- título estilo OneNote
        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        self.meta = QLabel()
        self.meta.setObjectName("PageMeta")
        root.addWidget(self.title)
        rule = QFrame()
        rule.setObjectName("TitleRule")
        root.addWidget(rule)
        root.addWidget(self.meta)

        # ---- barra de ferramentas
        bar = QFrame()
        bar.setObjectName("Toolbar")
        tb = QHBoxLayout(bar)
        tb.setContentsMargins(10, 8, 10, 8)
        tb.setSpacing(8)

        switch = QFrame()
        switch.setObjectName("ModeSwitch")
        sw = QHBoxLayout(switch)
        sw.setContentsMargins(3, 3, 3, 3)
        sw.setSpacing(2)
        self.btn_cols = QToolButton(text="Colunas")
        self.btn_rows = QToolButton(text="Linhas")
        self.btn_cell = QToolButton(text="Célula")
        self.btn_cols.setToolTip("Tudo por colunas: clicar seleciona a coluna inteira; digitar preenche a coluna toda")
        self.btn_rows.setToolTip("Tudo por linhas: clicar seleciona a linha inteira; digitar preenche a linha toda")
        self.btn_cell.setToolTip("Uma célula por vez: para corrigir valores individuais")
        self.mode_group = QButtonGroup(self)
        for b in (self.btn_cols, self.btn_rows, self.btn_cell):
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mode_group.addButton(b)
            sw.addWidget(b)
        self.btn_cols.setChecked(True)
        self.btn_cols.toggled.connect(lambda on: on and self.set_mode("cols"))
        self.btn_rows.toggled.connect(lambda on: on and self.set_mode("rows"))
        self.btn_cell.toggled.connect(lambda on: on and self.set_mode("cells"))
        for b in (self.btn_cols, self.btn_rows, self.btn_cell):
            # Fixed = nunca menor que o tamanho ideal (evita "C…s" em janela estreita)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        tb.addWidget(switch)

        self.btn_split = QToolButton()
        self.btn_split.setObjectName("SplitButton")
        self.btn_split.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_split.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_split.setToolTip("Como dividir cada linha em colunas (ex.: cada caractere em uma coluna)")
        self.split_menu = QMenu(self.btn_split)
        self.split_group = QActionGroup(self)
        for key, label in SPLITS:
            if key == "cells" and doc.fmt not in ("xlsx", "xls"):
                continue
            a = self.split_menu.addAction(label)
            a.setCheckable(True)
            a.setData(key)
            self.split_group.addAction(a)
            if key == "char":
                self.split_menu.addSeparator()
        self.split_group.triggered.connect(lambda a: self.set_split(a.data()))
        self.btn_split.setMenu(self.split_menu)
        self.btn_split.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        tb.addWidget(self.btn_split)
        tb.addWidget(_sep())

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("FilterEdit")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.addAction(theme.glyph_icon("filter", theme.C["muted"]), QLineEdit.ActionPosition.LeadingPosition)
        self.filter_edit.textChanged.connect(lambda _t: self._filter_timer.start())
        tb.addWidget(self.filter_edit, 2)

        tb.addWidget(QLabel("em:"))
        self.scope = QComboBox()
        self.scope.setMinimumWidth(110)
        self.scope.setToolTip("Onde procurar o texto do filtro")
        self.scope.currentIndexChanged.connect(lambda _i: self.apply_filter())
        self.scope.setMaximumWidth(260)
        tb.addWidget(self.scope, 1)

        self.match = QComboBox()
        for key, label in MATCHES.items():
            self.match.addItem(label, key)
        self.match.setToolTip("Como comparar")
        self.match.currentIndexChanged.connect(lambda _i: self.apply_filter())
        tb.addWidget(self.match)

        self.case = QToolButton(text="Aa")
        self.case.setCheckable(True)
        self.case.setProperty("kind", "ghost")
        self.case.setToolTip("Diferenciar maiúsculas de minúsculas")
        self.case.toggled.connect(lambda _on: self.apply_filter())
        tb.addWidget(self.case)

        self.count = QLabel()
        self.count.setObjectName("CountLabel")
        tb.addWidget(self.count)
        root.addWidget(bar)

        # ---- ações
        actions = QHBoxLayout()
        actions.setSpacing(4)
        self.btn_replace = _tool("Substituir", "replace", "Trocar valores na seleção (Ctrl+H)")
        self.btn_replace.setCheckable(True)
        self.btn_replace.toggled.connect(self.toggle_replace)
        self.btn_add_row = _tool("Linha", "add", "Inserir linha abaixo da seleção")
        self.btn_add_col = _tool("Coluna", "add", "Inserir coluna à direita da seleção")
        self.btn_delete = _tool("Excluir colunas", "delete", "Excluir o que estiver selecionado")
        self.btn_pull = _tool("Apagar e puxar ←", "erase",
                              "Apaga as células selecionadas e puxa o resto da linha para a esquerda,\n"
                              "sem deixar espaço. Ex.: trocar \"55\" por \"5\" apagando um caractere. (Ctrl+-)")
        self.btn_pull.clicked.connect(self.delete_shift_left)
        self.btn_undo = _tool("Desfazer", "undo", "Desfazer (Ctrl+Z)")
        self.btn_redo = _tool("Refazer", "redo", "Refazer (Ctrl+Y)")
        self.btn_add_row.clicked.connect(lambda: self.insert_rows(below=True))
        self.btn_add_col.clicked.connect(lambda: self.insert_cols(right=True))
        self.btn_delete.clicked.connect(self.delete_selection)
        self.btn_undo.clicked.connect(lambda: self.model.undo())
        self.btn_redo.clicked.connect(lambda: self.model.redo())
        for w in (self.btn_replace, self.btn_pull, self.btn_add_row, self.btn_add_col, self.btn_delete):
            actions.addWidget(w)
        actions.addWidget(_sep())
        actions.addWidget(self.btn_undo)
        actions.addWidget(self.btn_redo)
        actions.addWidget(_sep())
        self.header_check = QCheckBox("1ª linha é cabeçalho")
        self.header_check.setToolTip("Usa a primeira linha como nome das colunas")
        self.header_check.toggled.connect(self.set_header)
        actions.addWidget(self.header_check)
        actions.addStretch(1)
        self.sel_info = QLabel()
        self.sel_info.setObjectName("SelInfo")
        actions.addWidget(self.sel_info)
        root.addLayout(actions)

        # ---- dica didática
        self.tip = QFrame()
        self.tip.setObjectName("Tip")
        th = QHBoxLayout(self.tip)
        th.setContentsMargins(12, 8, 8, 8)
        bulb = QLabel(theme.G["lightbulb"])
        bulb.setFont(theme.glyph_label_font(16))
        bulb.setStyleSheet(f"color: {theme.C['warn']};")
        th.addWidget(bulb)
        self.tip_text = QLabel()
        self.tip_text.setObjectName("TipText")
        self.tip_text.setWordWrap(True)
        th.addWidget(self.tip_text, 1)
        close_tip = QToolButton()
        close_tip.setProperty("kind", "close")
        close_tip.setIcon(theme.glyph_icon("close", theme.C["muted"]))
        close_tip.setToolTip("Esconder dicas (dá para mostrar de novo em Exibir)")
        close_tip.clicked.connect(lambda: self.set_tips_visible(False))
        th.addWidget(close_tip)
        root.addWidget(self.tip)
        self.tip.setVisible(show_tips)

        # ---- painel Substituir
        self.replace_panel = self._build_replace_panel()
        self.replace_panel.hide()
        root.addWidget(self.replace_panel)

        # ---- grade
        self.view = GridView()
        self.view.customContextMenuRequested.connect(lambda pos: self.context_menu(self.view.viewport().mapToGlobal(pos)))
        for header in (self.view.horizontalHeader(), self.view.verticalHeader()):
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(lambda pos, h=header: self.context_menu(h.mapToGlobal(pos)))
        self.view.setItemDelegate(FillSelectionDelegate(self))
        root.addWidget(self.view, 1)
        self._install_shortcuts()

        # ---- abas da planilha
        self.tabs = QTabBar()
        self.tabs.setObjectName("SheetTabs")
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        for n in doc.sheet_names:
            self.tabs.addTab(n)
        self.tabs.currentChanged.connect(self.set_sheet)
        self.tabs.setVisible(len(doc.sheet_names) > 1)
        root.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignLeft)

        for m in doc.models:
            m.dirtyChanged.connect(lambda _d: self.dirtyChanged.emit())
            m.historyChanged.connect(self._on_history)
        doc.pathChanged.connect(self.update_title)
        self.update_title()
        self.set_sheet(0, first=True)
        self.set_mode("cols")

    # ----------------------------------------------------------------- estado
    @property
    def model(self) -> TableModel:
        return self.doc.models[self.sheet]

    def update_title(self) -> None:
        self.title.setText(self.doc.path.stem)
        try:
            mtime = dt.datetime.fromtimestamp(self.doc.path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        except OSError:
            mtime = "—"
        m = self.model if self.doc.models else None
        size = f"{m.data_row_count:,} linhas × {m.ncols:,} colunas".replace(",", ".") if m else ""
        folder = str(self.doc.path.parent)
        if len(folder) > 60:
            folder = folder[:22] + " … " + folder[-35:]
        self.meta.setText(f"{self.doc.fmt.upper()}   ·   {size}   ·   modificado em {mtime}   ·   {folder}")
        self.meta.setToolTip(str(self.doc.path))

    def set_tips_visible(self, on: bool) -> None:
        self._show_tips = on
        self.tip.setVisible(on)
        win = self.window()
        if hasattr(win, "on_tips_toggled"):
            win.on_tips_toggled(on)

    def set_sheet(self, index: int, first: bool = False) -> None:
        if index < 0:
            return
        if not first:
            self._sync_filter_to_model(clear=True)
        self.sheet = index
        m = self.model
        self.view.setModel(m)
        self.view.selectionModel().selectionChanged.connect(self._on_selection)
        if not getattr(m, "_editor_wired", False):
            m._editor_wired = True
            m.filterApplied.connect(lambda m=m: m is self.model and self._on_filter_applied())
            m.modelReset.connect(lambda m=m: m is self.model and self._on_selection())
        self._sync_split_ui()
        self._rebuild_scope()
        self._size_columns()
        self._on_history()
        self._on_selection()
        self._update_count()
        self.update_title()

    def _size_columns(self) -> None:
        m = self.model
        header = self.view.horizontalHeader()
        if m.split == "char":
            header.setDefaultSectionSize(36)
            for c in range(m.columnCount()):
                header.resizeSection(c, 36)
            return
        header.setDefaultSectionSize(120)
        if m.columnCount() <= 60:
            header.setResizeContentsPrecision(200)
            self.view.resizeColumnsToContents()
            for c in range(m.columnCount()):
                w = header.sectionSize(c)
                header.resizeSection(c, max(70, min(w + 18, 360)))

    def _rebuild_scope(self) -> None:
        m = self.model
        keep = self.scope.currentData()
        self.scope.blockSignals(True)
        self.scope.clear()
        self.scope.addItem("Todas as colunas", -1)
        for c in range(m.ncols):
            label = m.column_label(c)
            self.scope.addItem(label if label.startswith("Coluna") else f"{c + 1} · {label}", c)
        i = self.scope.findData(keep if keep is not None else -1)
        self.scope.setCurrentIndex(max(0, i))
        self.scope.blockSignals(False)

    def _on_history(self) -> None:
        self.btn_undo.setEnabled(self.model.can_undo())
        self.btn_redo.setEnabled(self.model.can_redo())
        self.historyChanged.emit()

    def _on_filter_applied(self) -> None:
        split_changed = self._sync_split_ui()
        if split_changed or self.scope.count() - 1 != self.model.ncols:
            self._rebuild_scope()
        if split_changed:
            self._size_columns()
        self._update_count()
        self.update_title()

    # --------------------------------------------------------------- dividir
    def _sync_split_ui(self) -> bool:
        """Atualiza botão Dividir e cabeçalho conforme o modelo. Devolve True se a divisão mudou."""
        m = self.model
        changed = getattr(self, "_shown_split", None) != m.split
        self._shown_split = m.split
        self.btn_split.setText(f"Dividir: {SPLIT_SHORT.get(m.split, m.split)}  ▾")
        self.btn_split.setIcon(theme.glyph_icon("replace" if m.split == "cells" else "sort"))
        for a in self.split_group.actions():
            a.setChecked(a.data() == m.split)
        self.header_check.blockSignals(True)
        self.header_check.setChecked(m.header)
        self.header_check.blockSignals(False)
        return changed

    def set_split(self, mode: str) -> None:
        m = self.model
        if mode == m.split:
            return
        if m.ncols * len(m.rows) > 3_000_000 or (mode == "char" and len(m.rows) > 200_000):
            dialogs.message(self, "Arquivo grande demais", "Dividir este arquivo geraria células demais para editar com conforto.", "warn")
            self._sync_split_ui()
            return
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.filter_edit.blockSignals(True)
            self.filter_edit.clear()
            self.filter_edit.blockSignals(False)
            m.resplit(mode)
        finally:
            QGuiApplication.restoreOverrideCursor()
        self.sel_info.setText("✓ Dividido  —  Ctrl+Z desfaz")
        self.sel_info.setToolTip("Ao salvar em CSV/TXT, cada linha volta a ser o texto original.")

    # ------------------------------------------------------------------ modo
    def set_mode(self, mode: str) -> None:
        cols, rows = mode == "cols", mode == "rows"
        target = {"cols": self.btn_cols, "rows": self.btn_rows, "cells": self.btn_cell}[mode]
        if not target.isChecked():
            target.setChecked(True)  # o toggled chama set_mode de novo
            return
        self.mode = mode
        on, off = theme.C["bg0"], theme.C["muted"]
        self.btn_cols.setIcon(theme.bars_icon(True, on if cols else off))
        self.btn_rows.setIcon(theme.bars_icon(False, on if rows else off))
        self.btn_cell.setIcon(theme.glyph_icon("edit", on if mode == "cells" else off))
        behavior = QAbstractItemView.SelectionBehavior
        self.view.setSelectionBehavior(behavior.SelectColumns if cols else (behavior.SelectRows if rows else behavior.SelectItems))
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for header, active in ((self.view.horizontalHeader(), not rows), (self.view.verticalHeader(), not cols)):
            header.setProperty("focus", "true" if active else "false")
            header.setHighlightSections(active)
            header.style().unpolish(header)
            header.style().polish(header)
        self.view.clearSelection()
        self.btn_delete.setText("Excluir colunas" if cols else "Excluir linhas")
        self.tip_text.setText(TIPS[mode])
        self.apply_filter()

    # ---------------------------------------------------------------- filtro
    def apply_filter(self) -> None:
        self._filter_timer.stop()
        text = self.filter_edit.text()
        by_line = self.match.currentData() == "lines"
        self.scope.setEnabled(not by_line)
        self.case.setEnabled(not by_line)
        self.filter_edit.setPlaceholderText(self._filter_placeholder())
        self.filter_edit.setProperty("active", "true" if text else "false")
        self.filter_edit.style().unpolish(self.filter_edit)
        self.filter_edit.style().polish(self.filter_edit)
        col = self.scope.currentData()
        mode = "cols" if self.mode == "cols" else "rows"
        self.model.set_filter(text, -1 if col is None else col, self.match.currentData(), self.case.isChecked(), mode)

    def _filter_placeholder(self) -> str:
        if self.match.currentData() == "lines":
            return "Números das linhas, ex.: 3, 6, 9, 15, 22  ou  10-20"
        if self.mode == "cols" and self.model.split != "char" and self.scope.currentData() in (None, -1):
            return "Filtrar: mostrar só colunas que têm…  (Ctrl+F)"
        return "Filtrar: mostrar só linhas que têm…  (Ctrl+F)"

    def _sync_filter_to_model(self, clear: bool) -> None:
        if clear and self.filter_edit.text():
            self.filter_edit.blockSignals(True)
            self.filter_edit.clear()
            self.filter_edit.blockSignals(False)
            self.model.set_filter("", -1, "contains", False, self.mode)

    def _update_count(self) -> None:
        m = self.model
        if not m.filter_active():
            self.count.setText("")
            return
        if m.f_col < 0 and self.mode == "cols" and m.split != "char" and m.f_match != "lines":
            self.count.setText(f"{m.columnCount()} de {m.ncols} colunas")
        else:
            self.count.setText(f"{m.rowCount()} de {m.data_row_count} linhas")

    def focus_filter(self) -> None:
        self.filter_edit.setFocus()
        self.filter_edit.selectAll()

    # ------------------------------------------------------------- seleção
    def selected_ranges(self):
        sm = self.view.selectionModel()
        return list(sm.selection()) if sm else []

    def selected_cells(self):
        """Pares (abs_linha, abs_coluna) selecionados; sem seleção = tudo que está visível."""
        m = self.model
        ranges = self.selected_ranges()
        vr, vc = m.visible_rows(), m.visible_cols()
        if not ranges:
            for ar in vr:
                for ac in vc:
                    yield ar, ac
            return
        for rg in ranges:
            cols = [vc[c] for c in range(rg.left(), rg.right() + 1)]
            for r in range(rg.top(), rg.bottom() + 1):
                ar = vr[r]
                for ac in cols:
                    yield ar, ac

    def _sel_spans(self):
        rows, cols = set(), set()
        m = self.model
        for rg in self.selected_ranges():
            cols.update(m.abs_col(c) for c in range(rg.left(), rg.right() + 1))
            rows.update(m.abs_row(r) for r in range(rg.top(), rg.bottom() + 1))
        return rows, cols

    def selection_size(self) -> int:
        return sum(rg.width() * rg.height() for rg in self.selected_ranges())

    def _selection_text(self) -> str:
        ranges = self.selected_ranges()
        m = self.model
        if not ranges:
            return ""
        cells = self.selection_size()
        rows, cols = self._sel_spans()
        n = f"{cells:,}".replace(",", ".")
        if self.mode == "cols" and all(rg.height() == m.rowCount() for rg in ranges):
            if len(cols) == 1:
                return f"{m.column_label(next(iter(cols)))} selecionada · {n} células"
            return f"{len(cols)} colunas selecionadas · {n} células"
        if self.mode == "rows" and all(rg.width() == m.columnCount() for rg in ranges):
            if len(rows) == 1:
                return f"Linha {next(iter(rows)) + 1} selecionada · {n} células"
            return f"{len(rows)} linhas selecionadas · {n} células"
        return f"{n} células selecionadas" if cells > 1 else "1 célula selecionada"

    def _on_selection(self, *_):
        text = self._selection_text()
        self.sel_info.setText(text + (FILL_HINT if self.selection_size() > 1 else ""))
        if self.replace_panel.isVisible():
            self.scope_label.setText(
                f"Onde: {text}" if text else "Onde: nada selecionado → vale para TODA a tabela visível"
            )

    # ------------------------------------------------------------ substituir
    def _build_replace_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ReplacePanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 12, 12, 12)
        lay.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel("Substituir na seleção")
        title.setObjectName("PanelTitle")
        top.addWidget(title)
        self.scope_label = QLabel()
        self.scope_label.setObjectName("ScopeLabel")
        top.addWidget(self.scope_label, 1)
        close = QToolButton()
        close.setProperty("kind", "close")
        close.setIcon(theme.glyph_icon("close", theme.C["muted"]))
        close.clicked.connect(lambda: self.btn_replace.setChecked(False))
        top.addWidget(close)
        lay.addLayout(top)

        modes = QHBoxLayout()
        self.rb_swap = QRadioButton("Trocar um texto por outro")
        self.rb_fill = QRadioButton("Preencher tudo com o mesmo valor")
        self.rb_swap.setChecked(True)
        modes.addWidget(self.rb_swap)
        modes.addWidget(self.rb_fill)
        modes.addStretch(1)
        lay.addLayout(modes)

        fields = QHBoxLayout()
        self.find_label = QLabel("Procurar:")
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("ex.: A")
        self.new_label = QLabel("Trocar por:")
        self.new_edit = QLineEdit()
        self.new_edit.setPlaceholderText("ex.: B  (vazio = apagar)")
        self.whole = QCheckBox("Só células inteiras iguais")
        self.whole.setToolTip("Marcado: só troca células cujo valor é exatamente o procurado.\n"
                              "Desmarcado: troca o texto em qualquer parte da célula.")
        self.rep_case = QCheckBox("Aa")
        self.rep_case.setToolTip("Diferenciar maiúsculas de minúsculas")
        apply_btn = QPushButton("Aplicar")
        apply_btn.setProperty("kind", "primary")
        apply_btn.setIcon(theme.glyph_icon("check", "#06152C"))
        apply_btn.clicked.connect(self.apply_replace)
        for w in (self.find_label, self.find_edit, self.new_label, self.new_edit, self.whole, self.rep_case, apply_btn):
            fields.addWidget(w, 1 if isinstance(w, QLineEdit) else 0)
        self.find_edit.returnPressed.connect(self.apply_replace)
        self.new_edit.returnPressed.connect(self.apply_replace)
        lay.addLayout(fields)

        def on_mode():
            fill = self.rb_fill.isChecked()
            for w in (self.find_label, self.find_edit, self.whole, self.rep_case):
                w.setVisible(not fill)
            self.new_label.setText("Valor:" if fill else "Trocar por:")
        self.rb_fill.toggled.connect(on_mode)
        return panel

    def toggle_replace(self, on: bool) -> None:
        self.replace_panel.setVisible(on)
        if on:
            self._on_selection()
            (self.new_edit if self.rb_fill.isChecked() else self.find_edit).setFocus()

    def open_replace(self) -> None:
        if self.btn_replace.isChecked():
            self.toggle_replace(True)
        else:
            self.btn_replace.setChecked(True)

    def apply_replace(self) -> None:
        fill = self.rb_fill.isChecked()
        find, new = self.find_edit.text(), self.new_edit.text()
        whole = self.whole.isChecked()
        if not fill and not find and not whole:
            dialogs.message(self, "Falta o texto", "Digite o que procurar. Para trocar só as células vazias, "
                            "deixe \"Procurar\" vazio e marque \"Só células inteiras iguais\".", "warn")
            return
        fn = replace_function(find, new, whole, self.rep_case.isChecked(), fill)
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            rows = self.model.rows
            changes = {}
            for ar, ac in self.selected_cells():
                old = rows[ar][ac]
                value = fn(old)
                if value != old:
                    changes[(ar, ac)] = value
            n = self.model.set_cells(changes)
        finally:
            QGuiApplication.restoreOverrideCursor()
        self.scope_label.setText(f"✓ {n} célula(s) alterada(s)" if n else "Nenhuma célula combinou — nada foi alterado")

    # ------------------------------------------------------ estrutura/edição
    def set_header(self, on: bool) -> None:
        self.model.set_header(on)
        self._rebuild_scope()
        self._size_columns()

    def insert_rows(self, below: bool) -> None:
        rows, _ = self._sel_spans()
        m = self.model
        if rows:
            at = max(rows) + 1 if below else min(rows)
        else:
            idx = self.view.currentIndex()
            at = (m.abs_row(idx.row()) + (1 if below else 0)) if idx.isValid() else len(m.rows)
        m.insert_rows(at)

    def insert_cols(self, right: bool) -> None:
        _, cols = self._sel_spans()
        m = self.model
        if cols:
            at = max(cols) + 1 if right else min(cols)
        else:
            idx = self.view.currentIndex()
            at = (m.abs_col(idx.column()) + (1 if right else 0)) if idx.isValid() else m.ncols
        m.insert_cols(at)
        self._rebuild_scope()

    def delete_selection(self) -> None:
        rows, cols = self._sel_spans()
        m = self.model
        if self.mode == "cols":
            full = [c for c in cols if all(rg.height() == m.rowCount() for rg in self.selected_ranges())]
            if not full:
                dialogs.message(self, "Selecione colunas", "Clique no número no topo de uma coluna para selecioná-la e depois em Excluir.", "warn")
                return
            if len(full) >= m.ncols:
                dialogs.message(self, "Não dá para excluir tudo", "A tabela precisa ter pelo menos uma coluna.", "warn")
                return
            if dialogs.confirm(self, "Excluir colunas", f"Excluir {len(full)} coluna(s) inteira(s)? Dá para desfazer com Ctrl+Z.", "Excluir", danger=True):
                m.remove_cols(full)
                self._rebuild_scope()
        else:
            if not rows:
                dialogs.message(self, "Selecione linhas", "Clique no número à esquerda de uma linha para selecioná-la e depois em Excluir.", "warn")
                return
            if dialogs.confirm(self, "Excluir linhas", f"Excluir {len(rows)} linha(s)? Dá para desfazer com Ctrl+Z.", "Excluir", danger=True):
                m.remove_rows(rows)

    def delete_shift_left(self) -> None:
        if not self.selected_ranges():
            dialogs.message(self, "Selecione o que apagar",
                            "Selecione as células que vão sumir (ex.: a coluna do segundo \"5\" nas linhas desejadas). "
                            "Dica: no filtro, escolha \"Nº da linha\" e digite 3, 6, 9, 15, 22 para ver só essas linhas.", "warn")
            return
        n = self.model.delete_cells_shift_left(list(self.selected_cells()))
        self.sel_info.setText(f"✓ {n} célula(s) apagada(s) e linha puxada para a esquerda  —  Ctrl+Z desfaz")

    def insert_shift_right(self) -> None:
        if self.selected_ranges():
            n = self.model.insert_cells_shift_right(list(self.selected_cells()))
            self.sel_info.setText(f"✓ {n} espaço(s) inserido(s), linha empurrada para a direita  —  Ctrl+Z desfaz")

    def clear_selection_cells(self) -> None:
        if not self.selected_ranges():
            return
        self.model.set_cells({cell: "" for cell in self.selected_cells()})

    def copy_selection(self) -> None:
        ranges = self.selected_ranges()
        if not ranges:
            return
        rg = ranges[0]
        m = self.model
        lines = []
        for r in range(rg.top(), rg.bottom() + 1):
            lines.append("\t".join(m.rows[m.abs_row(r)][m.abs_col(c)] for c in range(rg.left(), rg.right() + 1)))
        QGuiApplication.clipboard().setText("\r\n".join(lines))

    def paste(self) -> None:
        text = QGuiApplication.clipboard().text()
        if not text:
            return
        m = self.model
        idx = self.view.currentIndex()
        ranges = self.selected_ranges()
        top = ranges[0].top() if ranges else (idx.row() if idx.isValid() else 0)
        left = ranges[0].left() if ranges else (idx.column() if idx.isValid() else 0)
        block = [line.split("\t") for line in text.replace("\r\n", "\n").rstrip("\n").split("\n")]
        changes = {}
        if len(block) == 1 and len(block[0]) == 1 and ranges:
            for cell in self.selected_cells():  # um valor colado numa seleção: preenche tudo
                changes[cell] = block[0][0]
        else:
            for i, line in enumerate(block):
                r = top + i
                if r >= m.rowCount():
                    break
                for j, v in enumerate(line):
                    c = left + j
                    if c >= m.columnCount():
                        break
                    changes[(m.abs_row(r), m.abs_col(c))] = v
        m.set_cells(changes)

    def sort_current(self, descending: bool) -> None:
        idx = self.view.currentIndex()
        _, cols = self._sel_spans()
        col = min(cols) if cols else (self.model.abs_col(idx.column()) if idx.isValid() else None)
        if col is not None:
            self.model.sort_by(col, descending)

    def filter_by_current(self) -> None:
        idx = self.view.currentIndex()
        _, cols = self._sel_spans()
        col = min(cols) if cols else (self.model.abs_col(idx.column()) if idx.isValid() else None)
        if col is None:
            return
        i = self.scope.findData(col)
        if i >= 0:
            self.scope.setCurrentIndex(i)
        self.focus_filter()

    def _install_shortcuts(self) -> None:
        def add(seq, fn):
            a = QAction(self.view)
            a.setShortcut(QKeySequence(seq))
            a.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
            a.triggered.connect(fn)
            self.view.addAction(a)
        add(QKeySequence.StandardKey.Copy, self.copy_selection)
        add(QKeySequence.StandardKey.Paste, self.paste)
        add(Qt.Key.Key_Delete, self.clear_selection_cells)
        add(Qt.Key.Key_Backspace, self.clear_selection_cells)
        add("Ctrl+-", self.delete_shift_left)
        add("Ctrl++", self.insert_shift_right)
        add("Ctrl+Shift+=", self.insert_shift_right)

    def context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        cols = self.mode == "cols"
        def item(text, icon, fn, enabled=True):
            a = menu.addAction(theme.glyph_icon(icon), text)
            a.triggered.connect(fn)
            a.setEnabled(enabled)
        has_sel = bool(self.selected_ranges())
        item("Substituir na seleção…", "replace", self.open_replace)
        item("Filtrar por esta coluna…", "filter", self.filter_by_current, has_sel or self.view.currentIndex().isValid())
        menu.addSeparator()
        item("Copiar", "copy", self.copy_selection, has_sel)
        item("Colar", "paste", self.paste)
        item("Limpar conteúdo (deixa vazio)", "erase", self.clear_selection_cells, has_sel)
        item("Apagar e puxar a linha para a esquerda", "erase", self.delete_shift_left, has_sel)
        item("Inserir célula e empurrar para a direita", "add", self.insert_shift_right, has_sel)
        menu.addSeparator()
        item("Inserir linha acima", "add", lambda: self.insert_rows(below=False))
        item("Inserir linha abaixo", "add", lambda: self.insert_rows(below=True))
        item("Inserir coluna à esquerda", "add", lambda: self.insert_cols(right=False))
        item("Inserir coluna à direita", "add", lambda: self.insert_cols(right=True))
        item("Excluir colunas selecionadas" if cols else "Excluir linhas selecionadas", "delete", self.delete_selection, has_sel)
        menu.addSeparator()
        item("Ordenar A → Z por esta coluna", "sort", lambda: self.sort_current(False))
        item("Ordenar Z → A por esta coluna", "sort", lambda: self.sort_current(True))
        menu.exec(global_pos)
