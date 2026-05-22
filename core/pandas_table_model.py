import pandas as pd
import numpy as np
from pandas.api.types import is_float_dtype
from PyQt5.QtCore import QAbstractTableModel, Qt

class PandasTableModel(QAbstractTableModel):
    """
    A simple custom QAbstractTableModel to display a Pandas DataFrame
    in a PyQt QTableView. This enables viewing and editing data directly.
    """
    def __init__(self, data=None):
        super().__init__()
        self._data = pd.DataFrame() if data is None else data
        # Cache column data types to avoid repeated isinstance() checks during scrolling
        self._column_dtype_cache = self._build_dtype_cache()

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            if pd.isna(value):
                return ""
            # Check cached dtype to determine formatting without repeated isinstance() calls
            col_idx = index.column()
            if col_idx in self._column_dtype_cache and self._column_dtype_cache[col_idx] == 'float':
                return format(float(value), '.17g')
            return str(value)
            
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        if role == Qt.EditRole:
            try:
                # Attempt implicit conversion based on input format
                str_val = str(value)
                try:
                    if '.' in str_val or 'e' in str_val.lower():
                        val = float(str_val)
                    else:
                        val = int(str_val)
                except ValueError:
                    val = str_val
                    
                self._data.iloc[index.row(), index.column()] = val
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
            except Exception:
                return False
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        """Allow editing of column headers (horizontal headers only)."""
        if orientation == Qt.Horizontal and role == Qt.EditRole:
            try:
                new_name = str(value).strip()
                if not new_name:
                    return False
                
                # Rename the column in the DataFrame
                old_name = self._data.columns[section]
                self._data.rename(columns={old_name: new_name}, inplace=True)
                
                # Emit signal to notify views of the header change
                self.headerDataChanged.emit(orientation, section, section)
                return True
            except Exception as e:
                print(f"Error renaming header: {e}")
                return False
        return False

    def delete_column(self, section):
        """Delete a DataFrame column by section index."""
        try:
            section = int(section)
        except (TypeError, ValueError):
            return False

        if section < 0 or section >= self.columnCount():
            return False

        try:
            col_name = self._data.columns[section]
            self.beginResetModel()
            self._data.drop(columns=[col_name], inplace=True)
            # Rebuild dtype cache after column deletion
            self._column_dtype_cache = self._build_dtype_cache()
            self.endResetModel()
            return True
        except Exception as e:
            print(f"Error deleting column: {e}")
            return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return super().flags(index) | Qt.ItemIsEditable

    def _build_dtype_cache(self):
        """Build a cache mapping column indices to simplified dtype strings."""
        cache = {}
        for col_idx, dtype in enumerate(self._data.dtypes):
            # Classify dtypes into float or other for formatting purposes
            # pandas extension dtypes (e.g., StringDtype) are not always interpretable
            # by numpy.issubdtype, so use pandas helper first and fallback safely.
            if is_float_dtype(dtype):
                cache[col_idx] = 'float'
            else:
                try:
                    if np.issubdtype(dtype, np.floating):
                        cache[col_idx] = 'float'
                        continue
                except TypeError:
                    pass
                cache[col_idx] = 'other'
        return cache

    def setHeaderDataFlags(self, section, orientation):
        """Return flags for header editing. Used by table view for header section editing."""
        if orientation == Qt.Horizontal:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable
        return Qt.ItemIsEnabled
