import matplotlib
matplotlib.use('Qt5Agg')
import numpy as np
import pandas as pd
import mplcursors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QDialog,
    QComboBox,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from core.analysis import TrendlineAnalyzer
from .plot_settings_dialog import PlotSettingsDialog


class AddDatasetDialog(QDialog):
    """Select a dataset and configure X/Y columns before adding it to a plot."""

    def __init__(self, data_manager, existing_dataset_ids, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Dataset to Plot")
        self.resize(480, 360)

        self.data_manager = data_manager
        self.existing_dataset_ids = set(existing_dataset_ids)
        self.selected_dataset_id = None
        self.selected_x_col = None
        self.selected_y_cols = []

        self._candidate_ids = []

        self._init_ui()
        self._load_candidates()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        ds_row = QHBoxLayout()
        ds_row.addWidget(QLabel("Dataset:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        ds_row.addWidget(self.dataset_combo)
        layout.addLayout(ds_row)

        x_row = QHBoxLayout()
        x_row.addWidget(QLabel("X-Axis:"))
        self.x_combo = QComboBox()
        self.x_combo.currentTextChanged.connect(self._refresh_y_options)
        x_row.addWidget(self.x_combo)
        layout.addLayout(x_row)

        layout.addWidget(QLabel("Y-Axis (Hold Ctrl to Multi-select):"))
        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.y_list)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.add_btn = QPushButton("Add")
        self.cancel_btn = QPushButton("Cancel")
        self.add_btn.clicked.connect(self._accept_selection)
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    def _load_candidates(self):
        self.dataset_combo.clear()
        self._candidate_ids = []

        if self.data_manager is None:
            self.add_btn.setEnabled(False)
            return

        for ds_id, ds in self.data_manager.datasets.items():
            if ds_id in self.existing_dataset_ids:
                continue
            self._candidate_ids.append(ds_id)
            self.dataset_combo.addItem(ds.name, ds_id)

        has_candidates = len(self._candidate_ids) > 0
        self.dataset_combo.setEnabled(has_candidates)
        self.x_combo.setEnabled(has_candidates)
        self.y_list.setEnabled(has_candidates)
        self.add_btn.setEnabled(has_candidates)

        if has_candidates:
            self._on_dataset_changed()
        else:
            self.y_list.clear()
            self.x_combo.clear()

    def _current_dataset(self):
        ds_id = self.dataset_combo.currentData()
        if not ds_id or self.data_manager is None:
            return None
        return self.data_manager.get_dataset(ds_id)

    def _on_dataset_changed(self):
        ds = self._current_dataset()
        self.x_combo.clear()
        self.y_list.clear()
        if ds is None:
            return

        columns = [c for c in ds.df.columns.tolist() if c != "_source_file"]
        self.x_combo.addItems(columns)
        self._refresh_y_options()

    def _refresh_y_options(self):
        ds = self._current_dataset()
        self.y_list.clear()
        if ds is None:
            return

        x_col = self.x_combo.currentText()
        columns = [c for c in ds.df.columns.tolist() if c != "_source_file" and c != x_col]
        self.y_list.addItems(columns)

    def _accept_selection(self):
        ds = self._current_dataset()
        if ds is None:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset.")
            return

        x_col = self.x_combo.currentText()
        y_cols = [item.text() for item in self.y_list.selectedItems()]
        if not y_cols:
            cur = self.y_list.currentItem()
            if cur is not None:
                y_cols = [cur.text()]

        if not x_col or not y_cols:
            QMessageBox.warning(self, "Invalid Selection", "Please select both X and at least one Y column.")
            return

        self.selected_dataset_id = ds.id
        self.selected_x_col = x_col
        self.selected_y_cols = y_cols
        self.accept()

class PlotWindow(QMainWindow):
    """A standalone Plot Window supporting multiple plots, interactive panning/zooming, and scale modifications."""
    def __init__(
        self,
        data_frame,
        x_col,
        y_cols,
        plot_type="scatter",
        window_title=None,
        parent=None,
        dataset_id=None,
        dataset_name=None,
        data_manager=None,
    ):
        # Pass parent to allow closing this window when parent (MainWindow) closes
        super().__init__(parent) 
        
        # Ensures that closing the window actually destroys this Qt object
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # Store reference to parent for cleanup
        self.parent_window = parent
        self.data_manager = data_manager if data_manager is not None else getattr(parent, "data_manager", None)

        # Keep previous public attributes for compatibility with existing logic.
        self.df = data_frame
        self.x_col = x_col
        self.y_cols = y_cols if isinstance(y_cols, list) else [y_cols]
        self.plot_type = plot_type

        self._dataset_items = {}
        self._dataset_order = []
        self._dataset_list_updating = False

        base_dataset_name = dataset_name
        if not base_dataset_name and self.data_manager is not None and dataset_id:
            ds_obj = self.data_manager.get_dataset(dataset_id)
            if ds_obj is not None:
                base_dataset_name = ds_obj.name
        if not base_dataset_name:
            base_dataset_name = "Dataset"

        base_dataset_id = dataset_id or "__base__"
        self._add_dataset_item(base_dataset_id, base_dataset_name, data_frame, x_col, self.y_cols, visible=True)

        self._dataset_styles = {}
        self._marker_cycle = ['o', 's', '^', 'v', 'D', 'P', 'X', '*']
        self._line_cycle = ['-']

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
            'y_cols': [], # Store display labels for settings dialog
            'secondary_y': [], # Columns to plot on right axis
            'trend_enabled': False,
            'trend_type': 'Linear',
            'ma_enabled': False,
            'ma_window': 10,
            'layers': ["Moving Average", "Trendline", "Raw Data"]
        }
        self._sync_settings_series()
        
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

        dataset_layout = QHBoxLayout()
        dataset_layout.addWidget(QLabel("Datasets:"))
        self.dataset_list_widget = QListWidget()
        self.dataset_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.dataset_list_widget.setMaximumHeight(80)
        self.dataset_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dataset_list_widget.itemChanged.connect(self.on_dataset_item_changed)
        dataset_layout.addWidget(self.dataset_list_widget)
        layout.addLayout(dataset_layout, 0)
        
        # Establish the Matplotlib Figure and Canvas
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        
        # Add the built-in Navigation Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Keep manual subplot margins stable so the axes expands with window height.
        self.fig.set_layout_engine(None)
        
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.toolbar, 0)
        layout.addWidget(self.canvas, 1)
        
        # Add a bottom control panel
        controls_layout = QHBoxLayout()
        self.settings_btn = QPushButton("Plot Settings / Analysis")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        controls_layout.addWidget(self.settings_btn)

        self.add_dataset_btn = QPushButton("Add Dataset")
        self.add_dataset_btn.clicked.connect(self.open_add_dataset_dialog)
        controls_layout.addWidget(self.add_dataset_btn)

        self.remove_dataset_btn = QPushButton("Remove Dataset")
        self.remove_dataset_btn.clicked.connect(self.remove_selected_dataset)
        controls_layout.addWidget(self.remove_dataset_btn)

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
        layout.addLayout(controls_layout, 0)
        
        # Create Main Axis
        self.ax = self.fig.add_subplot(111)

        # Keep click-based vertical cursor interaction as a custom handler.
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_drag)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

        self._refresh_dataset_list_widget()

    def _add_dataset_item(self, dataset_id, dataset_name, dataframe, x_col, y_cols, visible=True):
        y_list = y_cols if isinstance(y_cols, list) else [y_cols]
        item = {
            'id': dataset_id,
            'name': str(dataset_name),
            'df': dataframe,
            'x_col': x_col,
            'y_cols': [c for c in y_list if c in dataframe.columns and c != x_col],
            'visible': bool(visible),
        }
        if x_col not in dataframe.columns:
            return False
        if not item['y_cols']:
            return False

        self._dataset_items[dataset_id] = item
        if dataset_id not in self._dataset_order:
            self._dataset_order.append(dataset_id)
        return True

    def _refresh_dataset_list_widget(self):
        self._dataset_list_updating = True
        self.dataset_list_widget.clear()

        for ds_id in self._dataset_order:
            item_data = self._dataset_items.get(ds_id)
            if item_data is None:
                continue

            text = f"{item_data['name']} ({len(item_data['y_cols'])} series)"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ds_id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked if item_data.get('visible', True) else Qt.Unchecked)
            self.dataset_list_widget.addItem(item)

        if self.dataset_list_widget.count() > 0:
            self.dataset_list_widget.setCurrentRow(0)

        self._dataset_list_updating = False

    def on_dataset_item_changed(self, item):
        if self._dataset_list_updating:
            return
        ds_id = item.data(Qt.UserRole)
        if ds_id not in self._dataset_items:
            return
        self._dataset_items[ds_id]['visible'] = item.checkState() == Qt.Checked
        self._sync_settings_series()
        self.draw_plot()

    def open_add_dataset_dialog(self):
        if self.data_manager is None:
            QMessageBox.warning(self, "Unavailable", "Dataset manager is unavailable in this plot window.")
            return

        dialog = AddDatasetDialog(self.data_manager, self._dataset_order, self)
        if not dialog.exec_():
            return

        ds = self.data_manager.get_dataset(dialog.selected_dataset_id)
        if ds is None:
            QMessageBox.warning(self, "Add Dataset", "Selected dataset no longer exists.")
            return

        added = self._add_dataset_item(
            ds.id,
            ds.name,
            ds.df,
            dialog.selected_x_col,
            dialog.selected_y_cols,
            visible=True,
        )
        if not added:
            QMessageBox.warning(self, "Add Dataset", "Failed to add dataset with the selected columns.")
            return

        self._sync_settings_series()
        self._refresh_dataset_list_widget()
        self.draw_plot()

    def remove_selected_dataset(self):
        current_item = self.dataset_list_widget.currentItem()
        if current_item is None:
            QMessageBox.information(self, "Remove Dataset", "Please select a dataset to remove.")
            return

        ds_id = current_item.data(Qt.UserRole)
        if ds_id not in self._dataset_items:
            return

        del self._dataset_items[ds_id]
        self._dataset_order = [item_id for item_id in self._dataset_order if item_id != ds_id]

        self._sync_settings_series()
        self._refresh_dataset_list_widget()
        self.draw_plot()

    def _series_label(self, dataset_name, y_col):
        return f"{dataset_name}: {y_col}"

    def _all_series_labels(self):
        labels = []
        for ds_id in self._dataset_order:
            item = self._dataset_items.get(ds_id)
            if item is None:
                continue
            for y_col in item['y_cols']:
                labels.append(self._series_label(item['name'], y_col))
        return labels

    def _sync_settings_series(self):
        all_labels = self._all_series_labels()
        self.settings['y_cols'] = all_labels
        self.settings['secondary_y'] = [
            label for label in self.settings.get('secondary_y', []) if label in all_labels
        ]

    def _get_visible_dataset_items(self):
        visible = []
        for ds_id in self._dataset_order:
            item = self._dataset_items.get(ds_id)
            if item is None or not item.get('visible', True):
                continue
            visible.append(item)
        return visible

    def _to_numeric_array(self, values):
        numeric = pd.to_numeric(values, errors='coerce')
        arr = np.asarray(numeric, dtype=float)
        if np.isfinite(arr).any():
            return arr

        dt = pd.to_datetime(values, errors='coerce')
        if not dt.notna().any():
            return arr

        # Convert datetime to UNIX seconds for interpolation while preserving NaT as NaN.
        out = np.full(len(dt), np.nan, dtype=float)
        valid_mask = dt.notna().to_numpy()
        if np.any(valid_mask):
            out[valid_mask] = dt[valid_mask].astype('int64').to_numpy(dtype=float) / 1_000_000_000.0
        return out

    def _build_series_numeric(self, item_data, y_col):
        x_raw = self._to_numeric_array(item_data['df'][item_data['x_col']])
        y_raw = self._to_numeric_array(item_data['df'][y_col])

        valid = np.isfinite(x_raw) & np.isfinite(y_raw)
        if not np.any(valid):
            return None, None

        x_vals = x_raw[valid]
        y_vals = y_raw[valid]

        order = np.argsort(x_vals)
        x_vals = x_vals[order]
        y_vals = y_vals[order]

        if x_vals.size == 0:
            return None, None

        # Collapse duplicate X points so interpolation receives monotonic coordinates.
        dedup = pd.DataFrame({'x': x_vals, 'y': y_vals}).groupby('x', as_index=False).mean()
        return dedup['x'].to_numpy(dtype=float), dedup['y'].to_numpy(dtype=float)

    def _dataset_style(self, dataset_id, ds_index):
        if dataset_id in self._dataset_styles:
            return self._dataset_styles[dataset_id]

        prop_cycle = matplotlib.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']
        style = {
            'color': colors[ds_index % len(colors)],
            'marker': self._marker_cycle[ds_index % len(self._marker_cycle)],
            'line': self._line_cycle[ds_index % len(self._line_cycle)],
        }
        self._dataset_styles[dataset_id] = style
        return style

    def _build_axis_label(self, names, fallback):
        unique = []
        for name in names:
            text = str(name).strip()
            if text and text not in unique:
                unique.append(text)

        if not unique:
            return fallback
        if len(unique) == 1:
            return unique[0]
        if len(unique) <= 3:
            return ", ".join(unique)
        return f"{fallback} ({len(unique)} series)"

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Ensure the canvas repaints immediately after Qt relayout.
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

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
            
        self._sync_settings_series()

        data_z = self.get_zorder("Raw Data")
        trend_z = self.get_zorder("Trendline")
        ma_z = self.get_zorder("Moving Average")

        secondary_cols = self.settings.get('secondary_y', [])
        has_secondary = len(secondary_cols) > 0
        
        if has_secondary:
            self.ax2 = self.ax.twinx()

        visible_items = self._get_visible_dataset_items()
        series_entries = []

        for ds_index, item_data in enumerate(visible_items):
            style = self._dataset_style(item_data['id'], ds_index)
            for y_col in item_data['y_cols']:
                x_vals, y_vals = self._build_series_numeric(item_data, y_col)
                if x_vals is None or y_vals is None:
                    continue
                series_entries.append({
                    'dataset_id': item_data['id'],
                    'dataset_name': item_data['name'],
                    'x_col': item_data['x_col'],
                    'y_col': y_col,
                    'x': x_vals,
                    'y': y_vals,
                    'label': self._series_label(item_data['name'], y_col),
                    'style': style,
                })

        if not series_entries:
            self.ax.set_title("No plottable numeric series")
            self.ax.grid(True, linestyle="--", alpha=0.6)
            self.canvas.draw_idle()
            return

        should_align = len(visible_items) > 1
        if should_align:
            common_x = np.unique(np.concatenate([entry['x'] for entry in series_entries]))
        else:
            common_x = None

        for idx, series in enumerate(series_entries):
            label_prefix = series['label']
            style = series['style']

            if should_align and common_x is not None and common_x.size > 0:
                if series['x'].size >= 2:
                    plot_x = common_x
                    plot_y = np.interp(common_x, series['x'], series['y'], left=np.nan, right=np.nan)
                else:
                    plot_x = common_x
                    plot_y = np.full(common_x.shape, np.nan, dtype=float)
                    close_idx = np.where(np.isclose(common_x, series['x'][0]))[0]
                    if close_idx.size > 0:
                        plot_y[close_idx[0]] = series['y'][0]
            else:
                plot_x = series['x']
                plot_y = series['y']

            target_ax = self.ax
            if label_prefix in secondary_cols and has_secondary:
                target_ax = self.ax2

            if self.plot_type == "scatter":
                raw_line = target_ax.plot(
                    plot_x,
                    plot_y,
                    marker=style['marker'],
                    linestyle='',
                    alpha=0.75,
                    label=label_prefix,
                    zorder=data_z,
                    color=style['color'],
                )[0]
            else:
                raw_line = target_ax.plot(
                    plot_x,
                    plot_y,
                    marker='',
                    linestyle=style['line'],
                    alpha=0.8,
                    label=label_prefix,
                    zorder=data_z,
                    color=style['color'],
                )[0]

            valid = np.isfinite(plot_x) & np.isfinite(plot_y)
            if np.any(valid):
                self._inspect_series.append({
                    'x': plot_x[valid],
                    'y': plot_y[valid],
                    'label': label_prefix,
                    'axis': target_ax,
                    'line': raw_line,
                })

            # Apply trendline only to the first plotted series to reduce clutter.
            if self.settings.get('trend_enabled') and idx == 0:
                trend_type = self.settings.get('trend_type')
                finite_mask = np.isfinite(plot_x) & np.isfinite(plot_y)
                x_vals = plot_x[finite_mask]
                y_vals = plot_y[finite_mask]
                x_span, y_span, eq_label = TrendlineAnalyzer.fit_trendline(x_vals, y_vals, trend_type)

                if x_span is not None:
                    target_ax.plot(
                        x_span,
                        y_span,
                        color='red',
                        linestyle='--',
                        linewidth=2.5,
                        label=f"{label_prefix} {eq_label}",
                        zorder=trend_z,
                    )

            if self.settings.get('ma_enabled'):
                window_size = self.settings.get('ma_window')
                ma_y = pd.Series(plot_y).rolling(window=window_size, center=True).mean().to_numpy()
                target_ax.plot(
                    plot_x,
                    ma_y,
                    color=style['color'],
                    linestyle=':',
                    linewidth=1.5,
                    label=f"{label_prefix} MA({window_size})",
                    zorder=ma_z,
                )

        # Handle Legends: Combine primary and secondary axes legends
        lines, labels = self.ax.get_legend_handles_labels()
        if has_secondary:
            lines2, labels2 = self.ax2.get_legend_handles_labels()
            lines += lines2
            labels += labels2
            secondary_names = [entry['y_col'] for entry in series_entries if entry['label'] in secondary_cols]
            self.ax2.set_ylabel(self._build_axis_label(secondary_names, "Secondary Y"))
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

        if should_align:
            self.ax.set_xlabel("Aligned X-axis (Interpolated)")
        else:
            first_item = visible_items[0]
            self.ax.set_xlabel(first_item['x_col'])

        primary_names = [entry['y_col'] for entry in series_entries if entry['label'] not in secondary_cols]
        self.ax.set_ylabel(self._build_axis_label(primary_names, "Primary Y"))

        if len(visible_items) > 1:
            plot_title = f"Multi-dataset Plot ({len(visible_items)} datasets)"
        else:
            plot_title = f"Plot: {', '.join(primary_names[:3])}"
        self.ax.set_title(plot_title)
        self.ax.grid(True, linestyle="--", alpha=0.6)

        # Keep the plot area filling the canvas vertically after window resize.
        self.fig.subplots_adjust(left=0.09, right=0.98, top=0.90, bottom=0.10)

        self._rebuild_picker_cursor()
        
        # Force refresh and recalculate layout
        self.fig.canvas.draw_idle() 
        self.fig.canvas.flush_events()
