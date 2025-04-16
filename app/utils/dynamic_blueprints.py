import os
import importlib
from flask import Blueprint

def register_dynamic_blueprints(app):
    """
    Automatically register all blueprints located in the blueprints directory.
    This allows modular addition of features without modifying __init__.py
    """
    blueprint_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blueprints')
    
    # Skip if we're not in a proper directory structure
    if not os.path.exists(blueprint_dir):
        return
    
    # Get all Python files from the blueprints directory
    for filename in os.listdir(blueprint_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            
            # Skip already registered blueprints (done explicitly in __init__.py)
            if module_name in ['main', 'auth', 'storage', 'admin']:
                continue
                
            try:
                # Import the module
                module_path = f'app.blueprints.{module_name}'
                module = importlib.import_module(module_path)
                
                # Find blueprint objects
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, Blueprint):
                        # Register the blueprint
                        if item_name.endswith('_bp'):
                            url_prefix = f'/{module_name}'
                            app.register_blueprint(item, url_prefix=url_prefix)
                            print(f"Registered dynamic blueprint: {item_name}")
            except Exception as e:
                print(f"Error registering dynamic blueprint {module_name}: {e}")
