import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QListWidget, QGroupBox,
    QFormLayout, QMessageBox, QWidget, QDoubleSpinBox,
    QCheckBox, QTextEdit, QTabWidget, QFileDialog,
    QRadioButton, QButtonGroup, QStackedWidget
)
from PyQt5.QtCore import Qt

from core.conversion_handlers import CONV_FIELD_SPECS, conv_summary
from core.header_detector import detect_columns_from_file
from core.downsampling import PACKAGE_REQUIREMENTS as DS_PACKAGE_REQUIREMENTS
from .column_detection_dialog import ColumnDetectionDialog


class CreateImportFormatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Import Format")
        self.resize(800, 650)

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

        # Internal storage
        self.y_columns = []
        self.conversions = []
        self.plot_figures = []
        self.postprocess_hidden_extra = []
        self.postprocess_deleted_extra = []
        self._y_editing_row = None
        self._conv_editing_row = None
        self.column_names_from_header = False
        self.x_source_name = ""
        self._plot_editing_row = None

        self._build_tab_file_format()
        self._build_tab_columns()
        self._build_tab_conversions()
        self._build_tab_plot_config()
        self._build_tab_downsampling()

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

        self.header_enabled = QCheckBox()
        self.header_enabled.setToolTip("Whether the file contains a metadata header section before the data block.")
        self.header_enabled.setChecked(False)
        self.header_enabled.stateChanged.connect(self._toggle_header_controls)

        self.header_lines = QSpinBox()
        self.header_lines.setRange(0, 50)
        self.header_lines.setToolTip("Total number of rows at the top that contain metadata or non-data text.")

        self.header_ignore = QLineEdit("#")
        self.header_ignore.setToolTip("Ignore header lines starting with this character/string.")

        lh.addRow("Header Enabled:", self.header_enabled)
        lh.addRow("Total Header Lines:", self.header_lines)
        lh.addRow("Ignore Prefix:", self.header_ignore)

        self.column_mode_group = QButtonGroup(self)
        self.column_mode_simple = QRadioButton("simple")
        self.column_mode_expert = QRadioButton("expert")
        self.column_mode_simple.setChecked(True)
        self.column_mode_simple.setToolTip("simple: split one header line.")
        self.column_mode_expert.setToolTip("expert: extract names with regex.")
        self.column_mode_group.addButton(self.column_mode_simple)
        self.column_mode_group.addButton(self.column_mode_expert)
        self.column_mode_simple.toggled.connect(self._toggle_column_source_mode)
        self.column_mode_expert.toggled.connect(self._toggle_column_source_mode)

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addWidget(self.column_mode_simple)
        mode_layout.addWidget(self.column_mode_expert)
        mode_layout.addStretch()

        self.simple_select_method = QComboBox()
        self.simple_select_method.addItems(["line_number", "marker"])
        self.simple_select_method.setToolTip("Choose a fixed header line number or the first line containing marker text.")
        self.simple_select_method.currentTextChanged.connect(self._toggle_simple_select_method)

        self.simple_column_line_number = QSpinBox()
        self.simple_column_line_number.setRange(1, 10000)
        self.simple_column_line_number.setValue(1)
        self.simple_column_line_number.setToolTip("1-based line number inside Total Header Lines.")

        self.simple_marker_text = QLineEdit()
        self.simple_marker_text.setToolTip("Find the first header line containing this text.")

        self.simple_separator = QLineEdit("")
        self.simple_separator.setToolTip("Header separator used for metadata and simple mode line split. Empty = use Data Separator.")

        self.expert_line_prefix = QLineEdit("")
        self.expert_line_prefix.setToolTip("Optional prefix filter before applying regex (e.g., %T).")

        self.expert_regex = QLineEdit("")
        self.expert_regex.setToolTip("Regex used to extract column names from header lines.")

        self.expert_name_group = QSpinBox()
        self.expert_name_group.setRange(1, 20)
        self.expert_name_group.setValue(1)
        self.expert_name_group.setToolTip("Required capture-group index for the column display name.")

        self.expert_index_group = QSpinBox()
        self.expert_index_group.setRange(0, 20)
        self.expert_index_group.setValue(0)
        self.expert_index_group.setSpecialValueText("None")
        self.expert_index_group.setToolTip("Optional capture-group index for numeric column order. 0 = none.")

        self._simple_mode_form = QFormLayout()
        self._simple_mode_form.setContentsMargins(0, 0, 0, 0)
        self._simple_mode_form.addRow("Header Select By:", self.simple_select_method)
        self._simple_mode_form.addRow("Header Line Number:", self.simple_column_line_number)
        self._simple_mode_form.addRow("Header Marker Text:", self.simple_marker_text)
        self._simple_mode_form.addRow("Header Separator:", self.simple_separator)
        self._simple_mode_widget = QWidget()
        self._simple_mode_widget.setLayout(self._simple_mode_form)

        self._expert_mode_form = QFormLayout()
        self._expert_mode_form.setContentsMargins(0, 0, 0, 0)
        self._expert_mode_form.addRow("Header Line Prefix:", self.expert_line_prefix)
        self._expert_mode_form.addRow("Header Regex:", self.expert_regex)
        self._expert_mode_form.addRow("Header Name Group:", self.expert_name_group)
        self._expert_mode_form.addRow("Header Index Group:", self.expert_index_group)
        self._expert_mode_widget = QWidget()
        self._expert_mode_widget.setLayout(self._expert_mode_form)

        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._simple_mode_widget)
        self._mode_stack.addWidget(self._expert_mode_widget)

        lh.addRow("Column Name Mode:", mode_widget)
        lh.addRow("", self._mode_stack)

        box_header.setLayout(lh)
        layout.addWidget(box_header)

        # Data Settings
        box_data = QGroupBox("Data Settings")
        ld = QFormLayout()

        self.data_sep = QLineEdit(",")
        self.data_sep.setToolTip("Character separating data values (e.g. ',' or '\\t').")

        self.data_ignore = QLineEdit("//")
        self.data_ignore.setToolTip("Ignore data lines starting with this prefix.")

        self.data_total_lines = QSpinBox()
        self.data_total_lines.setRange(0, 1000000)
        self.data_total_lines.setToolTip(
            "Maximum number of data rows to import after header skip. 0 means import all rows."
        )

        ld.addRow("Data Separator:", self.data_sep)
        ld.addRow("Ignore Prefix:", self.data_ignore)
        ld.addRow("Total Data Lines:", self.data_total_lines)
        box_data.setLayout(ld)
        layout.addWidget(box_data)

        self._toggle_column_source_mode()
        self._toggle_simple_select_method()
        self._toggle_header_controls()

        layout.addStretch()
        self.tabs.addTab(page, "File Format")

    # ==============================================================
    #  TAB 2 — Columns  (X + Y mapping)
    # ==============================================================
    def _build_tab_columns(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        detect_row = QHBoxLayout()
        self.btn_detect_columns = QPushButton("Detect from Sample File")
        self.btn_detect_columns.setToolTip(
            "Import one sample datalog and auto-fill X/Y columns from detected headers."
        )
        self.btn_detect_columns.clicked.connect(self.detect_columns_from_sample)
        self.detect_status = QLabel("No detection applied.")
        self.detect_status.setStyleSheet("color: #666;")
        detect_row.addWidget(self.btn_detect_columns)
        detect_row.addWidget(self.detect_status)
        detect_row.addStretch()
        layout.addLayout(detect_row)

        # X mapping
        box_x = QGroupBox("X-Axis Mapping")
        lx = QFormLayout()
        self.x_type = QComboBox()
        self.x_type.addItems(["column", "index"])
        self.x_type.setToolTip("'column' = use a data column;  'index' = row numbers (0, 1, 2, ...).")
        self.x_index = QSpinBox()
        self.x_index.setRange(0, 50)
        self.x_index.setToolTip("Zero-based column index for X (ignored if type is 'index').")
        self.x_type.currentTextChanged.connect(self._on_x_mapping_changed)
        self.x_index.valueChanged.connect(self._on_x_mapping_changed)
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
        self.y_hidden_check = QCheckBox("Hidden")
        self.y_hidden_check.setToolTip(
            "Keep this column in the imported table but hide it from plot selectors."
        )
        self.y_deleted_check = QCheckBox("Delete")
        self.y_deleted_check.setToolTip(
            "Delete this column after conversions complete."
        )
        self.y_deleted_check.toggled.connect(self._on_y_delete_toggled)
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
        y_add_row.addWidget(self.y_hidden_check)
        y_add_row.addWidget(self.y_deleted_check)
        y_add_row.addWidget(self.btn_add_y)
        y_add_row.addWidget(self.btn_cancel_y)
        y_add_row.addWidget(btn_del_y)
        ly.addLayout(y_add_row)

        self.y_list = QListWidget()
        self.y_list.itemDoubleClicked.connect(self._start_edit_y_column)
        ly.addWidget(self.y_list)

        self.postprocess_extra_label = QLabel("")
        self.postprocess_extra_label.setWordWrap(True)
        self.postprocess_extra_label.setStyleSheet("color: #666;")
        ly.addWidget(self.postprocess_extra_label)

        box_y.setLayout(ly)
        layout.addWidget(box_y)

        self.tabs.addTab(page, "Columns")
        self._refresh_postprocess_extra_label()

    def _build_header_config(self):
        expert_index_group = self.expert_index_group.value()
        return {
            "enabled": self.header_enabled.isChecked(),
            "lines": self.header_lines.value(),
            "ignore_prefix": self.header_ignore.text(),
            "fields": [],
            "column_name_mode": self._current_column_name_mode(),
            "simple_select_method": self.simple_select_method.currentText(),
            "simple_column_line_number": self.simple_column_line_number.value(),
            "simple_marker_text": self.simple_marker_text.text(),
            "simple_separator": self.simple_separator.text(),
            "expert_line_prefix": self.expert_line_prefix.text(),
            "expert_regex": self.expert_regex.text(),
            "expert_name_group": self.expert_name_group.value(),
            "expert_index_group": expert_index_group if expert_index_group > 0 else "",
        }

    def _build_data_config(self):
        return {
            "separator": self.data_sep.text(),
            "ignore_prefix": self.data_ignore.text(),
            "total_data_lines": self.data_total_lines.value(),
        }

    def _toggle_header_controls(self, _value=None):
        enabled = self.header_enabled.isChecked()
        is_simple = self._current_column_name_mode() == "simple"
        self.header_lines.setEnabled(enabled)
        self.header_ignore.setEnabled(enabled)
        self.column_mode_simple.setEnabled(enabled)
        self.column_mode_expert.setEnabled(enabled)
        self._mode_stack.setEnabled(enabled)
        self.simple_select_method.setEnabled(enabled and is_simple)
        self.simple_column_line_number.setEnabled(
            enabled and is_simple and self.simple_select_method.currentText() == "line_number"
        )
        self.simple_marker_text.setEnabled(
            enabled and is_simple and self.simple_select_method.currentText() == "marker"
        )
        self.simple_separator.setEnabled(enabled and is_simple)
        self.expert_line_prefix.setEnabled(enabled and not is_simple)
        self.expert_regex.setEnabled(enabled and not is_simple)
        self.expert_name_group.setEnabled(enabled and not is_simple)
        self.expert_index_group.setEnabled(enabled and not is_simple)

    def _set_form_row_visible(self, form_layout, widget, visible):
        label = form_layout.labelForField(widget) if form_layout is not None else None
        if label is not None:
            label.setVisible(visible)
        widget.setVisible(visible)

    def _current_column_name_mode(self):
        if self.column_mode_expert.isChecked():
            return "expert"
        return "simple"

    def _toggle_column_source_mode(self, _value=None):
        is_simple = self._current_column_name_mode() == "simple"
        if is_simple:
            self._mode_stack.setCurrentWidget(self._simple_mode_widget)
        else:
            self._mode_stack.setCurrentWidget(self._expert_mode_widget)
        self._toggle_simple_select_method()
        self._toggle_header_controls()

    def _toggle_simple_select_method(self, _value=None):
        if self._current_column_name_mode() != "simple":
            self._toggle_header_controls()
            return

        is_line_mode = self.simple_select_method.currentText() == "line_number"
        self._set_form_row_visible(self._simple_mode_form, self.simple_column_line_number, is_line_mode)
        self._set_form_row_visible(self._simple_mode_form, self.simple_marker_text, not is_line_mode)
        self._toggle_header_controls()

    def _on_x_mapping_changed(self, _value=None):
        # Manual X edits invalidate the previously detected source_name mapping.
        self.x_source_name = ""

    def _on_y_delete_toggled(self, checked):
        if checked:
            self.y_hidden_check.setChecked(False)
            self.y_hidden_check.setEnabled(False)
            return
        self.y_hidden_check.setEnabled(True)

    def _normalize_name_list(self, values):
        if isinstance(values, str):
            values = [v.strip() for v in values.split(",") if v.strip()]
        if not isinstance(values, list):
            return []

        names = []
        seen = set()
        for value in values or []:
            name = str(value).strip()
            if not name or name in seen:
                continue
            names.append(name)
            seen.add(name)
        return names

    def _format_y_item_text(self, y_col):
        text = f"{y_col.get('name', '')} (index {y_col.get('index', 0)})"
        if y_col.get("deleted", False):
            return f"{text} [delete]"
        if y_col.get("hidden", False):
            return f"{text} [hidden]"
        return text

    def _refresh_postprocess_extra_label(self):
        if not hasattr(self, "postprocess_extra_label"):
            return

        hidden = self._normalize_name_list(self.postprocess_hidden_extra)
        deleted = self._normalize_name_list(self.postprocess_deleted_extra)
        if not hidden and not deleted:
            self.postprocess_extra_label.setText("")
            return

        info = [
            "Additional post-process columns are preserved from config "
            "(not editable in this list):"
        ]
        if hidden:
            info.append(f"Hidden: {', '.join(hidden)}")
        if deleted:
            info.append(f"Deleted: {', '.join(deleted)}")
        self.postprocess_extra_label.setText("\n".join(info))

    def _build_postprocess_columns(self):
        y_names = {
            str(y_col.get("name", "")).strip()
            for y_col in self.y_columns
            if str(y_col.get("name", "")).strip()
        }
        hidden = [
            name for name in self._normalize_name_list(self.postprocess_hidden_extra)
            if name not in y_names
        ]
        deleted = [
            name for name in self._normalize_name_list(self.postprocess_deleted_extra)
            if name not in y_names
        ]

        for y_col in self.y_columns:
            name = str(y_col.get("name", "")).strip()
            if not name:
                continue
            if y_col.get("deleted", False):
                deleted.append(name)
            elif y_col.get("hidden", False):
                hidden.append(name)

        deleted = self._normalize_name_list(deleted)
        deleted_set = set(deleted)
        hidden = [name for name in self._normalize_name_list(hidden) if name not in deleted_set]

        return {
            "hidden": hidden,
            "deleted": deleted,
        }

    def detect_columns_from_sample(self):
        if self.y_columns:
            reply = QMessageBox.question(
                self,
                "Replace Existing Column Mapping",
                "Detected columns will replace your current Y-axis entries. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        sample_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sample Datalog",
            "",
            "All Files (*.*);;CSV Files (*.csv);;Text Files (*.txt)",
        )
        if not sample_path:
            return

        header_cfg = self._build_header_config()
        data_cfg = self._build_data_config()

        try:
            detection = detect_columns_from_file(sample_path, header_cfg, data_cfg)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Detection Failed",
                f"Unable to detect columns from the selected sample file.\n\n{str(exc)}",
            )
            return

        raw_columns = detection.get("raw_columns", [])
        if not raw_columns:
            QMessageBox.warning(
                self,
                "No Columns Detected",
                "No columns were detected. Check File Format settings (header lines, separator, ignore prefix).",
            )
            return

        preview = ColumnDetectionDialog(
            detected_columns=raw_columns,
            metadata=detection.get("metadata", {}),
            parent=self,
        )
        if preview.exec_() != QDialog.Accepted:
            return

        result = preview.get_result()
        x_cfg = result.get("x", {})
        y_cfg = result.get("y", [])

        if not y_cfg:
            QMessageBox.warning(self, "No Y Columns", "Please select at least one Y-axis column.")
            return

        self.y_columns = y_cfg
        self.y_list.clear()
        for yc in self.y_columns:
            self.y_list.addItem(self._format_y_item_text(yc))

        self.x_type.setCurrentText(x_cfg.get("type", "index"))
        self.x_index.setValue(int(x_cfg.get("index", 0)))
        self.x_source_name = x_cfg.get("source_name", "")

        self.column_names_from_header = bool(detection.get("column_names_from_header", False))
        self.detect_status.setText(f"Detected {len(raw_columns)} columns from sample.")
        self.detect_status.setStyleSheet("color: #0a7a0a;")

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
    #  TAB 5 — Downsampling
    # ==============================================================
    def _build_tab_downsampling(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)

        # ── Enable checkbox ────────────────────────────────
        self.ds_enable_cb = QCheckBox("Enable downsampling on import")
        self.ds_enable_cb.setToolTip(
            "When enabled, imported data is thinned using the selected algorithm "
            "before (or after) conversion formulas run.\n"
            "The dataset name will become  <filename>_downsampled_<method>."
        )
        layout.addWidget(self.ds_enable_cb)

        # ── Controls group ────────────────────────────────
        self.ds_controls_group = QGroupBox("Downsampling Settings")
        gl = QFormLayout()

        # Method combo – append "(not installed)" badge where needed
        self.ds_method_combo = QComboBox()
        _method_keys = ["decimation", "lttb", "dwt"]
        _method_labels = {
            "decimation": "Decimation (scipy.signal.decimate)",
            "lttb":       "LTTB - Largest Triangle Three Buckets (tsdownsample)",
            "dwt":        "DWT - Discrete Wavelet Transform (PyWavelets)",
        }
        for key in _method_keys:
            label = _method_labels[key]
            available = DS_PACKAGE_REQUIREMENTS[key][1]
            if not available:
                label += " (package not installed)"
            self.ds_method_combo.addItem(label, userData=key)
        gl.addRow("Algorithm:", self.ds_method_combo)

        # Timing combo
        self.ds_timing_combo = QComboBox()
        self.ds_timing_combo.addItem(
            "Before conversions (default - faster for large files)",
            userData="before_conversions",
        )
        self.ds_timing_combo.addItem(
            "After conversions (all derived columns included)",
            userData="after_conversions",
        )
        self.ds_timing_combo.setToolTip(
            "Before conversions: downsampling runs on raw columns first, then formulas\n"
            "evaluate on fewer rows - best for large files.\n\n"
            "After conversions: all derived columns exist before thinning - use when\n"
            "conversion outputs must be included in the downsampled result."
        )
        gl.addRow("Apply timing:", self.ds_timing_combo)

        self.ds_controls_group.setLayout(gl)
        layout.addWidget(self.ds_controls_group)

        # ── Parameter pages (QStackedWidget, one per method) ──
        params_label = QLabel("Method Parameters:")
        layout.addWidget(params_label)
        self.ds_stacked = QStackedWidget()

        # Page 0 – Decimation
        dec_page = QWidget()
        dec_form = QFormLayout(dec_page)
        self.ds_dec_factor = QSpinBox()
        self.ds_dec_factor.setRange(2, 10000)
        self.ds_dec_factor.setValue(10)
        self.ds_dec_factor.setToolTip(
            "Keep every Nth sample after anti-alias filtering.\n"
            "Example: factor=10 reduces 10 000 rows to 1 000 rows."
        )
        self.ds_dec_zero_phase = QCheckBox("Zero-phase filter (recommended)")
        self.ds_dec_zero_phase.setChecked(True)
        self.ds_dec_zero_phase.setToolTip(
            "Uses a forward-backward IIR filter that avoids phase distortion.\n"
            "Uncheck only if causal (one-pass) filtering is required."
        )
        dec_form.addRow("Factor:", self.ds_dec_factor)
        dec_form.addRow("", self.ds_dec_zero_phase)
        dec_note = QLabel(
            "Requires uniform x-axis spacing.\n"
            "Effective sample rate = original Hz / factor."
        )
        dec_note.setStyleSheet("color: #b35a00;")
        dec_note.setWordWrap(True)
        dec_form.addRow(dec_note)
        self.ds_stacked.addWidget(dec_page)

        # Page 1 – LTTB
        lttb_page = QWidget()
        lttb_form = QFormLayout(lttb_page)
        self.ds_lttb_n = QSpinBox()
        self.ds_lttb_n.setRange(2, 10_000_000)
        self.ds_lttb_n.setValue(5000)
        self.ds_lttb_n.setToolTip(
            "Target number of output samples.\n"
            "LTTB preserves the visual shape of the signal.\n"
            "First and last samples are always kept."
        )
        lttb_form.addRow("Target samples:", self.ds_lttb_n)
        lttb_note = QLabel("Works with non-uniform x-axis spacing.")
        lttb_note.setStyleSheet("color: #0a7a0a;")
        lttb_form.addRow(lttb_note)
        self.ds_stacked.addWidget(lttb_page)

        # Page 2 – DWT
        dwt_page = QWidget()
        dwt_form = QFormLayout(dwt_page)
        self.ds_dwt_wavelet = QLineEdit("db4")
        self.ds_dwt_wavelet.setToolTip(
            "PyWavelets wavelet name, e.g. db4, haar, sym8, coif2.\n"
            "Run pywt.wavelist() in Python to see all available names."
        )
        self.ds_dwt_level = QSpinBox()
        self.ds_dwt_level.setRange(1, 20)
        self.ds_dwt_level.setValue(3)
        self.ds_dwt_level.setToolTip(
            "Decomposition level. Higher = more aggressive reduction.\n"
            "Maximum level depends on signal length and wavelet."
        )
        self.ds_dwt_reconstruct = QCheckBox("Reconstruct to original length (smoothed)")
        self.ds_dwt_reconstruct.setChecked(False)
        self.ds_dwt_reconstruct.setToolTip(
            "Checked: output has the same number of rows as input, but smoothed.\n"
            "Unchecked: output is shorter - N / 2^level rows (approximation coefficients)."
        )
        dwt_form.addRow("Wavelet:", self.ds_dwt_wavelet)
        dwt_form.addRow("Level:", self.ds_dwt_level)
        dwt_form.addRow("", self.ds_dwt_reconstruct)
        dwt_note = QLabel("Requires uniform x-axis spacing.")
        dwt_note.setStyleSheet("color: #b35a00;")
        dwt_form.addRow(dwt_note)
        self.ds_stacked.addWidget(dwt_page)

        layout.addWidget(self.ds_stacked)
        layout.addStretch()
        self.tabs.addTab(page, "Downsampling")

        # ── Wire signals ──────────────────────────────────
        self.ds_enable_cb.stateChanged.connect(self._toggle_ds_controls)
        self.ds_method_combo.currentIndexChanged.connect(self._on_ds_method_changed)

        # Set initial state
        self._toggle_ds_controls()

    def _toggle_ds_controls(self):
        """Enable/disable all downsampling controls based on the enable checkbox."""
        enabled = self.ds_enable_cb.isChecked()
        self.ds_controls_group.setEnabled(enabled)
        self.ds_stacked.setEnabled(enabled)

    def _on_ds_method_changed(self, index):
        """Switch the parameter page to match the selected method."""
        self.ds_stacked.setCurrentIndex(index)

    def _collect_downsampling_config(self):
        """Read all downsampling tab widgets and return the config dict."""
        enabled = self.ds_enable_cb.isChecked()
        method_idx = self.ds_method_combo.currentIndex()
        method_key = self.ds_method_combo.itemData(method_idx) or "lttb"
        timing_key = self.ds_timing_combo.itemData(self.ds_timing_combo.currentIndex()) \
                     or "before_conversions"

        cfg = {
            "enabled": enabled,
            "method": method_key,
            "timing": timing_key,
        }

        # Only include the active method's parameters
        if method_key == "decimation":
            cfg["decimation"] = {
                "factor": self.ds_dec_factor.value(),
                "zero_phase": self.ds_dec_zero_phase.isChecked(),
            }
        elif method_key == "lttb":
            cfg["lttb"] = {
                "n_samples": self.ds_lttb_n.value(),
            }
        elif method_key == "dwt":
            cfg["dwt"] = {
                "wavelet": self.ds_dwt_wavelet.text().strip() or "db4",
                "level": self.ds_dwt_level.value(),
                "reconstruct": self.ds_dwt_reconstruct.isChecked(),
            }
        return cfg

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
        self.y_hidden_check.setChecked(bool(yc.get("hidden", False)))
        self.y_deleted_check.setChecked(bool(yc.get("deleted", False)))
        self._on_y_delete_toggled(self.y_deleted_check.isChecked())

        self._y_editing_row = row
        self.btn_add_y.setText("Update Y")
        self.btn_cancel_y.setVisible(True)

    def _cancel_edit_y(self):
        self._y_editing_row = None
        self.y_name_edit.clear()
        self.y_hidden_check.setChecked(False)
        self.y_deleted_check.setChecked(False)
        self._on_y_delete_toggled(False)
        self.btn_add_y.setText("Add Y")
        self.btn_cancel_y.setVisible(False)

    def _reset_y_form(self):
        self._cancel_edit_y()

    def add_y_column(self):
        name = self.y_name_edit.text().strip()
        index = self.y_index_spin.value()
        is_hidden = self.y_hidden_check.isChecked()
        is_deleted = self.y_deleted_check.isChecked()
        if not name:
            QMessageBox.warning(self, "Error", "Y column name cannot be empty.")
            return

        item_data = {
            "name": name,
            "index": index,
            "hidden": bool(is_hidden and not is_deleted),
            "deleted": bool(is_deleted),
        }

        if self._y_editing_row is None:
            self.y_columns.append(item_data)
            self.y_list.addItem(self._format_y_item_text(item_data))
            self._reset_y_form()
            return

        row = self._y_editing_row
        if row < 0 or row >= len(self.y_columns):
            QMessageBox.warning(self, "Error", "Selected Y column is out of range.")
            self._cancel_edit_y()
            return

        updated = item_data
        existing = self.y_columns[row]
        if existing.get("source_name") and existing.get("index") == index:
            updated["source_name"] = existing.get("source_name")
        self.y_columns[row] = updated
        item = self.y_list.item(row)
        if item is not None:
            item.setText(self._format_y_item_text(updated))
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
                **self._build_header_config(),
                "column_names_from_header": self.column_names_from_header,
            },
            "data": {
                **self._build_data_config(),
                "columns": {
                    "x": {
                        "type": self.x_type.currentText(),
                        "index": self.x_index.value(),
                        "source_name": self.x_source_name,
                    },
                    "y": [
                        {
                            key: value
                            for key, value in y_col.items()
                            if key in ("name", "index", "source_name")
                        }
                        for y_col in self.y_columns
                    ],
                },
            },
            "conversions": list(self.conversions),
            "plot_config": {
                "enabled": self.plot_auto_enabled.isChecked(),
                "figures": list(self.plot_figures),
            },
            "downsampling": self._collect_downsampling_config(),
            "postprocess_columns": self._build_postprocess_columns(),
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
        self.header_enabled.setChecked(bool(h.get("enabled")))
        self.header_lines.setValue(h.get("lines", 0))
        self.header_ignore.setText(h.get("ignore_prefix", ""))
        if h.get("column_name_mode", "simple") == "expert":
            self.column_mode_expert.setChecked(True)
        else:
            self.column_mode_simple.setChecked(True)
        self.simple_select_method.setCurrentText(h.get("simple_select_method", "line_number"))
        self.simple_column_line_number.setValue(int(h.get("simple_column_line_number", 1) or 1))
        self.simple_marker_text.setText(h.get("simple_marker_text", ""))
        self.simple_separator.setText(h.get("simple_separator", h.get("separator", "")))
        self.expert_line_prefix.setText(h.get("expert_line_prefix", ""))
        self.expert_regex.setText(h.get("expert_regex", ""))
        self.expert_name_group.setValue(int(h.get("expert_name_group", 1) or 1))
        expert_idx = h.get("expert_index_group", "")
        if expert_idx in (None, ""):
            self.expert_index_group.setValue(0)
        else:
            self.expert_index_group.setValue(int(expert_idx))
        self.column_names_from_header = h.get("column_names_from_header", False)
        self._toggle_column_source_mode()
        self._toggle_simple_select_method()
        self._toggle_header_controls()

        # 3. Data
        d = config.get("data", {})
        self.data_sep.setText(d.get("separator", ","))
        self.data_ignore.setText(d.get("ignore_prefix", "//"))
        self.data_total_lines.setValue(d.get("total_data_lines", 0))

        # 4. Columns
        cols = d.get("columns", {})
        post_cfg = config.get("postprocess_columns", {})
        hidden_names = self._normalize_name_list(post_cfg.get("hidden", []))
        deleted_names = self._normalize_name_list(post_cfg.get("deleted", []))
        hidden_set = set(hidden_names)
        deleted_set = set(deleted_names)
        xc = cols.get("x", {})
        self.x_type.setCurrentText(xc.get("type", "column"))
        self.x_index.setValue(xc.get("index", 0))
        self.x_source_name = xc.get("source_name", "")

        self.y_columns = []
        self.y_list.clear()
        mapped_names = []
        for yc in cols.get("y", []):
            n = yc.get("name", "")
            i = yc.get("index", 0)
            source_name = yc.get("source_name", "")
            is_deleted = n in deleted_set
            is_hidden = (n in hidden_set) and not is_deleted
            new_item = {
                "name": n,
                "index": i,
                "hidden": is_hidden,
                "deleted": is_deleted,
            }
            if source_name:
                new_item["source_name"] = source_name
            self.y_columns.append(new_item)
            self.y_list.addItem(self._format_y_item_text(new_item))
            mapped_names.append(n)

        mapped_set = set(mapped_names)
        self.postprocess_hidden_extra = [
            name for name in hidden_names
            if name not in mapped_set and name not in deleted_set
        ]
        self.postprocess_deleted_extra = [
            name for name in deleted_names
            if name not in mapped_set
        ]
        self._refresh_postprocess_extra_label()

        if self.column_names_from_header:
            self.detect_status.setText("Loaded detected-column mapping from config.")
            self.detect_status.setStyleSheet("color: #0a7a0a;")
        else:
            self.detect_status.setText("No detection applied.")
            self.detect_status.setStyleSheet("color: #666;")

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

        # 7. Downsampling
        ds = config.get("downsampling", {})
        self.ds_enable_cb.setChecked(bool(ds.get("enabled", False)))

        method = ds.get("method", "lttb")
        method_keys = [self.ds_method_combo.itemData(i)
                       for i in range(self.ds_method_combo.count())]
        if method in method_keys:
            self.ds_method_combo.setCurrentIndex(method_keys.index(method))

        timing = ds.get("timing", "before_conversions")
        timing_keys = [self.ds_timing_combo.itemData(i)
                       for i in range(self.ds_timing_combo.count())]
        if timing in timing_keys:
            self.ds_timing_combo.setCurrentIndex(timing_keys.index(timing))

        dec = ds.get("decimation", {})
        self.ds_dec_factor.setValue(int(dec.get("factor", 10)))
        self.ds_dec_zero_phase.setChecked(bool(dec.get("zero_phase", True)))

        lttb = ds.get("lttb", {})
        self.ds_lttb_n.setValue(int(lttb.get("n_samples", 5000)))

        dwt = ds.get("dwt", {})
        self.ds_dwt_wavelet.setText(str(dwt.get("wavelet", "db4")))
        self.ds_dwt_level.setValue(int(dwt.get("level", 3)))
        self.ds_dwt_reconstruct.setChecked(bool(dwt.get("reconstruct", False)))

        self._toggle_ds_controls()
        self._on_ds_method_changed(self.ds_method_combo.currentIndex())

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