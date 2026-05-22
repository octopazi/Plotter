from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QSpinBox, QPushButton, QTabWidget, QWidget,
    QListWidget, QGroupBox, QAbstractItemView, QFormLayout
)
from PyQt5.QtCore import Qt

class PlotSettingsDialog(QDialog):
    """A tabbed dialog for managing plot analysis (Trendline, MA) and layer order."""
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Settings")
        self.resize(460, 420)
        
        # Store a copy of current settings
        # format: { 'trend_enabled': bool, 'trend_type': str, 'ma_enabled': bool, 'ma_window': int, 'layers': list }
        self.settings = current_settings.copy()
        self.dataset_items = self.settings.get('dataset_items', [])
        if not isinstance(self.dataset_items, list):
            self.dataset_items = []

        if not isinstance(self.settings.get('manual_offset_deltas', {}), dict):
            self.settings['manual_offset_deltas'] = {}
        if not isinstance(self.settings.get('auto_offsets', {}), dict):
            self.settings['auto_offsets'] = {}
        if not isinstance(self.settings.get('alignment_ref', {}), dict):
            self.settings['alignment_ref'] = {}
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Analysis (Trendline & Moving Average)
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # Trendline Group
        trend_group = QGroupBox("Trendline")
        t_layout = QVBoxLayout(trend_group)
        self.trend_cb = QCheckBox("Enable Trendline")
        self.trend_cb.setChecked(self.settings.get('trend_enabled', False))
        
        t_inner = QHBoxLayout()
        t_inner.addWidget(QLabel("Type:"))
        self.trend_type_combo = QComboBox()
        self.trend_type_combo.addItems(["Linear", "Exponential", "Logarithmic", "Power"])
        self.trend_type_combo.setCurrentText(self.settings.get('trend_type', 'Linear'))
        t_inner.addWidget(self.trend_type_combo)
        
        t_layout.addWidget(self.trend_cb)
        t_layout.addLayout(t_inner)
        analysis_layout.addWidget(trend_group)
        
        # MA Group
        ma_group = QGroupBox("Moving Average")
        ma_layout = QVBoxLayout(ma_group)
        self.ma_cb = QCheckBox("Enable Moving Average")
        self.ma_cb.setChecked(self.settings.get('ma_enabled', False))
        
        ma_inner = QHBoxLayout()
        ma_inner.addWidget(QLabel("Window Size:"))
        self.ma_spin = QSpinBox()
        self.ma_spin.setRange(2, 1000)
        self.ma_spin.setValue(self.settings.get('ma_window', 10))
        ma_inner.addWidget(self.ma_spin)
        
        ma_layout.addWidget(self.ma_cb)
        ma_layout.addLayout(ma_inner)
        analysis_layout.addWidget(ma_group)
        
        analysis_layout.addStretch()
        
        # Tab 2: Layers
        layer_tab = QWidget()
        layer_layout = QVBoxLayout(layer_tab)
        layer_layout.addWidget(QLabel("Drag items or use buttons to reorder layers (Top = Front):"))
        
        self.layer_list = QListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layer_list.addItems(self.settings.get('layers', ["Moving Average", "Trendline", "Raw Data"]))
        layer_layout.addWidget(self.layer_list)
        
        btn_layout = QHBoxLayout()
        up_btn = QPushButton("Move Up")
        down_btn = QPushButton("Move Down")
        up_btn.clicked.connect(lambda: self.move_layer(-1))
        down_btn.clicked.connect(lambda: self.move_layer(1))
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        layer_layout.addLayout(btn_layout)
        
        # Tab 3: Secondary Axis
        secondary_tab = QWidget()
        sec_layout = QVBoxLayout(secondary_tab)
        sec_layout.addWidget(QLabel("Select Y-series to move to the Secondary Axis (Right):"))
        
        self.sec_list = QListWidget()
        self.sec_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        all_y = self.settings.get('y_cols', [])
        self.sec_list.addItems(all_y)
        
        # Pre-select based on current settings
        sec_y = self.settings.get('secondary_y', [])
        for i in range(self.sec_list.count()):
            item = self.sec_list.item(i)
            if item.text() in sec_y:
                item.setSelected(True)
        
        # Ensure selection is reflected in the UI immediately
        self.sec_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        sec_layout.addWidget(self.sec_list)
        sec_layout.addStretch()

        # Tab 4: Alignment
        alignment_tab = QWidget()
        align_layout = QVBoxLayout(alignment_tab)

        auto_group = QGroupBox("Auto Alignment")
        auto_layout = QVBoxLayout(auto_group)

        self.align_cb = QCheckBox("Enable Auto Alignment (scipy correlate)")
        self.align_cb.setChecked(self.settings.get('alignment_enabled', True))
        auto_layout.addWidget(self.align_cb)

        max_lag_row = QHBoxLayout()
        max_lag_row.addWidget(QLabel("Max Auto Lag (samples, 0 = unlimited):"))
        self.max_lag_spin = QSpinBox()
        self.max_lag_spin.setRange(0, 1000000)
        self.max_lag_spin.setValue(int(self.settings.get('max_auto_lag', 5000)))
        max_lag_row.addWidget(self.max_lag_spin)
        auto_layout.addLayout(max_lag_row)

        ref = self.settings.get('alignment_ref', {})
        ref_name = str(ref.get('dataset_name', '')).strip() or "(pending)"
        ref_y = str(ref.get('y_col', '')).strip() or "(first visible Y)"
        self.ref_label = QLabel(f"Reference: {ref_name} / {ref_y}")
        self.ref_label.setStyleSheet("color: gray;")
        auto_layout.addWidget(self.ref_label)

        align_layout.addWidget(auto_group)

        manual_group = QGroupBox("Manual Offset Delta (samples)")
        manual_form = QFormLayout(manual_group)
        self.offset_spins = {}

        manual_deltas = self.settings.get('manual_offset_deltas', {})
        auto_offsets = self.settings.get('auto_offsets', {})
        for idx, ds in enumerate(self.dataset_items):
            ds_id = ds.get('id')
            ds_name = str(ds.get('name', ds_id))
            if not ds_id:
                continue

            spin = QSpinBox()
            spin.setRange(-1000000, 1000000)
            spin.setValue(int(manual_deltas.get(ds_id, 0)))
            if idx == 0:
                spin.setValue(0)
                spin.setEnabled(False)

            auto_val = int(auto_offsets.get(ds_id, 0))
            label = f"{ds_name} (auto={auto_val:+d})"
            manual_form.addRow(label, spin)
            self.offset_spins[ds_id] = spin

        if not self.offset_spins:
            manual_form.addRow(QLabel("No datasets available"))

        align_layout.addWidget(manual_group)
        align_layout.addStretch()

        # Add Tabs
        self.tabs.addTab(analysis_tab, "Analysis")
        self.tabs.addTab(secondary_tab, "Secondary Axis")
        self.tabs.addTab(alignment_tab, "Alignment")
        self.tabs.addTab(layer_tab, "Layers")
        
        layout.addWidget(self.tabs)
        
        # Dialog Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.save_and_accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def move_layer(self, direction):
        curr = self.layer_list.currentRow()
        if curr == -1: return
        new = curr + direction
        if 0 <= new < self.layer_list.count():
            item = self.layer_list.takeItem(curr)
            self.layer_list.insertItem(new, item)
            self.layer_list.setCurrentRow(new)

    def _on_selection_changed(self):
        # This helper ensures the 'isSelected' state is stable
        pass

    def save_and_accept(self):
        self.settings['trend_enabled'] = self.trend_cb.isChecked()
        self.settings['trend_type'] = self.trend_type_combo.currentText()
        self.settings['ma_enabled'] = self.ma_cb.isChecked()
        self.settings['ma_window'] = self.ma_spin.value()
        self.settings['layers'] = [self.layer_list.item(i).text() for i in range(self.layer_list.count())]
        
        # Save Secondary Axis Tab
        selected_sec = [item.text() for item in self.sec_list.selectedItems()]
        self.settings['secondary_y'] = selected_sec

        # Save Alignment Tab
        self.settings['alignment_enabled'] = self.align_cb.isChecked()
        self.settings['max_auto_lag'] = self.max_lag_spin.value()

        manual_deltas = self.settings.get('manual_offset_deltas', {})
        if not isinstance(manual_deltas, dict):
            manual_deltas = {}
        for idx, ds in enumerate(self.dataset_items):
            ds_id = ds.get('id')
            if not ds_id or ds_id not in self.offset_spins:
                continue
            if idx == 0:
                manual_deltas[ds_id] = 0
            else:
                manual_deltas[ds_id] = int(self.offset_spins[ds_id].value())
        self.settings['manual_offset_deltas'] = manual_deltas
        
        self.accept()
