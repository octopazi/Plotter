import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QListWidget, QGroupBox,
    QFormLayout, QMessageBox
)


class CreateImportFormatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Import Format")
        self.resize(550, 700)

        main_layout = QVBoxLayout(self)

        # ----------------------------------------------------
        # 1. Format Name
        # ----------------------------------------------------
        box_format = QGroupBox("Format Name")
        layout_format = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("A unique name for this import format (e.g., 'EngineRuntime_v1'). Used as the filename.")
        layout_format.addRow("Name:", self.name_edit)
        box_format.setLayout(layout_format)
        main_layout.addWidget(box_format)

        # ----------------------------------------------------
        # 2. Header Settings
        # ----------------------------------------------------
        box_header = QGroupBox("Header Settings")
        layout_header = QFormLayout()

        self.header_enabled = QComboBox()
        self.header_enabled.addItems(["False", "True"])
        self.header_enabled.setToolTip("Whether the file contains a metadata header section before the data block.")

        self.header_lines = QSpinBox()
        self.header_lines.setRange(0, 50)
        self.header_lines.setToolTip("The total number of rows at the top of the file that contain metadata or non-data text.")

        self.header_sep = QLineEdit(":")
        self.header_sep.setToolTip("The character used to separate labels from values in the header lines (e.g. ':' in 'Date: 2024-01-01').")

        self.header_same_as_data = QComboBox()
        self.header_same_as_data.addItems(["False", "True"])
        self.header_same_as_data.setToolTip("Set to True if the header rows use the same column separator as the data block.")

        self.header_ignore = QLineEdit("#")
        self.header_ignore.setToolTip("Ignore any lines in the header area that start with this specific character or string.")

        layout_header.addRow("Header Enabled:", self.header_enabled)
        layout_header.addRow("Header Lines:", self.header_lines)
        layout_header.addRow("Header Separator:", self.header_sep)
        layout_header.addRow("Header Same-As-Data:", self.header_same_as_data)
        layout_header.addRow("Header Ignore Prefix:", self.header_ignore)

        box_header.setLayout(layout_header)
        main_layout.addWidget(box_header)

        # ----------------------------------------------------
        # 3. Data Settings
        # ----------------------------------------------------
        box_data = QGroupBox("Data Settings")
        layout_data = QFormLayout()

        self.data_sep = QLineEdit(",")
        self.data_sep.setToolTip("The character separating data values (e.g., ',' for CSV, '\t' for tab-separated).")

        self.data_ignore = QLineEdit("//")
        self.data_ignore.setToolTip("Ignore any lines within the data block that start with this prefix.")

        self.data_header_lines = QSpinBox()
        self.data_header_lines.setRange(0, 10)
        self.data_header_lines.setToolTip("The number of labels/names rows immediately preceding the data values (usually 1 for CSV column headers).")

        layout_data.addRow("Data Separator:", self.data_sep)
        layout_data.addRow("Data Ignore Prefix:", self.data_ignore)
        layout_data.addRow("Data Header Lines:", self.data_header_lines)

        box_data.setLayout(layout_data)
        main_layout.addWidget(box_data)

        # ----------------------------------------------------
        # 4. Column Mapping (X & Y)
        # ----------------------------------------------------
        box_columns = QGroupBox("Column Mapping")
        col_layout = QVBoxLayout()

        # X mapping
        x_layout = QFormLayout()
        self.x_type = QComboBox()
        self.x_type.addItems(["column", "index"])
        self.x_type.setToolTip("'column' = use a specific data column for X-axis; 'index' = generate X-axis as row numbers (0, 1, 2, ...).")

        self.x_index = QSpinBox()
        self.x_index.setRange(0, 50)
        self.x_index.setToolTip("The zero-based column index to use for the X-axis (only used if X Type is 'column'). Ignored if X Type is 'index'.")

        x_layout.addRow("X Type:", self.x_type)
        x_layout.addRow("X Column Index:", self.x_index)
        col_layout.addLayout(x_layout)

        # Y mapping
        y_layout = QVBoxLayout()
        self.y_list = QListWidget()

        y_add_layout = QHBoxLayout()
        self.y_name_edit = QLineEdit()
        self.y_name_edit.setToolTip("The display name for the Y-axis source.")
        self.y_index_spin = QSpinBox()
        self.y_index_spin.setRange(0, 50)
        self.y_index_spin.setToolTip("The zero-based column index in the data file for this Y value.")

        btn_add_y = QPushButton("Add Y")
        btn_add_y.clicked.connect(self.add_y_column)

        btn_del_y = QPushButton("Delete Selected")
        btn_del_y.clicked.connect(self.delete_y_column)

        y_add_layout.addWidget(QLabel("Name:"))
        y_add_layout.addWidget(self.y_name_edit)
        y_add_layout.addWidget(QLabel("Index:"))
        y_add_layout.addWidget(self.y_index_spin)
        y_add_layout.addWidget(btn_add_y)
        y_add_layout.addWidget(btn_del_y)

        y_layout.addLayout(y_add_layout)
        y_layout.addWidget(QLabel("Y Columns:"))
        y_layout.addWidget(self.y_list)

        col_layout.addLayout(y_layout)
        box_columns.setLayout(col_layout)
        main_layout.addWidget(box_columns)

        # Internal storage
        self.y_columns = []
        self.conversions = []

        # ----------------------------------------------------
        # 5. Conversion Rules
        # ----------------------------------------------------
        box_conv = QGroupBox("Conversions")
        conv_layout = QVBoxLayout()

        self.conv_name = QLineEdit()
        self.conv_name.setToolTip("A name for this calculated column.")
        self.conv_formula = QLineEdit()
        self.conv_formula.setToolTip("Mathematical formula (e.g., 'col1 * 10 + 5'). Use 'col[i]' to reference column indices.")
        self.conv_output_index = QSpinBox()
        self.conv_output_index.setRange(0, 100)
        self.conv_output_index.setToolTip("The virtual column index assigned to the result of this calculation.")

        btn_add_conv = QPushButton("Add Rule")
        btn_del_conv = QPushButton("Delete Selected")

        # connect buttons
        btn_add_conv.clicked.connect(self.add_conversion_rule)
        btn_del_conv.clicked.connect(self.delete_conversion_rule)

        form_conv = QFormLayout()
        form_conv.addRow("Name:", self.conv_name)
        form_conv.addRow("Formula:", self.conv_formula)
        form_conv.addRow("Output Index:", self.conv_output_index)

        conv_layout.addLayout(form_conv)

        btn_conv_layout = QHBoxLayout()
        btn_conv_layout.addWidget(btn_add_conv)
        btn_conv_layout.addWidget(btn_del_conv)
        conv_layout.addLayout(btn_conv_layout)

        self.conv_list = QListWidget()
        conv_layout.addWidget(QLabel("Conversion Rules:"))
        conv_layout.addWidget(self.conv_list)

        box_conv.setLayout(conv_layout)
        main_layout.addWidget(box_conv)

        # ----------------------------------------------------
        # 6. Save Button
        # ----------------------------------------------------
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        main_layout.addWidget(save_btn)

    # ======================================================
    #  ADD Y COLUMN
    # ======================================================
    def add_y_column(self):
        name = self.y_name_edit.text().strip()
        index = self.y_index_spin.value()

        if not name:
            QMessageBox.warning(self, "Error", "Y column name cannot be empty.")
            return

        self.y_columns.append({"name": name, "index": index})
        self.y_list.addItem(f"{name} (index {index})")

        self.y_name_edit.clear()

    # ======================================================
    # DELETE Y COLUMN
    # ======================================================
    def delete_y_column(self):
        selected = self.y_list.currentRow()
        if selected >= 0:
            self.y_list.takeItem(selected)
            self.y_columns.pop(selected)
        else:
            QMessageBox.warning(self, "Error", "No Y column selected.")

    # ======================================================
    # ADD CONVERSION RULE
    # ======================================================
    def add_conversion_rule(self):
        name = self.conv_name.text().strip()
        formula = self.conv_formula.text().strip()
        idx = self.conv_output_index.value()

        if not name or not formula:
            QMessageBox.warning(self, "Error", "Conversion name and formula required.")
            return

        conv = {
            "name": name,
            "formula": formula,
            "output_index": idx
        }

        self.conversions.append(conv)
        self.conv_list.addItem(f"{name}: {formula} -> col {idx}")

        # Clear fields
        self.conv_name.clear()
        self.conv_formula.clear()

    # ======================================================
    # DELETE CONVERSION RULE
    # ======================================================
    def delete_conversion_rule(self):
        selected = self.conv_list.currentRow()
        if selected >= 0:
            self.conv_list.takeItem(selected)
            self.conversions.pop(selected)
        else:
            QMessageBox.warning(self, "Error", "No conversion rule selected.")

    # ======================================================
    # SAVE CONFIG FILE
    # ======================================================
    def save_config(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Format Name cannot be empty.")
            return

        config = {
            "name": name,
            "header": {
                "enabled": self.header_enabled.currentText() == "True",
                "lines": self.header_lines.value(),
                "separator": self.header_sep.text(),
                "same_as_data": self.header_same_as_data.currentText() == "True",
                "ignore_prefix": self.header_ignore.text(),
                "fields": [],
                "column_names_from_header": False
            },
            "data": {
                "separator": self.data_sep.text(),
                "ignore_prefix": self.data_ignore.text(),
                "header_lines": self.data_header_lines.value(),
                "columns": {
                    "x": {
                        "type": self.x_type.currentText(),
                        "index": self.x_index.value()
                    },
                    "y": self.y_columns
                }
            },
            "conversions": self.conversions
        }

        # Save to ./Config/
        config_dir = os.path.join(os.getcwd(), "Config")
        os.makedirs(config_dir, exist_ok=True)

        save_path = os.path.join(config_dir, f"{name}.json")

        with open(save_path, "w") as f:
            json.dump(config, f, indent=4)

        QMessageBox.information(self, "Saved", f"Saved to: {save_path}")
        self.accept()  # Close dialog

class EditImportFormatDialog(CreateImportFormatDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Import Format")
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{e}")
            self.reject()
            return

        # 1. Format Name
        self.name_edit.setText(config.get("name", ""))

        # 2. Header Settings
        header = config.get("header", {})
        self.header_enabled.setCurrentText("True" if header.get("enabled", False) else "False")
        self.header_lines.setValue(header.get("lines", 0))
        self.header_sep.setText(header.get("separator", ""))
        self.header_same_as_data.setCurrentText("True" if header.get("same_as_data", False) else "False")
        self.header_ignore.setText(header.get("ignore_prefix", ""))

        # 3. Data Settings
        data = config.get("data", {})
        self.data_sep.setText(data.get("separator", ","))
        self.data_ignore.setText(data.get("ignore_prefix", "//"))
        self.data_header_lines.setValue(data.get("header_lines", 0))

        # 4. Column Mapping
        columns = data.get("columns", {})
        x_col = columns.get("x", {})
        self.x_type.setCurrentText(x_col.get("type", "column"))
        self.x_index.setValue(x_col.get("index", 0))

        self.y_columns = []
        self.y_list.clear()
        for y_col in columns.get("y", []):
            name = y_col.get("name", "")
            index = y_col.get("index", 0)
            self.y_columns.append({"name": name, "index": index})
            self.y_list.addItem(f"{name} (index {index})")

        # 5. Conversion Rules
        self.conversions = []
        self.conv_list.clear()
        for conv in config.get("conversions", []):
            name = conv.get("name", "")
            formula = conv.get("formula", "")
            idx = conv.get("output_index", 0)
            self.conversions.append({"name": name, "formula": formula, "output_index": idx})
            self.conv_list.addItem(f"{name}: {formula} -> col {idx}")