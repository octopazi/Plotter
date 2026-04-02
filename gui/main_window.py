import os
from PyQt5.QtWidgets import QMainWindow, QAction, QFileDialog, QInputDialog, QMessageBox
from core.config_manager import ConfigManager
from core.file_loader import FileLoader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plotter")
        self.resize(800, 600)

        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        import_datalog_action = QAction("Import Datalog", self)
        import_datalog_action.triggered.connect(self.open_import_datalog_dialog)
        file_menu.addAction(import_datalog_action)

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
        scatter_action.triggered.connect(lambda: self.open_plot_dialog("scatter"))
        plot_menu.addAction(scatter_action)

        line_scatter_action = QAction("Line + Scatter Plot", self)
        line_scatter_action.triggered.connect(lambda: self.open_plot_dialog("line_scatter"))
        plot_menu.addAction(line_scatter_action)

        # Tools menu (FFT)
        tools_menu = menubar.addMenu("Tools")
        fft_action = QAction("FFT", self)
        tools_menu.addAction(fft_action)
        
        # Track active plot windows so they don't get garbage collected
        self.plot_windows = []

    def open_import_datalog_dialog(self):
        from .import_datalog import ImportDatalogDialog
        dialog = ImportDatalogDialog(self)
        if dialog.exec_():
            print(f"User requested to import {len(dialog.selected_files)} files using config {dialog.selected_config}")
            try:
                # Use the new load_datalogs method for multi-file support
                dataset = FileLoader.load_datalogs(dialog.selected_files, dialog.selected_config)
                if dataset is None:
                    return

                # Store it in MainWindow instance for future analysis/plotting tools
                self.current_dataset = dataset
                
                # Show summary
                row_count = len(dataset["dataframe"])
                meta_info = "\n".join([f"{k}: {v}" for k, v in dataset["metadata"].items()])
                
                file_summary = ", ".join([os.path.basename(f) for f in dialog.selected_files[:3]])
                if len(dialog.selected_files) > 3:
                    file_summary += f", and {len(dialog.selected_files)-3} more..."
                
                msg = f"Successfully imported {len(dialog.selected_files)} file(s):\n{file_summary}\n\nMetadata Summary:\n{meta_info}\n\nTotal Rows (Combined): {row_count}"
                QMessageBox.information(self, "Success", msg)
                print(f"Data Head:\n{dataset['dataframe'].head()}")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Import Error", f"Failed to import datalog: {str(e)}")

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

    def open_plot_dialog(self, plot_type):
        if not hasattr(self, 'current_dataset') or self.current_dataset is None:
            QMessageBox.warning(self, "No Data", "Please import a datalog first.")
            return
            
        df = self.current_dataset['dataframe']
        columns = df.columns.tolist()
        
        # 1. Pop UI to ask for X and Y Selection
        from .plot_setup_dialog import PlotSetupDialog
        dialog = PlotSetupDialog(columns, plot_type=plot_type, parent=self)
        if dialog.exec_():
            x_col = dialog.selected_x
            y_col = dialog.selected_y
            
            # 2. Show Plot Window after user confirmed input.
            from .plot_window import PlotWindow
            plot_win = PlotWindow(df, x_col, y_col, plot_type=plot_type)
            
            # Avoid early garbage collection by maintaining references to open plots
            self.plot_windows.append(plot_win)
            plot_win.show()

    def open_scatter_plot(self):
        # Deprecated: replaced by open_plot_dialog
        self.open_plot_dialog("scatter")

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