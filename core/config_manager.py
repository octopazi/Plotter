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
    def validate_config(config_data):
        """Validates if the dictionary contains the required config schema."""
        # Basic validation: check for top-level keys
        required_keys = ["name", "header", "data"]
        for key in required_keys:
            if key not in config_data:
                return False, f"Missing required key: '{key}'"
        
        # We can add more specific type/schema checks here later
        return True, "Valid configuration."

    @staticmethod
    def import_external_config(file_path, overwrite=False):
        """Reads an external config, validates it, and saves it to the Config folder."""
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
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
