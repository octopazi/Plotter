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
