import sys

from PySide6.QtWidgets import QApplication

from converter_window import ConverterWindow


def main() -> None:
    app = QApplication(sys.argv)

    window = ConverterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()