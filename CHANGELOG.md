# Changelog

All notable changes to this project will be documented in this file.

## [v0.3.0-alpha] - 2026-05-28

### Added
- Import-time downsampling pipeline with configurable timing (`before_conversions` or `after_conversions`) and support for Decimation, LTTB, and DWT methods.
- Downsampling controls in the config editor via dedicated Plot Config and Downsampling tabs.
- Multi-select dataset deletion dialog for removing multiple datasets at once.
- FFT dialog row-range selection and preferred dataset preselection from current context.
- FFT output dataset naming that includes selected signal context.
- Multi-dataset plotting in a single plot window with dataset add/remove controls.
- Auto/manual dataset alignment using cross-correlation with interpolation fallback for mismatched sampling.
- Post-process column handling at import (`hidden` and `deleted`) with GUI warnings when rules cannot be fully applied.
- Dataset script plugin workflow (`Script -> Dataset process`) with plugin discovery/validation and sample plugin support.

### Changed
- Application version bumped to `0.3.0-alpha`.
- Data viewer rendering performance improved for large datasets.
- Import pipeline robustness improved for header regex extraction and column mapping edge cases.

### Fixed
- Added missing `openpyxl` dependency for Excel export reliability.
- Normalized separator handling to avoid CSV parsing failures from values like `", "`.
- Resolved single-line multi-header regex extraction issues in expert mode.
- Prevented unintended index promotion and mapping failures during file loading.
- Fixed dtype classification in the table model to avoid float-type related TypeError crashes.
- Fixed DWT downsampling read-only array error.

## [v0.2.0-alpha] - 2026-04-21

### Added
- Header-detection workflow with sample-file detection, simple/expert column name modes, and preview-assisted X/Y mapping.
- Config-driven plot definitions, including auto-plot after import and manual `Run Config Plots` execution.
- Plot inspection tools with coordinate picking, pinned annotations, and draggable vertical cursors.
- Column statistics summary dialog and table-header actions for dataset inspection and column deletion.
- Persistent UI settings for remembering the last-used config selections and import directory.
- Version-aware build spec naming (`Plotter-<version>`) using `PLOTTER_VERSION` or `main.py` fallback.
- Local release automation via `scripts/release.ps1`.
- GitHub Actions tag-based prerelease workflow (`.github/workflows/release.yml`).
- Version validation utility (`scripts/validate_version.py`) enforcing `MAJOR.MINOR.PATCH-alpha`.
- Source-controlled UTF-8 `requirements.txt` for CI-friendly dependency installation.

### Changed
- Application version bumped to `0.2.0-alpha`.
- Config editing now supports inline updates for Y columns, conversion steps, and plot figures, with unsaved-change protection.
- Header/data parsing now supports richer header extraction, optional header-row column names, and configurable data row limits.
- Import flow now surfaces column-name mismatch warnings and can launch config-defined plots immediately after import.
- Release process now validates changelog/release notes version consistency.

### Fixed
- Table view now preserves full floating-point precision instead of truncating numeric values to four decimals.
- Config names are kept consistent with their filename when loading or editing saved configs.
- Build outputs are now deterministically versioned for release packaging.

## [v0.1.0-alpha] - 2026-04-10

### Added
- Initial alpha release of Plotter.
- Customizable data import system (user-defined JSON configs).
- Multi-file import and dataset management (add/delete/inspect datasets).
- Modular analysis tools: FFT, trendline, moving average.
- Flexible plotting: scatter/line plots, multi y-axis, draggable legends.
- Export datasets as CSV or Excel (multi-sheet).
- GUI for config creation and editing (3-tab dialog).

### Changed
- Refactored DataManager for centralized dataset state and origin tracking.
- Improved error handling for formula/conversion failures (GUI warnings).

### Fixed
- N/A (first release)
