import os
import json

class ConfigManager:
    """Manages the configuration files for data import formats."""

    @staticmethod
    def get_config_dir():
        """Returns the absolute path to the Config directory."""
        return os.path.join(os.getcwd(), "Config")

    @staticmethod
    def get_available_configs():
        """Scans the Config directory and returns a list of available JSON config files."""
        config_dir = ConfigManager.get_config_dir()
        if not os.path.exists(config_dir):
            return []
        
        return [f for f in os.listdir(config_dir) if f.endswith('.json')]

    @staticmethod
    def get_config_path(filename):
        """Returns the full path for a specific configuration file."""
        return os.path.join(ConfigManager.get_config_dir(), filename)

    @staticmethod
    def load_config(filename):
        """Loads a config file and sanitizes special characters and empty strings."""
        config_path = ConfigManager.get_config_path(filename)
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Keep internal config name aligned with filename stem.
        filename_stem = os.path.splitext(os.path.basename(filename))[0]
        if config.get("name") != filename_stem:
            config["name"] = filename_stem
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
        return ConfigManager.sanitize_config(config)

    @staticmethod
    def sanitize_config(config):
        """Sanitizes special character literals (e.g., '\\t') into actual characters and handles empty strings."""
        def clean_string(val):
            if isinstance(val, str):
                # Convert explicit escaped strings back to actual special characters
                # Useful if user typed "\\" then "t" in a UI or manual JSON
                return val.replace('\\t', '\t').replace('\\n', '\n').replace('\\r', '\r')
            return val

        for section in ["header", "data"]:
            if section in config:
                # Sanitize separators
                if "separator" in config[section]:
                    config[section]["separator"] = clean_string(config[section]["separator"])
                
                # Sanitize ignore_prefix (convert empty string to None so Pandas isn't confused)
                if "ignore_prefix" in config[section]:
                    prefix = config[section]["ignore_prefix"]
                    if prefix == "":
                        config[section]["ignore_prefix"] = None
                    else:
                        config[section]["ignore_prefix"] = clean_string(prefix)

        # Optional section: plot auto-generation defaults
        plot_cfg = config.get("plot_config")
        if not isinstance(plot_cfg, dict):
            config["plot_config"] = {"enabled": False, "figures": []}
        else:
            figures = plot_cfg.get("figures", [])
            if not isinstance(figures, list):
                figures = []

            clean_figures = []
            for fig in figures:
                if not isinstance(fig, dict):
                    continue

                y_cols = fig.get("y_columns", [])
                if isinstance(y_cols, str):
                    y_cols = [c.strip() for c in y_cols.split(",") if c.strip()]
                elif isinstance(y_cols, list):
                    y_cols = [str(c).strip() for c in y_cols if str(c).strip()]
                else:
                    y_cols = []

                clean_figures.append({
                    "title": str(fig.get("title", "")).strip(),
                    "plot_type": str(fig.get("plot_type", "scatter")).strip() or "scatter",
                    "x_column": str(fig.get("x_column", "")).strip(),
                    "y_columns": y_cols,
                })

            config["plot_config"] = {
                "enabled": bool(plot_cfg.get("enabled", False)),
                "figures": clean_figures,
            }

        return config

    @staticmethod
    def validate_config(config_data):
        """Validates if the dictionary contains the required config schema."""
        # Basic validation: check for top-level keys
        required_keys = ["name", "header", "data"]
        for key in required_keys:
            if key not in config_data:
                return False, f"Missing required key: '{key}'"

        # Optional validation for plot_config.
        if "plot_config" in config_data:
            plot_cfg = config_data.get("plot_config")
            if not isinstance(plot_cfg, dict):
                return False, "Invalid 'plot_config': expected object."

            if "enabled" in plot_cfg and not isinstance(plot_cfg.get("enabled"), bool):
                return False, "Invalid 'plot_config.enabled': expected boolean."

            figures = plot_cfg.get("figures", [])
            if not isinstance(figures, list):
                return False, "Invalid 'plot_config.figures': expected array."

            for idx, fig in enumerate(figures, start=1):
                if not isinstance(fig, dict):
                    return False, f"Invalid figure #{idx}: expected object."

                if "y_columns" in fig and not isinstance(fig.get("y_columns"), list):
                    return False, f"Invalid figure #{idx} 'y_columns': expected array."
        
        # We can add more specific type/schema checks here later
        return True, "Valid configuration."

    @staticmethod
    def import_external_config(file_path, overwrite=False):
        """Reads an external config, validates it, and saves it to the Config folder."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_config_data = json.load(f)
            
            # Immediately sanitize before validation
            config_data = ConfigManager.sanitize_config(raw_config_data)

            is_valid, msg = ConfigManager.validate_config(config_data)
            if not is_valid:
                return False, msg, None
            
            # Use the name defined inside the config for the filename
            name = config_data.get("name", "imported_config")
            dest_path = ConfigManager.get_config_path(f"{name}.json")
            
            if not overwrite and os.path.exists(dest_path):
                return False, "ALREADY_EXISTS", name
            
            # Write it to the local Config folder
            with open(dest_path, 'w') as f:
                json.dump(config_data, f, indent=4)
                
            return True, f"Successfully imported configuration as '{name}.json'.", name
        except json.JSONDecodeError:
            return False, "The selected file is not a valid JSON document.", None
        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}", None
