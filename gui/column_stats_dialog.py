from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ColumnStatsDialog(QDialog):
    def __init__(self, dataset_name, column_name, stats, parent=None):
        super().__init__(parent)
        self.dataset_name = dataset_name
        self.column_name = column_name
        self.stats = stats

        self.setWindowTitle("Column Statistics Summary")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        meta_group = QGroupBox("Selection")
        meta_form = QFormLayout(meta_group)
        meta_form.addRow("Dataset:", QLabel(self.dataset_name))
        meta_form.addRow("Column:", QLabel(self.column_name))
        layout.addWidget(meta_group)

        stats_group = QGroupBox("Statistics")
        stats_form = QFormLayout(stats_group)
        stats_form.addRow("Total rows:", QLabel(str(self.stats["count_total"])))
        stats_form.addRow("Valid numeric rows:", QLabel(str(self.stats["count_valid"])))
        stats_form.addRow("Invalid/NaN rows:", QLabel(str(self.stats["count_invalid"])))
        stats_form.addRow("Min:", QLabel(self._fmt(self.stats["min"])))
        stats_form.addRow("Max:", QLabel(self._fmt(self.stats["max"])))
        stats_form.addRow("Peak-to-peak:", QLabel(self._fmt(self.stats["peak_to_peak"])))
        stats_form.addRow("RMS:", QLabel(self._fmt(self.stats["rms"])))
        stats_form.addRow("SD (Population):", QLabel(self._fmt(self.stats["sd_population"])))
        layout.addWidget(stats_group)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copy")
        close_btn = QPushButton("Close")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        close_btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _fmt(self, value):
        return f"{value:.6g}"

    def _copy_to_clipboard(self):
        text = (
            f"Dataset: {self.dataset_name}\n"
            f"Column: {self.column_name}\n"
            f"Total rows: {self.stats['count_total']}\n"
            f"Valid numeric rows: {self.stats['count_valid']}\n"
            f"Invalid/NaN rows: {self.stats['count_invalid']}\n"
            f"Min: {self._fmt(self.stats['min'])}\n"
            f"Max: {self._fmt(self.stats['max'])}\n"
            f"Peak-to-peak: {self._fmt(self.stats['peak_to_peak'])}\n"
            f"RMS: {self._fmt(self.stats['rms'])}\n"
            f"SD (Population): {self._fmt(self.stats['sd_population'])}"
        )
        QApplication.clipboard().setText(text)