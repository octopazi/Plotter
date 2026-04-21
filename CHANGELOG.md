# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.0-alpha] - 2026-04-21

### Added
- Version-aware build spec naming (`Plotter-<version>`) using `PLOTTER_VERSION` or `main.py` fallback.
- Local release automation via `scripts/release.ps1`.
- GitHub Actions tag-based prerelease workflow (`.github/workflows/release.yml`).
- Version validation utility (`scripts/validate_version.py`) enforcing `MAJOR.MINOR.PATCH-alpha`.
- UTF-8 `requirements.txt` for CI-friendly dependency installation.

### Changed
- Application version bumped to `0.2.0-alpha`.
- Release process now validates changelog/release notes version consistency.

### Fixed
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
