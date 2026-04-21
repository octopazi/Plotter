# Changelog

All notable changes to this project will be documented in this file.

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
