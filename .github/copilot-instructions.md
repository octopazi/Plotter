

# Copilot Instructions for Plotter Project
## Collaboration & Communication Guidelines

To maximize accuracy and project alignment, AI agents should:
- **Plan before coding:** For any new task or development, outline your approach, including implementation details, design choices, and potential edge cases.
- **Explain your reasoning:** Clearly communicate your plan and rationale before making changes. Highlight any concerns or trade-offs.
- **Ask clarifying questions:** If any requirements, context, or goals are unclear, proactively ask the user for clarification. Treat the process as an ongoing interview to refine your understanding.
- **Iterate with feedback:** Use user responses to refine your plan and implementation, ensuring the solution matches expectations.

This approach ensures a collaborative, discussion-driven workflow for higher quality and more context-aware results.

## Project Overview
- **Purpose:** Desktop GUI tool for importing, converting, and plotting data from raw CSV or text files, with a focus on flexibility and extensibility.
- **Key Features:**
  - Customizable import system: Users can define how to parse and convert data from various file formats using configuration files and equations.
  - Built-in FFT analysis: Modular FFT processing is included, and the architecture supports adding more analysis tools easily.
  - Flexible plotting: Supports scatter plots (with multi y-axis), with a roadmap for more plot types and advanced visualization.
- **Tech Stack:** Python, PyQt5 for GUI, pandas/matplotlib/plotly for data handling and visualization.
- **Key Directories:**
  - `gui/`: PyQt5 dialogs and main window logic (e.g., `main_window.py`, `create_config.py`).
  - `core/`: Backend logic (planned for config/data management and analysis modules).
  - `Config/`: User-created or sample configuration JSONs for data import formats.
  - `Sample/`: Example data and format templates for testing and development.


## Architecture & Data Flow
- **Entry Point:** `main.py` launches the PyQt5 app and shows `MainWindow`.
- **MainWindow:**
  - Menubar provides access to file import, config creation/import, plotting, and analysis tools.
  - Dialogs for config creation/import are in `gui/create_config.py` and `gui/import_config.py`.
- **Config System:**
  - Config files (JSON) define how to parse, map, and convert data files (see `Sample/datalog_format_sample_v1.json` and `Sample/datalog_format_sample_v2.json`).
  - Configs specify header/data parsing, column mapping, and conversion formulas (supporting custom equations for data transformation).
- **Modularity:**
  - Analysis tools (e.g., FFT) are designed as modular components, making it easy to add new processing or analysis features in the future.
- **Extensibility:**
  - Add new config templates in `Config/` or `Sample/`.
  - Extend backend logic in `core/` for file loading, config management, or new analysis modules.


## Developer Workflows
- **Run App:**
  - `py main.py` (Windows PowerShell)
- **Dependencies:**
  - Install from `requirement.txt` (note: file name is not standard, should be `requirements.txt`)
    - `pip install -r requirement.txt`
- **Testing:**
  - No explicit test suite or test runner found. Add tests in a `tests/` folder if needed.
- **Debugging:**
  - Use print statements or PyQt5's built-in dialog messages for debugging GUI logic.


## Project-Specific Patterns & Conventions
- **Config JSON Structure:**
  - Follows a schema with `header`, `data`, `columns`, and `conversions` sections.
  - See `Sample/datalog_format_sample_v2.json` for a full-featured example.
- **Dialog Naming:**
  - Dialog classes are named `*Dialog` (e.g., `CreateImportFormatDialog`).
- **GUI Actions:**
  - Menubar actions are connected to dialog popups for config and file operations.
- **Analysis Modularity:**
  - FFT and other analysis tools should be implemented as independent modules, easily invoked from the GUI and extendable for future features.
- **Plotting:**
  - Scatter plot is the initial supported plot type, with multi y-axis support. Design plotting logic to allow for future plot types and advanced options.
- **Empty Core Files:**
  - `core/config_manager.py` and `core/file_loader.py` are placeholders for future logic.


## Integration Points
- **PyQt5:** All GUI logic uses PyQt5 widgets and dialogs.
- **Data Import:** Configs drive how data files are parsed, mapped, and converted for plotting and analysis.
- **Analysis:** FFT and future tools should be modular and callable from the GUI.
- **Plotting:** Scatter/multi y-axis plots are supported; plotting logic should be modular for future expansion.


## Examples
- To add a new data format, create a JSON config in `Config/` following the sample structure.
- To add a new analysis tool (e.g., FFT), implement it as a module in `core/` and connect it to the GUI via menu actions.
- To extend backend logic, implement functions in `core/` and connect them to GUI actions.

---

For questions or unclear conventions, review `Sample/` configs and `gui/` dialog code for working examples. If adding new features, follow the dialog/action patterns in `gui/main_window.py` and `gui/create_config.py`.
