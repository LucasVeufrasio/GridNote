"""Um arquivo aberto: caminho, formato, abas (uma TableModel por aba) e metadados."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .fileio import Sheet, read_file, write_file
from .model import TableModel


class Document(QObject):
    dirtyChanged = Signal()
    pathChanged = Signal()

    def __init__(self, path: Path, sheets: list[Sheet], meta: dict):
        super().__init__()
        self.path = Path(path)
        self.meta = meta
        self.sheet_names = [s.name for s in sheets]
        fmt = self.path.suffix.lower()
        split = meta.get("txt_mode") if fmt == ".txt" else (meta.get("delimiter") if fmt == ".csv" else None)
        self.models = [TableModel(s.rows, s.header, split or "cells", self) for s in sheets]
        for m in self.models:
            m.dirtyChanged.connect(lambda _d: self.dirtyChanged.emit())

    @classmethod
    def open(cls, path: str | Path, txt_mode: str = "auto") -> "Document":
        loaded = read_file(path, txt_mode)
        return cls(Path(path), loaded.sheets, loaded.meta)

    @property
    def fmt(self) -> str:
        return self.path.suffix.lower().lstrip(".")

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def dirty(self) -> bool:
        return any(m.dirty for m in self.models)

    def key(self) -> str:
        return path_key(self.path)

    def sheets(self, only: int | None = None) -> list[Sheet]:
        idx = range(len(self.models)) if only is None else [only]
        return [Sheet(self.sheet_names[i], self.models[i].rows, self.models[i].header) for i in idx]

    def sync_meta(self, sheet: int) -> None:
        """Faz o CSV/TXT ser gravado do jeito que está dividido na tela."""
        split = self.models[sheet].split
        if split in ("char", "line"):
            self.meta["txt_mode"] = split
        elif split != "cells":
            self.meta["txt_mode"] = split
            self.meta["delimiter"] = split
        else:
            self.meta.pop("txt_mode", None)

    def save(self, current_sheet: int = 0) -> None:
        self.sync_meta(current_sheet)
        single = self.fmt in ("csv", "txt")
        write_file(self.path, self.fmt, self.sheets(current_sheet if single else None), self.meta)
        for m in self.models:
            m.mark_saved()

    def save_as(self, path: Path, fmt: str, options: dict, current_sheet: int) -> bool:
        """Grava em outro arquivo. Devolve True se o documento passou a ser esse arquivo.

        Word/PDF são exportações (não dá para reabrir para editar), e CSV/TXT de um arquivo
        com várias abas também: nesses casos o documento continua apontando para o original.
        """
        single = fmt in ("csv", "txt")
        becomes = fmt in ("xlsx", "xls") or (single and len(self.models) == 1)
        meta = dict(self.meta)
        meta.update(options)
        meta["title"] = Path(path).stem
        sheets = self.sheets(current_sheet if single else None)
        write_file(path, fmt, sheets, meta)
        if becomes:
            self.path = Path(path)
            self.meta = {k: v for k, v in meta.items() if k != "title"}
            for m in self.models:
                m.mark_saved()
            self.pathChanged.emit()
        return becomes

    def discard(self) -> None:
        for m in self.models:
            m.discard()


def path_key(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(path))
