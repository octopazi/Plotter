import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QListWidget, QAbstractItemView
)
from core.config_manager import ConfigManager

class ImportDatalogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Datalog")
        self.resize(500, 350)
        
        self.selected_config = None
        self.selected_files = []
        
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
        
        # File Selection Area
        layout.addWidget(QLabel("Datalog Files:"))
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.file_list_widget)
        
        file_btns = QHBoxLayout()
        self.add_btn = QPushButton("Add Files")
        self.remove_btn = QPushButton("Remove Selected")
        self.add_btn.clicked.connect(self.browse_files)
        self.remove_btn.clicked.connect(self.remove_files)
        
        file_btns.addWidget(self.add_btn)
        file_btns.addWidget(self.remove_btn)
        file_btns.addStretch()
        layout.addLayout(file_btns)
        
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
            
    def browse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Datalog Files", "", "All Files (*.*);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        if file_paths:
            for path in file_paths:
                # Avoid adding duplicates
                items = [self.file_list_widget.item(i).text() for i in range(self.file_list_widget.count())]
                if path not in items:
                    self.file_list_widget.addItem(path)

    def remove_files(self):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.file_list_widget.takeItem(self.file_list_widget.row(item))
            
    def accept_import(self):
        config = self.config_combo.currentText()
        file_count = self.file_list_widget.count()
        
        if not self.config_combo.isEnabled() or not config:
            QMessageBox.warning(self, "Warning", "Please select a valid configuration file.")
            return
            
        if file_count == 0:
            QMessageBox.warning(self, "Warning", "Please add at least one datalog file.")
            return
            
        self.selected_config = config
        self.selected_files = [self.file_list_widget.item(i).text() for i in range(file_count)]
        self.accept()
