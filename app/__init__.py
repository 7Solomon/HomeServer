from datetime import datetime, timezone
from app.utils.admin_cli_tool import create_admin, create_api_token, create_predigt_user
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

    @app.template_filter('make_aware')
    def make_aware_filter(dt):
        """Make a naive datetime timezone-aware (assume UTC)"""
        if dt is None:
            return None
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
            from datetime import timezone
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
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
    app.cli.add_command(create_api_token)
    app.cli.add_command(create_predigt_user)

    # Import and register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.storage import storage_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.ocr import ocr_bp
    #from app.blueprints.predigt_upload import predigt_upload_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(storage_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(ocr_bp, url_prefix="/ocr")
    #app.register_blueprint(predigt_upload_api_bp, url_prefix="/predigt_upload")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Import and register dynamic blueprints
        from app.utils.dynamic_blueprints import register_dynamic_blueprints
        register_dynamic_blueprints(app)
    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}
    
    # Add custom Jinja2 filter for safe datetime comparison
    @app.template_filter('is_expired')
    def is_expired_filter(expires_at):
        """Safely check if a datetime has expired"""
        if not expires_at:
            return False
        try:
            # Make sure both datetimes are timezone-aware
            now = datetime.now(timezone.utc)
            if expires_at.tzinfo is None:
                # Make expires_at timezone-aware if it isn't
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            elif now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            return expires_at < now
        except (TypeError, AttributeError):
            return None  # Return None to indicate error
    
    return app

