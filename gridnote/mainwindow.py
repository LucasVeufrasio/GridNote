"""Janela principal: barra lateral, página central e barra obrigatória de Salvar/Cancelar."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter,
    QStackedWidget, QVBoxLayout, QWidget,
)

from . import config, dialogs, theme
from .dialogs import UnsavedDialog
from .document import Document, path_key
from .editor import DocumentEditor
from .fileio import OPEN_EXTS, SAVE_FORMATS, FileFormatError
from .sidebar import NavPanel

OPEN_FILTER = "Planilhas e textos (*.csv *.txt *.xlsx *.xls);;Todos os arquivos (*.*)"


class Welcome(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.setObjectName("Welcome")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 40)
        outer.addStretch(1)
        box = QVBoxLayout()
        box.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(theme.app_icon_pixmap(72))
        box.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("Bem-vindo ao GridNote")
        title.setObjectName("WelcomeTitle")
        box.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)
        sub = QLabel("Abra CSV, TXT e Excel, edite por colunas ou linhas e salve em Excel, CSV, TXT, Word ou PDF.")
        sub.setObjectName("WelcomeSub")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(sub)
        box.addSpacing(18)

        steps = QGridLayout()
        steps.setSpacing(14)
        items = [
            ("1", "Vincule uma pasta", "Os arquivos dela aparecem na barra lateral, como no OneNote."),
            ("2", "Escolha Colunas ou Linhas", "Clique no topo de uma coluna para selecioná-la inteira e use Substituir."),
            ("3", "Salve ou cancele", "A bolinha branca ● mostra o que falta salvar. Nada se perde sem você decidir."),
        ]
        for i, (num, head, text) in enumerate(items):
            card = QFrame()
            card.setObjectName("StepCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 16, 18, 18)
            n = QLabel(num)
            n.setObjectName("StepNum")
            n.setFixedSize(32, 32)
            n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(n)
            h = QLabel(head)
            h.setObjectName("StepTitle")
            cl.addWidget(h)
            t = QLabel(text)
            t.setObjectName("StepText")
            t.setWordWrap(True)
            cl.addWidget(t)
            cl.addStretch(1)
            card.setMinimumWidth(200)
            steps.addWidget(card, 0, i)
        box.addLayout(steps)
        box.addSpacing(18)

        btns = QHBoxLayout()
        btns.addStretch(1)
        link = QPushButton("Vincular uma pasta")
        link.setProperty("kind", "primary")
        link.setIcon(theme.glyph_icon("link", "#06152C"))
        link.clicked.connect(win.link_folder)
        open_ = QPushButton("Abrir arquivo")
        open_.setIcon(theme.glyph_icon("open_file"))
        open_.clicked.connect(win.open_dialog)
        help_ = QPushButton("Como usar")
        help_.setProperty("kind", "ghost")
        help_.setIcon(theme.glyph_icon("help"))
        help_.clicked.connect(win.show_help)
        for b in (link, open_, help_):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btns.addWidget(b)
        btns.addStretch(1)
        box.addLayout(btns)
        hint = QLabel("Dica: você também pode arrastar arquivos para esta janela.")
        hint.setObjectName("EmptyHint")
        box.addWidget(hint, 0, Qt.AlignmentFlag.AlignHCenter)

        wrap = QHBoxLayout()
        wrap.addStretch(1)
        inner = QWidget()
        inner.setLayout(box)
        inner.setMaximumWidth(860)
        wrap.addWidget(inner, 4)
        wrap.addStretch(1)
        outer.addLayout(wrap)
        outer.addStretch(2)


class SaveBar(QFrame):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.setObjectName("SaveBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 9, 16, 9)
        lay.setSpacing(10)
        self.icon = QLabel()
        lay.addWidget(self.icon)
        self.text = QLabel()
        self.text.setObjectName("SaveText")
        lay.addWidget(self.text, 1)
        self.btn_cancel = QPushButton("Cancelar alterações")
        self.btn_cancel.setProperty("kind", "danger")
        self.btn_cancel.setIcon(theme.glyph_icon("cancel", theme.C["danger"]))
        self.btn_cancel.setToolTip("Volta o arquivo para como ele estava na última vez que foi salvo")
        self.btn_save_as = QPushButton("Salvar como…")
        self.btn_save_as.setIcon(theme.glyph_icon("save_as"))
        self.btn_save_as.setToolTip("Excel, CSV, TXT, Word ou PDF (Ctrl+Shift+S)")
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("kind", "primary")
        self.btn_save.setIcon(theme.glyph_icon("save", "#06152C"))
        self.btn_save.setToolTip("Grava no próprio arquivo (Ctrl+S)")
        self.btn_save.setMinimumWidth(110)
        for b in (self.btn_cancel, self.btn_save_as, self.btn_save):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b)
        self.btn_cancel.clicked.connect(win.discard_current)
        self.btn_save_as.clicked.connect(win.save_as_current)
        self.btn_save.clicked.connect(win.save_current)

    def show_state(self, doc: Document | None) -> None:
        self.setVisible(doc is not None)
        if doc is None:
            return
        dirty = doc.dirty
        self.setProperty("dirty", "true" if dirty else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        for child in self.findChildren(QLabel):
            child.style().unpolish(child)
            child.style().polish(child)
        if dirty:
            self.icon.setPixmap(theme.dot_pixmap("#FFFFFF", 14))
            self.text.setText(f"Alterações não salvas em \"{doc.name}\" — salve ou cancele antes de fechar.")
        else:
            self.icon.setPixmap(theme.glyph_icon("check", theme.C["ok"]).pixmap(18, 18))
            self.text.setText(f"Tudo salvo em \"{doc.name}\".")
        self.btn_cancel.setEnabled(dirty)
        self.btn_save.setEnabled(dirty)


class MainWindow(QMainWindow):
    def __init__(self, files: list[str] | None = None):
        super().__init__()
        self.cfg = config.load()
        self.docs: dict[str, tuple[Document, DocumentEditor]] = {}
        self.order: list[str] = []
        self.active: str | None = None

        self.setWindowIcon(theme.app_icon())
        self.setAcceptDrops(True)
        self.resize(1360, 820)
        self.setMinimumSize(900, 560)

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.nav = NavPanel()
        self.nav.openPath.connect(self.open_path)
        self.nav.linkFolder.connect(self.link_folder)
        self.nav.openFileDialog.connect(self.open_dialog)
        self.nav.activateDoc.connect(self.activate)
        self.nav.closeDoc.connect(self.close_doc)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.stack = QStackedWidget()
        self.welcome = Welcome(self)
        self.stack.addWidget(self.welcome)
        rl.addWidget(self.stack, 1)
        self.savebar = SaveBar(self)
        rl.addWidget(self.savebar)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(self.nav)
        self.split.addWidget(right)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([300, 1060])
        lay.addWidget(self.split)
        self.right = right

        self._build_menu()
        self.nav.set_folder(self.cfg.get("folder"))
        if self.cfg.get("panel_bottom"):
            self.act_bottom.setChecked(True)
        geo = self.cfg.get("geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
        self.refresh()
        for f in files or []:
            self.open_path(f)

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        mb = self.menuBar()

        def act(menu, text, fn, shortcut=None, icon=None):
            a = QAction(text, self)
            if icon:
                a.setIcon(theme.glyph_icon(icon))
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        m = mb.addMenu("&Arquivo")
        act(m, "Abrir arquivo…", self.open_dialog, QKeySequence.StandardKey.Open, "open_file")
        act(m, "Vincular pasta…", self.link_folder, "Ctrl+Shift+O", "link")
        m.addSeparator()
        self.act_save = act(m, "Salvar", self.save_current, QKeySequence.StandardKey.Save, "save")
        self.act_save_as = act(m, "Salvar como…", self.save_as_current, "Ctrl+Shift+S", "save_as")
        self.act_discard = act(m, "Cancelar alterações", self.discard_current, None, "cancel")
        m.addSeparator()
        self.act_close = act(m, "Fechar arquivo", lambda: self.active and self.close_doc(self.active), "Ctrl+W", "close")
        act(m, "Sair", self.close, "Alt+F4")

        e = mb.addMenu("&Editar")
        self.act_undo = act(e, "Desfazer", lambda: self._editor() and self._editor().model.undo(), QKeySequence.StandardKey.Undo, "undo")
        self.act_redo = act(e, "Refazer", lambda: self._editor() and self._editor().model.redo(), "Ctrl+Y", "redo")
        e.addSeparator()
        self.act_filter = act(e, "Filtrar…", lambda: self._editor() and self._editor().focus_filter(), QKeySequence.StandardKey.Find, "filter")
        self.act_replace = act(e, "Substituir…", lambda: self._editor() and self._editor().open_replace(), "Ctrl+H", "replace")
        e.addSeparator()
        act(e, "Modo Colunas", lambda: self._editor() and self._editor().set_mode("cols"), "Ctrl+1")
        act(e, "Modo Linhas", lambda: self._editor() and self._editor().set_mode("rows"), "Ctrl+2")

        v = mb.addMenu("E&xibir")
        self.act_bottom = QAction("Pasta embaixo da tela", self, checkable=True)
        self.act_bottom.setIcon(theme.glyph_icon("dock_bottom"))
        self.act_bottom.toggled.connect(self.set_panel_bottom)
        v.addAction(self.act_bottom)
        self.act_tips = QAction("Mostrar dicas", self, checkable=True)
        self.act_tips.setIcon(theme.glyph_icon("lightbulb"))
        self.act_tips.setChecked(self.cfg.get("show_tips", True))
        self.act_tips.toggled.connect(self.on_tips_toggled)
        v.addAction(self.act_tips)

        h = mb.addMenu("Aj&uda")
        act(h, "Como usar", self.show_help, "F1", "help")
        act(h, "Sobre o GridNote", lambda: dialogs.message(
            self, "GridNote", f"Versão {config.APP_VERSION}\nEditor de CSV, TXT e Excel com salvamento em "
            "Excel, CSV, TXT, Word e PDF.\nTudo roda neste computador; nenhum dado é enviado para a internet."))

    # -------------------------------------------------------------- abertura
    def open_dialog(self) -> None:
        start = self.cfg.get("folder") or str(Path.home())
        paths, _ = QFileDialog.getOpenFileNames(self, "Abrir arquivo", start, OPEN_FILTER)
        for p in paths:
            self.open_path(p)

    def link_folder(self) -> None:
        start = self.cfg.get("folder") or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Escolha a pasta para vincular", start)
        if folder:
            self.cfg["folder"] = folder
            config.save(self.cfg)
            self.nav.set_folder(folder)

    def open_path(self, path: str) -> None:
        p = Path(path)
        key = path_key(p)
        if key in self.docs:
            self.activate(key)
            return
        if p.suffix.lower() not in OPEN_EXTS:
            dialogs.message(self, "Formato não suportado", f"O GridNote abre {', '.join(OPEN_EXTS)}.\n\n{p.name}", "warn")
            return
        txt_mode = "auto"
        if p.suffix.lower() == ".txt":
            d = dialogs.TxtImportDialog(self, p)
            if not d.exec():
                return
            txt_mode = d.mode()
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc = Document.open(p, txt_mode)
        except FileFormatError as e:
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível abrir", str(e), "error")
            return
        except Exception as e:  # noqa: BLE001 - nunca derrubar o app por um arquivo ruim
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível abrir", f"{p.name}\n\n{type(e).__name__}: {e}", "error")
            return
        try:
            editor = DocumentEditor(doc, show_tips=self.act_tips.isChecked())
        finally:
            QGuiApplication.restoreOverrideCursor()
        doc.dirtyChanged.connect(self.refresh)
        doc.pathChanged.connect(lambda d=doc: self._rekey(d))
        editor.historyChanged.connect(self._update_actions)
        self.docs[key] = (doc, editor)
        self.order.append(key)
        self.stack.addWidget(editor)
        self.activate(key)

    def _rekey(self, doc: Document) -> None:
        old = next(k for k, (d, _e) in self.docs.items() if d is doc)
        new = doc.key()
        if new == old:
            self.refresh()
            return
        if new in self.docs:  # salvou por cima de outro arquivo aberto: fecha a cópia antiga
            other, other_editor = self.docs.pop(new)
            self.order.remove(new)
            self.stack.removeWidget(other_editor)
            other_editor.deleteLater()
        self.docs[new] = self.docs.pop(old)
        self.order[self.order.index(old)] = new
        if self.active == old:
            self.active = new
        self.refresh()

    def activate(self, key: str) -> None:
        if key not in self.docs:
            return
        self.active = key
        self.stack.setCurrentWidget(self.docs[key][1])
        self.refresh()

    def _doc(self) -> Document | None:
        return self.docs[self.active][0] if self.active in self.docs else None

    def _editor(self) -> DocumentEditor | None:
        return self.docs[self.active][1] if self.active in self.docs else None

    # ---------------------------------------------------------------- estado
    def refresh(self) -> None:
        doc = self._doc()
        if doc is None:
            self.stack.setCurrentWidget(self.welcome)
        self.nav.set_open_docs(
            [(k, self.docs[k][0].name, self.docs[k][0].fmt, self.docs[k][0].dirty) for k in self.order], self.active
        )
        self.savebar.show_state(doc)
        dirty_any = any(d.dirty for d, _e in self.docs.values())
        title = "GridNote"
        if doc:
            title = f"{'● ' if doc.dirty else ''}{doc.name} — GridNote"
        self.setWindowTitle(title)
        self.setWindowModified(dirty_any)
        self._update_actions()

    def _update_actions(self) -> None:
        doc, ed = self._doc(), self._editor()
        has = doc is not None
        self.act_save.setEnabled(has and doc.dirty)
        self.act_discard.setEnabled(has and doc.dirty)
        for a in (self.act_save_as, self.act_close, self.act_filter, self.act_replace):
            a.setEnabled(has)
        self.act_undo.setEnabled(bool(ed and ed.model.can_undo()))
        self.act_redo.setEnabled(bool(ed and ed.model.can_redo()))

    def on_tips_toggled(self, on: bool) -> None:
        if self.act_tips.isChecked() != on:
            self.act_tips.setChecked(on)
            return
        self.cfg["show_tips"] = on
        config.save(self.cfg)
        for _d, ed in self.docs.values():
            ed._show_tips = on
            ed.tip.setVisible(on)

    def set_panel_bottom(self, bottom: bool) -> None:
        self.split.setOrientation(Qt.Orientation.Vertical if bottom else Qt.Orientation.Horizontal)
        self.split.insertWidget(1 if bottom else 0, self.nav)
        self.nav.set_orientation(bottom)
        total = self.split.height() if bottom else self.split.width()
        panel = 260 if bottom else 300
        sizes = [total - panel, panel] if bottom else [panel, total - panel]
        self.split.setSizes(sizes)
        self.cfg["panel_bottom"] = bottom
        config.save(self.cfg)

    def show_help(self) -> None:
        dialogs.HelpDialog(self).exec()

    # ---------------------------------------------------------------- salvar
    def _save_doc(self, key: str) -> bool:
        doc, editor = self.docs[key]
        if doc.fmt in ("xlsx", "xls") and not self.cfg.get("excel_values_ok"):
            ok = dialogs.confirm(
                self, "Salvar planilha do Excel",
                "O GridNote grava os valores das células. Cores, fórmulas, mesclagens e gráficos "
                "da planilha original não são mantidos.\n\nSe precisar deles, use \"Salvar como…\" "
                "para gravar uma cópia com outro nome.",
                "Entendi, salvar", "Voltar",
            )
            if not ok:
                return False
            self.cfg["excel_values_ok"] = True
            config.save(self.cfg)
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc.save(editor.sheet)
        except FileFormatError as e:
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível salvar", str(e), "error")
            return False
        except Exception as e:  # noqa: BLE001
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível salvar", f"{type(e).__name__}: {e}", "error")
            return False
        QGuiApplication.restoreOverrideCursor()
        editor.update_title()
        self.refresh()
        return True

    def save_current(self) -> None:
        if self.active and self._doc().dirty:
            self._save_doc(self.active)

    def save_as_current(self) -> None:
        doc, editor = self._doc(), self._editor()
        if doc is None:
            return
        doc.sync_meta(editor.sheet)
        d = dialogs.SaveAsDialog(self, doc, len(doc.models))
        if not d.exec():
            return
        fmt, options = d.fmt(), d.values()
        label, ext, _desc, _editable = SAVE_FORMATS[fmt]
        folder = self.cfg.get("folder") or str(doc.path.parent)
        suggestion = str(Path(folder) / (doc.path.stem + ext))
        path, _ = QFileDialog.getSaveFileName(self, f"Salvar como {label}", suggestion, f"{label} (*{ext})")
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext
        target = path_key(path)
        if target in self.docs and self.docs[target][0] is not doc and self.docs[target][0].dirty:
            dialogs.message(self, "Arquivo aberto com alterações",
                            "Esse arquivo está aberto no GridNote com alterações não salvas. "
                            "Salve ou cancele as alterações dele primeiro.", "warn")
            return
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            became = doc.save_as(Path(path), fmt, options, editor.sheet)
        except FileFormatError as e:
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível salvar", str(e), "error")
            return
        except Exception as e:  # noqa: BLE001
            QGuiApplication.restoreOverrideCursor()
            dialogs.message(self, "Não foi possível salvar", f"{type(e).__name__}: {e}", "error")
            return
        QGuiApplication.restoreOverrideCursor()
        editor.update_title()
        self.refresh()
        if not became:
            extra = (" As alterações do arquivo aberto continuam pendentes: salve-o ou cancele antes de fechar."
                     if doc.dirty else "")
            dialogs.message(self, "Arquivo gerado", f"{Path(path).name} foi salvo.{extra}")

    def discard_current(self) -> None:
        doc, editor = self._doc(), self._editor()
        if not doc or not doc.dirty:
            return
        if dialogs.confirm(self, "Cancelar alterações",
                           f"Todas as alterações feitas em \"{doc.name}\" desde o último salvamento serão perdidas.",
                           "Cancelar alterações", "Voltar", danger=True):
            doc.discard()
            editor.update_title()
            self.refresh()

    # ---------------------------------------------------------------- fechar
    def close_doc(self, key: str) -> bool:
        if key not in self.docs:
            return True
        doc, editor = self.docs[key]
        if doc.dirty:
            self.activate(key)
            choice = UnsavedDialog.ask(self, [doc.name])
            if choice == UnsavedDialog.BACK:
                return False
            if choice == UnsavedDialog.SAVE and not self._save_doc(key):
                return False
            if choice == UnsavedDialog.DISCARD:
                doc.discard()
        pos = self.order.index(key)
        self.order.remove(key)
        del self.docs[key]
        self.stack.removeWidget(editor)
        editor.deleteLater()
        if self.active == key:
            self.active = self.order[min(pos, len(self.order) - 1)] if self.order else None
            if self.active:
                self.stack.setCurrentWidget(self.docs[self.active][1])
        self.refresh()
        return True

    def closeEvent(self, event) -> None:
        dirty = [k for k in self.order if self.docs[k][0].dirty]
        if dirty:
            choice = UnsavedDialog.ask(self, [self.docs[k][0].name for k in dirty], closing_app=True)
            if choice == UnsavedDialog.BACK:
                event.ignore()
                return
            if choice == UnsavedDialog.SAVE:
                for k in dirty:
                    if not self._save_doc(k):
                        self.activate(k)
                        event.ignore()
                        return
        self.cfg["geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        config.save(self.cfg)
        event.accept()

    # ---------------------------------------------------------- arrastar
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(url.toLocalFile())
