"""Diálogos: importar .txt, salvar como, alterações pendentes, mensagens e ajuda."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QScrollArea, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout,
    QWidget,
)

from . import theme
from .fileio import SAVE_FORMATS, TXT_MODES, rectangular, resolve_txt_mode, split_text, text_lines_of


def _button(text: str, kind: str | None = None, icon: str | None = None) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if icon:
        color = "#06152C" if kind == "primary" else (theme.C["danger"] if kind == "danger" else None)
        b.setIcon(theme.glyph_icon(icon, color))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("DialogTitle")
    return lbl


def _text(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("DialogText")
    lbl.setWordWrap(True)
    return lbl


class BaseDialog(QDialog):
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(24, 22, 24, 20)
        self.lay.setSpacing(12)

    def add_buttons(self, *buttons: QPushButton) -> None:
        row = QHBoxLayout()
        row.addStretch(1)
        for b in buttons:
            row.addWidget(b)
        self.lay.addSpacing(6)
        self.lay.addLayout(row)


# ---------------------------------------------------------------------------
class TxtImportDialog(BaseDialog):
    """Pergunta como dividir um .txt em colunas, com pré-visualização."""

    def __init__(self, parent, path: Path):
        super().__init__(parent, "Abrir arquivo de texto")
        self.resize(760, 560)
        self.lines = text_lines_of(path)[:12]
        self.lay.addWidget(_title(f"Como dividir \"{path.name}\" em colunas?"))
        self.lay.addWidget(_text(
            "Arquivos .txt não têm colunas definidas. Escolha como separar cada linha — "
            "a prévia abaixo mostra o resultado. Para arquivos de posição fixa (ex.: CNAB), "
            "use \"Cada caractere em uma coluna\"."
        ))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        self.group = QButtonGroup(self)
        for i, (key, label) in enumerate(TXT_MODES.items()):
            rb = QRadioButton(label)
            rb.setProperty("mode", key)
            self.group.addButton(rb)
            grid.addWidget(rb, i // 2, i % 2)
            if key == "auto":
                rb.setChecked(True)
        self.group.buttonToggled.connect(lambda *_: self.refresh())
        self.lay.addLayout(grid)
        self.detected = QLabel()
        self.detected.setObjectName("SelInfo")
        self.lay.addWidget(self.detected)
        self.preview = QTableWidget()
        self.preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview.verticalHeader().setDefaultSectionSize(24)
        self.lay.addWidget(self.preview, 1)
        ok = _button("Abrir", "primary", "check")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        cancel = _button("Cancelar", "ghost")
        cancel.clicked.connect(self.reject)
        self.add_buttons(cancel, ok)
        self.refresh()

    def mode(self) -> str:
        return self.group.checkedButton().property("mode")

    def refresh(self) -> None:
        chosen = self.mode()
        real = resolve_txt_mode(self.lines, chosen)
        if chosen == "auto":
            self.detected.setText(f"Detectado: {TXT_MODES[real]}")
        else:
            self.detected.setText("")
        rows = rectangular(split_text(self.lines, real))
        ncols = min(len(rows[0]), 200)
        self.preview.setRowCount(len(rows))
        self.preview.setColumnCount(ncols)
        self.preview.setHorizontalHeaderLabels([str(i + 1) for i in range(ncols)])
        for r, row in enumerate(rows):
            for c in range(ncols):
                self.preview.setItem(r, c, QTableWidgetItem(row[c]))
        if real == "char":
            for c in range(ncols):
                self.preview.setColumnWidth(c, 30)
        else:
            self.preview.resizeColumnsToContents()


# ---------------------------------------------------------------------------
ENCODINGS = [
    ("utf-8-sig", "UTF-8 com BOM (abre certo no Excel)"),
    ("utf-8", "UTF-8"),
    ("cp1252", "ANSI / Windows-1252 (sistemas antigos)"),
]
CSV_DELIMS = [(";", "Ponto e vírgula  ( ; )"), (",", "Vírgula  ( , )"), ("\t", "Tabulação"), ("|", "Barra vertical  ( | )")]
TXT_SAVE = [("\t", "Tabulação"), (";", "Ponto e vírgula  ( ; )"), (",", "Vírgula  ( , )"), ("|", "Barra vertical  ( | )"),
            ("char", "Sem separador (largura fixa)"), ("line", "Uma coluna por linha")]
FORMAT_ICON = {"xlsx": "document", "xls": "document", "csv": "document", "txt": "document", "docx": "document", "pdf": "document"}


def _combo(items, current) -> QComboBox:
    cb = QComboBox()
    for key, label in items:
        cb.addItem(label, key)
    i = cb.findData(current)
    cb.setCurrentIndex(max(0, i))
    return cb


class SaveAsDialog(BaseDialog):
    """Escolha do formato e das opções antes de escolher o local."""

    def __init__(self, parent, doc, sheet_count: int):
        super().__init__(parent, "Salvar como")
        self.resize(640, 520)
        self.doc = doc
        self.lay.addWidget(_title("Salvar como…"))
        self.lay.addWidget(_text("Escolha o formato. Depois você escolhe a pasta e o nome do arquivo."))

        grid = QGridLayout()
        grid.setSpacing(10)
        self.group = QButtonGroup(self)
        for i, (key, (label, ext, desc, _editable)) in enumerate(SAVE_FORMATS.items()):
            card = QPushButton(f"  {label}  ·  {ext}\n  {desc}")
            card.setObjectName("FormatCard")
            card.setCheckable(True)
            card.setMinimumHeight(62)
            card.setProperty("fmt", key)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(card)
            grid.addWidget(card, i // 2, i % 2)
        self.lay.addLayout(grid)

        self.options = QWidget()
        form = QFormLayout(self.options)
        form.setContentsMargins(0, 6, 0, 0)
        meta = doc.meta
        self.csv_delim = _combo(CSV_DELIMS, meta.get("delimiter", ";"))
        self.txt_mode = _combo(TXT_SAVE, meta.get("txt_mode", "\t"))
        self.encoding = _combo(ENCODINGS, meta.get("encoding", "utf-8-sig"))
        self.lbl_delim = QLabel("Separador:")
        self.lbl_txt = QLabel("Divisão:")
        self.lbl_enc = QLabel("Codificação:")
        form.addRow(self.lbl_delim, self.csv_delim)
        form.addRow(self.lbl_txt, self.txt_mode)
        form.addRow(self.lbl_enc, self.encoding)
        self.lay.addWidget(self.options)

        self.note = _text("")
        self.note.setObjectName("ScopeLabel")
        self.lay.addWidget(self.note)
        self.lay.addStretch(1)
        self.sheet_count = sheet_count

        ok = _button("Escolher local e salvar", "primary", "save")
        ok.clicked.connect(self.accept)
        cancel = _button("Voltar", "ghost")
        cancel.clicked.connect(self.reject)
        self.add_buttons(cancel, ok)

        self.group.buttonToggled.connect(lambda *_: self.refresh())
        start = doc.fmt if doc.fmt in SAVE_FORMATS else "xlsx"
        for b in self.group.buttons():
            if b.property("fmt") == start:
                b.setChecked(True)
        self.refresh()

    def fmt(self) -> str:
        return self.group.checkedButton().property("fmt")

    def values(self) -> dict:
        f = self.fmt()
        if f == "csv":
            return {"delimiter": self.csv_delim.currentData(), "encoding": self.encoding.currentData()}
        if f == "txt":
            return {"txt_mode": self.txt_mode.currentData(), "encoding": self.encoding.currentData()}
        return {}

    def refresh(self) -> None:
        f = self.fmt()
        for w in (self.lbl_delim, self.csv_delim):
            w.setVisible(f == "csv")
        for w in (self.lbl_txt, self.txt_mode):
            w.setVisible(f == "txt")
        for w in (self.lbl_enc, self.encoding):
            w.setVisible(f in ("csv", "txt"))
        notes = []
        if f in ("docx", "pdf"):
            notes.append("Word e PDF são para ler/imprimir. O arquivo aberto continua com as alterações "
                         "pendentes até você salvá-lo em um formato editável.")
        if f in ("csv", "txt") and self.sheet_count > 1:
            notes.append("Este arquivo tem várias abas: só a aba atual vai para o arquivo. "
                         "Para manter todas, use Excel.")
        if f in ("xlsx", "xls"):
            notes.append("São gravados os valores das células (sem cores, fórmulas ou mesclagens).")
        if f == "xls":
            notes.append("O .xls aceita no máximo 65.536 linhas e 256 colunas.")
        if f == "docx":
            notes.append("O Word aceita no máximo 63 colunas por tabela.")
        self.note.setText("\n".join(notes))


# ---------------------------------------------------------------------------
class UnsavedDialog(BaseDialog):
    """Obriga a escolher: salvar, descartar ou voltar."""

    SAVE, DISCARD, BACK = "save", "discard", "back"

    def __init__(self, parent, names: list[str], closing_app: bool):
        super().__init__(parent, "Alterações não salvas")
        self.choice = self.BACK
        self.setMinimumWidth(480)
        many = len(names) > 1
        self.lay.addWidget(_title("Você tem alterações não salvas" if many else "Este arquivo tem alterações não salvas"))
        self.lay.addWidget(_text(
            ("Antes de fechar o GridNote, " if closing_app else "Antes de fechar, ")
            + "escolha o que fazer com " + ("estes arquivos:" if many else "este arquivo:")
        ))
        box = QVBoxLayout()
        box.setSpacing(6)
        for n in names[:12]:
            row = QFrame()
            row.setObjectName("FileRow")
            h = QHBoxLayout(row)
            h.setContentsMargins(10, 7, 10, 7)
            dot = QLabel()
            dot.setPixmap(theme.dot_pixmap("#FFFFFF", 12))
            h.addWidget(dot)
            h.addWidget(QLabel(n), 1)
            box.addWidget(row)
        if len(names) > 12:
            box.addWidget(_text(f"… e mais {len(names) - 12} arquivo(s)."))
        self.lay.addLayout(box)

        save = _button("Salvar tudo" if many else "Salvar", "primary", "save")
        discard = _button("Descartar alterações", "danger", "delete")
        back = _button("Voltar e continuar editando", "ghost")
        save.setDefault(True)
        save.clicked.connect(lambda: self._done(self.SAVE))
        discard.clicked.connect(lambda: self._done(self.DISCARD))
        back.clicked.connect(lambda: self._done(self.BACK))
        self.add_buttons(back, discard, save)

    def _done(self, choice: str) -> None:
        self.choice = choice
        self.accept()

    @classmethod
    def ask(cls, parent, names: list[str], closing_app: bool = False) -> str:
        d = cls(parent, names, closing_app)
        d.exec()
        return d.choice


# ---------------------------------------------------------------------------
def message(parent, title: str, text: str, kind: str = "info") -> None:
    d = BaseDialog(parent, title)
    d.setMinimumWidth(420)
    row = QHBoxLayout()
    icon = QLabel(theme.G["warning" if kind != "info" else "check"])
    icon.setFont(theme.glyph_label_font(26))
    icon.setStyleSheet(f"color: {theme.C['danger'] if kind == 'error' else (theme.C['warn'] if kind == 'warn' else theme.C['ok'])};")
    icon.setAlignment(Qt.AlignmentFlag.AlignTop)
    row.addWidget(icon)
    col = QVBoxLayout()
    col.addWidget(_title(title))
    col.addWidget(_text(text))
    row.addLayout(col, 1)
    d.lay.addLayout(row)
    ok = _button("Entendi", "primary")
    ok.clicked.connect(d.accept)
    d.add_buttons(ok)
    d.exec()


def confirm(parent, title: str, text: str, yes: str, no: str = "Voltar", danger: bool = False) -> bool:
    d = BaseDialog(parent, title)
    d.setMinimumWidth(420)
    d.lay.addWidget(_title(title))
    d.lay.addWidget(_text(text))
    y = _button(yes, "danger" if danger else "primary")
    n = _button(no, "ghost")
    y.clicked.connect(d.accept)
    n.clicked.connect(d.reject)
    d.add_buttons(n, y)
    return d.exec() == QDialog.DialogCode.Accepted


HELP_HTML = """
<style>
h2 {{ color:#FFFFFF; margin-top:18px; }} p, li {{ color:#C9D7EC; line-height:150%; }}
b {{ color:#FFFFFF; }} .k {{ background:#1A3666; padding:1px 6px; border-radius:4px; color:#FFFFFF; }}
</style>
<h2>1. Vincule uma pasta</h2>
<p>Clique em <b>Vincular pasta</b> na barra lateral. Todos os arquivos <b>.csv, .txt, .xlsx e .xls</b>
dessa pasta (e das subpastas) aparecem ali, como os cadernos do OneNote. Um clique abre o arquivo.</p>
<h2>2. Escolha: Colunas ou Linhas</h2>
<ul>
<li><b>Colunas</b>: clicar em qualquer célula seleciona a <b>coluna inteira</b>. O filtro esconde as
colunas que não têm o texto digitado.</li>
<li><b>Linhas</b>: clicar seleciona a <b>linha inteira</b>. O filtro mostra só as linhas que têm o texto.</li>
<li>No campo <b>em:</b> dá para escolher uma coluna específica — aí o filtro mostra as linhas em que
essa coluna combina com o texto.</li>
</ul>
<h2>3. Trocar valores de uma coluna inteira</h2>
<p>Selecione a coluna (clique no número no topo), clique em <b>Substituir</b> <span class="k">Ctrl+H</span> e:</p>
<ul>
<li><b>Trocar texto</b>: troca, por exemplo, todo "A" por "B" só dentro da seleção;</li>
<li><b>Preencher</b>: coloca o mesmo valor em todas as células selecionadas.</li>
</ul>
<p>Células alteradas ficam <b>destacadas em amarelo</b> até você salvar.</p>
<h2>4. Salvar ou Cancelar</h2>
<p>Enquanto houver alterações, o arquivo mostra uma <b>bolinha branca</b> ● e a barra de baixo fica amarela.
Você pode trocar de arquivo à vontade, mas para fechar é preciso <b>Salvar</b> ou <b>Cancelar alterações</b>.
<b>Salvar como</b> grava em Excel (.xlsx/.xls), CSV, TXT, Word ou PDF.</p>
<h2>Atalhos</h2>
<p><span class="k">Ctrl+S</span> salvar · <span class="k">Ctrl+Shift+S</span> salvar como ·
<span class="k">Ctrl+Z</span>/<span class="k">Ctrl+Y</span> desfazer/refazer · <span class="k">Ctrl+F</span> filtrar ·
<span class="k">Ctrl+H</span> substituir · <span class="k">Ctrl+C</span>/<span class="k">Ctrl+V</span> copiar/colar (compatível com Excel) ·
<span class="k">Delete</span> limpar seleção · <span class="k">F2</span> editar célula</p>
"""


class HelpDialog(BaseDialog):
    def __init__(self, parent):
        super().__init__(parent, "Como usar o GridNote")
        self.resize(680, 640)
        self.lay.addWidget(_title("Como usar o GridNote"))
        view = QTextBrowser()
        view.setOpenExternalLinks(False)
        view.setStyleSheet(f"background: {theme.C['bg1']}; border: 1px solid {theme.C['border']}; border-radius: 10px; padding: 8px;")
        view.setHtml(HELP_HTML.format())
        self.lay.addWidget(view, 1)
        ok = _button("Fechar", "primary")
        ok.clicked.connect(self.accept)
        self.add_buttons(ok)
