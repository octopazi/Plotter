# Project TODOs & Future Enhancements

## Data Import & Management
- [x] **Basic Single-File Import:** Implemented logic to parse headers, map columns, and apply formulas.
- [x] **Multi-File Import:** Updated `ImportDatalogDialog` to allow selecting multiple files at once.
- [x] **Data Merging/Appending:** Updated `FileLoader` to process multiple files and track origin via `_source_file`.
- [x] **Dataset State Management (DataManager Architecture):** Refactored `MainWindow` to use a centralized `DataManager` holding `Dataset` objects. Extracted separate file logic from previous concatenated dataframes.
- [x] **Delete Dataset:** Added "Delete Dataset" via File menu and right-click context menu on the dataset list. Prompts confirmation, removes the dataset from `DataManager`, clears the table view, and refreshes the file list.
- [ ] **Project Save/Load:** Implement a system to save current project state. *Discussion: Use HDF5 (`.h5`) or Parquet for fast, space-efficient data storage, bundled with a JSON file mapping plot settings, UI states, and dataset relationships.*
- [x] **Data Export Function:** Users can open `File → Export Dataset` to select any combination of loaded datasets via checkboxes and export them as CSV (one file per dataset) or as a single Excel workbook (each dataset on a separate, customisable sheet).

## User Experience (UX) & Polish
- [x] **Dataset Viewer / Panel:** Added a UI panel split (QSplitter) with a QListWidget for loaded files and QTableView for data inspection.
- [x] **Data Modification Hook:** Because `PandasTableModel` holds a direct reference to the `Dataset.df`, UI edits edit the dataframe immediately without reverse-mapping index overhead.
- [ ] **Formula Error Handling:** Add GUI warning dialogs for when user-defined formulas fail mathematically (e.g., division by zero) instead of just printing to the terminal.
- [ ] **Loading Indicators:** Add a progress bar or loading spinner for importing large datalog files.
- [ ] **Enhanced Plot Toolbars:** Potential custom UI for plot saving and figure management beyond the standard Matplotlib toolbar.

## Plotting & Analysis
- [x] **Multi-Y-axis Support:** Implement plotting multiple data columns on the same figure with independent Y-scales.
- [x] **Independent Analysis Selection:** In Multi-Y mode, allow users to select specifically which Y-axis a Trendline or MA should be applied to.
- [ ] **Cross-Plotting Support:** Update `PlotSetupDialog` to allow selecting X and Y axes from *different* datasets, pulling from the `DataManager`.
- [ ] **Advanced Plots:** Roadmap for adding additional plot types (e.g., Histogram, Box Plot) beyond scatter/line.
- [x] **Draggable Legends:** Updated plot windows to allow legends to be moved manually by the user.
- [ ] **Interactive Inspection:** Implement a Coordinate Picker (Crosshair) and Vertical Markers/Cursors for data measurement.
- [ ] **Performance (Resampling):** Implement data downsampling/decimation for smooth plotting of massive datasets (e.g., 250k+ rows). *Strategy: Use LTTB (Largest Triangle Three Buckets) downsampling or simply slice standard skips for the plotting view while keeping the raw data untouched in the DataManager.*

## Further Discussion Needed
- [x] **FFT Implementation Strategy:** Implemented via the `DataManager`—FFT results become a new `Dataset` linked to their parent.
- [ ] **Unit Conversion Library:** Determine if a dedicated unit management system (e.g., Pint) should be integrated into the config system.
- [ ] **Data Storage Architecture:** Optimization of memory usage. *Strategy: For massive logs, consider migrating from purely RAM-based Pandas to memory-mapped files (e.g., Dask, Vaex, or PyTables) if active RAM usage exceeds system limits.*
