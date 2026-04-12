import matplotlib
matplotlib.use('Qt5Agg')
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel
from PyQt5.QtCore import Qt
from core.analysis import TrendlineAnalyzer
from .plot_settings_dialog import PlotSettingsDialog

class PlotWindow(QMainWindow):
    """A standalone Plot Window supporting multiple plots, interactive panning/zooming, and scale modifications."""
    def __init__(self, data_frame, x_col, y_cols, plot_type="scatter", window_title=None, parent=None):
        # Pass parent to allow closing this window when parent (MainWindow) closes
        super().__init__(parent) 
        
        # Ensures that closing the window actually destroys this Qt object
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # Store reference to parent for cleanup
        self.parent_window = parent
        
        self.df = data_frame
        self.x_col = x_col
        # Support single or multiple Y-cols
        self.y_cols = y_cols if isinstance(y_cols, list) else [y_cols] 
        self.plot_type = plot_type

        # Interactive inspection state
        self.coordinate_picker_enabled = False
        self.vertical_cursor_enabled = False
        self._inspect_series = []
        self._crosshair_vline = None
        self._crosshair_hline = None
        self._crosshair_annot = None
        self._crosshair_axis = None
        self._cursor_x_values = []
        self._cursor_lines = []
        
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

        self.coord_picker_btn = QPushButton("Coordinate Picker")
        self.coord_picker_btn.setCheckable(True)
        self.coord_picker_btn.toggled.connect(self.toggle_coordinate_picker)
        controls_layout.addWidget(self.coord_picker_btn)

        self.cursor_btn = QPushButton("Vertical Cursors")
        self.cursor_btn.setCheckable(True)
        self.cursor_btn.toggled.connect(self.toggle_vertical_cursors)
        controls_layout.addWidget(self.cursor_btn)

        self.clear_cursor_btn = QPushButton("Clear Cursors")
        self.clear_cursor_btn.clicked.connect(self.clear_vertical_cursors)
        controls_layout.addWidget(self.clear_cursor_btn)

        self.inspect_label = QLabel("Inspection: Off")
        controls_layout.addWidget(self.inspect_label)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Create Main Axis
        self.ax = self.fig.add_subplot(111)

        # Connect matplotlib inspection events once.
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)

    def toggle_coordinate_picker(self, enabled):
        self.coordinate_picker_enabled = bool(enabled)
        if not self.coordinate_picker_enabled:
            self._hide_crosshair()
        self._update_inspection_label()

    def toggle_vertical_cursors(self, enabled):
        self.vertical_cursor_enabled = bool(enabled)
        if not self.vertical_cursor_enabled:
            self.clear_vertical_cursors()
        self._update_inspection_label()

    def _update_inspection_label(self):
        parts = []
        if self.coordinate_picker_enabled:
            parts.append("Picker")
        if self.vertical_cursor_enabled:
            parts.append("Cursors")
        if not parts:
            self.inspect_label.setText("Inspection: Off")
            return

        if len(self._cursor_x_values) == 2:
            x1, x2 = self._cursor_x_values
            dx = x2 - x1
            self.inspect_label.setText(
                f"Inspection: {' + '.join(parts)} | X1={x1:.6g}, X2={x2:.6g}, dX={dx:.6g}"
            )
        else:
            self.inspect_label.setText(f"Inspection: {' + '.join(parts)}")

    def _hide_crosshair(self):
        for artist in (self._crosshair_vline, self._crosshair_hline, self._crosshair_annot):
            if artist is not None:
                artist.set_visible(False)
        self.canvas.draw_idle()

    def _clear_crosshair_artists(self):
        for attr in ("_crosshair_vline", "_crosshair_hline", "_crosshair_annot"):
            artist = getattr(self, attr)
            if artist is not None:
                try:
                    artist.remove()
                except Exception:
                    pass
            setattr(self, attr, None)
        self._crosshair_axis = None

    def clear_vertical_cursors(self):
        for line in self._cursor_lines:
            try:
                line.remove()
            except Exception:
                pass
        self._cursor_lines = []
        self._cursor_x_values = []
        self._update_inspection_label()
        self.canvas.draw_idle()

    def _ensure_crosshair(self, axis):
        if axis is None:
            return False
        if self._crosshair_axis is axis and self._crosshair_vline is not None:
            return True

        self._clear_crosshair_artists()
        self._crosshair_axis = axis
        self._crosshair_vline = axis.axvline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.8, zorder=90)
        self._crosshair_hline = axis.axhline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.8, zorder=90)
        self._crosshair_annot = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8),
            fontsize=9,
            zorder=95,
        )
        return True

    def _nearest_point(self, event):
        if not self._inspect_series:
            return None

        best = None
        for series in self._inspect_series:
            x_vals = series.get('x')
            y_vals = series.get('y')
            axis = series.get('axis')
            label = series.get('label')
            if x_vals is None or y_vals is None or len(x_vals) == 0:
                continue

            pts = np.column_stack((x_vals, y_vals))
            disp = axis.transData.transform(pts)
            d2 = (disp[:, 0] - event.x) ** 2 + (disp[:, 1] - event.y) ** 2
            idx = int(np.argmin(d2))
            candidate = {
                'distance2': float(d2[idx]),
                'x': float(x_vals[idx]),
                'y': float(y_vals[idx]),
                'label': label,
                'axis': axis,
            }
            if best is None or candidate['distance2'] < best['distance2']:
                best = candidate

        # Pixel threshold to avoid snapping to distant points.
        if best is None or best['distance2'] > (20 ** 2):
            return None
        return best

    def on_mouse_move(self, event):
        if not self.coordinate_picker_enabled:
            return
        if event.inaxes not in [self.ax, getattr(self, 'ax2', None)]:
            self._hide_crosshair()
            return

        nearest = self._nearest_point(event)
        if nearest is None:
            self._hide_crosshair()
            return

        axis = nearest['axis']
        if not self._ensure_crosshair(axis):
            return

        x_val = nearest['x']
        y_val = nearest['y']
        label = nearest['label']

        self._crosshair_vline.set_xdata([x_val, x_val])
        self._crosshair_hline.set_ydata([y_val, y_val])
        self._crosshair_vline.set_visible(True)
        self._crosshair_hline.set_visible(True)

        self._crosshair_annot.xy = (x_val, y_val)
        self._crosshair_annot.set_text(f"{label}\nX={x_val:.6g}, Y={y_val:.6g}")
        self._crosshair_annot.set_visible(True)

        self.canvas.draw_idle()

    def on_mouse_click(self, event):
        if not self.vertical_cursor_enabled:
            return
        if event.button != 1:
            return
        if event.inaxes not in [self.ax, getattr(self, 'ax2', None)]:
            return
        if event.xdata is None:
            return

        x_val = float(event.xdata)
        if len(self._cursor_x_values) >= 2:
            self.clear_vertical_cursors()

        line = self.ax.axvline(x_val, color='tab:purple', linestyle='--', linewidth=1.2, zorder=92)
        self._cursor_lines.append(line)
        self._cursor_x_values.append(x_val)

        self._update_inspection_label()
        self.canvas.draw_idle()

    def closeEvent(self, event):
        """Clean up references when the plot window is closed."""
        if self.parent_window and hasattr(self.parent_window, 'plot_windows'):
            try:
                self.parent_window.plot_windows.remove(self)
            except (ValueError, AttributeError):
                pass
        event.accept()

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
        self._inspect_series = []
        self._clear_crosshair_artists()
        self.clear_vertical_cursors()
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
            label_prefix = y_col  # Always use the actual column name
            color = colors[i % len(colors)] # Pick color from cycle based on series index
            
            # Determine which axis to use
            target_ax = self.ax
            if y_col in secondary_cols:
                target_ax = self.ax2
            
            # Decide drawing style based on plot_type
            if self.plot_type == "scatter":
                raw_line = target_ax.plot(self.df[self.x_col], self.df[y_col], marker='o', linestyle='', alpha=0.7, label=f"{label_prefix}", zorder=data_z, color=color)[0]
            elif self.plot_type == "line_scatter":
                raw_line = target_ax.plot(self.df[self.x_col], self.df[y_col], marker='', linestyle='-', alpha=0.7, label=f"{label_prefix}", zorder=data_z, color=color)[0]

            # Keep numeric copies for nearest-point inspection.
            try:
                x_num = np.asarray(self.df[self.x_col], dtype=float)
                y_num = np.asarray(self.df[y_col], dtype=float)
            except Exception:
                continue
            valid = np.isfinite(x_num) & np.isfinite(y_num)
            if np.any(valid):
                self._inspect_series.append({
                    'x': x_num[valid],
                    'y': y_num[valid],
                    'label': y_col,
                    'axis': target_ax,
                    'line': raw_line,
                })
                
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
            
        # Remove old legend before creating a new one
        if self.fig.legends:
            for leg_obj in self.fig.legends:
                leg_obj.remove()
            
        # Add legend to the figure level for proper draggability and z-order handling
        # Use 'upper left' as default location since figure legend doesn't support 'best'
        leg = self.fig.legend(lines, labels, loc='upper right', framealpha=0.95)
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
