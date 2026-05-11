from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)


class DeleteDatasetsDialog(QDialog):
    """Dialog for selecting multiple datasets to delete."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setWindowTitle("Delete Datasets")
        self.resize(520, 380)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select one or more datasets to delete:"))

        self.dataset_list_widget = QListWidget()
        self.dataset_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.dataset_list_widget)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Delete Selected")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_dataset_list()

    def _populate_dataset_list(self):
        summaries = self.data_manager.get_all_summaries()
        for summary in summaries:
            label = f"{summary['name']} [{summary['type']}] ({summary['rows']} rows)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, summary["id"])
            self.dataset_list_widget.addItem(item)

    def selected_dataset_ids(self):
        return [
            item.data(Qt.UserRole)
            for item in self.dataset_list_widget.selectedItems()
            if item.data(Qt.UserRole)
        ]

    def accept(self):
        if not self.selected_dataset_ids():
            QMessageBox.warning(self, "No Selection", "Please select at least one dataset to delete.")
            return
        super().accept()
