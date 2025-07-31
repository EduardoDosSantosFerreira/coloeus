import sys
from ui import FileScannerWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("coloeus.ico"))  # Adicione um ícone se desejar
    
    window = FileScannerWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()