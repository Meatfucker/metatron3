import json
import os

class SettingsLoader:
    def __init__(self, directory):
        """Initialize and automatically load all JSON files from the given directory."""
        self.configs = {}
        self.load_all(directory)

    def load_all(self, directory):
        """Scans the directory and loads all JSON files."""
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory '{directory}' not found.")

        for file in os.listdir(directory):
            if file.endswith(".json"):
                self._load_file(os.path.join(directory, file))

    def _load_file(self, filepath):
        """Loads a single JSON file and stores it under its filename (without extension)."""
        base_name = os.path.splitext(os.path.basename(filepath))[0]  # Get filename without extension
        with open(filepath, "r", encoding="utf-8") as f:
            self.configs[base_name] = json.load(f)

    def get(self, filename, key, default=None):
        """Fetches a key from the specified config file, returning default if not found."""
        return self.configs.get(filename, {}).get(key, default)

    def __getitem__(self, filename):
        """Allows dictionary-like access: config['filename']['key']"""
        if filename in self.configs:
            return self.configs[filename]
        raise KeyError(f"Config '{filename}' not loaded.")

    def list_configs(self):
        """Returns a list of loaded config names."""
        return list(self.configs.keys())