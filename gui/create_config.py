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
        self._build_tab_plot_config()

        # ── Save / Close Buttons ───────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        close_btn = QPushButton("Close")
        save_btn.clicked.connect(self.save_config)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(close_btn)
        root_layout.addLayout(btn_row)

        # Internal storage
        self.y_columns = []
        self.conversions = []
        self.plot_figures = []
        self._y_editing_row = None
        self._conv_editing_row = None
        self._plot_editing_row = None
        self._saved_state = self._collect_config_state()

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
        self.btn_add_y = QPushButton("Add Y")
        self.btn_add_y.clicked.connect(self.add_y_column)
        self.btn_cancel_y = QPushButton("Cancel")
        self.btn_cancel_y.setVisible(False)
        self.btn_cancel_y.clicked.connect(self._cancel_edit_y)
        btn_del_y = QPushButton("Delete Selected")
        btn_del_y.clicked.connect(self.delete_y_column)

        y_add_row.addWidget(QLabel("Name:"))
        y_add_row.addWidget(self.y_name_edit)
        y_add_row.addWidget(QLabel("Index:"))
        y_add_row.addWidget(self.y_index_spin)
        y_add_row.addWidget(self.btn_add_y)
        y_add_row.addWidget(self.btn_cancel_y)
        y_add_row.addWidget(btn_del_y)
        ly.addLayout(y_add_row)

        self.y_list = QListWidget()
        self.y_list.itemDoubleClicked.connect(self._start_edit_y_column)
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
        self.btn_add_conv = QPushButton("Add Rule")
        self.btn_add_conv.setToolTip("Append this conversion step to the list.")
        self.btn_cancel_conv = QPushButton("Cancel")
        self.btn_cancel_conv.setToolTip("Exit edit mode without applying changes.")
        self.btn_cancel_conv.setVisible(False)
        btn_del = QPushButton("Delete Selected")
        btn_del.setToolTip("Remove the selected step.")
        btn_up = QPushButton("▲ Move Up")
        btn_up.setToolTip("Move earlier (order matters for chaining).")
        btn_down = QPushButton("▼ Move Down")
        btn_down.setToolTip("Move later.")
        self.btn_add_conv.clicked.connect(self.add_conversion_rule)
        self.btn_cancel_conv.clicked.connect(self._cancel_edit_conv)
        btn_del.clicked.connect(self.delete_conversion_rule)
        btn_up.clicked.connect(self.move_conversion_up)
        btn_down.clicked.connect(self.move_conversion_down)
        btn_row.addWidget(self.btn_add_conv)
        btn_row.addWidget(self.btn_cancel_conv)
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
        self.conv_list.itemDoubleClicked.connect(self._start_edit_conv_rule)
        layout.addWidget(self.conv_list)

        self.tabs.addTab(page, "Conversions")

    # ==============================================================
    #  TAB 4 — Plot Config  (Auto plot after import)
    # ==============================================================
    def _build_tab_plot_config(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        box_auto = QGroupBox("Auto Plot")
        la = QVBoxLayout()
        self.plot_auto_enabled = QCheckBox("Enable auto plot after import")
        self.plot_auto_enabled.setToolTip(
            "If enabled, the app creates plots immediately after importing datalog files using this config."
        )
        la.addWidget(self.plot_auto_enabled)

        warn_label = QLabel(
            "Warning: Auto plot runs for every imported file.\n"
            "Large multi-file imports can open many plot windows."
        )
        warn_label.setWordWrap(True)
        warn_label.setStyleSheet("color: #b35a00;")
        la.addWidget(warn_label)
        box_auto.setLayout(la)
        layout.addWidget(box_auto)

        box_fig = QGroupBox("Figure Definitions")
        lf = QVBoxLayout()

        figure_form = QFormLayout()
        self.plot_title_edit = QLineEdit()
        self.plot_title_edit.setPlaceholderText("Optional title")
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["scatter", "line_scatter"])
        self.plot_x_edit = QLineEdit()
        self.plot_x_edit.setPlaceholderText("X column name")
        self.plot_y_edit = QLineEdit()
        self.plot_y_edit.setPlaceholderText("Y columns (comma separated)")

        figure_form.addRow("Title:", self.plot_title_edit)
        figure_form.addRow("Type:", self.plot_type_combo)
        figure_form.addRow("X Column:", self.plot_x_edit)
        figure_form.addRow("Y Columns:", self.plot_y_edit)
        lf.addLayout(figure_form)

        figure_btn_row = QHBoxLayout()
        self.btn_add_plot_figure = QPushButton("Add Figure")
        self.btn_add_plot_figure.clicked.connect(self.add_plot_figure)
        self.btn_cancel_plot_figure = QPushButton("Cancel")
        self.btn_cancel_plot_figure.setVisible(False)
        self.btn_cancel_plot_figure.clicked.connect(self._cancel_edit_plot_figure)
        btn_del_figure = QPushButton("Delete Selected")
        btn_del_figure.clicked.connect(self.delete_plot_figure)
        figure_btn_row.addWidget(self.btn_add_plot_figure)
        figure_btn_row.addWidget(self.btn_cancel_plot_figure)
        figure_btn_row.addWidget(btn_del_figure)
        figure_btn_row.addStretch()
        lf.addLayout(figure_btn_row)

        self.plot_figure_list = QListWidget()
        self.plot_figure_list.itemDoubleClicked.connect(self._start_edit_plot_figure)
        lf.addWidget(self.plot_figure_list)
        box_fig.setLayout(lf)
        layout.addWidget(box_fig)

        self.tabs.addTab(page, "Plot Config")

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
    def _start_edit_y_column(self, item):
        row = self.y_list.row(item)
        if row < 0 or row >= len(self.y_columns):
            return

        yc = self.y_columns[row]
        self.y_name_edit.setText(yc.get("name", ""))
        self.y_index_spin.setValue(yc.get("index", 0))

        self._y_editing_row = row
        self.btn_add_y.setText("Update Y")
        self.btn_cancel_y.setVisible(True)

    def _cancel_edit_y(self):
        self._y_editing_row = None
        self.y_name_edit.clear()
        self.btn_add_y.setText("Add Y")
        self.btn_cancel_y.setVisible(False)

    def _reset_y_form(self):
        self._cancel_edit_y()

    def add_y_column(self):
        name = self.y_name_edit.text().strip()
        index = self.y_index_spin.value()
        if not name:
            QMessageBox.warning(self, "Error", "Y column name cannot be empty.")
            return

        if self._y_editing_row is None:
            self.y_columns.append({"name": name, "index": index})
            self.y_list.addItem(f"{name} (index {index})")
            self.y_name_edit.clear()
            return

        row = self._y_editing_row
        if row < 0 or row >= len(self.y_columns):
            QMessageBox.warning(self, "Error", "Selected Y column is out of range.")
            self._cancel_edit_y()
            return

        self.y_columns[row] = {"name": name, "index": index}
        item = self.y_list.item(row)
        if item is not None:
            item.setText(f"{name} (index {index})")
        self._reset_y_form()

    def delete_y_column(self):
        selected = self.y_list.currentRow()
        if selected >= 0:
            if self._y_editing_row is not None:
                if self._y_editing_row == selected:
                    self._cancel_edit_y()
                elif self._y_editing_row > selected:
                    self._y_editing_row -= 1
            self.y_list.takeItem(selected)
            self.y_columns.pop(selected)
        else:
            QMessageBox.warning(self, "Error", "No Y column selected.")

    # ==============================================================
    #  Conversion Rule Helpers
    # ==============================================================
    def _load_conv_into_form(self, conv):
        output_name = str(conv.get("name", ""))
        conv_type = str(conv.get("type", "expr"))

        self.conv_name.setText(output_name)

        idx = self.conv_type_combo.findText(conv_type)
        if idx < 0:
            idx = self.conv_type_combo.findText("expr")
        if idx >= 0:
            self.conv_type_combo.setCurrentIndex(idx)

        specs = CONV_FIELD_SPECS.get(self.conv_type_combo.currentText(), [])
        for spec in specs:
            key = spec["key"]
            if key not in conv:
                continue
            value = conv.get(key)
            w = self._conv_widgets.get(key)
            if w is None:
                continue

            if key == "map" and isinstance(w, QTextEdit):
                map_dict = value if isinstance(value, dict) else {}
                lines = [f"{k}={v}" for k, v in map_dict.items()]
                w.setPlainText("\n".join(lines))
            elif isinstance(w, QLineEdit):
                w.setText(str(value))
            elif isinstance(w, QSpinBox):
                try:
                    w.setValue(int(value))
                except Exception:
                    pass
            elif isinstance(w, QDoubleSpinBox):
                try:
                    w.setValue(float(value))
                except Exception:
                    pass
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            elif isinstance(w, QComboBox):
                value_str = str(value)
                w_idx = w.findText(value_str)
                if w_idx >= 0:
                    w.setCurrentIndex(w_idx)
            elif isinstance(w, QTextEdit):
                w.setPlainText(str(value))

    def _start_edit_conv_rule(self, item):
        row = self.conv_list.row(item)
        if row < 0 or row >= len(self.conversions):
            return

        self._load_conv_into_form(self.conversions[row])
        self._conv_editing_row = row
        self.btn_add_conv.setText("Update Rule")
        self.btn_cancel_conv.setVisible(True)

    def _cancel_edit_conv(self):
        self._conv_editing_row = None
        self._reset_conv_widgets()
        self.btn_add_conv.setText("Add Rule")
        self.btn_cancel_conv.setVisible(False)

    def _reset_conv_form(self):
        self._cancel_edit_conv()

    def _build_conversion_from_form(self):
        output_name = self.conv_name.text().strip()
        conv_type = self.conv_type_combo.currentText()

        if not output_name:
            QMessageBox.warning(self, "Error", "Output Name cannot be empty.")
            return None

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
                return None

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
                        return None
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

        return conv

    def add_conversion_rule(self):
        conv = self._build_conversion_from_form()
        if conv is None:
            return

        summary = conv_summary(conv)
        output_name = conv.get("name", "")

        if self._conv_editing_row is None:
            self.conversions.append(conv)
            self.conv_list.addItem(f"[{len(self.conversions)}] {output_name}  ←  {summary}")
            self._reset_conv_widgets()
            return

        row = self._conv_editing_row
        if row < 0 or row >= len(self.conversions):
            QMessageBox.warning(self, "Error", "Selected conversion rule is out of range.")
            self._cancel_edit_conv()
            return

        self.conversions[row] = conv
        item = self.conv_list.item(row)
        if item is not None:
            item.setText(f"[{row + 1}] {output_name}  ←  {summary}")
        self._reset_conv_form()

    def delete_conversion_rule(self):
        selected = self.conv_list.currentRow()
        if selected >= 0:
            if self._conv_editing_row is not None:
                if self._conv_editing_row == selected:
                    self._cancel_edit_conv()
                elif self._conv_editing_row > selected:
                    self._conv_editing_row -= 1
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
    #  Plot Config Helpers
    # ==============================================================
    def _parse_y_columns(self, y_text):
        return [col.strip() for col in y_text.split(",") if col.strip()]

    def _plot_figure_summary(self, figure):
        fig_title = figure.get("title", "").strip()
        title_text = fig_title if fig_title else "(untitled)"
        y_text = ", ".join(figure.get("y_columns", []))
        return (
            f"{title_text} | {figure.get('plot_type', 'scatter')} | "
            f"x={figure.get('x_column', '')} | y={y_text}"
        )

    def _start_edit_plot_figure(self, item):
        row = self.plot_figure_list.row(item)
        if row < 0 or row >= len(self.plot_figures):
            return

        figure = self.plot_figures[row]
        self.plot_title_edit.setText(str(figure.get("title", "")))
        self.plot_type_combo.setCurrentText(str(figure.get("plot_type", "scatter")))
        self.plot_x_edit.setText(str(figure.get("x_column", "")))
        self.plot_y_edit.setText(", ".join(figure.get("y_columns", [])))

        self._plot_editing_row = row
        self.btn_add_plot_figure.setText("Update Figure")
        self.btn_cancel_plot_figure.setVisible(True)

    def _cancel_edit_plot_figure(self):
        self._plot_editing_row = None
        self.plot_title_edit.clear()
        self.plot_type_combo.setCurrentText("scatter")
        self.plot_x_edit.clear()
        self.plot_y_edit.clear()
        self.btn_add_plot_figure.setText("Add Figure")
        self.btn_cancel_plot_figure.setVisible(False)

    def _build_plot_figure_from_form(self):
        x_column = self.plot_x_edit.text().strip()
        y_columns = self._parse_y_columns(self.plot_y_edit.text().strip())
        if not x_column:
            QMessageBox.warning(self, "Error", "Plot figure X column cannot be empty.")
            return None
        if not y_columns:
            QMessageBox.warning(self, "Error", "Plot figure must include at least one Y column.")
            return None

        return {
            "title": self.plot_title_edit.text().strip(),
            "plot_type": self.plot_type_combo.currentText(),
            "x_column": x_column,
            "y_columns": y_columns,
        }

    def add_plot_figure(self):
        figure = self._build_plot_figure_from_form()
        if figure is None:
            return

        if self._plot_editing_row is None:
            self.plot_figures.append(figure)
            self.plot_figure_list.addItem(self._plot_figure_summary(figure))
            self._cancel_edit_plot_figure()
            return

        row = self._plot_editing_row
        if row < 0 or row >= len(self.plot_figures):
            QMessageBox.warning(self, "Error", "Selected plot figure is out of range.")
            self._cancel_edit_plot_figure()
            return

        self.plot_figures[row] = figure
        item = self.plot_figure_list.item(row)
        if item is not None:
            item.setText(self._plot_figure_summary(figure))
        self._cancel_edit_plot_figure()

    def delete_plot_figure(self):
        selected = self.plot_figure_list.currentRow()
        if selected >= 0:
            if self._plot_editing_row is not None:
                if self._plot_editing_row == selected:
                    self._cancel_edit_plot_figure()
                elif self._plot_editing_row > selected:
                    self._plot_editing_row -= 1
            self.plot_figure_list.takeItem(selected)
            self.plot_figures.pop(selected)
            return
        QMessageBox.warning(self, "Error", "No plot figure selected.")

    def _collect_config_state(self):
        """Build a normalized state payload for save and dirty-state checks."""
        return {
            "name": self.name_edit.text().strip(),
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
                    "y": list(self.y_columns),
                },
            },
            "conversions": list(self.conversions),
            "plot_config": {
                "enabled": self.plot_auto_enabled.isChecked(),
                "figures": list(self.plot_figures),
            },
        }

    def _mark_saved(self):
        self._saved_state = self._collect_config_state()

    def _has_unsaved_changes(self):
        return self._collect_config_state() != self._saved_state

    def closeEvent(self, event):
        if not self._has_unsaved_changes():
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Close without saving?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    # ==============================================================
    #  Save
    # ==============================================================
    def save_config(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Format Name cannot be empty.")
            return

        config = self._collect_config_state()

        config_dir = os.path.join(os.getcwd(), "Config")
        os.makedirs(config_dir, exist_ok=True)
        save_path = os.path.join(config_dir, f"{name}.json")

        current_path = getattr(self, "config_path", None)
        is_same_file = (
            current_path is not None
            and os.path.abspath(current_path) == os.path.abspath(save_path)
        )
        if os.path.exists(save_path) and not is_same_file:
            reply = QMessageBox.question(
                self,
                "Overwrite Config",
                f"A config named '{name}.json' already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        self.config_path = save_path
        self._mark_saved()
        QMessageBox.information(self, "Saved", f"Saved to: {save_path}")


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
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{e}")
            self.reject()
            return

        filename_stem = os.path.splitext(os.path.basename(self.config_path))[0]
        if config.get("name") != filename_stem:
            config["name"] = filename_stem

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

        # 6. Plot config
        plot_cfg = config.get("plot_config", {})
        self.plot_auto_enabled.setChecked(bool(plot_cfg.get("enabled", False)))
        self.plot_figures = []
        self.plot_figure_list.clear()
        for figure in plot_cfg.get("figures", []):
            raw_y_columns = figure.get("y_columns", [])
            if isinstance(raw_y_columns, str):
                y_columns = [col.strip() for col in raw_y_columns.split(",") if col.strip()]
            elif isinstance(raw_y_columns, list):
                y_columns = [str(col).strip() for col in raw_y_columns if str(col).strip()]
            else:
                y_columns = []

            normalized_figure = {
                "title": str(figure.get("title", "")).strip(),
                "plot_type": str(figure.get("plot_type", "scatter")),
                "x_column": str(figure.get("x_column", "")).strip(),
                "y_columns": y_columns,
            }
            self.plot_figures.append(normalized_figure)
            self.plot_figure_list.addItem(self._plot_figure_summary(normalized_figure))
        self._cancel_edit_plot_figure()

        self._mark_saved()

    def save_config(self):
        new_name = self.name_edit.text().strip()
        old_name = os.path.splitext(os.path.basename(self.config_path))[0]

        if not new_name:
            QMessageBox.warning(self, "Error", "Format Name cannot be empty.")
            return

        config_dir = os.path.dirname(self.config_path)
        new_path = os.path.join(config_dir, f"{new_name}.json")

        if new_name != old_name:
            if os.path.exists(new_path):
                reply = QMessageBox.question(
                    self,
                    "Overwrite Config",
                    f"A config named '{new_name}.json' already exists. Overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
                os.remove(new_path)

            if os.path.exists(self.config_path):
                os.remove(self.config_path)

            self.config_path = new_path

        super().save_config()