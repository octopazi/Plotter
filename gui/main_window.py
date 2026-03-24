from PyQt5.QtWidgets import QMainWindow, QAction, QFileDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plotter")
        self.resize(800, 600)

        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Data File", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        import_config_action = QAction("Import Data Format Config", self)
        import_config_action.triggered.connect(self.open_import_config_dialog)
        file_menu.addAction(import_config_action)

        create_config_action = QAction("Create Data Format Config", self)
        create_config_action.triggered.connect(self.open_create_config_dialog)
        file_menu.addAction(create_config_action)

        # Plot menu
        plot_menu = menubar.addMenu("Plot")
        scatter_action = QAction("Scatter Plot", self)
        plot_menu.addAction(scatter_action)

        # Tools menu (FFT)
        tools_menu = menubar.addMenu("Tools")
        fft_action = QAction("FFT", self)
        tools_menu.addAction(fft_action)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*.*)"
        )
        if file_path:
            print("Selected:", file_path)

    def open_import_config_dialog(self):
        from .import_config import ImportConfigDialog
        dialog = ImportConfigDialog(self)
        if dialog.exec_():
            config = dialog.get_config()
            print("Loaded config:", config)

    def open_create_config_dialog(self):
        from .create_config import CreateImportFormatDialog
        dialog = CreateImportFormatDialog(self)
        if dialog.exec_():
            config = dialog.get_config()
            print("Created config:", config)