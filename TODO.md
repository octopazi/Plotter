# Project TODOs & Future Enhancements

## Data Import & Management
- [x] **Basic Single-File Import:** Implemented logic to parse headers, map columns, and apply formulas.
- [x] **Multi-File Import:** Updated `ImportDatalogDialog` to allow selecting multiple files at once.
- [x] **Data Merging/Appending:** Updated `FileLoader` to process multiple files and track origin via `_source_file`.
- [x] **Dataset State Management (DataManager Architecture):** Refactored `MainWindow` to use a centralized `DataManager` holding `Dataset` objects. Extracted separate file logic from previous concatenated dataframes.
- [x] **Delete Dataset:** Added "Delete Dataset" via File menu and right-click context menu on the dataset list. Prompts confirmation, removes the dataset from `DataManager`, clears the table view, and refreshes the file list.
- [ ] **Project Save/Load:** Implement a system to save current project state. *Discussion: Use HDF5 (`.h5`) or Parquet for fast, space-efficient data storage, bundled with a JSON file mapping plot settings, UI states, and dataset relationships.*
- [x] **Data Export Function:** Users can open `File → Export Dataset` to select any combination of loaded datasets via checkboxes and export them as CSV (one file per dataset) or as a single Excel workbook (each dataset on a separate, customisable sheet).

- [x] **Config 'Format Name' Consistency:** Enforce that the config's "format name" always matches the filename (without extension) on load/save. Automatically update the field to prevent ambiguity and accidental duplication. If a user renames a config file, update the "format name" accordingly when loading.
- [x] **Post-Process Column Controls (Hidden/Delete):** Added config-driven `postprocess_columns` support to hide columns from plot selectors or delete them after import processing.

## User Experience (UX) & Polish
- [x] **Dataset Viewer / Panel:** Added a UI panel split (QSplitter) with a QListWidget for loaded files and QTableView for data inspection.
- [x] **Data Modification Hook:** Because `PandasTableModel` holds a direct reference to the `Dataset.df`, UI edits edit the dataframe immediately without reverse-mapping index overhead.
- [x] **Formula Error Handling:** Resolved via the conversion handler module. Conversion failures are collected as structured errors and surfaced in GUI warning dialogs after import.
- [ ] **Loading Indicators:** Add a progress bar or loading spinner for importing large datalog files.
- [ ] **Enhanced Plot Toolbars:** Potential custom UI for plot saving and figure management beyond the standard Matplotlib toolbar.

- [x] **Inline Editing for Y Columns/Conversions:** Enable inline editing (double-click or context menu) for Y columns and conversion formulas in column mapping and conversion dialogs. Users can modify entries directly without deleting/re-adding.
- [ ] **Version & Build Date Display:** Show version and build date in the main window (status bar, window title, or About dialog under Help menu).

## Plotting & Analysis
- [x] **Multi-Y-axis Support:** Implement plotting multiple data columns on the same figure with independent Y-scales.
- [x] **Independent Analysis Selection:** In Multi-Y mode, allow users to select specifically which Y-axis a Trendline or MA should be applied to.
- [x] **Cross-Dataset Plotting (Plot Window Workflow):** Plot windows support adding/removing additional datasets with independent X/Y selections per dataset.
- [ ] **Cross-Plotting Support in Setup Dialog:** Update `PlotSetupDialog` to allow selecting X and Y axes from *different* datasets before opening the first plot window.
- [ ] **Advanced Plots:** Roadmap for adding additional plot types (e.g., Histogram, Box Plot) beyond scatter/line.
- [x] **Draggable Legends:** Updated plot windows to allow legends to be moved manually by the user.
- [x] **Interactive Inspection:** Implemented coordinate picker with pinned annotations and draggable vertical markers/cursors for measurement.
- [x] **Performance (Import-Time Downsampling):** Implemented configurable import-time downsampling/decimation (Decimation, LTTB, DWT) with optional timing before/after conversions.
- [ ] **Performance (Viewport Rendering):** Add plot-time viewport downsampling/level-of-detail for smoother pan/zoom on massive in-memory datasets.

- [x] **Column Statistics Summary:** Implemented for selected columns via Data Viewer header right-click context menu and `Tools → Column Statistics Summary`. Results are shown in a summary dialog with Min, Max, peak-to-peak, RMS, and SD (Population / Excel STDEV.P style), plus valid/invalid sample counts.
- [ ] **Toggleable Statistics Panel:** Add an optional show/hide statistics panel (dock-style) for persistent, live column stats viewing without reopening dialogs.
- [ ] **Apply Formula to Column:** Allow applying custom formulas to columns from the main window (right-click or formula bar for direct calculation, similar to conversions).
- [x] **FFT Output Naming (Column Info):** Update FFT output dataset naming to include column name (e.g., 'filename -- FFT (column)').

## Further Discussion Needed
- [x] **FFT Implementation Strategy:** Implemented via the `DataManager`—FFT results become a new `Dataset` linked to their parent.
- [ ] **Unit Conversion Library:** Determine if a dedicated unit management system (e.g., Pint) should be integrated into the config system.
- [x] **Config GUI — Extended Conversion Types:** Refactored the config dialog into a **5-tab QTabWidget** (File Format / Columns / Conversions / Plot Config / Downsampling). The Conversions tab uses a **metadata-driven dynamic form** powered by `CONV_FIELD_SPECS` in `conversion_handlers.py` — the GUI reads field specs at runtime and builds widgets automatically. Adding a new conversion type only requires adding a handler + spec entry in `conversion_handlers.py`; **zero GUI code changes needed**. Includes Move Up/Down for sequential ordering. `conv_summary()` centralised in `conversion_handlers.py` is used by both the dialog and the Edit dialog for consistent display.
- [ ] **Data Storage Architecture:** Optimization of memory usage. *Strategy: For massive logs, consider migrating from purely RAM-based Pandas to memory-mapped files (e.g., Dask, Vaex, or PyTables) if active RAM usage exceeds system limits.*
