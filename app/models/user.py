from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # email = db.Column(db.String(128)) # qutshcing bruache ich nicht
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    is_approved = db.Column(db.Boolean, default=False)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    @property
    def is_predigt_berechtigt(self):
        return self.role in ['admin', 'predigt']
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        """Check if provided password matches the stored hash"""
        return check_password_hash(self.password_hash, password)
    
   
    # Relationships for storage system
    files = db.relationship('File', backref='user', lazy=True)
    directories = db.relationship('Directory', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))