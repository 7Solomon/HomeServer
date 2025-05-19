import os
import json
# Define the path to the project root relative to this file
# This file is in app/workables/config/
# Project root is ../../../../ from this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'instance', 'config.json')

def get_config():
    """Loads configuration from instance/config.json."""
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {CONFIG_FILE_PATH}")
        return {} # Return empty dict or raise an error
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in configuration file at {CONFIG_FILE_PATH}")
        return {} # Return empty dict or raise an error
    except Exception as e:
        print(f"An unexpected error occurred while reading config: {e}")
        return {}
