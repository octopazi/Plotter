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
    def __init__(self, data_frame, x_col, y_cols, plot_type="scatter", window_title=None, parent=None):
        # We pass parent=None mostly so that these show as separate independent windows that don't block each other.
        super().__init__(None) 
        
        # Ensures that closing the window actually destroys this Qt object
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.df = data_frame
        self.x_col = x_col
        # Support single or multiple Y-cols
        self.y_cols = y_cols if isinstance(y_cols, list) else [y_cols] 
        self.plot_type = plot_type
        
        # Initial Plot Settings
        self.settings = {
            'y_cols': self.y_cols, # Store for settings dialog
            'secondary_y': [], # Columns to plot on right axis
            'trend_enabled': False,
            'trend_type': 'Linear',
            'ma_enabled': False,
            'ma_window': 10,
            'layers': ["Moving Average", "Trendline", "Raw Data"]
        }
        
        y_str = ", ".join(self.y_cols)
        title = window_title if window_title else f"{plot_type.capitalize()} Plot: {y_str} vs {x_col}"
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
        # Check if secondary axis is needed
        if hasattr(self, 'ax2'):
            try:
                self.ax2.clear() # Clear before removing to be safe
                self.ax2.remove()
            except:
                pass
            del self.ax2
            
        data_z = self.get_zorder("Raw Data")
        trend_z = self.get_zorder("Trendline")
        ma_z = self.get_zorder("Moving Average")

        secondary_cols = self.settings.get('secondary_y', [])
        has_secondary = len(secondary_cols) > 0
        
        if has_secondary:
            self.ax2 = self.ax.twinx()

        # Get the standard color cycle from Matplotlib
        prop_cycle = matplotlib.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']

        # Iterate through all selected Y columns
        for i, y_col in enumerate(self.y_cols):
            label_prefix = f"{y_col}" if len(self.y_cols) > 1 else "Data"
            color = colors[i % len(colors)] # Pick color from cycle based on series index
            
            # Determine which axis to use
            target_ax = self.ax
            if y_col in secondary_cols:
                target_ax = self.ax2
            
            # Decide drawing style based on plot_type
            if self.plot_type == "scatter":
                target_ax.plot(self.df[self.x_col], self.df[y_col], marker='o', linestyle='', alpha=0.7, label=f"{label_prefix}", zorder=data_z, color=color)
            elif self.plot_type == "line_scatter":
                target_ax.plot(self.df[self.x_col], self.df[y_col], marker='', linestyle='-', alpha=0.7, label=f"{label_prefix}", zorder=data_z, color=color)
                
            # Check if Trendline is requested (only for the first Y series for now to avoid clutter)
            if self.settings.get('trend_enabled') and i == 0:
                trend_type = self.settings.get('trend_type')
                
                mask = self.df[self.x_col].notna() & self.df[y_col].notna()
                x_vals = self.df[self.x_col][mask].values
                y_vals = self.df[y_col][mask].values
                
                x_span, y_span, eq_label = TrendlineAnalyzer.fit_trendline(x_vals, y_vals, trend_type)
                
                if x_span is not None:
                    # Use a derivative of the main series color or red for contrast
                    target_ax.plot(x_span, y_span, color='red', linestyle='--', linewidth=2.5, label=f"{y_col} {eq_label}", zorder=trend_z)
            
            # Check if Moving Average is requested
            if self.settings.get('ma_enabled'):
                window_size = self.settings.get('ma_window')
                ma_y = self.df[y_col].rolling(window=window_size, center=True).mean()
                # Use same color as main data but different linestyle for MA
                target_ax.plot(self.df[self.x_col], ma_y, color=color, linestyle=':', linewidth=1.5, label=f"{y_col} MA({window_size})", zorder=ma_z)

        # Handle Legends: Combine primary and secondary axes legends
        lines, labels = self.ax.get_legend_handles_labels()
        if has_secondary:
            lines2, labels2 = self.ax2.get_legend_handles_labels()
            lines += lines2
            labels += labels2
            self.ax2.set_ylabel(", ".join(secondary_cols[:2]) + ("..." if len(secondary_cols) > 2 else ""))
            # Ensure secondary axis is behind the legend but in front of data if needed
            self.ax2.set_zorder(self.ax.get_zorder() + 1)
            self.ax.set_facecolor("none") # Make primary axis transparent so secondary shows through
            
        # Add legend to the figure or axis that is on top
        leg = self.ax.legend(lines, labels)
        if leg:
            leg.set_draggable(True)
            leg.set_zorder(100) # Ensure it is on the very top

        self.ax.set_xlabel(self.x_col)
        # Label only primary columns on the left axis
        primary_cols = [c for c in self.y_cols if c not in secondary_cols]
        self.ax.set_ylabel(", ".join(primary_cols[:2]) + ("..." if len(primary_cols) > 2 else ""))
        
        plot_title = f"Plot: {', '.join(self.y_cols[:3])} vs {self.x_col}"
        self.ax.set_title(plot_title)
        self.ax.grid(True, linestyle="--", alpha=0.6)
        
        # Force refresh and recalculate layout
        self.fig.canvas.draw_idle() 
        self.fig.canvas.flush_events()
