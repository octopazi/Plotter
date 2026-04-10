import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QListWidget, QGroupBox,
    QFormLayout, QMessageBox, QWidget, QDoubleSpinBox,
    QCheckBox, QTextEdit, QTabWidget
)
from PyQt5.QtCore import Qt

from core.conversion_handlers import CONV_FIELD_SPECS, conv_summary


class CreateImportFormatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Import Format")
        self.resize(600, 650)

        root_layout = QVBoxLayout(self)

        # ── Format Name (always visible above tabs) ────────
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Format Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip(
            "A unique name for this import format (e.g., 'EngineRuntime_v1'). Used as the filename."
        )
        name_row.addWidget(self.name_edit)
        root_layout.addLayout(name_row)

        # ── Tab Widget ─────────────────────────────────────
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        self._build_tab_file_format()
        self._build_tab_columns()
        self._build_tab_conversions()

        # ── Save Button ────────────────────────────────────
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        root_layout.addWidget(save_btn)

        # Internal storage
        self.y_columns = []
        self.conversions = []

    # ==============================================================
    #  TAB 1 — File Format  (Header + Data settings)
    # ==============================================================
    def _build_tab_file_format(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Header Settings
        box_header = QGroupBox("Header Settings")
        lh = QFormLayout()

        self.header_enabled = QComboBox()
        self.header_enabled.addItems(["False", "True"])
        self.header_enabled.setToolTip("Whether the file contains a metadata header section before the data block.")

        self.header_lines = QSpinBox()
        self.header_lines.setRange(0, 50)
        self.header_lines.setToolTip("Total number of rows at the top that contain metadata or non-data text.")

        self.header_sep = QLineEdit(":")
        self.header_sep.setToolTip("Character separating labels from values in header lines (e.g. ':').")

        self.header_same_as_data = QComboBox()
        self.header_same_as_data.addItems(["False", "True"])
        self.header_same_as_data.setToolTip("True if header rows use the same separator as the data block.")

        self.header_ignore = QLineEdit("#")
        self.header_ignore.setToolTip("Ignore header lines starting with this character/string.")

        lh.addRow("Header Enabled:", self.header_enabled)
        lh.addRow("Header Lines:", self.header_lines)
        lh.addRow("Header Separator:", self.header_sep)
        lh.addRow("Same-As-Data:", self.header_same_as_data)
        lh.addRow("Ignore Prefix:", self.header_ignore)
        box_header.setLayout(lh)
        layout.addWidget(box_header)

        # Data Settings
        box_data = QGroupBox("Data Settings")
        ld = QFormLayout()

        self.data_sep = QLineEdit(",")
        self.data_sep.setToolTip("Character separating data values (e.g. ',' or '\\t').")

        self.data_ignore = QLineEdit("//")
        self.data_ignore.setToolTip("Ignore data lines starting with this prefix.")

        self.data_header_lines = QSpinBox()
        self.data_header_lines.setRange(0, 10)
        self.data_header_lines.setToolTip("Number of column-name rows preceding the data (usually 0 or 1).")

        ld.addRow("Data Separator:", self.data_sep)
        ld.addRow("Ignore Prefix:", self.data_ignore)
        ld.addRow("Data Header Lines:", self.data_header_lines)
        box_data.setLayout(ld)
        layout.addWidget(box_data)

        layout.addStretch()
        self.tabs.addTab(page, "File Format")

    # ==============================================================
    #  TAB 2 — Columns  (X + Y mapping)
    # ==============================================================
    def _build_tab_columns(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # X mapping
        box_x = QGroupBox("X-Axis Mapping")
        lx = QFormLayout()
        self.x_type = QComboBox()
        self.x_type.addItems(["column", "index"])
        self.x_type.setToolTip("'column' = use a data column;  'index' = row numbers (0, 1, 2, ...).")
        self.x_index = QSpinBox()
        self.x_index.setRange(0, 50)
        self.x_index.setToolTip("Zero-based column index for X (ignored if type is 'index').")
        lx.addRow("X Type:", self.x_type)
        lx.addRow("X Column Index:", self.x_index)
        box_x.setLayout(lx)
        layout.addWidget(box_x)

        # Y mapping
        box_y = QGroupBox("Y-Axis Columns")
        ly = QVBoxLayout()

        y_add_row = QHBoxLayout()
        self.y_name_edit = QLineEdit()
        self.y_name_edit.setToolTip("Display name for this Y column.")
        self.y_index_spin = QSpinBox()
        self.y_index_spin.setRange(0, 50)
        self.y_index_spin.setToolTip("Zero-based column index in the data file.")
        btn_add_y = QPushButton("Add Y")
        btn_add_y.clicked.connect(self.add_y_column)
        btn_del_y = QPushButton("Delete Selected")
        btn_del_y.clicked.connect(self.delete_y_column)

        y_add_row.addWidget(QLabel("Name:"))
        y_add_row.addWidget(self.y_name_edit)
        y_add_row.addWidget(QLabel("Index:"))
        y_add_row.addWidget(self.y_index_spin)
        y_add_row.addWidget(btn_add_y)
        y_add_row.addWidget(btn_del_y)
        ly.addLayout(y_add_row)

        self.y_list = QListWidget()
        ly.addWidget(self.y_list)
        box_y.setLayout(ly)
        layout.addWidget(box_y)

        self.tabs.addTab(page, "Columns")

    # ==============================================================
    #  TAB 3 — Conversions  (metadata-driven dynamic form)
    # ==============================================================
    def _build_tab_conversions(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # ── Name + Type selector row ───────────────────────
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Output Name:"))
        self.conv_name = QLineEdit()
        self.conv_name.setToolTip("Name of the new output column produced by this step.")
        self.conv_name.setMinimumWidth(120)
        top_row.addWidget(self.conv_name)
        top_row.addSpacing(10)
        top_row.addWidget(QLabel("Type:"))
        self.conv_type_combo = QComboBox()
        self.conv_type_combo.setToolTip("Select the conversion type.")
        # Populate from the registry — order follows CONV_FIELD_SPECS keys
        for type_name in CONV_FIELD_SPECS:
            self.conv_type_combo.addItem(type_name)
        self.conv_type_combo.currentTextChanged.connect(self._rebuild_conv_fields)
        top_row.addWidget(self.conv_type_combo)
        top_row.addStretch()
        layout.addLayout(top_row)

        # ── Dynamic fields area ────────────────────────────
        self._conv_fields_container = QWidget()
        self._conv_fields_layout = QFormLayout(self._conv_fields_container)
        self._conv_fields_layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._conv_fields_container)

        # Holds references to dynamically-created widgets keyed by field "key"
        self._conv_widgets = {}
        self._rebuild_conv_fields(self.conv_type_combo.currentText())

        # ── Buttons row ────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Rule")
        btn_add.setToolTip("Append this conversion step to the list.")
        btn_del = QPushButton("Delete Selected")
        btn_del.setToolTip("Remove the selected step.")
        btn_up = QPushButton("▲ Move Up")
        btn_up.setToolTip("Move earlier (order matters for chaining).")
        btn_down = QPushButton("▼ Move Down")
        btn_down.setToolTip("Move later.")
        btn_add.clicked.connect(self.add_conversion_rule)
        btn_del.clicked.connect(self.delete_conversion_rule)
        btn_up.clicked.connect(self.move_conversion_up)
        btn_down.clicked.connect(self.move_conversion_down)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_up)
        btn_row.addWidget(btn_down)
        layout.addLayout(btn_row)

        # ── Conversion list ────────────────────────────────
        layout.addWidget(QLabel(
            "⚠ Conversions run top-to-bottom. A step can reference columns from earlier steps."
        ))
        self.conv_list = QListWidget()
        layout.addWidget(self.conv_list)

        self.tabs.addTab(page, "Conversions")

    # ==============================================================
    #  Dynamic Field Builder — reads CONV_FIELD_SPECS at runtime
    # ==============================================================
    def _rebuild_conv_fields(self, conv_type):
        """Tear down and rebuild the dynamic field form for *conv_type*."""
        # Remove old widgets
        while self._conv_fields_layout.count():
            item = self._conv_fields_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._conv_widgets = {}
        specs = CONV_FIELD_SPECS.get(conv_type, [])

        for spec in specs:
            key     = spec["key"]
            label   = spec.get("label", key)
            wtype   = spec["widget"]
            tooltip = spec.get("tooltip", "")

            if wtype == "lineedit":
                w = QLineEdit()
                w.setPlaceholderText(spec.get("placeholder", ""))
                if "default" in spec:
                    w.setText(str(spec["default"]))

            elif wtype == "spinbox":
                w = QSpinBox()
                w.setRange(spec.get("min", 0), spec.get("max", 100))
                w.setSingleStep(spec.get("step", 1))
                w.setValue(spec.get("default", 0))

            elif wtype == "doublespinbox":
                w = QDoubleSpinBox()
                w.setRange(spec.get("min", 0), spec.get("max", 1e12))
                w.setDecimals(spec.get("decimals", 4))
                w.setSingleStep(spec.get("step", 1))
                w.setValue(spec.get("default", 0.0))

            elif wtype == "checkbox":
                w = QCheckBox(label)
                w.setChecked(spec.get("default", False))
                # For checkboxes the label is inside the widget; use empty label in form
                w.setToolTip(tooltip)
                self._conv_fields_layout.addRow("", w)
                self._conv_widgets[key] = w
                continue

            elif wtype == "combo":
                w = QComboBox()
                for item_text in spec.get("items", []):
                    w.addItem(item_text)
                default = spec.get("default", "")
                if default:
                    idx = w.findText(str(default))
                    if idx >= 0:
                        w.setCurrentIndex(idx)

            elif wtype == "textedit":
                w = QTextEdit()
                w.setPlaceholderText(spec.get("placeholder", ""))
                if spec.get("height"):
                    w.setFixedHeight(spec["height"])
                if "default" in spec:
                    w.setPlainText(str(spec["default"]))

            else:
                continue   # skip unknown widget types gracefully

            w.setToolTip(tooltip)
            self._conv_fields_layout.addRow(f"{label}:", w)
            self._conv_widgets[key] = w

    def _read_conv_widget_value(self, key):
        """Read the current value from a dynamically-created conversion widget."""
        w = self._conv_widgets.get(key)
        if w is None:
            return None
        if isinstance(w, QLineEdit):
            return w.text().strip()
        elif isinstance(w, QSpinBox):
            return w.value()
        elif isinstance(w, QDoubleSpinBox):
            return w.value()
        elif isinstance(w, QCheckBox):
            return w.isChecked()
        elif isinstance(w, QComboBox):
            return w.currentText()
        elif isinstance(w, QTextEdit):
            return w.toPlainText().strip()
        return None

    def _reset_conv_widgets(self):
        """Reset all dynamic conversion widgets to their spec defaults."""
        conv_type = self.conv_type_combo.currentText()
        specs = CONV_FIELD_SPECS.get(conv_type, [])
        for spec in specs:
            key = spec["key"]
            w = self._conv_widgets.get(key)
            if w is None:
                continue
            if isinstance(w, QLineEdit):
                w.clear()
            elif isinstance(w, QSpinBox):
                w.setValue(spec.get("default", 0))
            elif isinstance(w, QDoubleSpinBox):
                w.setValue(spec.get("default", 0.0))
            elif isinstance(w, QCheckBox):
                w.setChecked(spec.get("default", False))
            elif isinstance(w, QComboBox):
                default = spec.get("default", "")
                idx = w.findText(str(default))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif isinstance(w, QTextEdit):
                w.clear()
        self.conv_name.clear()

    # ==============================================================
    #  Y Column Helpers
    # ==============================================================
    def add_y_column(self):
        name = self.y_name_edit.text().strip()
        index = self.y_index_spin.value()
        if not name:
            QMessageBox.warning(self, "Error", "Y column name cannot be empty.")
            return
        self.y_columns.append({"name": name, "index": index})
        self.y_list.addItem(f"{name} (index {index})")
        self.y_name_edit.clear()

    def delete_y_column(self):
        selected = self.y_list.currentRow()
        if selected >= 0:
            self.y_list.takeItem(selected)
            self.y_columns.pop(selected)
        else:
            QMessageBox.warning(self, "Error", "No Y column selected.")

    # ==============================================================
    #  Conversion Rule Helpers
    # ==============================================================
    def add_conversion_rule(self):
        output_name = self.conv_name.text().strip()
        conv_type = self.conv_type_combo.currentText()

        if not output_name:
            QMessageBox.warning(self, "Error", "Output Name cannot be empty.")
            return

        specs = CONV_FIELD_SPECS.get(conv_type, [])
        conv = {"name": output_name, "type": conv_type}

        # Collect values from dynamic widgets
        for spec in specs:
            key = spec["key"]
            value = self._read_conv_widget_value(key)

            # Validate required fields
            if spec.get("required") and (value is None or value == ""):
                QMessageBox.warning(
                    self, "Error",
                    f"'{spec.get('label', key)}' is required for type '{conv_type}'."
                )
                return

            # Special handling for the lookup "map" field — parse key=value lines
            if key == "map" and conv_type == "lookup":
                map_dict = {}
                for line in (value or "").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if "=" not in line:
                        QMessageBox.warning(
                            self, "Error",
                            f"Invalid map line (expected 'key=value'):\n  {line}"
                        )
                        return
                    k, v = line.split("=", 1)
                    map_dict[k.strip()] = v.strip()
                conv[key] = map_dict
                continue

            # Skip falsy optional values so the JSON stays clean
            if value is None or value == "" or value is False:
                if spec.get("required"):
                    conv[key] = value
                continue

            conv[key] = value

        self.conversions.append(conv)
        summary = conv_summary(conv)
        self.conv_list.addItem(f"[{len(self.conversions)}] {output_name}  ←  {summary}")
        self._reset_conv_widgets()

    def delete_conversion_rule(self):
        selected = self.conv_list.currentRow()
        if selected >= 0:
            self.conv_list.takeItem(selected)
            self.conversions.pop(selected)
            self._refresh_conv_list_labels()
        else:
            QMessageBox.warning(self, "Error", "No conversion rule selected.")

    def move_conversion_up(self):
        row = self.conv_list.currentRow()
        if row <= 0:
            return
        self.conversions[row], self.conversions[row - 1] = (
            self.conversions[row - 1], self.conversions[row]
        )
        item = self.conv_list.takeItem(row)
        self.conv_list.insertItem(row - 1, item)
        self.conv_list.setCurrentRow(row - 1)
        self._refresh_conv_list_labels()

    def move_conversion_down(self):
        row = self.conv_list.currentRow()
        if row < 0 or row >= self.conv_list.count() - 1:
            return
        self.conversions[row], self.conversions[row + 1] = (
            self.conversions[row + 1], self.conversions[row]
        )
        item = self.conv_list.takeItem(row)
        self.conv_list.insertItem(row + 1, item)
        self.conv_list.setCurrentRow(row + 1)
        self._refresh_conv_list_labels()

    def _refresh_conv_list_labels(self):
        for i in range(self.conv_list.count()):
            item = self.conv_list.item(i)
            text = item.text()
            if text.startswith("["):
                text = text[text.index("]") + 1:].lstrip()
            item.setText(f"[{i + 1}] {text}")

    # ==============================================================
    #  Save
    # ==============================================================
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
                "column_names_from_header": False,
            },
            "data": {
                "separator": self.data_sep.text(),
                "ignore_prefix": self.data_ignore.text(),
                "header_lines": self.data_header_lines.value(),
                "columns": {
                    "x": {
                        "type": self.x_type.currentText(),
                        "index": self.x_index.value(),
                    },
                    "y": self.y_columns,
                },
            },
            "conversions": self.conversions,
        }

        config_dir = os.path.join(os.getcwd(), "Config")
        os.makedirs(config_dir, exist_ok=True)
        save_path = os.path.join(config_dir, f"{name}.json")

        with open(save_path, "w") as f:
            json.dump(config, f, indent=4)

        QMessageBox.information(self, "Saved", f"Saved to: {save_path}")
        self.accept()


# ==================================================================
#  Edit Dialog — inherits everything, just pre-fills from a config
# ==================================================================
class EditImportFormatDialog(CreateImportFormatDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Import Format")
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{e}")
            self.reject()
            return

        # 1. Format Name
        self.name_edit.setText(config.get("name", ""))

        # 2. Header
        h = config.get("header", {})
        self.header_enabled.setCurrentText("True" if h.get("enabled") else "False")
        self.header_lines.setValue(h.get("lines", 0))
        self.header_sep.setText(h.get("separator", ""))
        self.header_same_as_data.setCurrentText("True" if h.get("same_as_data") else "False")
        self.header_ignore.setText(h.get("ignore_prefix", ""))

        # 3. Data
        d = config.get("data", {})
        self.data_sep.setText(d.get("separator", ","))
        self.data_ignore.setText(d.get("ignore_prefix", "//"))
        self.data_header_lines.setValue(d.get("header_lines", 0))

        # 4. Columns
        cols = d.get("columns", {})
        xc = cols.get("x", {})
        self.x_type.setCurrentText(xc.get("type", "column"))
        self.x_index.setValue(xc.get("index", 0))

        self.y_columns = []
        self.y_list.clear()
        for yc in cols.get("y", []):
            n = yc.get("name", "")
            i = yc.get("index", 0)
            self.y_columns.append({"name": n, "index": i})
            self.y_list.addItem(f"{n} (index {i})")

        # 5. Conversions
        self.conversions = []
        self.conv_list.clear()
        for step_idx, c in enumerate(config.get("conversions", []), start=1):
            self.conversions.append(c)
            summary = conv_summary(c)
            self.conv_list.addItem(
                f"[{step_idx}] {c.get('name', '')}  ←  {summary}"
            )