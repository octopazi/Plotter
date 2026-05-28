from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QGroupBox,
    QVBoxLayout,
)

from core.app_settings import AppSettings
from core.script_manager import ScriptManager


class ScriptProcessDialog(QDialog):
    LAST_SCRIPT_KEY = "script_process/last_script"

    def __init__(self, data_manager, preferred_dataset_id=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.preferred_dataset_id = preferred_dataset_id
        self.created_dataset_ids = []
        self.selected_script = None

        self.setWindowTitle("Dataset Process")
        self.setMinimumWidth(540)
        self.setMinimumHeight(420)

        self._build_ui()
        self._populate_scripts()
        self._populate_datasets()

    def _build_ui(self):
        root = QVBoxLayout(self)

        script_group = QGroupBox("Script")
        script_layout = QVBoxLayout(script_group)

        script_row = QHBoxLayout()
        script_row.addWidget(QLabel("Dataset process script:"))
        self.script_combo = QComboBox()
        self.script_combo.currentIndexChanged.connect(self._on_script_changed)
        script_row.addWidget(self.script_combo)
        script_layout.addLayout(script_row)

        self.script_hint = QLabel("Choose a Python file from the Plugin folder.")
        self.script_hint.setWordWrap(True)
        self.script_hint.setStyleSheet("color: gray;")
        script_layout.addWidget(self.script_hint)
        root.addWidget(script_group)

        dataset_group = QGroupBox("Source Datasets")
        dataset_layout = QVBoxLayout(dataset_group)

        select_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_row.addWidget(self.select_all_btn)
        select_row.addWidget(self.deselect_all_btn)
        select_row.addStretch()
        dataset_layout.addLayout(select_row)

        self.dataset_list = QListWidget()
        self.dataset_list.setSelectionMode(QAbstractItemView.NoSelection)
        dataset_layout.addWidget(self.dataset_list)
        root.addWidget(dataset_group)

        self.status_label = QLabel("Select one or more datasets, then run the chosen script.")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.run_btn = QPushButton("Run Script")
        self.cancel_btn = QPushButton("Cancel")
        self.run_btn.clicked.connect(self._on_run)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.cancel_btn)
        root.addLayout(btn_row)

    def _populate_scripts(self):
        self.script_combo.clear()
        scripts = ScriptManager.get_available_scripts()

        if not scripts:
            self.script_combo.addItem("(No scripts found)", None)
            self.script_combo.setEnabled(False)
            self.run_btn.setEnabled(False)
            self.script_hint.setText("No Python scripts were found in the Plugin folder.")
            return

        self.script_combo.setEnabled(True)
        self.run_btn.setEnabled(True)
        for script in scripts:
            label = script["stem"]
            self.script_combo.addItem(label, script["filename"])

        AppSettings.restore_combo_selection(self.script_combo, self.LAST_SCRIPT_KEY)

    def _populate_datasets(self):
        self.dataset_list.clear()

        summaries = self.data_manager.get_all_summaries()
        for summary in summaries:
            label = f"{summary['name']}  [{summary['type']}]  ({summary['rows']} rows)"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if summary["id"] == self.preferred_dataset_id else Qt.Unchecked)
            item.setData(Qt.UserRole, summary["id"])
            self.dataset_list.addItem(item)

        if self.dataset_list.count() == 0:
            self.status_label.setText("No datasets are available.")
            self.run_btn.setEnabled(False)

    def _select_all(self):
        for index in range(self.dataset_list.count()):
            self.dataset_list.item(index).setCheckState(Qt.Checked)

    def _deselect_all(self):
        for index in range(self.dataset_list.count()):
            self.dataset_list.item(index).setCheckState(Qt.Unchecked)

    def _on_script_changed(self, index):
        script_filename = self.script_combo.itemData(index)
        if not script_filename:
            self.script_hint.setText("Choose a Python file from the Plugin folder.")
            return

        script_path = ScriptManager.get_script_path(script_filename)
        self.script_hint.setText(f"Selected: {script_filename}  |  {script_path}")

    def _selected_dataset_ids(self):
        result = []
        for index in range(self.dataset_list.count()):
            item = self.dataset_list.item(index)
            if item.checkState() == Qt.Checked:
                ds_id = item.data(Qt.UserRole)
                if ds_id:
                    result.append(ds_id)
        return result

    def _on_run(self):
        script_filename = self.script_combo.currentData()
        if not script_filename:
            QMessageBox.warning(self, "No Script", "Please select a script first.")
            return

        selected_ids = self._selected_dataset_ids()
        if not selected_ids:
            QMessageBox.warning(self, "No Dataset", "Please select at least one dataset.")
            return

        self.created_dataset_ids = []
        errors = []

        for ds_id in selected_ids:
            source_ds = self.data_manager.get_dataset(ds_id)
            if source_ds is None:
                errors.append(f"Dataset {ds_id}: not found")
                continue

            try:
                processed_ds = ScriptManager.run_script(
                    script_filename,
                    source_ds,
                    context={
                        "selected_dataset_ids": selected_ids,
                        "source_dataset_id": source_ds.id,
                        "source_dataset_name": source_ds.name,
                    },
                )
                self.data_manager.register_dataset(processed_ds)
                self.created_dataset_ids.append(processed_ds.id)
            except Exception as exc:
                errors.append(f"[{source_ds.name}] {exc}")

        if errors:
            QMessageBox.warning(
                self,
                "Script Warnings",
                "Some datasets could not be processed:\n\n" + "\n".join(errors),
            )

        if not self.created_dataset_ids:
            return

        AppSettings.save_combo_selection(self.script_combo, self.LAST_SCRIPT_KEY)
        self.selected_script = script_filename
        self.accept()
