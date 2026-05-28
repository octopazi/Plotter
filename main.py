# Version identifier for release tracking
__version__ = "0.3.0-alpha"

import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def ensure_config_folder_and_reference():
    config_dir = os.path.join(os.getcwd(), "Config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    plugin_dir = os.path.join(os.getcwd(), "Plugin")
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
    # Copy bundled reference file if not present
    ref_src = resource_path(os.path.join("Config", "full_config_reference.json"))
    ref_dst = os.path.join(config_dir, "full_config_reference.json")
    if not os.path.exists(ref_dst):
        try:
            shutil.copyfile(ref_src, ref_dst)
        except Exception as e:
            print(f"Warning: Could not copy reference config: {e}")

    # Copy bundled plugin files if not present
    plugin_seed_files = ["fft_example.py", "README.md"]
    for file_name in plugin_seed_files:
        src = resource_path(os.path.join("Plugin", file_name))
        dst = os.path.join(plugin_dir, file_name)
        if not os.path.exists(dst):
            try:
                shutil.copyfile(src, dst)
            except Exception as e:
                print(f"Warning: Could not copy plugin file '{file_name}': {e}")

if __name__ == "__main__":
    ensure_config_folder_and_reference()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
