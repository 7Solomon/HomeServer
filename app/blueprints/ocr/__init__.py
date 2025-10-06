from flask import Blueprint

ocr_bp = Blueprint('ocr', __name__)

# Upload folder for OCR files
import os
from app.blueprints.storage import UPLOAD_FOLDER

OCR_UPLOAD_FOLDER = os.path.abspath(os.path.normpath(os.path.join(UPLOAD_FOLDER, 'ocr_temp')))
os.makedirs(OCR_UPLOAD_FOLDER, exist_ok=True)

from app.blueprints.ocr import routes, api