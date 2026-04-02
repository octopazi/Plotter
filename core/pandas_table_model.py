import pandas as pd
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
            if isinstance(value, float):
                return f"{value:.4f}"
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

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
            
        col_name = self._data.columns[index.column()]
        if col_name == '_source_file':
            return super().flags(index) # Read-only
            
        return super().flags(index) | Qt.ItemIsEditable
