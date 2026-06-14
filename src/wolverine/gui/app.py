"""Application entry point for the Wolverine V3 Pro GUI."""


def main():
    import sys
    from PyQt6.QtWidgets import QApplication
    from .style import STYLE
    from .main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    app.setApplicationName("Wolverine V3 Pro")

    win = MainWindow()
    win.setWindowTitle("Wolverine V3 Pro")
    win.setMinimumSize(800, 580)
    win.resize(1000, 640)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
