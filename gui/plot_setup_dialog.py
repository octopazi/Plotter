from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton

class PlotSetupDialog(QDialog):
    def __init__(self, columns, plot_type="scatter", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Setup {plot_type.capitalize()} Plot")
        self.resize(300, 150)
        
        self.columns = columns
        self.plot_type = plot_type
        self.selected_x = None
        self.selected_y = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # X-Axis Selection
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("Select X-Axis:"))
        self.x_combo = QComboBox()
        self.x_combo.addItems(self.columns)
        x_layout.addWidget(self.x_combo)
        layout.addLayout(x_layout)
        
        # Y-Axis Selection
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Select Y-Axis:"))
        self.y_combo = QComboBox()
        self.y_combo.addItems(self.columns)
        y_layout.addWidget(self.y_combo)
        layout.addLayout(y_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.plot_btn = QPushButton("Plot")
        self.cancel_btn = QPushButton("Cancel")
        
        self.plot_btn.clicked.connect(self.accept_plot)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.plot_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
    def accept_plot(self):
        self.selected_x = self.x_combo.currentText()
        self.selected_y = self.y_combo.currentText()
        self.accept()
