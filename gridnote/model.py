"""Modelo da grade: dados, filtro por coluna/linha, desfazer/refazer e estado "não salvo".

Os dados ficam em `rows` (lista de linhas de str). A grade enxerga só as linhas em
`_vr` e as colunas em `_vc` — é assim que o filtro funciona sem copiar dados.
Índices "abs" são posições reais em `rows`; índices da grade são posições visíveis.
"""
from __future__ import annotations

import re
from bisect import bisect_left

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont

from . import theme
from .fileio import join_row, looks_like_header, rectangular, split_text

UNDO_LIMIT = 200

MATCHES = {
    "contains": "Contém",
    "equals": "É igual a",
    "starts": "Começa com",
    "ends": "Termina com",
    "lines": "Nº da linha",
}


def parse_line_numbers(text: str) -> set[int]:
    """'3, 6, 9-12' -> {3, 6, 9, 10, 11, 12}. Ignora o que não for número."""
    out: set[int] = set()
    for part in re.split(r"[,;\s]+", text.strip()):
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            continue
        a = int(m.group(1))
        b = int(m.group(2) or a)
        if b - a <= 1_000_000:
            out.update(range(min(a, b), max(a, b) + 1))
    return out


def _copy(rows):
    return [r[:] for r in rows]


class TableModel(QAbstractTableModel):
    dirtyChanged = Signal(bool)
    historyChanged = Signal()
    filterApplied = Signal()

    def __init__(self, rows: list[list[str]], header: bool = False, split: str = "cells", parent=None):
        super().__init__(parent)
        self.rows = rows
        self.header = header
        # como as linhas estão divididas: "cells" (planilha), um separador, "char" ou "line"
        self.split = split
        self._orig_split = split
        self._orig_header = header
        self._orig = _copy(rows)
        self._undo: list[list] = []
        self._idx = 0
        self._clean = 0
        self._struct_dirty = False
        # filtro
        self.mode = "cols"          # "cols" ou "rows"
        self.f_text = ""
        self.f_col = -1              # -1 = todas as colunas
        self.f_match = "contains"
        self.f_case = False
        self._vr: range | list[int] = range(0)
        self._vc: range | list[int] = range(0)
        self._compute_view()

    # ------------------------------------------------------------------ básico
    @property
    def ncols(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def offset(self) -> int:
        return 1 if self.header and self.rows else 0

    @property
    def data_row_count(self) -> int:
        return max(0, len(self.rows) - self.offset)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._vr)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._vc)

    def abs_row(self, r: int) -> int:
        return self._vr[r]

    def abs_col(self, c: int) -> int:
        return self._vc[c]

    def visible_rows(self):
        return self._vr

    def visible_cols(self):
        return self._vc

    def column_label(self, ac: int) -> str:
        if self.header and self.rows and self.rows[0][ac].strip():
            return self.rows[0][ac]
        return f"Coluna {ac + 1}"

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        ar, ac = self._vr[index.row()], self._vc[index.column()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.rows[ar][ac]
        if role == Qt.ItemDataRole.BackgroundRole and self._is_modified(ar, ac):
            return QColor(theme.C["modified"])
        if role == Qt.ItemDataRole.ToolTipRole and self._is_modified(ar, ac):
            return f"Alterado (antes: \"{self._orig[ar][ac]}\")"
        return None

    def _is_modified(self, ar, ac) -> bool:
        if self._struct_dirty or self._idx == self._clean:
            return False
        try:
            return self.rows[ar][ac] != self._orig[ar][ac]
        except IndexError:
            return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if section >= len(self._vc):
                return None
            ac = self._vc[section]
            if role == Qt.ItemDataRole.DisplayRole:
                return self.rows[0][ac] if self.header and self.rows and self.rows[0][ac].strip() else str(ac + 1)
            if role == Qt.ItemDataRole.ToolTipRole:
                return f"Coluna {ac + 1} — clique para selecionar a coluna inteira"
        else:
            if section >= len(self._vr):
                return None
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._vr[section] + 1)
            if role == Qt.ItemDataRole.ToolTipRole:
                return f"Linha {self._vr[section] + 1} do arquivo — clique para selecionar a linha inteira"
        if role == Qt.ItemDataRole.FontRole:
            f = QFont()
            f.setBold(True)
            return f
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        ar, ac = self._vr[index.row()], self._vc[index.column()]
        return self.set_cells({(ar, ac): str(value)}) > 0

    # --------------------------------------------------------------- histórico
    @property
    def dirty(self) -> bool:
        return self._idx != self._clean

    def can_undo(self) -> bool:
        return self._idx > 0

    def can_redo(self) -> bool:
        return self._idx < len(self._undo)

    def _push(self, entry) -> None:
        was = self.dirty
        del self._undo[self._idx:]
        if self._clean > self._idx:
            self._clean = -1  # o estado salvo ficou num ramo descartado
        self._undo.append(entry)
        self._idx += 1
        if len(self._undo) > UNDO_LIMIT:
            self._undo.pop(0)
            self._idx -= 1
            self._clean = self._clean - 1 if self._clean > 0 else -1
        self._after_history(was)

    def _after_history(self, was_dirty: bool) -> None:
        if self._clean < 0:
            self._struct_dirty = True
        else:
            lo, hi = sorted((self._clean, self._idx))
            self._struct_dirty = any(e[0] == "snap" for e in self._undo[lo:hi])
        self.historyChanged.emit()
        if was_dirty != self.dirty:
            self.dirtyChanged.emit(self.dirty)

    def undo(self) -> None:
        if not self.can_undo():
            return
        was = self.dirty
        self._idx -= 1
        self._apply(self._undo[self._idx], redo=False)
        self._after_history(was)
        self._refresh_all()

    def redo(self) -> None:
        if not self.can_redo():
            return
        was = self.dirty
        self._apply(self._undo[self._idx], redo=True)
        self._idx += 1
        self._after_history(was)
        self._refresh_all()

    def _apply(self, entry, redo: bool) -> None:
        if entry[0] == "cells":
            for ar, ac, old, new in entry[1]:
                self.rows[ar][ac] = new if redo else old
        else:  # "snap": troca o estado atual pelo guardado
            current = (_copy(self.rows), self.split, self.header)
            self.beginResetModel()
            self.rows, self.split, self.header = entry[1], entry[2], entry[3]
            entry[1:4] = current
            self._compute_view()
            self.endResetModel()
            self.filterApplied.emit()

    def mark_saved(self) -> None:
        was = self.dirty
        self._orig = _copy(self.rows)
        self._orig_split, self._orig_header = self.split, self.header
        self._clean = self._idx
        self._after_history(was)
        self._refresh_all()

    def discard(self) -> None:
        was = self.dirty
        self.beginResetModel()
        self.rows = _copy(self._orig)
        self.split, self.header = self._orig_split, self._orig_header
        self._undo.clear()
        self._idx = self._clean = 0
        self._compute_view()
        self.endResetModel()
        self._after_history(was)
        self.filterApplied.emit()

    def _refresh_all(self) -> None:
        if self.rowCount() and self.columnCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))
        if self.header and self.columnCount():
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount() - 1)

    # ----------------------------------------------------------------- edições
    def set_cells(self, changes: dict[tuple[int, int], str]) -> int:
        diff = [(ar, ac, self.rows[ar][ac], new) for (ar, ac), new in changes.items() if self.rows[ar][ac] != new]
        if not diff:
            return 0
        for ar, ac, _, new in diff:
            self.rows[ar][ac] = new
        self._push(["cells", diff])
        self._refresh_all()
        return len(diff)

    def _structural(self, fn) -> None:
        self._push(["snap", _copy(self.rows), self.split, self.header])
        self.beginResetModel()
        fn()
        self.endResetModel()
        self.filterApplied.emit()

    def insert_rows(self, at: int, count: int = 1) -> None:
        at = max(self.offset, min(at, len(self.rows)))

        def do():
            for _ in range(count):
                self.rows.insert(at, [""] * max(1, self.ncols))
            vr = [i + count if i >= at else i for i in self._vr]
            pos = bisect_left(vr, at)
            vr[pos:pos] = range(at, at + count)
            self._vr = vr
        self._structural(do)

    def insert_cols(self, at: int, count: int = 1) -> None:
        at = max(0, min(at, self.ncols))

        def do():
            for r in self.rows:
                r[at:at] = [""] * count
            vc = [i + count if i >= at else i for i in self._vc]
            pos = bisect_left(vc, at)
            vc[pos:pos] = range(at, at + count)
            self._vc = vc
        self._structural(do)

    def remove_rows(self, abs_rows) -> None:
        gone = sorted(set(abs_rows))
        if not gone:
            return

        def do():
            for i in reversed(gone):
                del self.rows[i]
            if not self.rows or len(self.rows) <= self.offset:
                self.rows.append([""] * max(1, self.ncols or 1))
            gone_set = set(gone)
            self._vr = [i - bisect_left(gone, i) for i in self._vr if i not in gone_set]
            if not self._vr and self.data_row_count:
                self._compute_view()
        self._structural(do)

    def remove_cols(self, abs_cols) -> None:
        gone = sorted(set(abs_cols))
        if not gone or len(gone) >= self.ncols:
            return

        def do():
            for r in self.rows:
                for i in reversed(gone):
                    del r[i]
            gone_set = set(gone)
            self._vc = [i - bisect_left(gone, i) for i in self._vc if i not in gone_set]
            if not self._vc:
                self._compute_view()
        self._structural(do)

    def delete_cells_shift_left(self, cells) -> int:
        """Apaga as células e puxa o resto da linha para a esquerda (sem deixar espaço)."""
        by_row: dict[int, set[int]] = {}
        for ar, ac in cells:
            by_row.setdefault(ar, set()).add(ac)
        if not by_row:
            return 0
        width = self.ncols

        def do():
            for ar, cols in by_row.items():
                row = self.rows[ar]
                for ac in sorted(cols, reverse=True):
                    del row[ac]
                row.extend([""] * (width - len(row)))
        self._structural(do)
        return sum(len(c) for c in by_row.values())

    def insert_cells_shift_right(self, cells) -> int:
        """Insere uma célula vazia antes de cada célula e empurra o resto da linha para a direita."""
        by_row: dict[int, set[int]] = {}
        for ar, ac in cells:
            by_row.setdefault(ar, set()).add(ac)
        if not by_row:
            return 0
        old = self.ncols

        def do():
            for ar, cols in by_row.items():
                row = self.rows[ar]
                for ac in sorted(cols, reverse=True):
                    row.insert(ac, "")
            new = max(len(r) for r in self.rows)
            for r in self.rows:
                r.extend([""] * (new - len(r)))
            if new > old:
                self._vc = list(self._vc) + list(range(old, new))
        self._structural(do)
        return sum(len(c) for c in by_row.values())

    def sort_by(self, ac: int, descending: bool = False) -> None:
        def key(row):
            v = row[ac].strip()
            try:
                return (0, float(v.replace(".", "").replace(",", ".")) if "," in v else float(v), "")
            except ValueError:
                return (1, 0.0, v.casefold())

        def do():
            body = self.rows[self.offset:]
            body.sort(key=key, reverse=descending)
            self.rows[self.offset:] = body
            self._compute_view()
        self._structural(do)

    def resplit(self, mode: str) -> None:
        """Junta cada linha de volta em texto e divide de novo (ex.: cada caractere uma coluna)."""
        if mode == self.split:
            return
        lines = [join_row(r, self.split) for r in self.rows]
        new_rows = rectangular(split_text(lines, mode))

        def do():
            self.rows = new_rows
            self.split = mode
            self.header = mode not in ("char", "line") and looks_like_header(new_rows)
            self.f_text, self.f_col = "", -1
            self._compute_view()
        self._structural(do)

    def set_header(self, on: bool) -> None:
        if on == self.header:
            return
        self.beginResetModel()
        self.header = on
        self._compute_view()
        self.endResetModel()
        self.filterApplied.emit()

    # ------------------------------------------------------------------ filtro
    def set_filter(self, text: str, col: int, match: str, case: bool, mode: str) -> None:
        self.f_text, self.f_col, self.f_match, self.f_case, self.mode = text, col, match, case, mode
        if self.f_col >= self.ncols:
            self.f_col = -1
        self.beginResetModel()
        self._compute_view()
        self.endResetModel()
        self.filterApplied.emit()

    def filter_active(self) -> bool:
        return bool(self.f_text)

    def _matcher(self):
        needle = self.f_text if self.f_case else self.f_text.casefold()
        m = self.f_match
        norm = (lambda s: s) if self.f_case else str.casefold
        if m == "equals":
            return lambda s: norm(s) == needle
        if m == "starts":
            return lambda s: norm(s).startswith(needle)
        if m == "ends":
            return lambda s: norm(s).endswith(needle)
        return lambda s: needle in norm(s)

    def _compute_view(self) -> None:
        start, n, w = self.offset, len(self.rows), self.ncols
        self._vr, self._vc = range(start, n), range(w)
        if not self.f_text:
            return
        if self.f_match == "lines":  # números de linha do arquivo (como aparecem à esquerda)
            wanted = parse_line_numbers(self.f_text)
            self._vr = [r for r in range(start, n) if r + 1 in wanted]
            return
        ok = self._matcher()
        if self.f_col >= 0:
            c = self.f_col
            self._vr = [r for r in range(start, n) if ok(self.rows[r][c])]
        elif self.mode == "rows" or self.split == "char":
            if self.split == "char":  # procura no texto da linha inteira (ex.: "55" ocupa duas colunas)
                self._vr = [r for r in range(start, n) if ok(join_row(self.rows[r], "char"))]
            else:
                self._vr = [r for r in range(start, n) if any(ok(v) for v in self.rows[r])]
        else:  # modo colunas, todas: mostra só colunas que têm o texto (no título ou em alguma célula)
            cols = []
            for c in range(w):
                if (self.header and ok(self.rows[0][c])) or any(ok(self.rows[r][c]) for r in range(start, n)):
                    cols.append(c)
            self._vc = cols


def replace_function(find: str, new: str, whole: bool, case: bool, fill: bool):
    """Devolve uma função valor_antigo -> valor_novo para a ferramenta Substituir."""
    if fill:
        return lambda old: new
    if whole:
        if case:
            return lambda old: new if old == find else old
        target = find.casefold()
        return lambda old: new if old.casefold() == target else old
    if case:
        return lambda old: old.replace(find, new)
    rx = re.compile(re.escape(find), re.IGNORECASE)
    return lambda old: rx.sub(lambda _m: new, old)
