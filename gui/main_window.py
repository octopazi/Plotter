import os
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QInputDialog, QMessageBox, 
    QSplitter, QWidget, QVBoxLayout, QListWidget, QTableView, QLabel, QHeaderView, QListWidgetItem,
    QMenu
)
from PyQt5.QtCore import Qt
from core.config_manager import ConfigManager
from core.file_loader import FileLoader
from core.data_manager import DataManager
from core.pandas_table_model import PandasTableModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plotter")
        self.resize(1000, 700)
        
        self.data_manager = DataManager()

        # Setup Central Widget with Splitter for Data Viewer
        self.setup_central_widget()

        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        import_datalog_action = QAction("Import Datalog", self)
        import_datalog_action.triggered.connect(self.open_import_datalog_dialog)
        file_menu.addAction(import_datalog_action)

        delete_dataset_action = QAction("Delete Dataset", self)
        delete_dataset_action.triggered.connect(self.delete_selected_dataset)
        file_menu.addAction(delete_dataset_action)

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
        fft_action.triggered.connect(self.open_fft_dialog)
        tools_menu.addAction(fft_action)
        
        # Track active plot windows so they don't get garbage collected
        self.plot_windows = []

    def closeEvent(self, event):
        """Close all plot windows when the main window is closed."""
        for plot_win in self.plot_windows:
            try:
                plot_win.close()
            except:
                pass
        self.plot_windows.clear()
        event.accept()

    def setup_central_widget(self):
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # Left Panel (File List)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Imported Files:"))
        self.file_list_widget = QListWidget()
        # Connect selection change to updating data viewer
        self.file_list_widget.currentItemChanged.connect(self.on_file_selected)
        # Enable right-click context menu for deleting datasets
        self.file_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list_widget.customContextMenuRequested.connect(self.show_file_list_context_menu)
        left_layout.addWidget(self.file_list_widget)

        # Right Panel (Data Viewer)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Data Viewer (Editable):"))
        self.data_table_view = QTableView()
        # Optimize view for large data sets
        self.data_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        right_layout.addWidget(self.data_table_view)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set proportion 1:4
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

    def open_import_datalog_dialog(self):
        from .import_datalog import ImportDatalogDialog
        dialog = ImportDatalogDialog(self)
        if dialog.exec_():
            print(f"User requested to import {len(dialog.selected_files)} files using config {dialog.selected_config}")
            try:
                added_count = 0
                last_dataset = None
                
                # Load each file and add to DataManager independently
                for file_path in dialog.selected_files:
                    result = FileLoader.load_datalog(file_path, dialog.selected_config)
                    if not result: continue
                    
                    df = result['dataframe']
                    metadata = result['metadata']
                    name = os.path.basename(file_path)
                    
                    ds_id = self.data_manager.add_dataset(name, df, metadata, dataset_type="raw")
                    last_dataset = self.data_manager.get_dataset(ds_id)
                    added_count += 1
                
                if added_count == 0:
                    return
                
                self.update_file_list_widget()
                
                # Show summary
                msg = f"Successfully imported {added_count} file(s)."
                QMessageBox.information(self, "Success", msg)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Import Error", f"Failed to import datalog: {str(e)}")

    def update_file_list_widget(self):
        self.file_list_widget.clear()
        summaries = self.data_manager.get_all_summaries()
        for summary in summaries:
            item = QListWidgetItem(f"{summary['name']} ({summary['rows']} rows)")
            item.setData(Qt.UserRole, summary['id'])
            self.file_list_widget.addItem(item)

    def on_file_selected(self, current, previous):
        if not current:
            return
            
        ds_id = current.data(Qt.UserRole)
        dataset = self.data_manager.get_dataset(ds_id)
        
        if dataset:
            # Update the table model directly with the dataset's dataframe
            self.table_model = PandasTableModel(dataset.df)
            self.data_table_view.setModel(self.table_model)
            
            # Edits in PandasTableModel modify dataset.df directly in memory, 
            # so no manual 'sync_edited_data' index mapping is required anymore!

    def show_file_list_context_menu(self, position):
        """Show a right-click context menu on the dataset list."""
        item = self.file_list_widget.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        delete_action = QAction("Delete Dataset", self)
        delete_action.triggered.connect(self.delete_selected_dataset)
        menu.addAction(delete_action)
        menu.exec_(self.file_list_widget.mapToGlobal(position))

    def delete_selected_dataset(self):
        """Delete the currently selected dataset from the DataManager and refresh the UI."""
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a dataset to delete.")
            return

        ds_id = current_item.data(Qt.UserRole)
        dataset = self.data_manager.get_dataset(ds_id)
        if not dataset:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{dataset.name}' from memory?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.data_manager.remove_dataset(ds_id)

        # Clear the table view if the deleted dataset was being displayed
        self.data_table_view.setModel(None)

        self.update_file_list_widget()

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
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Data", "Please select a dataset from the left panel to plot.")
            return
            
        ds_id = current_item.data(Qt.UserRole)
        dataset = self.data_manager.get_dataset(ds_id)
        if not dataset:
            return
            
        df = dataset.df
        columns = df.columns.tolist()
        # Filter out source file column for plot selection
        if '_source_file' in columns:
            columns.remove('_source_file')
        
        # 1. Pop UI to ask for X and Y Selection
        from .plot_setup_dialog import PlotSetupDialog
        dialog = PlotSetupDialog(columns, plot_type=plot_type, parent=self)
        if dialog.exec_():
            x_col = dialog.selected_x
            y_cols = dialog.selected_y_columns
            
            # 2. Show Plot Window after user confirmed input.
            from .plot_window import PlotWindow
            plot_win = PlotWindow(df, x_col, y_cols, plot_type=plot_type, window_title=f"{dataset.name} - Plot", parent=self)
            
            # Avoid early garbage collection by maintaining references to open plots
            self.plot_windows.append(plot_win)
            plot_win.show()

    def open_fft_dialog(self):
        from .fft_dialog import FFTDialog
        dialog = FFTDialog(self.data_manager, parent=self)
        if dialog.exec_():
            self.update_file_list_widget()
            # Auto-select the newly created FFT dataset in the list
            for i in range(self.file_list_widget.count()):
                item = self.file_list_widget.item(i)
                if item.data(Qt.UserRole) == dialog.new_dataset_id:
                    self.file_list_widget.setCurrentItem(item)
                    break
            QMessageBox.information(self, "FFT Complete",
                                    "FFT result has been added to the dataset list.")

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