from app import db
from datetime import datetime, timezone

class Predigt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    youtube_url = db.Column(db.String(255), unique=True, nullable=False)
    youtube_video_id = db.Column(db.String(50), nullable=True) # Extracted from URL
    downloaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    local_file_path = db.Column(db.String(512), nullable=True) # Path to the audio file after download
    is_compressed = db.Column(db.Boolean, default=False)
    compressed_at = db.Column(db.DateTime, nullable=True)
    ftp_remote_path = db.Column(db.String(512), nullable=True) # Path on the FTP server
    uploaded_to_ftp_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='streamed') # e.g., streamed,cut, downloaded, compressed, uploaded, error
    error_message = db.Column(db.Text, nullable=True) # To store any error messages during processing


    def __repr__(self):
        return f'<Predigt {self.id} - {self.title}>'