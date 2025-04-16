from app import db
from datetime import datetime, timedelta, timezone

class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref='tokens')
    
    def is_valid(self):
        return self.is_active and self.expires_at > datetime.now(timezone.utc)
    
    def __repr__(self):
        return f'<ApiToken {self.id}>'
    
