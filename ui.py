from typing import List
import os
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QMessageBox, QHeaderView,
    QProgressBar, QGroupBox, QLineEdit, QFileDialog, QDoubleSpinBox, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QIcon, QColor, QPalette, QPixmap, QPainter
from script import SystemScanner, FileInfo, ProgramInfo

def white_icon_from_theme(name, fallback=None):
    """
    Retorna um QIcon branco, mesmo se o ícone for monocromático ou temático.
    Usado para ícones que devem sempre aparecer brancos (ex: lupa de busca).
    """
    white = QColor(255, 255, 255)
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        pixmap = icon.pixmap(24, 24)
        if not pixmap.isNull():
            colored = QPixmap(pixmap.size())
            colored.fill(Qt.transparent)
            painter = QPainter(colored)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored.rect(), white)
            painter.end()
            return QIcon(colored)
    if fallback:
        return fallback
    return icon

def deep_blue_icon_from_theme(name, fallback=None):
    """
    Retorna um QIcon azul escuro, mesmo se o ícone for monocromático ou temático.
    Usado para ícones que aparecem em caixas brancas, para garantir que sejam sempre azul escuro.
    """
    azul_escuro = QColor(30, 58, 138)
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        pixmap = icon.pixmap(24, 24)
        if not pixmap.isNull():
            colored = QPixmap(pixmap.size())
            colored.fill(Qt.transparent)
            painter = QPainter(colored)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored.rect(), azul_escuro)
            painter.end()
            return QIcon(colored)
    if fallback:
        return fallback
    return icon

class ScannerThread(QThread):
    scan_complete = Signal(object)
    scan_error = Signal(str)

    def __init__(self, scan_type, *args, **kwargs):
        super().__init__()
        self.scan_type = scan_type
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            if self.scan_type == "programs":
                result = SystemScanner.get_installed_programs()
            elif self.scan_type == "files":
                result = SystemScanner.scan_files(*self.args, **self.kwargs)
            self.scan_complete.emit(result)
        except Exception as e:
            self.scan_error.emit(str(e))

class FileScannerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Coloeus - Gerenciador de Espaço em Disco")
        self.setMinimumSize(QSize(900, 650))
        self.setup_palette()
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f2f5; }
            QGroupBox {
                border: 1px solid #d1d5db; border-radius: 6px; margin-top: 15px; padding-top: 20px; background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #000000; font-weight: bold;
            }
            QTableWidget {
                border: 1px solid #d1d5db; background-color: white; border-radius: 4px; gridline-color: #e5e7eb;
                selection-background-color: #1e3a8a; selection-color: white; color: #000000;
            }
            QTableWidget::item:selected {
                background-color: #2563eb !important; color: #fff !important;
            }
            QHeaderView::section {
                background-color: #1e3a8a; color: white; padding: 5px; border: none; font-weight: bold;
            }
            QPushButton {
                padding: 8px 16px; border-radius: 4px; border: 1px solid #1e3a8a; background-color: #1e3a8a;
                color: white; font-weight: 500; min-width: 80px;
            }
            QPushButton:hover { background-color: #1e40af; border-color: #1e40af; }
            QPushButton:pressed { background-color: #1d4ed8; border-color: #1d4ed8; }
            QPushButton:disabled { background-color: #9ca3af; border-color: #9ca3af; color: #e5e7eb; }
            QPushButton.secondary {
                background-color: white; color: #000000; border: 1px solid #d1d5db;
            }
            QPushButton.secondary:hover { background-color: #f3f4f6; border-color: #9ca3af; }
            QPushButton.secondary:pressed { background-color: #e5e7eb; }
            QPushButton#delete-btn, QPushButton#open-folder-btn {
                color: #2563eb;
                border-color: #2563eb;
            }
            QPushButton#delete-btn:hover, QPushButton#open-folder-btn:hover {
                background-color: #e0e7ff;
                border-color: #1e40af;
            }
            QTabWidget::pane {
                border: 1px solid #d1d5db; border-radius: 4px; background: white; margin-top: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px; background: #f3f4f6; border: 1px solid #d1d5db; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; color: #000000;
            }
            QTabBar::tab:selected {
                background: white; border-color: #d1d5db; border-bottom: 1px solid white; margin-bottom: -1px;
                color: #000000; font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #e5e7eb; }
            QProgressBar {
                border: 1px solid #d1d5db; border-radius: 4px; text-align: center; background: white; color: #000000;
            }
            QProgressBar::chunk { background-color: #1e3a8a; width: 10px; }
            QLineEdit, QDoubleSpinBox {
                border: 1px solid #d1d5db; border-radius: 4px; padding: 5px; background: white; min-height: 25px; color: #000000;
            }
            QLineEdit:focus, QDoubleSpinBox:focus { border: 1px solid #1e3a8a; }
            QLabel { color: #000000; }
            .status-label {
                color: #000000; font-style: italic; padding: 5px; border-top: 1px solid #e5e7eb; background-color: #f9fafb;
            }
            QPushButton#browse-btn { padding: 5px; min-width: 0; }
        """)
        self.init_ui()
        self.show_admin_warning()
        self.show_developer_mode_warning()

    def setup_palette(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(240, 242, 245))
        palette.setColor(QPalette.WindowText, QColor(30, 58, 138))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(243, 244, 246))
        palette.setColor(QPalette.ToolTipBase, QColor(30, 58, 138))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(17, 24, 39))
        palette.setColor(QPalette.Button, QColor(30, 58, 138))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(30, 58, 138))
        palette.setColor(QPalette.Highlight, QColor(30, 58, 138))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(156, 163, 175))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(156, 163, 175))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(156, 163, 175))
        palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(209, 213, 219))
        self.setPalette(palette)

    def show_admin_warning(self):
        if not SystemScanner.is_admin():
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Aviso de Permissão")
            msg.setText("Algumas funcionalidades podem não funcionar sem privilégios de administrador.")
            msg.setInformativeText("Recomendado executar o Coloeus como administrador para acesso completo.")
            msg.setStandardButtons(QMessageBox.Ok)
            # Deixa a fonte branca para o aviso de permissão
            msg.setStyleSheet("""
                QLabel, QMessageBox {
                    color: #fff;
                    background-color: #1e3a8a;
                    font-weight: bold;
                }
                QPushButton {
                    color: #1e3a8a;
                    background-color: #fff;
                    border-radius: 4px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background-color: #e0e7ff;
                }
            """)
            msg.exec()

    def show_developer_mode_warning(self):
        # Aviso para abrir o programa em modo administrador, fonte branca
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Aviso de modo administrador")
        msg.setText("Este programa deve ser aberto em modo administrador para testes e depuração.\n\n"
                    "Algumas funcionalidades podem não funcionar corretamente fora desse modo.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QLabel, QMessageBox {
                color: #fff;
                background-color: #1e3a8a;
                font-weight: bold;
            }
            QPushButton {
                color: #1e3a8a;
                background-color: #fff;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #e0e7ff;
            }
        """)
        msg.exec()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        title_label = QLabel("Coloeus - Gerenciador de Espaço em Disco")
        title_label.setStyleSheet("""
            font-size: 18px; font-weight: bold; color: #1e3a8a;
            padding-bottom: 10px; border-bottom: 2px solid #1e3a8a;
        """)
        main_layout.addWidget(title_label)

        self.tabs = QTabWidget()
        self.programs_tab = QWidget()
        self.init_programs_tab()
        self.tabs.addTab(self.programs_tab, " Programas ")

        self.files_tab = QWidget()
        self.init_files_tab()
        self.tabs.addTab(self.files_tab, " Scanner de Arquivos ")

        main_layout.addWidget(self.tabs)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def init_programs_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.scan_programs_btn = QPushButton("Escanear Programas")
        # Use white icon for search/magnifier
        self.scan_programs_btn.setIcon(white_icon_from_theme("system-search"))
        self.scan_programs_btn.clicked.connect(self.scan_programs)
        btn_layout.addWidget(self.scan_programs_btn)

        self.uninstall_btn = QPushButton("Desinstalar")
        # Use deep blue icon for white background
        self.uninstall_btn.setIcon(deep_blue_icon_from_theme("edit-delete"))
        self.uninstall_btn.clicked.connect(self.uninstall_program)
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.setProperty("class", "secondary")
        btn_layout.addWidget(self.uninstall_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.programs_table = QTableWidget()
        self.programs_table.setColumnCount(5)
        self.programs_table.setHorizontalHeaderLabels(["Nome", "Versão", "Tamanho (MB)", "Publicador", "Localização"])
        self.programs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.programs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.programs_table.setSortingEnabled(True)
        self.programs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.programs_table.verticalHeader().setVisible(False)
        layout.addWidget(self.programs_table)

        self.status_bar = QLabel("Pronto")
        self.status_bar.setProperty("class", "status-label")
        layout.addWidget(self.status_bar)

        self.programs_tab.setLayout(layout)

        # Visual feedback for row selection in programs table
        self.programs_table.itemSelectionChanged.connect(self.on_program_selected)

    def init_files_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        settings_group = QGroupBox("Configurações de Busca")
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(10)

        dirs_layout = QHBoxLayout()
        dirs_layout.setSpacing(10)
        dirs_layout.addWidget(QLabel("Diretórios:"))

        self.dirs_input = QLineEdit()
        self.dirs_input.setPlaceholderText("C:\\\\, D:\\\\")
        self.dirs_input.setText("C:\\")
        dirs_layout.addWidget(self.dirs_input)

        self.browse_btn = QPushButton("...")
        self.browse_btn.setObjectName("browse-btn")
        self.browse_btn.setMaximumWidth(30)
        self.browse_btn.clicked.connect(self.browse_directories)
        self.browse_btn.setProperty("class", "secondary")
        dirs_layout.addWidget(self.browse_btn)

        settings_layout.addLayout(dirs_layout)

        size_layout = QHBoxLayout()
        size_layout.setSpacing(10)
        size_layout.addWidget(QLabel("Tamanho:"))

        self.min_size_input = QDoubleSpinBox()
        self.min_size_input.setRange(0, 99999)
        self.min_size_input.setValue(50)
        self.min_size_input.setSuffix(" MB")
        size_layout.addWidget(self.min_size_input)

        # Botão para diminuir o valor do min_size_input
        self.min_size_minus_btn = QPushButton("-")
        self.min_size_minus_btn.setMaximumWidth(30)
        self.min_size_minus_btn.clicked.connect(lambda: self.adjust_spinbox(self.min_size_input, -1))
        size_layout.addWidget(self.min_size_minus_btn)

        # Botão para aumentar o valor do min_size_input
        self.min_size_plus_btn = QPushButton("+")
        self.min_size_plus_btn.setMaximumWidth(30)
        self.min_size_plus_btn.clicked.connect(lambda: self.adjust_spinbox(self.min_size_input, 1))
        size_layout.addWidget(self.min_size_plus_btn)

        size_layout.addWidget(QLabel("até"))

        self.max_size_input = QDoubleSpinBox()
        self.max_size_input.setRange(0, 99999)
        self.max_size_input.setValue(0)
        self.max_size_input.setSpecialValueText("Ilimitado")
        self.max_size_input.setSuffix(" MB")
        size_layout.addWidget(self.max_size_input)

        # Botão para diminuir o valor do max_size_input
        self.max_size_minus_btn = QPushButton("-")
        self.max_size_minus_btn.setMaximumWidth(30)
        self.max_size_minus_btn.clicked.connect(lambda: self.adjust_spinbox(self.max_size_input, -1))
        size_layout.addWidget(self.max_size_minus_btn)

        # Botão para aumentar o valor do max_size_input
        self.max_size_plus_btn = QPushButton("+")
        self.max_size_plus_btn.setMaximumWidth(30)
        self.max_size_plus_btn.clicked.connect(lambda: self.adjust_spinbox(self.max_size_input, 1))
        size_layout.addWidget(self.max_size_plus_btn)

        settings_layout.addLayout(size_layout)

        ext_layout = QHBoxLayout()
        ext_layout.setSpacing(10)
        ext_layout.addWidget(QLabel("Extensões:"))

        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("Ex: .mp4, .avi (deixe vazio para todas)")
        ext_layout.addWidget(self.ext_input)

        settings_layout.addLayout(ext_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.scan_files_btn = QPushButton("Iniciar Busca")
        # Use white icon for search/magnifier
        self.scan_files_btn.setIcon(white_icon_from_theme("system-search"))
        self.scan_files_btn.clicked.connect(self.scan_files)
        btn_layout.addWidget(self.scan_files_btn)

        self.delete_file_btn = QPushButton("Excluir Selecionados")
        self.delete_file_btn.setIcon(deep_blue_icon_from_theme("edit-delete"))
        self.delete_file_btn.setObjectName("delete-btn")
        self.delete_file_btn.clicked.connect(self.delete_files)
        self.delete_file_btn.setEnabled(False)
        self.delete_file_btn.setProperty("class", "secondary")
        btn_layout.addWidget(self.delete_file_btn)

        self.open_folder_btn = QPushButton("Abrir Localização")
        self.open_folder_btn.setIcon(deep_blue_icon_from_theme("folder-open"))
        self.open_folder_btn.setObjectName("open-folder-btn")
        self.open_folder_btn.clicked.connect(self.open_file_location)
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.setProperty("class", "secondary")
        btn_layout.addWidget(self.open_folder_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["Arquivo", "Tamanho", "Extensão", "Modificado", "Localização"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.MultiSelection)
        self.files_table.setSortingEnabled(True)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        layout.addWidget(self.files_table)

        self.files_status_bar = QLabel("Pronto")
        self.files_status_bar.setProperty("class", "status-label")
        layout.addWidget(self.files_status_bar)

        self.files_progress_bar = QProgressBar()
        self.files_progress_bar.setVisible(False)
        layout.addWidget(self.files_progress_bar)

        self.files_tab.setLayout(layout)

        # Visual feedback for row selection in files table
        self.files_table.itemSelectionChanged.connect(self.on_file_selected)

    def adjust_spinbox(self, spinbox, delta):
        value = spinbox.value() + delta
        if value < spinbox.minimum():
            value = spinbox.minimum()
        if value > spinbox.maximum():
            value = spinbox.maximum()
        spinbox.setValue(value)

    def on_file_selected(self):
        selected_rows = set(index.row() for index in self.files_table.selectedIndexes())
        # Visual feedback: highlight row (already handled by stylesheet), show notification
        if selected_rows:
            self.visual_feedback(f"{len(selected_rows)} arquivo(s) selecionado(s)", success=True)
        else:
            self.visual_feedback("Nenhum arquivo selecionado.", success=False)

    def on_program_selected(self):
        selected_rows = set(index.row() for index in self.programs_table.selectedIndexes())
        if selected_rows:
            self.visual_feedback(f"{len(selected_rows)} programa(s) selecionado(s)", success=True)
        else:
            self.visual_feedback("Nenhum programa selecionado.", success=False)

    def browse_directories(self):
        dirs = QFileDialog.getExistingDirectory(
            self, "Selecionar Diretório", "C:\\",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if dirs:
            self.dirs_input.setText(dirs)
            self.visual_feedback("Diretório selecionado!", success=True)

    def scan_programs(self):
        self.programs_table.setRowCount(0)
        self.status_bar.setText("Escaneando programas instalados...")
        self.status_bar.setStyleSheet("color: #1e3a8a;")
        self.scanner_thread = ScannerThread("programs")
        self.scanner_thread.scan_complete.connect(self.display_programs)
        self.scanner_thread.scan_error.connect(self.show_error)
        self.scanner_thread.start()

    def display_programs(self, programs: List[ProgramInfo]):
        self.programs_table.setRowCount(len(programs))
        for row, program in enumerate(programs):
            self.programs_table.setItem(row, 0, QTableWidgetItem(program.name))
            self.programs_table.setItem(row, 1, QTableWidgetItem(program.version))
            self.programs_table.setItem(row, 2, QTableWidgetItem(str(program.size // 1024)))
            self.programs_table.setItem(row, 3, QTableWidgetItem(program.publisher or "N/A"))
            self.programs_table.setItem(row, 4, QTableWidgetItem(program.install_location or "N/A"))
        self.uninstall_btn.setEnabled(len(programs) > 0)
        self.status_bar.setText(f"Encontrados {len(programs)} programas")
        self.visual_feedback("Programas listados com sucesso!", success=True)

    def scan_files(self):
        self.files_table.setRowCount(0)
        self.files_status_bar.setText("Preparando busca de arquivos...")
        self.files_status_bar.setStyleSheet("color: #1e3a8a;")
        self.files_progress_bar.setVisible(True)
        self.files_progress_bar.setRange(0, 0)
        directories = [d.strip() for d in self.dirs_input.text().split(",") if d.strip()]
        min_size = int(self.min_size_input.value() * 1024 * 1024)
        max_size = int(self.max_size_input.value() * 1024 * 1024) if self.max_size_input.value() > 0 else None
        extensions = None
        if self.ext_input.text().strip():
            extensions = [ext.strip().lower() for ext in self.ext_input.text().split(",")]
            extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
        self.scanner_thread = ScannerThread("files", directories, min_size, max_size, extensions)
        self.scanner_thread.scan_complete.connect(self.display_files)
        self.scanner_thread.scan_error.connect(self.show_error)
        self.scanner_thread.start()

    def display_files(self, files: List[FileInfo]):
        self.files_progress_bar.setVisible(False)
        self.files_table.setRowCount(len(files))
        for row, file in enumerate(files):
            filename = os.path.basename(file.path)
            dirname = os.path.dirname(file.path)
            self.files_table.setItem(row, 0, QTableWidgetItem(filename))
            size_item = QTableWidgetItem()
            size = file.size
            if size >= 1024**3:
                size_item.setData(Qt.DisplayRole, f"{size / (1024**3):.2f} GB")
            elif size >= 1024**2:
                size_item.setData(Qt.DisplayRole, f"{size / (1024**2):.2f} MB")
            elif size >= 1024:
                size_item.setData(Qt.DisplayRole, f"{size / 1024:.2f} KB")
            else:
                size_item.setData(Qt.DisplayRole, f"{size} B")
            self.files_table.setItem(row, 1, size_item)
            self.files_table.setItem(row, 2, QTableWidgetItem(file.extension))
            date_item = QTableWidgetItem()
            date_item.setData(Qt.DisplayRole, time.strftime("%Y-%m-%d %H:%M", time.localtime(file.last_modified)))
            self.files_table.setItem(row, 3, date_item)
            self.files_table.setItem(row, 4, QTableWidgetItem(dirname))
        self.delete_file_btn.setEnabled(len(files) > 0)
        self.open_folder_btn.setEnabled(len(files) > 0)
        total_size = sum(f.size for f in files)
        if total_size >= 1024**3:
            total_size_str = f"{total_size / (1024**3):.2f} GB"
        elif total_size >= 1024**2:
            total_size_str = f"{total_size / (1024**2):.2f} MB"
        else:
            total_size_str = f"{total_size / 1024:.2f} KB"
        self.files_status_bar.setText(f"Encontrados {len(files)} arquivos - Total: {total_size_str}")
        self.visual_feedback("Busca concluída!", success=True)

    def uninstall_program(self):
        selected_row = self.programs_table.currentRow()
        if selected_row >= 0:
            program_name = self.programs_table.item(selected_row, 0).text()
            uninstall_string = self.programs_table.item(selected_row, 4).text()
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Confirmar Desinstalação")
            msg_box.setText(f"Tem certeza que deseja desinstalar '{program_name}'?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            # Setar fonte clara/branca para a caixa de confirmação
            msg_box.setStyleSheet("""
                QLabel, QMessageBox {
                    color: #fff;
                    background-color: #1e3a8a;
                    font-weight: bold;
                }
                QPushButton {
                    color: #1e3a8a;
                    background-color: #fff;
                    border-radius: 4px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background-color: #e0e7ff;
                }
            """)
            reply = msg_box.exec()
            if reply == QMessageBox.Yes:
                self.status_bar.setText(f"Desinstalando {program_name}...")
                self.status_bar.setStyleSheet("color: #1e3a8a;")
                QApplication.processEvents()
                success = SystemScanner.uninstall_program(uninstall_string)
                if success:
                    self.visual_feedback(f"'{program_name}' desinstalado!", success=True)
                    self.scan_programs()
                else:
                    self.visual_feedback(f"Falha ao desinstalar '{program_name}'.", success=False)
                    self.status_bar.setText("Erro ao desinstalar programa")

    def delete_files(self):
        selected_rows = set(index.row() for index in self.files_table.selectedIndexes())
        if not selected_rows:
            self.visual_feedback("Nenhum arquivo selecionado.", success=False)
            return
        file_paths = []
        total_size = 0
        for row in selected_rows:
            file_name = self.files_table.item(row, 0).text()
            file_dir = self.files_table.item(row, 4).text()
            file_path = os.path.join(file_dir, file_name)
            file_paths.append(file_path)
            size_text = self.files_table.item(row, 1).text()
            if "GB" in size_text:
                total_size += float(size_text.replace(" GB", "")) * 1024**3
            elif "MB" in size_text:
                total_size += float(size_text.replace(" MB", "")) * 1024**2
            elif "KB" in size_text:
                total_size += float(size_text.replace(" KB", "")) * 1024
            else:
                total_size += float(size_text.replace(" B", ""))
        if total_size >= 1024**3:
            total_size_str = f"{total_size / (1024**3):.2f} GB"
        elif total_size >= 1024**2:
            total_size_str = f"{total_size / (1024**2):.2f} MB"
        else:
            total_size_str = f"{total_size / 1024:.2f} KB"
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirmar Exclusão")
        msg_box.setText(
            f"Tem certeza que deseja excluir {len(file_paths)} arquivo(s) (Total: {total_size_str})?\nEsta ação não pode ser desfeita."
        )
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # Setar fonte clara/branca para a caixa de confirmação
        msg_box.setStyleSheet("""
            QLabel, QMessageBox {
                color: #fff;
                background-color: #1e3a8a;
                font-weight: bold;
            }
            QPushButton {
                color: #1e3a8a;
                background-color: #fff;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #e0e7ff;
            }
        """)
        reply = msg_box.exec()
        if reply == QMessageBox.Yes:
            success_count = 0
            for file_path in file_paths:
                if SystemScanner.delete_file(file_path):
                    success_count += 1
            self.files_status_bar.setText(f"{success_count}/{len(file_paths)} arquivos excluídos")
            if success_count > 0:
                self.visual_feedback("Arquivos excluídos!", success=True)
                self.scan_files()
            if success_count < len(file_paths):
                self.visual_feedback(f"{len(file_paths) - success_count} arquivo(s) não puderam ser excluídos.", success=False)

    def open_file_location(self):
        selected_row = self.files_table.currentRow()
        if selected_row >= 0:
            file_dir = self.files_table.item(selected_row, 4).text()
            if os.path.exists(file_dir):
                os.startfile(file_dir)
                self.visual_feedback("Abrindo pasta...", success=True)
            else:
                self.visual_feedback("Diretório não encontrado.", success=False)

    def show_error(self, error_msg):
        self.files_progress_bar.setVisible(False)
        self.status_bar.setText("Erro durante a operação")
        self.status_bar.setStyleSheet("color: #b91c1c;")
        self.files_status_bar.setText("Erro durante a operação")
        self.files_status_bar.setStyleSheet("color: #b91c1c;")
        QMessageBox.critical(self, "Erro", f"Ocorreu um erro:\n{error_msg}", QMessageBox.Ok)
        self.visual_feedback("Erro durante a operação.", success=False)

    def visual_feedback(self, message, success=True):
        color = "#059669" if success else "#b91c1c"
        self.status_bar.setText(message)
        self.status_bar.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.files_status_bar.setText(message)
        self.files_status_bar.setStyleSheet(f"color: {color}; font-weight: bold;")
        QTimer.singleShot(2000, self.reset_status_bar)

    def reset_status_bar(self):
        self.status_bar.setText("Pronto")
        self.status_bar.setStyleSheet("color: #000;")
        self.files_status_bar.setText("Pronto")
        self.files_status_bar.setStyleSheet("color: #000;")