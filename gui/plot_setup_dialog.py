from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QListWidget, QAbstractItemView

class PlotSetupDialog(QDialog):
    def __init__(self, columns, plot_type="scatter", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Setup {plot_type.capitalize()} Plot")
        self.resize(400, 300)
        
        self.columns = columns
        self.plot_type = plot_type
        self.selected_x = None
        self.selected_y_columns = []
        
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
        
        # Y-Axis Selection (Multi-select)
        layout.addWidget(QLabel("Select Y-Axis (Hold Ctrl to Multi-select):"))
        self.y_list_widget = QListWidget()
        self.y_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.y_list_widget.addItems([c for c in self.columns if c != self.x_combo.currentText()])
        layout.addWidget(self.y_list_widget)
        
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
        
        # Update Y options when X changes
        self.x_combo.currentTextChanged.connect(self.update_y_options)
        
    def update_y_options(self, current_x):
        # We don't want to plot X against itself
        self.y_list_widget.clear()
        self.y_list_widget.addItems([c for c in self.columns if c != current_x])
        
    def accept_plot(self):
        self.selected_x = self.x_combo.currentText()
        selected_items = self.y_list_widget.selectedItems()
        self.selected_y_columns = [item.text() for item in selected_items]
        
        # Fallback if nothing selected
        if not self.selected_y_columns:
            # Just use whatever is highlighted
            cur = self.y_list_widget.currentItem()
            if cur:
                self.selected_y_columns = [cur.text()]
                
        self.accept()
