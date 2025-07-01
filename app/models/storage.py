from app import db
from datetime import datetime, timezone

class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('directory.id'), nullable=True)
    is_admin_only = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    files = db.relationship('File', backref='directory', lazy=True)
    parent = db.relationship('Directory', backref='subdirectories', remote_side=[id])
    
    def __repr__(self):
        return f'<Directory {self.name}>'

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    path = db.Column(db.String(256), nullable=False)
    size = db.Column(db.Integer, nullable=False)  # Size in bytes
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    directory_id = db.Column(db.Integer, db.ForeignKey('directory.id'), nullable=True)
    
    def __repr__(self):
        return f'<File {self.name}>'