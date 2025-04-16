from flask import Blueprint

# Create blueprint
storage_bp = Blueprint('storage', __name__)

# Define constants
import os
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

# Import routes at the end to avoid circular imports
from app.blueprints.storage import web, api

