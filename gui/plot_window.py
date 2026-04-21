import matplotlib
matplotlib.use('Qt5Agg')
import numpy as np
import mplcursors
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
        self._picker_hover_cursor = None
        self._picker_click_cursor = None
        self._cursor_x_values = []
        self._cursor_lines = []
        self._dragging_cursor_index = None
        self._cursor_pick_threshold_px = 8
        
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

        # Keep click-based vertical cursor interaction as a custom handler.
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_drag)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

    def toggle_coordinate_picker(self, enabled):
        if enabled and mplcursors is None:
            self.coordinate_picker_enabled = False
            self.coord_picker_btn.blockSignals(True)
            self.coord_picker_btn.setChecked(False)
            self.coord_picker_btn.blockSignals(False)
            self.inspect_label.setText("Inspection: Picker unavailable")
            return

        self.coordinate_picker_enabled = bool(enabled)
        if self.coordinate_picker_enabled and self.vertical_cursor_enabled:
            self.cursor_btn.blockSignals(True)
            self.cursor_btn.setChecked(False)
            self.cursor_btn.blockSignals(False)
            self.vertical_cursor_enabled = False
            self.clear_vertical_cursors()
        self._set_picker_enabled(self.coordinate_picker_enabled)
        self._update_inspection_label()

    def toggle_vertical_cursors(self, enabled):
        self.vertical_cursor_enabled = bool(enabled)
        if self.vertical_cursor_enabled and self.coordinate_picker_enabled:
            self.coord_picker_btn.blockSignals(True)
            self.coord_picker_btn.setChecked(False)
            self.coord_picker_btn.blockSignals(False)
            self.coordinate_picker_enabled = False
            self._set_picker_enabled(False)
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

    def _remove_picker_cursors(self):
        for attr in ("_picker_hover_cursor", "_picker_click_cursor"):
            cursor = getattr(self, attr)
            if cursor is None:
                continue
            try:
                cursor.remove()
            except Exception:
                pass
            setattr(self, attr, None)

    def _set_picker_enabled(self, enabled):
        hover = self._picker_hover_cursor
        click = self._picker_click_cursor

        if hover is not None:
            hover.enabled = bool(enabled)
            hover.visible = bool(enabled)
            if not enabled:
                for selection in tuple(hover.selections):
                    hover.remove_selection(selection)

        if click is not None:
            # Keep placed annotations visible even when picker mode is disabled.
            click.enabled = bool(enabled)
            click.visible = True

        if not enabled and (hover is not None or click is not None):
            self.canvas.draw_idle()

    def _format_picker_annotation(self, selection):
        label = selection.artist.get_label() if selection.artist is not None else ""
        if label.startswith("_"):
            label = "Series"

        target = selection.target
        x_val = float(target[0])
        y_val = float(target[1])
        selection.annotation.set_text(f"{label}\nX={x_val:.6g}, Y={y_val:.6g}")

    def _on_picker_hover_add(self, selection):
        # Hover cursor keeps prior coordinate readout and adds transient crosshair lines.
        self._format_picker_annotation(selection)
        axis = selection.artist.axes if selection.artist is not None else None
        if axis is None:
            return
        x_val = float(selection.target[0])
        y_val = float(selection.target[1])
        vline = axis.axvline(x_val, color='gray', linestyle='--', linewidth=0.8, alpha=0.8, zorder=90)
        hline = axis.axhline(y_val, color='gray', linestyle='--', linewidth=0.8, alpha=0.8, zorder=90)
        if hasattr(vline, 'set_in_layout'):
            vline.set_in_layout(False)
        if hasattr(hline, 'set_in_layout'):
            hline.set_in_layout(False)
        selection.extras.extend([vline, hline])

    def _on_picker_click_add(self, selection):
        # Click cursor supports multiple pinned, draggable annotations.
        self._format_picker_annotation(selection)
        selection.annotation.draggable(True)

    def _rebuild_picker_cursor(self):
        self._remove_picker_cursors()
        if mplcursors is None:
            return

        artists = [
            series.get('line')
            for series in self._inspect_series
            if series.get('line') is not None
        ]
        if not artists:
            return

        self._picker_hover_cursor = mplcursors.cursor(
            artists,
            hover=mplcursors.HoverMode.Transient,
            multiple=False,
            highlight=False,
            bindings={
                'toggle_enabled': None,
                'toggle_visible': None,
            },
            annotation_kwargs={
                'bbox': dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8),
                'fontsize': 9,
            },
        )
        self._picker_hover_cursor.connect("add", self._on_picker_hover_add)

        self._picker_click_cursor = mplcursors.cursor(
            artists,
            hover=False,
            multiple=True,
            highlight=False,
            bindings={
                'toggle_enabled': None,
                'toggle_visible': None,
            },
            annotation_kwargs={
                'bbox': dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8),
                'fontsize': 9,
                'arrowprops': dict(arrowstyle='->', color='0.35', linewidth=1.0),
            },
        )
        self._picker_click_cursor.connect("add", self._on_picker_click_add)
        self._set_picker_enabled(self.coordinate_picker_enabled)

    def clear_vertical_cursors(self):
        for line in self._cursor_lines:
            try:
                line.remove()
            except Exception:
                pass
        self._cursor_lines = []
        self._cursor_x_values = []
        self._dragging_cursor_index = None
        self._update_inspection_label()
        self.canvas.draw_idle()

    def _find_cursor_index_at_event(self, event):
        if event.x is None or not self._cursor_lines:
            return None

        best_idx = None
        best_dist = None
        for idx, x_val in enumerate(self._cursor_x_values):
            x_disp = self.ax.transData.transform((x_val, 0))[0]
            dist = abs(float(event.x) - float(x_disp))
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = idx

        if best_dist is None or best_dist > self._cursor_pick_threshold_px:
            return None
        return best_idx

    def on_mouse_click(self, event):
        if not self.vertical_cursor_enabled:
            return
        if event.inaxes not in [self.ax, getattr(self, 'ax2', None)]:
            return

        if event.button == 3:
            idx = self._find_cursor_index_at_event(event)
            if idx is None:
                return
            try:
                self._cursor_lines[idx].remove()
            except Exception:
                pass
            del self._cursor_lines[idx]
            del self._cursor_x_values[idx]
            self._dragging_cursor_index = None
            self._update_inspection_label()
            self.canvas.draw_idle()
            return

        if event.button != 1:
            return
        if event.xdata is None:
            return

        # Left-click on an existing cursor line starts dragging instead of placing a new cursor.
        idx = self._find_cursor_index_at_event(event)
        if idx is not None:
            self._dragging_cursor_index = idx
            return

        x_val = float(event.xdata)
        if len(self._cursor_x_values) >= 2:
            return

        line = self.ax.axvline(x_val, color='tab:purple', linestyle='--', linewidth=1.2, zorder=92)
        self._cursor_lines.append(line)
        self._cursor_x_values.append(x_val)

        self._update_inspection_label()
        self.canvas.draw_idle()

    def on_mouse_drag(self, event):
        if not self.vertical_cursor_enabled:
            return
        if self._dragging_cursor_index is None:
            return
        if event.inaxes not in [self.ax, getattr(self, 'ax2', None)]:
            return
        if event.xdata is None:
            return

        idx = self._dragging_cursor_index
        if idx >= len(self._cursor_lines):
            self._dragging_cursor_index = None
            return

        x_val = float(event.xdata)
        self._cursor_lines[idx].set_xdata([x_val, x_val])
        self._cursor_x_values[idx] = x_val
        self._update_inspection_label()
        self.canvas.draw_idle()

    def on_mouse_release(self, event):
        if event.button == 1:
            self._dragging_cursor_index = None

    def closeEvent(self, event):
        """Clean up references when the plot window is closed."""
        self._remove_picker_cursors()
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
        self._remove_picker_cursors()
        self.ax.clear()
        self._inspect_series = []
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

        self._rebuild_picker_cursor()
        
        # Force refresh and recalculate layout
        self.fig.canvas.draw_idle() 
        self.fig.canvas.flush_events()
