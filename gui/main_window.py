import os
from PyQt5.QtWidgets import QMainWindow, QAction, QFileDialog, QInputDialog, QMessageBox
from core.config_manager import ConfigManager

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

        # Config menu
        config_menu = menubar.addMenu("Config")

        new_config_action = QAction("New", self)
        new_config_action.triggered.connect(self.open_create_config_dialog)
        config_menu.addAction(new_config_action)

        import_config_action = QAction("Import", self)
        import_config_action.triggered.connect(self.open_import_config_dialog)
        config_menu.addAction(import_config_action)

        edit_config_action = QAction("Edit", self)
        edit_config_action.triggered.connect(self.open_edit_config_dialog)
        config_menu.addAction(edit_config_action)

        delete_config_action = QAction("Delete", self)
        delete_config_action.triggered.connect(self.open_delete_config_dialog)
        config_menu.addAction(delete_config_action)

        # Plot menu
        plot_menu = menubar.addMenu("Plot")
        scatter_action = QAction("Scatter Plot", self)
        plot_menu.addAction(scatter_action)

        # Tools menu (FFT)
        tools_menu = menubar.addMenu("Tools")
        fft_action = QAction("FFT", self)
        tools_menu.addAction(fft_action)

    def open_import_config_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Config File", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            success, message, name = ConfigManager.import_external_config(file_path, overwrite=False)
            if success:
                QMessageBox.information(self, "Success", message)
            elif message == "ALREADY_EXISTS":
                reply = QMessageBox.question(
                    self, "File Exists", 
                    f"A configuration named '{name}' already exists in your workspace. Do you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    success, message, _ = ConfigManager.import_external_config(file_path, overwrite=True)
                    if success:
                        QMessageBox.information(self, "Success", message)
                    else:
                        QMessageBox.warning(self, "Import Failed", message)
            else:
                QMessageBox.warning(self, "Import Failed", message)

    def open_create_config_dialog(self):
        from .create_config import CreateImportFormatDialog
        dialog = CreateImportFormatDialog(self)
        dialog.exec_()

    def open_edit_config_dialog(self):
        config_files = ConfigManager.get_available_configs()
        if not config_files:
            QMessageBox.warning(self, "Error", "No config files found in the Config folder.")
            return

        item, ok = QInputDialog.getItem(self, "Edit Config", "Select config to edit:", config_files, 0, False)
        if ok and item:
            config_path = ConfigManager.get_config_path(item)
            from .create_config import EditImportFormatDialog
            dialog = EditImportFormatDialog(config_path, self)
            dialog.exec_()

    def open_delete_config_dialog(self):
        config_files = ConfigManager.get_available_configs()
        if not config_files:
            QMessageBox.warning(self, "Error", "No config files found in the Config folder.")
            return

        item, ok = QInputDialog.getItem(self, "Delete Config", "Select config to delete:", config_files, 0, False)
        if ok and item:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to completely delete '{item}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                config_path = ConfigManager.get_config_path(item)
                try:
                    os.remove(config_path)
                    QMessageBox.information(self, "Deleted", f"Successfully deleted '{item}'.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete file:\n{e}")