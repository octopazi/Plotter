import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QGroupBox, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QSizePolicy, QAbstractItemView, QHeaderView,
    QStackedWidget, QWidget
)
from PyQt5.QtCore import Qt


class ExportDialog(QDialog):
    """
    Dialog for exporting one or more datasets to CSV or Excel format.

    Modes:
      - CSV:   Each selected dataset is saved as an individual .csv file.
               Single dataset  → user picks a file path.
               Multiple datasets → user picks a folder; files are named after each dataset.
      - Excel: All selected datasets are written into a single .xlsx workbook,
               each dataset on a separate sheet. Sheet names are editable before export.
    """

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Export Dataset")
        self.setMinimumWidth(520)
        self.setMinimumHeight(480)

        self._build_ui()
        self._populate_dataset_list()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Dataset selection ──────────────────────────────────────────
        ds_group = QGroupBox("Select Datasets to Export")
        ds_layout = QVBoxLayout(ds_group)

        select_btns = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_deselect_all = QPushButton("Deselect All")
        select_btns.addWidget(self.btn_select_all)
        select_btns.addWidget(self.btn_deselect_all)
        select_btns.addStretch()
        ds_layout.addLayout(select_btns)

        self.dataset_list = QListWidget()
        self.dataset_list.setSelectionMode(QAbstractItemView.NoSelection)
        ds_layout.addWidget(self.dataset_list)
        root.addWidget(ds_group)

        # ── Format selector ────────────────────────────────────────────
        fmt_group = QGroupBox("Export Format")
        fmt_layout = QHBoxLayout(fmt_group)
        self.radio_csv = QRadioButton("CSV (.csv)  —  one file per dataset")
        self.radio_excel = QRadioButton("Excel (.xlsx)  —  all datasets in one workbook")
        self.radio_csv.setChecked(True)
        self._fmt_group = QButtonGroup(self)
        self._fmt_group.addButton(self.radio_csv)
        self._fmt_group.addButton(self.radio_excel)
        fmt_layout.addWidget(self.radio_csv)
        fmt_layout.addWidget(self.radio_excel)
        root.addWidget(fmt_group)

        # ── Stacked panel: blank (CSV) vs sheet-name editor (Excel) ────
        self.stacked = QStackedWidget()

        # Page 0: CSV (empty placeholder)
        csv_page = QWidget()
        self.stacked.addWidget(csv_page)

        # Page 1: Excel sheet names
        excel_page = QWidget()
        excel_layout = QVBoxLayout(excel_page)
        excel_layout.setContentsMargins(0, 0, 0, 0)
        excel_layout.addWidget(QLabel("Customize sheet names (optional):"))
        self.sheet_table = QTableWidget(0, 2)
        self.sheet_table.setHorizontalHeaderLabels(["Dataset", "Sheet Name"])
        self.sheet_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sheet_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sheet_table.verticalHeader().setVisible(False)
        self.sheet_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        excel_layout.addWidget(self.sheet_table)
        self.stacked.addWidget(excel_page)

        root.addWidget(self.stacked)

        # ── Buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_export = QPushButton("Export")
        self.btn_export.setDefault(True)
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_export)
        btn_row.addWidget(self.btn_cancel)
        root.addLayout(btn_row)

    def _populate_dataset_list(self):
        """Fill the checkbox list with all datasets currently in DataManager."""
        self.dataset_list.clear()
        summaries = self.data_manager.get_all_summaries()
        for summary in summaries:
            item = QListWidgetItem(f"{summary['name']}  ({summary['rows']} rows, {len(summary['columns'])} cols)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, summary['id'])
            self.dataset_list.addItem(item)

    # ------------------------------------------------------------------ #
    #  Signal Connections                                                  #
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.radio_csv.toggled.connect(self._on_format_changed)
        self.radio_excel.toggled.connect(self._on_format_changed)
        # Rebuild sheet-name table whenever checkboxes change
        self.dataset_list.itemChanged.connect(self._refresh_sheet_table)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_cancel.clicked.connect(self.reject)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _select_all(self):
        for i in range(self.dataset_list.count()):
            self.dataset_list.item(i).setCheckState(Qt.Checked)

    def _deselect_all(self):
        for i in range(self.dataset_list.count()):
            self.dataset_list.item(i).setCheckState(Qt.Unchecked)

    def _on_format_changed(self):
        if self.radio_excel.isChecked():
            self.stacked.setCurrentIndex(1)
            self._refresh_sheet_table()
        else:
            self.stacked.setCurrentIndex(0)

    def _get_checked_items(self):
        """Return list of (ds_id, dataset_name) for every checked item."""
        result = []
        for i in range(self.dataset_list.count()):
            item = self.dataset_list.item(i)
            if item.checkState() == Qt.Checked:
                ds_id = item.data(Qt.UserRole)
                ds = self.data_manager.get_dataset(ds_id)
                if ds:
                    result.append((ds_id, ds.name))
        return result

    def _refresh_sheet_table(self):
        """Rebuild the sheet-name editor table to match the current checked datasets."""
        if not self.radio_excel.isChecked():
            return

        checked = self._get_checked_items()
        self.sheet_table.setRowCount(len(checked))
        for row, (ds_id, name) in enumerate(checked):
            # Dataset name column (read-only)
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setData(Qt.UserRole, ds_id)
            self.sheet_table.setItem(row, 0, name_item)

            # Sheet name column (editable, pre-filled with a sanitised name)
            sheet_item = QTableWidgetItem(self._safe_sheet_name(name))
            self.sheet_table.setItem(row, 1, sheet_item)

    @staticmethod
    def _safe_sheet_name(name, max_len=31):
        """Excel sheet names ≤ 31 chars and no special characters."""
        invalid = r'\/*?:[]]'
        for ch in invalid:
            name = name.replace(ch, '_')
        return name[:max_len]

    def _make_unique_sheet_names(self, raw_names):
        """Ensure no duplicate sheet names by appending _2, _3, etc."""
        seen = {}
        result = []
        for name in raw_names:
            if name not in seen:
                seen[name] = 1
                result.append(name)
            else:
                seen[name] += 1
                candidate = f"{name[:28]}_{seen[name]}"
                result.append(candidate)
        return result

    # ------------------------------------------------------------------ #
    #  Export Logic                                                        #
    # ------------------------------------------------------------------ #

    def _on_export(self):
        checked = self._get_checked_items()
        if not checked:
            QMessageBox.warning(self, "No Selection", "Please check at least one dataset to export.")
            return

        if self.radio_csv.isChecked():
            self._export_csv(checked)
        else:
            self._export_excel(checked)

    def _export_csv(self, checked):
        """Export each checked dataset as a separate CSV file."""
        if len(checked) == 1:
            ds_id, name = checked[0]
            ds = self.data_manager.get_dataset(ds_id)
            # Suggest a filename based on dataset name (strip extension, add .csv)
            base = os.path.splitext(name)[0]
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save CSV", f"{base}.csv", "CSV Files (*.csv);;All Files (*.*)"
            )
            if not file_path:
                return
            try:
                df = ds.df.copy()
                if '_source_file' in df.columns:
                    df = df.drop(columns=['_source_file'])
                df.to_csv(file_path, index=False)
                QMessageBox.information(self, "Export Successful",
                                        f"Dataset exported to:\n{file_path}")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{e}")

        else:
            # Multiple datasets → ask for a folder
            folder = QFileDialog.getExistingDirectory(self, "Select Output Folder for CSV Files")
            if not folder:
                return
            errors = []
            exported = []
            for ds_id, name in checked:
                ds = self.data_manager.get_dataset(ds_id)
                base = os.path.splitext(name)[0]
                file_path = os.path.join(folder, f"{base}.csv")
                # Avoid silently overwriting if two datasets share the same base name
                file_path = self._unique_file_path(file_path)
                try:
                    df = ds.df.copy()
                    if '_source_file' in df.columns:
                        df = df.drop(columns=['_source_file'])
                    df.to_csv(file_path, index=False)
                    exported.append(os.path.basename(file_path))
                except Exception as e:
                    errors.append(f"{name}: {e}")

            if errors:
                QMessageBox.warning(self, "Export Completed with Errors",
                                    "Some files failed to export:\n" + "\n".join(errors))
            else:
                QMessageBox.information(self, "Export Successful",
                                        f"Exported {len(exported)} file(s) to:\n{folder}\n\n"
                                        + "\n".join(exported))
            self.accept()

    def _export_excel(self, checked):
        """Export all checked datasets into one Excel workbook, one sheet each."""
        # Collect sheet names from the editable table
        sheet_names_raw = []
        for row in range(self.sheet_table.rowCount()):
            sheet_item = self.sheet_table.item(row, 1)
            raw = sheet_item.text().strip() if sheet_item else ""
            sheet_names_raw.append(self._safe_sheet_name(raw) if raw else self._safe_sheet_name(checked[row][1]))

        sheet_names = self._make_unique_sheet_names(sheet_names_raw)

        # Pick output file
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Workbook", "export.xlsx",
            "Excel Files (*.xlsx);;All Files (*.*)"
        )
        if not file_path:
            return

        try:
            with __import__('openpyxl').Workbook() as _:
                pass  # just a quick reachability check
        except ImportError:
            QMessageBox.critical(self, "Missing Dependency",
                                 "The 'openpyxl' package is required for Excel export.\n"
                                 "Install it with:  pip install openpyxl")
            return

        try:
            import pandas as pd
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                for (ds_id, name), sheet_name in zip(checked, sheet_names):
                    ds = self.data_manager.get_dataset(ds_id)
                    df = ds.df.copy()
                    if '_source_file' in df.columns:
                        df = df.drop(columns=['_source_file'])
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            summary = "\n".join(
                f"  • {name}  →  sheet '{sn}'" for (_, name), sn in zip(checked, sheet_names)
            )
            QMessageBox.information(self, "Export Successful",
                                    f"Workbook saved to:\n{file_path}\n\n{summary}")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Excel file:\n{e}")

    # ------------------------------------------------------------------ #
    #  Utility                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _unique_file_path(path):
        """If a file already exists, append _2, _3, ... before the extension."""
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 2
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"
