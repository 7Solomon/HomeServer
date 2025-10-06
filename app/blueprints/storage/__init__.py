from flask import Blueprint
import os

# Create blueprint
storage_bp = Blueprint('storage', __name__)

# Define constants - normalize paths for the current OS
UPLOAD_FOLDER = os.path.abspath(os.path.normpath(os.path.join('content', 'uploads')))
PREDIGT_FOLDER = os.path.abspath(os.path.normpath(os.path.join('content', 'predigten')))

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PREDIGT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'json'}

# Import routes at the end to avoid circular imports
from app.blueprints.storage import web, api, applications, utils, predigten, overleaf

