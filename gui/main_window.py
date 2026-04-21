import os
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QInputDialog, QMessageBox, 
    QSplitter, QWidget, QVBoxLayout, QListWidget, QTableView, QLabel, QHeaderView, QListWidgetItem,
    QMenu
)
from PyQt5.QtCore import Qt
from core.config_manager import ConfigManager
from core.column_stats import compute_column_stats
from core.file_loader import FileLoader
from core.data_manager import DataManager
from core.pandas_table_model import PandasTableModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plotter")
        self.resize(1000, 700)
        
        self.data_manager = DataManager()
        self.table_model = None

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

        export_dataset_action = QAction("Export Dataset", self)
        export_dataset_action.triggered.connect(self.open_export_dialog)
        file_menu.addAction(export_dataset_action)

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

        run_config_plots_action = QAction("Run Config Plots", self)
        run_config_plots_action.triggered.connect(self.open_run_config_plots_dialog)
        plot_menu.addAction(run_config_plots_action)

        # Tools menu (FFT)
        tools_menu = menubar.addMenu("Tools")
        fft_action = QAction("FFT", self)
        fft_action.triggered.connect(self.open_fft_dialog)
        tools_menu.addAction(fft_action)

        stats_action = QAction("Column Statistics Summary", self)
        stats_action.triggered.connect(lambda _checked=False: self.open_column_statistics())
        tools_menu.addAction(stats_action)
        
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
        # Enable editing of headers by double-clicking
        header = self.data_table_view.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.sectionDoubleClicked.connect(self.edit_header)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_table_header_context_menu)
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
                imported_dataset_ids = []
                all_conversion_errors = []   # (filename, ConversionError) pairs
                
                # Load each file and add to DataManager independently
                for file_path in dialog.selected_files:
                    result = FileLoader.load_datalog(file_path, dialog.selected_config)
                    if not result: continue
                    
                    df = result['dataframe']
                    metadata = result['metadata']
                    name = os.path.basename(file_path)

                    # Collect conversion errors for this file
                    for err in result.get('conversion_errors', []):
                        all_conversion_errors.append((name, err))
                    
                    ds_id = self.data_manager.add_dataset(name, df, metadata, dataset_type="raw")
                    imported_dataset_ids.append(ds_id)
                    added_count += 1
                
                if added_count == 0:
                    return
                
                self.update_file_list_widget()
                auto_plot_summary = self._run_auto_plot_after_import(imported_dataset_ids, dialog.selected_config)

                # Report any conversion errors as a single warning dialog
                if all_conversion_errors:
                    lines = []
                    for filename, err in all_conversion_errors:
                        lines.append(f"[{filename}]  {err}")
                    QMessageBox.warning(
                        self, "Conversion Warnings",
                        f"{len(all_conversion_errors)} conversion step(s) failed and were skipped.\n"
                        f"The affected output columns are absent from the dataset.\n\n"
                        + "\n\n".join(lines)
                    )
                
                # Show summary
                msg = f"Successfully imported {added_count} file(s)."
                if auto_plot_summary.get("enabled"):
                    msg += (
                        f"\nAuto plots created: {auto_plot_summary.get('created', 0)}"
                        f" / {auto_plot_summary.get('requested', 0)}."
                    )
                    skipped = auto_plot_summary.get("skipped", [])
                    if skipped:
                        msg += "\nSkipped figures:"
                        for reason in skipped[:8]:
                            msg += f"\n- {reason}"
                        if len(skipped) > 8:
                            msg += f"\n- ... and {len(skipped) - 8} more"
                elif auto_plot_summary.get("config_error"):
                    msg += (
                        "\nAuto plot was skipped because plot config could not be loaded: "
                        f"{auto_plot_summary.get('config_error')}"
                    )
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

    def edit_header(self, section):
        """Allow user to edit column header by double-clicking on it."""
        header = self.data_table_view.horizontalHeader()
        old_name = self.table_model._data.columns[section]
        
        # Show a dialog to get the new column name
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Column",
            f"Enter new name for column '{old_name}':",
            text=old_name
        )
        
        if ok and new_name.strip():
            # Use the model's setHeaderData method to rename
            success = self.table_model.setHeaderData(section, Qt.Horizontal, new_name, Qt.EditRole)
            if success:
                QMessageBox.information(self, "Success", f"Column renamed to '{new_name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to rename column")

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

    def show_table_header_context_menu(self, position):
        """Show a right-click context menu on the data table headers."""
        if not self.table_model:
            return

        header = self.data_table_view.horizontalHeader()
        section = header.logicalIndexAt(position)
        if section < 0:
            return

        try:
            column_name = str(self.table_model._data.columns[section])
        except Exception:
            return

        menu = QMenu(self)
        stats_action = QAction("Column Statistics Summary", self)
        stats_action.triggered.connect(lambda: self.open_column_statistics(section))
        menu.addAction(stats_action)

        delete_action = QAction(f"Delete Column '{column_name}'", self)
        delete_action.triggered.connect(lambda: self.delete_column(section))
        menu.addAction(delete_action)

        menu.exec_(header.mapToGlobal(position))

    def delete_column(self, section):
        """Delete a column from the current dataset after user confirmation."""
        if not self.table_model:
            return

        try:
            section = int(section)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Invalid Selection", "Selected column is invalid.")
            return

        if section < 0 or section >= self.table_model.columnCount():
            QMessageBox.warning(self, "Invalid Selection", "Selected column is out of range.")
            return

        column_name = str(self.table_model._data.columns[section])
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete column '{column_name}' from this dataset?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        if not self.table_model.delete_column(section):
            QMessageBox.warning(self, "Delete Failed", f"Failed to delete column '{column_name}'.")
            return

        self.data_table_view.clearSelection()
        QMessageBox.information(self, "Column Deleted", f"Column '{column_name}' was deleted.")

    def get_current_dataset(self):
        """Return the currently selected dataset object from the list panel."""
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            return None
        ds_id = current_item.data(Qt.UserRole)
        if not ds_id:
            return None
        return self.data_manager.get_dataset(ds_id)

    def open_column_statistics(self, column_index=None):
        dataset = self.get_current_dataset()
        if dataset is None:
            QMessageBox.warning(self, "No Data", "Please select a dataset first.")
            return

        df = dataset.df
        if df.empty:
            QMessageBox.warning(self, "No Data", "Selected dataset is empty.")
            return

        # QAction.triggered emits a bool, which is not a valid table column index.
        if isinstance(column_index, bool):
            column_index = None

        if column_index is None:
            current_idx = self.data_table_view.currentIndex()
            if current_idx.isValid():
                column_index = current_idx.column()

        if column_index is None:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                QMessageBox.warning(self, "No Numeric Columns", "This dataset has no numeric columns.")
                return

            selected_col, ok = QInputDialog.getItem(
                self,
                "Column Statistics Summary",
                "Select numeric column:",
                numeric_cols,
                0,
                False,
            )
            if not ok:
                return
            column_name = selected_col
        else:
            try:
                column_index = int(column_index)
            except (TypeError, ValueError):
                QMessageBox.warning(self, "Invalid Selection", "Selected column is invalid.")
                return

            if column_index < 0 or column_index >= len(df.columns):
                QMessageBox.warning(self, "Invalid Selection", "Selected column is out of range.")
                return
            column_name = df.columns[column_index]

        if column_name == "_source_file":
            QMessageBox.warning(
                self,
                "Unsupported Column",
                "Statistics are not available for '_source_file'.",
            )
            return

        try:
            stats = compute_column_stats(df[column_name])
        except ValueError as e:
            QMessageBox.warning(self, "Statistics Unavailable", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Statistics Error", f"Failed to compute statistics:\n{str(e)}")
            return

        from .column_stats_dialog import ColumnStatsDialog
        dialog = ColumnStatsDialog(dataset.name, column_name, stats, self)
        dialog.exec_()

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

    def open_export_dialog(self):
        """Open the Export Dataset dialog."""
        if not self.data_manager.datasets:
            QMessageBox.warning(self, "No Data", "No datasets are loaded. Please import a datalog first.")
            return
        from .export_dialog import ExportDialog
        dialog = ExportDialog(self.data_manager, parent=self)
        dialog.exec_()

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
            self._create_plot_window(dataset, x_col, y_cols, plot_type, window_title=f"{dataset.name} - Plot")

    def open_run_config_plots_dialog(self):
        if not self.data_manager.datasets:
            QMessageBox.warning(self, "No Data", "No datasets are loaded. Please import a datalog first.")
            return

        config_files = ConfigManager.get_available_configs()
        if not config_files:
            QMessageBox.warning(self, "No Config", "No config files found in the Config folder.")
            return

        item, ok = QInputDialog.getItem(
            self,
            "Run Config Plots",
            "Select config for plot figures:",
            config_files,
            0,
            False,
        )
        if not ok or not item:
            return

        dataset_ids = list(self.data_manager.datasets.keys())
        summary = self._run_config_plots(
            dataset_ids,
            item,
            require_enabled=False,
            context_label="Run Config Plots",
        )

        if summary.get("config_error"):
            QMessageBox.warning(
                self,
                "Run Config Plots",
                f"Failed to load plot config: {summary.get('config_error')}",
            )
            return

        if summary.get("aborted"):
            QMessageBox.information(
                self,
                "Run Config Plots",
                "Plot launch was cancelled.",
            )
            return

        if summary.get("no_figures"):
            QMessageBox.information(
                self,
                "Run Config Plots",
                "No plot figures are defined in this config.",
            )
            return

        msg = (
            f"Created {summary.get('created', 0)} of {summary.get('requested', 0)} "
            f"requested plot windows."
        )
        skipped = summary.get("skipped", [])
        if skipped:
            msg += "\nSkipped figures:"
            for reason in skipped[:10]:
                msg += f"\n- {reason}"
            if len(skipped) > 10:
                msg += f"\n- ... and {len(skipped) - 10} more"

        QMessageBox.information(self, "Run Config Plots", msg)

    def _create_plot_window(self, dataset, x_col, y_cols, plot_type, window_title=None):
        from .plot_window import PlotWindow

        plot_win = PlotWindow(
            dataset.df,
            x_col,
            y_cols,
            plot_type=plot_type,
            window_title=window_title,
            parent=self,
        )

        # Avoid early garbage collection by maintaining references to open plots
        self.plot_windows.append(plot_win)
        plot_win.show()
        return plot_win

    def _resolve_column_name(self, available_columns, requested_name):
        req = str(requested_name).strip()
        if not req:
            return None

        if req in available_columns:
            return req

        req_lower = req.lower()
        for col in available_columns:
            if col.lower() == req_lower:
                return col
        return None

    def _build_auto_plot_selection(self, df, figure_cfg):
        available_columns = [col for col in df.columns.tolist() if col != "_source_file"]
        if len(available_columns) < 2:
            return None, None, "not enough columns to build a plot"

        x_col = self._resolve_column_name(available_columns, figure_cfg.get("x_column", ""))
        if not x_col:
            return None, None, f"x column '{figure_cfg.get('x_column', '')}' not found"

        y_cols = []
        for y_name in figure_cfg.get("y_columns", []):
            y_col = self._resolve_column_name(available_columns, y_name)
            if y_col and y_col != x_col and y_col not in y_cols:
                y_cols.append(y_col)

        if not y_cols:
            return None, None, "no valid y columns were found"

        return x_col, y_cols, None

    def _confirm_bulk_plot_open(self, requested_count, context_label):
        if requested_count <= 10:
            return True

        reply = QMessageBox.question(
            self,
            "Large Plot Batch",
            f"{context_label} will open {requested_count} plot windows.\n"
            "This can slow down the UI. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _run_config_plots(self, dataset_ids, config_filename, require_enabled, context_label):
        summary = {
            "enabled": False,
            "created": 0,
            "requested": 0,
            "skipped": [],
            "config_error": None,
            "aborted": False,
            "no_figures": False,
        }

        try:
            config = ConfigManager.load_config(config_filename)
        except Exception as e:
            summary["config_error"] = str(e)
            return summary

        plot_cfg = config.get("plot_config", {})
        summary["enabled"] = bool(plot_cfg.get("enabled", False))
        if require_enabled and not summary["enabled"]:
            return summary

        figures = plot_cfg.get("figures", [])
        if not figures:
            summary["no_figures"] = True
            return summary

        summary["requested"] = len(dataset_ids) * len(figures)
        if not self._confirm_bulk_plot_open(summary["requested"], context_label):
            summary["aborted"] = True
            return summary

        for ds_id in dataset_ids:
            dataset = self.data_manager.get_dataset(ds_id)
            if not dataset:
                continue

            for idx, figure_cfg in enumerate(figures, start=1):
                x_col, y_cols, reason = self._build_auto_plot_selection(dataset.df, figure_cfg)
                if reason:
                    summary["skipped"].append(f"{dataset.name} / figure #{idx}: {reason}")
                    continue

                plot_type = str(figure_cfg.get("plot_type", "scatter"))
                if plot_type not in ("scatter", "line_scatter"):
                    plot_type = "scatter"

                fig_title = str(figure_cfg.get("title", "")).strip()
                window_title = f"{dataset.name} - {fig_title}" if fig_title else f"{dataset.name} - Auto Plot {idx}"

                try:
                    self._create_plot_window(dataset, x_col, y_cols, plot_type, window_title=window_title)
                    summary["created"] += 1
                except Exception as e:
                    summary["skipped"].append(f"{dataset.name} / figure #{idx}: failed to render ({str(e)})")

        return summary

    def _run_auto_plot_after_import(self, imported_dataset_ids, config_filename):
        return self._run_config_plots(
            imported_dataset_ids,
            config_filename,
            require_enabled=True,
            context_label="Auto plot after import",
        )

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