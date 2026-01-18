"""Configuration loader for FreeCAD MCP."""
import os
import json


DEFAULT_CONFIG = {
    "server": {
        "host": "localhost",
        "port": 9876,
        "max_clients": 5,
        "connection_timeout": 30,
        "buffer_size": 32768,
        "max_buffer_size": 1048576
    },
    "logging": {
        "max_lines": 100,
        "level": "INFO"
    },
    "security": {
        "allowed_modules": ["FreeCAD", "Part", "Draft", "Sketcher", "PartDesign", "Mesh", "Arch", "math", "numpy"],
        "enable_validation": True
    },
    "paths": {
        "macro_dir": "auto"
    }
}


def load_config(config_path=None):
    """Load configuration from file with fallback to defaults.

    Args:
        config_path: Optional path to config file. If None, searches for config.json
                    in the module directory.

    Returns:
        dict: Configuration dictionary with all settings.
    """
    if config_path is None:
        # Default to config.json in module directory
        module_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(module_dir, "config.json")

    # Start with default config
    config = DEFAULT_CONFIG.copy()

    # Try to load from file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # Deep merge file config over defaults
                config = _deep_merge(config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default configuration")
    else:
        print(f"Config file not found at {config_path}, using defaults")

    return config


def _deep_merge(base, override):
    """Deep merge override dict into base dict.

    Args:
        base: Base dictionary
        override: Dictionary to merge over base

    Returns:
        dict: Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
