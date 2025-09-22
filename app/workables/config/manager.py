from dataclasses import dataclass
import os
import json
# Define the path to the project root relative to this file
# This file is in app/workables/config/
# Project root is ../../../../ from this file's location
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'HomeServer', 'instance', 'config.json')


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
    


#### I LIKE THIS BUT NOT IMPLEMENTED BECAUSE NOT WANT TO BREACK

#config = None
#@dataclass
#class Config:
#    config_json_not_empty: str
#    
#    YOUTUBE_API_KEY: str
#    channel_id: str
#    
#    server: str
#    name: str
#    password: str
#    
#    website_exists: str
#    website_url: str
#    update_url: str
#
#    threshold_db: str
#    ratio: str
#    attack: str
#    release: str
#
#    @staticmethod
#    def from_dict(data: dict):
#        return Config(
#            config_json_not_empty=data.get("config_json_not_empty", None),
#            YOUTUBE_API_KEY=data.get("YOUTUBE_API_KEY", None),
#            channel_id=data.get("channel_id", None),
#            server=data.get("server", None),
#            name=data.get("name", None),
#            password=data.get("password", None),
#            website_exists=data.get("website_exists", None),
#            website_url=data.get("website_url", None),
#            update_url=data.get("update_url", None),
#            threshold_db=data.get("threshold_db", None),
#            ratio=data.get("ratio", None),
#            attack=data.get("attack", None),
#            release=data.get("release", None)
#        )
