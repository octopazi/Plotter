import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt
from core.analysis import TrendlineAnalyzer
from .plot_settings_dialog import PlotSettingsDialog

class PlotWindow(QMainWindow):
    """A standalone Plot Window supporting multiple plots, interactive panning/zooming, and scale modifications."""
    def __init__(self, data_frame, x_col, y_col, plot_type="scatter", window_title=None, parent=None):
        # We pass parent=None mostly so that these show as separate independent windows that don't block each other.
        super().__init__(None) 
        
        # Ensures that closing the window actually destroys this Qt object
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.df = data_frame
        self.x_col = x_col
        self.y_col = y_col
        self.plot_type = plot_type
        
        # Initial Plot Settings
        self.settings = {
            'trend_enabled': False,
            'trend_type': 'Linear',
            'ma_enabled': False,
            'ma_window': 10,
            'layers': ["Moving Average", "Trendline", "Raw Data"]
        }
        
        title = window_title if window_title else f"{plot_type.capitalize()} Plot: {y_col} vs {x_col}"
        self.setWindowTitle(title)
        self.resize(800, 600)
        
        self.init_ui()
        self.draw_plot()
        
    def init_ui(self):
        # The central widget
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout(self.main_widget)
        
        # Establish the Matplotlib Figure and Canvas
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        
        # Add the built-in Navigation Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Ensure tight layout behavior out of the box
        self.fig.set_layout_engine("tight")
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Add a bottom control panel
        controls_layout = QHBoxLayout()
        self.settings_btn = QPushButton("Plot Settings / Analysis")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        controls_layout.addWidget(self.settings_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Create Main Axis
        self.ax = self.fig.add_subplot(111)

    def open_settings_dialog(self):
        dialog = PlotSettingsDialog(self.settings, self)
        if dialog.exec_():
            self.settings = dialog.settings
            self.draw_plot()

    def get_zorder(self, layer_name):
        """Returns z-order based on list position. Bottom of list = Lowest Z."""
        items = self.settings.get('layers', [])
        # In UI list, top item is visually in front, so should have highest Z.
        rev_items = list(reversed(items))
        if layer_name in rev_items:
            return rev_items.index(layer_name) + 5
        return 1

    def draw_plot(self):
        self.ax.clear()
        
        data_z = self.get_zorder("Raw Data")
        trend_z = self.get_zorder("Trendline")
        ma_z = self.get_zorder("Moving Average")

        # Decide drawing style based on plot_type
        if self.plot_type == "scatter":
            self.ax.plot(self.df[self.x_col], self.df[self.y_col], marker='o', linestyle='', alpha=0.7, label="Data", zorder=data_z)
        elif self.plot_type == "line_scatter":
            self.ax.plot(self.df[self.x_col], self.df[self.y_col], marker='', linestyle='-', alpha=0.7, label="Data", zorder=data_z)
            
        # Check if Trendline is requested
        if self.settings.get('trend_enabled'):
            trend_type = self.settings.get('trend_type')
            
            mask = self.df[self.x_col].notna() & self.df[self.y_col].notna()
            x_vals = self.df[self.x_col][mask].values
            y_vals = self.df[self.y_col][mask].values
            
            x_span, y_span, eq_label = TrendlineAnalyzer.fit_trendline(x_vals, y_vals, trend_type)
            
            if x_span is not None:
                self.ax.plot(x_span, y_span, color='red', linestyle='--', linewidth=2.5, label=eq_label, zorder=trend_z)
        
        # Check if Moving Average is requested
        if self.settings.get('ma_enabled'):
            window_size = self.settings.get('ma_window')
            ma_y = self.df[self.y_col].rolling(window=window_size, center=True).mean()
            self.ax.plot(self.df[self.x_col], ma_y, color='green', linestyle='-', linewidth=2, label=f"MA (Win={window_size})", zorder=ma_z)

        # Add a legend
        leg = self.ax.legend()
        if leg:
            leg.set_draggable(True)

        self.ax.set_xlabel(self.x_col)
        self.ax.set_ylabel(self.y_col)
        
        plot_title = f"Plot: {self.y_col} vs {self.x_col}"
        self.ax.set_title(plot_title)
        self.ax.grid(True, linestyle="--", alpha=0.6)
        self.canvas.draw()
