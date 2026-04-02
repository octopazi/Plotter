import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from core.config_manager import ConfigManager

class ImportDatalogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Datalog")
        self.resize(500, 150)
        
        self.selected_config = None
        self.selected_file = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Config Selection
        config_layout = QHBoxLayout()
        config_label = QLabel("Configuration File:")
        self.config_combo = QComboBox()
        self.populate_configs()
        config_layout.addWidget(config_label)
        config_layout.addWidget(self.config_combo)
        layout.addLayout(config_layout)
        
        # File Selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Datalog File:")
        self.file_line_edit = QLineEdit()
        self.file_line_edit.setReadOnly(True)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_line_edit)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.cancel_btn = QPushButton("Cancel")
        
        self.import_btn.clicked.connect(self.accept_import)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
    def populate_configs(self):
        configs = ConfigManager.get_available_configs()
        if configs:
            self.config_combo.addItems(configs)
        else:
            self.config_combo.addItem("No configs found")
            self.config_combo.setEnabled(False)
            
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Datalog File", "", "All Files (*.*);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        if file_path:
            self.file_line_edit.setText(file_path)
            
    def accept_import(self):
        config = self.config_combo.currentText()
        file_path = self.file_line_edit.text()
        
        if not self.config_combo.isEnabled() or not config:
            QMessageBox.warning(self, "Warning", "Please select a valid configuration file.")
            return
            
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a datalog file.")
            return
            
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Warning", "The selected file does not exist.")
            return
            
        self.selected_config = config
        self.selected_file = file_path
        self.accept()
