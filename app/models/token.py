from app import db
from datetime import datetime, timedelta, timezone

class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    is_active = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='api_tokens', lazy=True)
    
    def is_valid(self):
        expires_at_aware = self.expires_at
        if hasattr(self.expires_at, 'tzinfo') and self.expires_at.tzinfo is None:
            print(f"  self.expires_at.tzinfo is None. Assuming UTC and making it aware.")
            expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
        elif hasattr(self.expires_at, 'tzinfo'):
            print(f"  self.expires_at.tzinfo: {self.expires_at.tzinfo}")
        else:
            print(f"  self.expires_at has no tzinfo attribute (should not happen with datetime objects)")

        current_utc_time = datetime.now(timezone.utc) 
        return self.is_active and expires_at_aware > current_utc_time

    
    
    def __repr__(self):
        return f'<ApiToken {self.id}>'
