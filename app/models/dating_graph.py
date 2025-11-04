from app import db
from datetime import datetime, timezone

# Relationship table for many-to-many between Person and Category
person_category = db.Table('person_category',
    db.Column('person_id', db.Integer, db.ForeignKey('person.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.now(timezone.utc))
)


class DatingProfile(db.Model):
    """Represents a dating profile being tracked"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    profile_name = db.Column(db.String(100)) 
    is_default = db.Column(db.Boolean, default=False)
    color_theme = db.Column(db.String(7), default='#667eea')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Person(db.Model):
    """
    Represents a person in the dating graph
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), nullable=True)
    custom_id = db.Column(db.String(50), unique=True, nullable=False)  # e.g., "HINGE_001"
    
    # Details
    fun_fact = db.Column(db.Text, nullable=True)
    story = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Status & Dating Info
    status = db.Column(db.String(50), default='unknown')  # interested, dating, friend, no_connection, ghosted
    first_contact_date = db.Column(db.Date, nullable=True)
    last_contact_date = db.Column(db.Date, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Visual positioning (for graph layout persistence)
    position_x = db.Column(db.Float, nullable=True)
    position_y = db.Column(db.Float, nullable=True)
    
    # Relationships
    categories = db.relationship('Category', secondary=person_category, backref=db.backref('persons', lazy='dynamic'))
    connections_from = db.relationship('Connection', foreign_keys='Connection.from_person_id', backref='from_person', lazy='dynamic', cascade='all, delete-orphan')
    connections_to = db.relationship('Connection', foreign_keys='Connection.to_person_id', backref='to_person', lazy='dynamic', cascade='all, delete-orphan')
    dates = db.relationship('DateEvent', backref='person', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Person {self.custom_id} - {self.name}>'
    
    def to_dict(self):
        """Convert person to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'nickname': self.nickname,
            'custom_id': self.custom_id,
            'fun_fact': self.fun_fact,
            'story': self.story,
            'notes': self.notes,
            'status': self.status,
            'first_contact_date': self.first_contact_date.isoformat() if self.first_contact_date else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'categories': [cat.to_dict() for cat in self.categories],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Category(db.Model):
    """
    Categories like "Hinge", "Tinder", "Introduced by Fabi", etc.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(50), default='platform')  # platform, introduction, event, other
    color = db.Column(db.String(7), default='#667eea')  # Hex color for visual distinction
    icon = db.Column(db.String(50), nullable=True)  # Font Awesome icon name
    description = db.Column(db.Text, nullable=True)
    
    # Visual positioning (for graph layout persistence)
    position_x = db.Column(db.Float, nullable=True)
    position_y = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'color': self.color,
            'icon': self.icon,
            'description': self.description,
            'person_count': self.persons.count(),
            'position_x': self.position_x,
            'position_y': self.position_y,
            'created_at': self.created_at.isoformat()
        }


class Connection(db.Model):
    """
    Represents connections between people (e.g., "Sarah introduced me to Anna")
    """
    id = db.Column(db.Integer, primary_key=True)
    
    from_person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    to_person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    
    connection_type = db.Column(db.String(50), default='knows')  # introduced, friend_of, dated, knows
    description = db.Column(db.Text, nullable=True)
    strength = db.Column(db.Integer, default=5)  # 1-10 scale
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        db.UniqueConstraint('from_person_id', 'to_person_id', 'connection_type', name='unique_connection'),
    )
    
    def __repr__(self):
        return f'<Connection {self.from_person_id} -> {self.to_person_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'from_person_id': self.from_person_id,
            'to_person_id': self.to_person_id,
            'connection_type': self.connection_type,
            'description': self.description,
            'strength': self.strength,
            'created_at': self.created_at.isoformat()
        }


class DateEvent(db.Model):
    """
    Represents actual dates/meetings with people
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<DateEvent {self.person_id} on {self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'person_id': self.person_id,
            'date': self.date.isoformat(),
            'title': self.title,
            'location': self.location,
            'description': self.description,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }


class GraphSnapshot(db.Model):
    """
    Saves graph layouts for different views
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    layout_data = db.Column(db.JSON, nullable=False)  # Stores positions and settings
    
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<GraphSnapshot {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'layout_data': self.layout_data,
            'created_at': self.created_at.isoformat()
        }