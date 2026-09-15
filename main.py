"""Ponto de entrada do GridNote."""
import sys

from PySide6.QtWidgets import QApplication

from gridnote import theme
from gridnote.mainwindow import MainWindow


def main() -> int:
    if sys.platform == "win32":
        import ctypes

        # faz a barra de tarefas usar o ícone do app, e não o do Python
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GridNote.Editor")
    app = QApplication(sys.argv)
    app.setApplicationName("GridNote")
    theme.apply(app)
    win = MainWindow(sys.argv[1:])
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
