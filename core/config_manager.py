import os
import json
from .downsampling import validate_downsampling_config

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

        def clean_name_list(values):
            if isinstance(values, str):
                values = [v.strip() for v in values.split(',') if v.strip()]
            if not isinstance(values, list):
                return []

            names = []
            seen = set()
            for value in values:
                name = str(value).strip()
                if not name or name in seen:
                    continue
                names.append(name)
                seen.add(name)
            return names

        for section in ["header", "data"]:
            if section in config:
                # Sanitize separators
                if "separator" in config[section]:
                    sep = clean_string(config[section]["separator"])
                    # Common user input like ", " should be normalized to ","
                    # to avoid pandas treating it as a multi-char regex separator.
                    if isinstance(sep, str):
                        stripped_sep = sep.strip()
                        if len(sep) > 1 and len(stripped_sep) == 1:
                            sep = stripped_sep
                    config[section]["separator"] = sep

                if section == "header" and "simple_separator" in config[section]:
                    config[section]["simple_separator"] = clean_string(config[section]["simple_separator"])
                
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

        # Optional section: downsampling
        ds_cfg = config.get("downsampling")
        if not isinstance(ds_cfg, dict):
            config["downsampling"] = {"enabled": False}
        else:
            # Coerce enabled
            config["downsampling"]["enabled"] = bool(ds_cfg.get("enabled", False))
            # Coerce timing default
            timing = ds_cfg.get("timing", "before_conversions")
            if timing not in ("before_conversions", "after_conversions"):
                timing = "before_conversions"
            config["downsampling"]["timing"] = timing
            # Method is preserved as-is; full validation happens in validate_config

        # Optional section: post-process column visibility/removal
        post_cfg = config.get("postprocess_columns")
        if not isinstance(post_cfg, dict):
            config["postprocess_columns"] = {"hidden": [], "deleted": []}
        else:
            deleted = clean_name_list(post_cfg.get("deleted", []))
            deleted_set = set(deleted)
            hidden = [name for name in clean_name_list(post_cfg.get("hidden", [])) if name not in deleted_set]
            config["postprocess_columns"] = {
                "hidden": hidden,
                "deleted": deleted,
            }

        def normalize_input_type(value):
            normalized = str(value or "auto").strip().lower()
            return normalized if normalized in ("auto", "string") else "auto"

        data_cfg = config.get("data")
        if isinstance(data_cfg, dict):
            columns_cfg = data_cfg.get("columns")
            if isinstance(columns_cfg, dict):
                x_cfg = columns_cfg.get("x")
                if isinstance(x_cfg, dict):
                    x_cfg["input_type"] = normalize_input_type(x_cfg.get("input_type"))

                y_cfg = columns_cfg.get("y")
                if isinstance(y_cfg, list):
                    for y_col in y_cfg:
                        if isinstance(y_col, dict):
                            y_col["input_type"] = normalize_input_type(y_col.get("input_type"))

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

        # Optional section: downsampling
        if "downsampling" in config_data:
            ok, msg = validate_downsampling_config(config_data["downsampling"])
            if not ok:
                return False, msg

        # Optional section: postprocess_columns
        if "postprocess_columns" in config_data:
            post_cfg = config_data.get("postprocess_columns")
            if not isinstance(post_cfg, dict):
                return False, "Invalid 'postprocess_columns': expected object."

            for key in ("hidden", "deleted"):
                values = post_cfg.get(key, [])
                if not isinstance(values, list):
                    return False, f"Invalid 'postprocess_columns.{key}': expected array."

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
