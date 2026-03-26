# Plotter

A desktop GUI tool for importing, converting, analyzing, and plotting data from raw CSV or text files. Designed for flexibility, extensibility, and ease of use for scientific and engineering data workflows.

## Features
- **Customizable Data Import:**
  - Import data from various CSV or text formats using user-defined configuration files (JSON).
  - Configurable parsing, column mapping, and data conversion using custom equations.
- **Modular Analysis Tools:**
  - Built-in FFT (Fast Fourier Transform) analysis.
  - Modular architecture allows easy addition of new analysis tools.
- **Flexible Plotting:**
  - Scatter plot support with multi y-axis capability.
  - Designed for future expansion to more plot types and advanced visualization.

## Architecture Overview
- **GUI:** Built with PyQt5. Main window and dialogs in `gui/`.
- **Config System:**
  - Create different data import format base on the config system, support header/data column naming, import conversion and basic filters
- **Backend Logic:**
  - Placeholder modules in `core/` for config management, file loading, and analysis tools.

## Getting Started
1. **Install Dependencies:**
   ```powershell
   pip install -r requirement.txt
   ```
2. **Run the Application:**
   ```powershell
   py main.py
   ```

## Usage
- Use the menubar to import data files, create/import configs, and access plotting/analysis tools.
- Create or edit import formats via the GUI or by editing JSON files in `Config/`.
- FFT and other analysis tools are accessible from the Tools menu.

## Project Structure
```
main.py                  # Entry point
requirement.txt          # Python dependencies
Config/                  # User and sample config files
Sample/                  # Example data and config templates
gui/                     # PyQt5 GUI dialogs and main window
core/                    # Backend logic (placeholders for now)
```

## Extending the Project
- **Add a new data format:** Create a JSON config in `Config/` following the sample structure.
- **Add a new analysis tool:** Implement as a module in `core/` and connect to the GUI.
- **Extend plotting:** Update plotting logic in the GUI to support new plot types or features.

## Notes
- The project is under active development. Some backend modules are placeholders.
- For questions on config structure or extending features, see the sample configs and GUI dialog code.

---