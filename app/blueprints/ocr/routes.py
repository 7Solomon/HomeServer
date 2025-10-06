from flask import render_template
from app.blueprints.ocr import ocr_bp
from app.utils.auth import approved_user_required

@ocr_bp.route('/page')
@approved_user_required
def page():
    """Main OCR page"""
    return render_template('ocr/ocr.html')