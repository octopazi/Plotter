from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget, QAbstractItemView, QLineEdit,
    QMessageBox, QFormLayout, QGroupBox
)
from PyQt5.QtCore import Qt
from core.fft import FFTAnalyzer


class FFTDialog(QDialog):
    """
    Dialog for running FFT analysis on an existing dataset.

    Workflow
    --------
    1. User selects a source dataset from the list.
    2. User picks one or more numeric signal columns (multi-select).
    3. User enters sample rate (Hz) and optional unit label.
    4. On 'Run FFT', the result DataFrame is stored as a new 'fft' dataset
       in the shared DataManager and the dialog closes accepted.
    """

    def __init__(self, data_manager, preferred_dataset_id=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.preferred_dataset_id = preferred_dataset_id
        self.new_dataset_id = None  # Populated on successful run

        self.setWindowTitle("FFT Analysis")
        self.setMinimumWidth(440)
        self.init_ui()
        self._populate_dataset_list()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def init_ui(self):
        root_layout = QVBoxLayout(self)

        # --- Dataset Selection ---
        ds_group = QGroupBox("Source Dataset")
        ds_layout = QVBoxLayout(ds_group)

        self.dataset_combo = QComboBox()
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        ds_layout.addWidget(self.dataset_combo)
        root_layout.addWidget(ds_group)

        # --- Signal Column Selection ---
        sig_group = QGroupBox("Signal Columns  (Hold Ctrl to multi-select)")
        sig_layout = QVBoxLayout(sig_group)

        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.column_list.setMinimumHeight(120)
        sig_layout.addWidget(self.column_list)
        root_layout.addWidget(sig_group)

        # --- FFT Parameters ---
        param_group = QGroupBox("Parameters")
        param_form = QFormLayout(param_group)

        self.sample_rate_edit = QLineEdit("16000")
        self.sample_rate_edit.setPlaceholderText("e.g. 16000")
        param_form.addRow("Sample Rate (Hz):", self.sample_rate_edit)

        self.unit_edit = QLineEdit("unit")
        self.unit_edit.setPlaceholderText("e.g. cnt, V, g")
        param_form.addRow("Unit Label:", self.unit_edit)

        self.start_row_edit = QLineEdit()
        self.start_row_edit.setPlaceholderText("0 (first row)")
        param_form.addRow("Start Row:", self.start_row_edit)

        self.end_row_edit = QLineEdit()
        self.end_row_edit.setPlaceholderText("(last row)")
        param_form.addRow("End Row:", self.end_row_edit)

        self.row_range_hint = QLabel()
        self.row_range_hint.setStyleSheet("color: gray;")
        param_form.addRow("", self.row_range_hint)

        root_layout.addWidget(param_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run FFT")
        self.cancel_btn = QPushButton("Cancel")

        self.run_btn.clicked.connect(self._on_run)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.cancel_btn)
        root_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------
    def _populate_dataset_list(self):
        """Fill the dataset combo from DataManager."""
        self.dataset_combo.clear()
        summaries = self.data_manager.get_all_summaries()
        if not summaries:
            self.dataset_combo.addItem("(No datasets loaded)", None)
            self.run_btn.setEnabled(False)
            return

        self.run_btn.setEnabled(True)
        for s in summaries:
            label = f"{s['name']}  [{s['type']}]  ({s['rows']} rows)"
            self.dataset_combo.addItem(label, s['id'])

        # Default to the dataset currently selected in data viewer when available.
        preferred_index = self.dataset_combo.findData(self.preferred_dataset_id)
        if preferred_index >= 0:
            self.dataset_combo.setCurrentIndex(preferred_index)
        else:
            self.dataset_combo.setCurrentIndex(0)

    def _on_dataset_changed(self, index):
        """Update the column list when the user picks a different dataset."""
        self.column_list.clear()
        ds_id = self.dataset_combo.itemData(index)
        if ds_id is None:
            return

        dataset = self.data_manager.get_dataset(ds_id)
        if dataset is None:
            return

        metadata = dataset.metadata if isinstance(dataset.metadata, dict) else {}
        hidden_columns = self._normalize_hidden_columns(metadata.get("hidden_columns", []))
        hidden_set = set(hidden_columns)

        numeric_cols = dataset.df.select_dtypes(include='number').columns.tolist()
        if hidden_set:
            numeric_cols = [col for col in numeric_cols if col not in hidden_set]

        if not numeric_cols:
            self.column_list.addItem("(No visible numeric columns found)")
            return

        self.column_list.addItems(numeric_cols)

        # Update row range hint
        total_rows = len(dataset.df)
        self.row_range_hint.setText(f"Dataset has {total_rows} rows  (valid: 0 – {total_rows - 1})")
        self.end_row_edit.setPlaceholderText(f"{total_rows} (last row)")

    def _normalize_hidden_columns(self, values):
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return []

        hidden = []
        seen = set()
        for value in values:
            name = str(value).strip()
            if not name or name in seen:
                continue
            hidden.append(name)
            seen.add(name)
        return hidden

    # ------------------------------------------------------------------
    # Run FFT
    # ------------------------------------------------------------------
    def _on_run(self):
        # 1. Validate dataset selection
        ds_id = self.dataset_combo.currentData()
        if ds_id is None:
            QMessageBox.warning(self, "No Dataset", "Please load a dataset first.")
            return

        source_ds = self.data_manager.get_dataset(ds_id)
        if source_ds is None:
            QMessageBox.warning(self, "Dataset Error", "Selected dataset could not be found.")
            return

        # 2. Validate signal column selection
        selected_items = self.column_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Columns", "Please select at least one signal column.")
            return
        signal_cols = [item.text() for item in selected_items]

        # 3. Validate sample rate
        try:
            sample_rate = float(self.sample_rate_edit.text().strip())
            if sample_rate <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Sample Rate",
                                "Sample rate must be a positive number (e.g. 16000).")
            return

        unit = self.unit_edit.text().strip() or "unit"

        # 4. Validate and apply row range
        total_rows = len(source_ds.df)
        start_text = self.start_row_edit.text().strip()
        end_text = self.end_row_edit.text().strip()
        try:
            row_start = int(start_text) if start_text else 0
            row_end = int(end_text) if end_text else total_rows
        except ValueError:
            QMessageBox.warning(self, "Invalid Row Range", "Start Row and End Row must be integers.")
            return
        if row_start < 0 or row_end > total_rows or row_start >= row_end:
            QMessageBox.warning(
                self, "Invalid Row Range",
                f"Row range must satisfy: 0 ≤ Start Row < End Row ≤ {total_rows}.\n"
                f"Entered: {row_start} – {row_end}"
            )
            return
        subset_df = source_ds.df.iloc[row_start:row_end]
        using_full_range = (row_start == 0 and row_end == total_rows)

        # 5. Run FFT via core module
        try:
            fft_df = FFTAnalyzer.compute(subset_df, signal_cols, sample_rate, unit)
            metadata = FFTAnalyzer.build_metadata(source_ds, signal_cols, sample_rate, unit)
            metadata["row_start"] = row_start
            metadata["row_end"] = row_end
        except Exception as e:
            QMessageBox.critical(self, "FFT Error", f"FFT computation failed:\n{str(e)}")
            return

        # 6. Store result as a new 'fft' dataset in DataManager
        cols_label = ", ".join(signal_cols)
        if using_full_range:
            result_name = f"{source_ds.name} — FFT [{cols_label}]"
        else:
            result_name = f"{source_ds.name} — FFT [{cols_label}] rows {row_start}–{row_end}"
        self.new_dataset_id = self.data_manager.add_dataset(
            name=result_name,
            dataframe=fft_df,
            metadata=metadata,
            dataset_type="fft",
            parent_id=source_ds.id
        )


        self.accept()
