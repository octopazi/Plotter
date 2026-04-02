from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QCheckBox, QSpinBox, QPushButton, QTabWidget, QWidget,
    QListWidget, QGroupBox, QAbstractItemView
)
from PyQt5.QtCore import Qt

class PlotSettingsDialog(QDialog):
    """A tabbed dialog for managing plot analysis (Trendline, MA) and layer order."""
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Settings")
        self.resize(400, 350)
        
        # Store a copy of current settings
        # format: { 'trend_enabled': bool, 'trend_type': str, 'ma_enabled': bool, 'ma_window': int, 'layers': list }
        self.settings = current_settings.copy()
        
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
        
        # Add Tabs
        self.tabs.addTab(analysis_tab, "Analysis")
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

    def save_and_accept(self):
        self.settings['trend_enabled'] = self.trend_cb.isChecked()
        self.settings['trend_type'] = self.trend_type_combo.currentText()
        self.settings['ma_enabled'] = self.ma_cb.isChecked()
        self.settings['ma_window'] = self.ma_spin.value()
        self.settings['layers'] = [self.layer_list.item(i).text() for i in range(self.layer_list.count())]
        self.accept()
