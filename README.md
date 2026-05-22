
# Plotter ![Alpha](https://img.shields.io/badge/status-alpha-orange)

A desktop GUI tool for importing, converting, analyzing, and plotting data from raw CSV or text files. Designed for flexibility, extensibility, and ease of use in scientific and engineering workflows.

**Version:** 0.2.0-alpha

---

## 🚧 Alpha Release Notice
This is an **alpha release** for early user feedback. Features and UI may change. Please report any bugs or suggestions (see Feedback below).

---

## Key Features

- **Customizable Data Import**
  - Import single or multiple files (CSV, TXT) using user-defined JSON configuration files.
  - Configurable parsing, column mapping, and sequential data conversions (math, hex, bitmask, lookup, etc.).
  - Multi-file import with dataset origin tracking and merging.

- **Dataset Management**
  - Centralized DataManager architecture: manage multiple datasets, delete datasets, and inspect data in a split-panel viewer.
  - Export selected datasets as CSV or Excel (one file per dataset or multi-sheet workbook).

- **Analysis Tools**
  - Built-in FFT (Fast Fourier Transform) analysis with results as new linked datasets.
  - Modular design for adding new analysis tools (e.g., trendlines, moving averages).

- **Flexible Plotting**
  - Scatter/line plots with multi y-axis support and draggable legends.
  - Per-axis trendline and moving average overlays.
  - Optional config-driven auto-plot after import with multiple figure definitions.
  - Roadmap: cross-dataset plotting, advanced plot types (histogram, box plot), interactive inspection tools.

- **User Experience**
  - Dynamic config creation GUI (5-tab dialog: File Format, Columns, Conversions, Plot Config, Downsampling).
  - Column cleanup controls: mark mapped columns as hidden (plot UI only) or deleted (remove after processing).
  - Formula error handling with detailed GUI warnings.
  - Modern PyQt5 interface with persistent settings.

---

## Architecture Overview

- **GUI:** PyQt5 main window and dialogs in `gui/` (import, config, plot, analysis, export, etc.).
- **Config System:**
  - JSON configs define header/data parsing, column mapping, and conversion formulas.
  - See `Sample/full_config_reference.json` for all supported conversion types.
- **Backend Logic:**
  - `core/` modules for config management, file loading, data management, conversion handlers, and analysis (FFT, trendlines, etc.).
- **Extensibility:**
  - Add new config templates in `Config/` or `Sample/`.
  - Add new analysis modules in `core/` and connect via the GUI.
  - Extend plotting logic for new plot types and features.

---

## Getting Started

1. **Install Dependencies:**
   ```powershell
  pip install -r requirements.txt
   ```
2. **Run the Application:**
   ```powershell
   python main.py
   ```

---

## Usage

- Use the menubar to import data files, create/import configs, and access plotting/analysis tools.
- Create or edit import formats via the GUI or by editing JSON files in `Config/`.
- FFT and other analysis tools are accessible from the Tools menu.
- Inspect, delete, and export datasets from the dataset panel.

---

## Build & Release Workflow

### Version Naming Rules

- This project currently enforces prerelease format: `MAJOR.MINOR.PATCH-alpha`
- Valid example: `0.2.0-alpha`
- Invalid examples: `0.2-alpha`, `v0.2.0-alpha`, `0.2.0-alpha.1` (not used in this project policy)
- The only source of truth is `__version__` in `main.py`
- Git tags must be prefixed with `v`, so release tag for this version is `v0.2.0-alpha`

### Local Release (Windows PowerShell)

Run this from project root:

```powershell
./scripts/release.ps1
```

What this script does:

1. Validates version naming and consistency with `CHANGELOG.md` and `RELEASE_NOTES.md`
2. Cleans previous build output (`build/` and `dist/`)
3. Installs dependencies and PyInstaller
4. Builds with `main.spec`
5. Creates versioned outputs in `dist/Plotter-<version>/` plus `dist/Plotter-<version>.zip`

### GitHub Actions Release (Beginner Guide)

The workflow file is `.github/workflows/release.yml`.

How it works:

1. Trigger: push a git tag like `v0.2.0-alpha`
2. CI installs Python + dependencies
3. CI validates that tag version matches `main.py` version
4. CI builds PyInstaller bundle and zips it
5. CI creates a GitHub prerelease and uploads the ZIP artifact

One-time repository setup:

1. Open GitHub repository settings
2. Ensure Actions are enabled
3. Ensure workflow has permission to write repository contents (for creating releases)

Release commands:

```bash
git add .
git commit -m "release: v0.2.0-alpha"
git push origin main
git tag v0.2.0-alpha
git push origin v0.2.0-alpha
```

After pushing the tag, open the Actions tab and watch the `Build and Release` workflow.

---

## Project Structure

```
main.py                  # Entry point
requirements.txt         # Python dependencies (UTF-8 for CI)
scripts/release.ps1      # Local release automation
scripts/validate_version.py # Version rule validator
Config/                  # User and sample config files
Sample/                  # Example data and config templates
gui/                     # PyQt5 GUI dialogs and main window
core/                    # Backend logic (data, config, analysis, conversion)
```

---

## Roadmap & Future Development

- [ ] Project save/load system (HDF5/Parquet + JSON for UI/project state)
- [ ] Formula error dialogs for all conversion failures
- [ ] Loading indicators for large file imports
- [ ] Enhanced plot toolbars and advanced plot types (histogram, box plot)
- [ ] Cross-dataset plotting and interactive inspection tools (crosshair, markers)
- [ ] Performance optimizations for large datasets (downsampling, memory-mapped files)
- [ ] Unit conversion library integration (e.g., Pint)
- [ ] Data storage/memory optimization for massive logs

See `TODO.md` for detailed progress and discussion.

---

## Extending the Project

- **Add a new data format:** Create a JSON config in `Config/` following the sample structure.
- **Add a new analysis tool:** Implement as a module in `core/` and connect to the GUI.
- **Extend plotting:** Update plotting logic in the GUI to support new plot types or features.

---

## Feedback & Issues

- Please report bugs, suggestions, or UX feedback via [GitHub Issues](https://github.com/octopazi/Plotter/issues) or by contacting the maintainer.
- For questions on config structure or extending features, see the sample configs and GUI dialog code.

---

## License

MIT License. See `LICENSE` for details.