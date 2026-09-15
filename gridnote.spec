# PyInstaller: gera dist/GridNote.exe (arquivo único, sem precisar instalar nada)
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["main.py"],
    pathex=[],
    hiddenimports=[],
    excludes=[
        "tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
        "PySide6.QtOpenGL", "PySide6.QtSvg", "PySide6.QtPdf", "PySide6.QtDBus",
    ],
    noarchive=False,
)

# Enxuga: sem traduções do Qt (a interface já é em português), sem OpenGL por software
# e só os plugins que o app usa.
KEEP_PLUGINS = ("platforms", "styles", "imageformats\\qico", "iconengines")


def keep(entry):
    name = entry[0].replace("/", "\\").lower()
    if "translations" in name or "opengl32sw" in name:
        return False
    if "\\plugins\\" in name:
        return any(k in name for k in KEEP_PLUGINS)
    return True


a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GridNote",
    icon="assets/gridnote.ico",
    console=False,
    upx=False,
    version=None,
)
