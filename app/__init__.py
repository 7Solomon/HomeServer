from datetime import datetime,timezone
from app.utils.admin_cli_tool import create_admin
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Default configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///home_server.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Override with custom config if provided
    if config:
        app.config.update(config)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    

    # Add Cli
    app.cli.add_command(create_admin)

    # Import and register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.storage import storage_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(storage_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Import and register dynamic blueprints
        from app.utils.dynamic_blueprints import register_dynamic_blueprints
        register_dynamic_blueprints(app)

    # Add context processor for template variables
    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}
    
    return app

