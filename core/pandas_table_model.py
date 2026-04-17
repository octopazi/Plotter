import pandas as pd
import numpy as np
from PyQt5.QtCore import QAbstractTableModel, Qt

class PandasTableModel(QAbstractTableModel):
    """
    A simple custom QAbstractTableModel to display a Pandas DataFrame
    in a PyQt QTableView. This enables viewing and editing data directly.
    """
    def __init__(self, data=None):
        super().__init__()
        self._data = pd.DataFrame() if data is None else data

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
            # Handle both Python floats and NumPy floating types.
            # Convert to a native Python float and format with
            # enough significant digits to preserve precision.
            if isinstance(value, (float, np.floating)):
                return format(float(value), '.17g')
            return str(value)
            
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        if role == Qt.EditRole:
            try:
                # Basic string conversion to maintain general types
                col_type = type(self._data.iloc[index.row(), index.column()])
                
                # Attempt implicit conversion
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
            self.endResetModel()
            return True
        except Exception as e:
            print(f"Error deleting column: {e}")
            return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return super().flags(index) | Qt.ItemIsEditable

    def setHeaderDataFlags(self, section, orientation):
        """Return flags for header editing. Used by table view for header section editing."""
        if orientation == Qt.Horizontal:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable
        return Qt.ItemIsEnabled
