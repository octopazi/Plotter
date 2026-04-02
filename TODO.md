# Project TODOs & Future Enhancements

## Data Import & Management
- [x] **Basic Single-File Import:** Implemented logic to parse headers, map columns, and apply formulas.
- [ ] **Multi-File Import:** Update `ImportDatalogDialog` to allow selecting multiple files at once.
- [ ] **Data Merging/Appending:** Update `FileLoader` to process multiple files and merge them or keep them as a list of independent DataFrames.
- [ ] **Dataset State Management:** Refactor `MainWindow` to store multiple datasets (e.g., `self.datasets = {"file1": df1, "file2": df2}`) instead of overwriting `self.current_dataset`.
- [ ] **Project Save/Load:** Implement a system to save current project state (file paths, configurations, plot settings) to resume work later.
- [ ] **Data Export Function:** Allow users to select specific dataframes and columns to export back to CSV/Excel.

## User Experience (UX) & Polish
- [ ] **Dataset Viewer / Panel:** Add a UI panel or list widget to the Main Window so users can see which datasets and columns are currently loaded in memory.
- [ ] **Formula Error Handling:** Add GUI warning dialogs for when user-defined formulas fail mathematically (e.g., division by zero) instead of just printing to the terminal.
- [ ] **Loading Indicators:** Add a progress bar or loading spinner for importing large datalog files.
- [ ] **Enhanced Plot Toolbars:** Potential custom UI for plot saving and figure management beyond the standard Matplotlib toolbar.

## Plotting & Analysis
- [ ] **Multi-Y-axis Support:** Implement plotting multiple data columns on the same figure with independent Y-scales.
- [ ] **Independent Analysis Selection:** In Multi-Y mode, allow users to select specifically which Y-axis a Trendline or MA should be applied to.
- [ ] **Advanced Plots:** Roadmap for adding additional plot types (e.g., Histogram, Box Plot) beyond scatter/line.
- [ ] **Draggable Legends:** Update plot windows to allow legends to be moved manually by the user.
- [ ] **Interactive Inspection:** Implement a Coordinate Picker (Crosshair) and Vertical Markers/Cursors for data measurement.
- [ ] **Performance (Resampling):** Implement data downsampling/decimation for smooth plotting of massive datasets.

## Further Discussion Needed
- [ ] **FFT Implementation Strategy:** Discussion on how to store FFT results (new DataFrames?) and where to display them.
- [ ] **Unit Conversion Library:** Determine if a dedicated unit management system (e.g., Pint) should be integrated into the config system.
- [ ] **Data Storage Architecture:** Optimization of memory usage when handling multiple large datalogs and calculated analysis results.
