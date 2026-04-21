from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QPlainTextEdit,
)
from PyQt5.QtCore import Qt


class ColumnDetectionDialog(QDialog):
    def __init__(self, detected_columns, metadata=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detected Columns Preview")
        self.resize(760, 600)

        self.detected_columns = detected_columns or []
        self.metadata = metadata or {}

        self._build_ui()
        self._populate_metadata()
        self._populate_table()
        self._populate_axis_lists()

    def _build_ui(self):
        root = QVBoxLayout(self)

        meta_box = QGroupBox("Extracted Metadata")
        meta_layout = QVBoxLayout(meta_box)
        self.metadata_text = QPlainTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setPlaceholderText("No metadata extracted from header fields.")
        self.metadata_text.setFixedHeight(120)
        meta_layout.addWidget(self.metadata_text)
        root.addWidget(meta_box)

        table_box = QGroupBox("Detected Columns")
        table_layout = QVBoxLayout(table_box)
        self.columns_table = QTableWidget(0, 3)
        self.columns_table.setHorizontalHeaderLabels(["Index", "Detected Name", "Display Name"])
        self.columns_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.columns_table.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.columns_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        table_layout.addWidget(self.columns_table)
        root.addWidget(table_box)

        axis_box = QGroupBox("Axis Assignment")
        axis_layout = QHBoxLayout(axis_box)

        left = QVBoxLayout()
        left.addWidget(QLabel("X-Axis Column:"))
        self.x_combo = QComboBox()
        left.addWidget(self.x_combo)
        left.addWidget(QLabel("Leave as 'Use index' to generate row index x-axis."))

        right = QVBoxLayout()
        right.addWidget(QLabel("Y-Axis Columns (multi-select):"))
        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QAbstractItemView.MultiSelection)
        right.addWidget(self.y_list)

        axis_layout.addLayout(left, 1)
        axis_layout.addLayout(right, 1)
        root.addWidget(axis_box)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_apply)
        buttons.addWidget(btn_cancel)
        root.addLayout(buttons)

    def _populate_metadata(self):
        if not self.metadata:
            self.metadata_text.clear()
            return

        lines = [f"{k}: {v}" for k, v in self.metadata.items()]
        self.metadata_text.setPlainText("\n".join(lines))

    def _populate_table(self):
        self.columns_table.setRowCount(len(self.detected_columns))
        for idx, col_name in enumerate(self.detected_columns):
            item_idx = QTableWidgetItem(str(idx))
            item_idx.setFlags(item_idx.flags() & ~Qt.ItemIsEditable)

            item_detected = QTableWidgetItem(col_name)
            item_detected.setFlags(item_detected.flags() & ~Qt.ItemIsEditable)

            item_display = QTableWidgetItem(col_name)

            self.columns_table.setItem(idx, 0, item_idx)
            self.columns_table.setItem(idx, 1, item_detected)
            self.columns_table.setItem(idx, 2, item_display)

    def _populate_axis_lists(self):
        self.x_combo.addItem("Use index", None)
        for idx, col_name in enumerate(self.detected_columns):
            self.x_combo.addItem(f"{idx}: {col_name}", idx)

        for idx, col_name in enumerate(self.detected_columns):
            item = QListWidgetItem(f"{idx}: {col_name}")
            item.setData(Qt.UserRole, idx)
            if idx > 0:
                item.setSelected(True)
            self.y_list.addItem(item)

    def get_result(self):
        renamed_columns = []
        for idx in range(self.columns_table.rowCount()):
            display_item = self.columns_table.item(idx, 2)
            display_name = display_item.text().strip() if display_item else ""
            if not display_name:
                display_name = self.detected_columns[idx]
            renamed_columns.append(display_name)

        selected_x = self.x_combo.currentData()
        x_config = {
            "type": "index",
            "index": 0,
            "name": "x",
            "source_name": "",
        }
        if selected_x is not None:
            x_idx = int(selected_x)
            x_config = {
                "type": "column",
                "index": x_idx,
                "name": renamed_columns[x_idx],
                "source_name": self.detected_columns[x_idx],
            }

        y_config = []
        selected_items = self.y_list.selectedItems()
        for item in selected_items:
            idx = item.data(Qt.UserRole)
            idx_int = int(idx)
            y_config.append(
                {
                    "name": renamed_columns[idx_int],
                    "index": idx_int,
                    "source_name": self.detected_columns[idx_int],
                }
            )

        return {
            "x": x_config,
            "y": y_config,
            "display_names": renamed_columns,
        }
