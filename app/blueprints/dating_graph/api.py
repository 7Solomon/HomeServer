from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from app import db
from app.models.dating_graph import Category, Person, DateEvent, GraphSnapshot, person_category
from datetime import datetime
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError

from app.blueprints.dating_graph import dating_graph_bp

# ============================================================================
# WEB ROUTES
# ============================================================================

@dating_graph_bp.route('/page')
@login_required
def page():
    """Main dating graph page"""
    return render_template('dating_graph/dating_graph.html')


# ============================================================================
# API ENDPOINTS - PERSONS
# ============================================================================

@dating_graph_bp.route('/api/persons', methods=['GET'])
@login_required
def get_persons():
    """Get all persons with optional filters"""
    category_id = request.args.get('category_id', type=int)
    status = request.args.get('status')
    search = request.args.get('search')
    
    query = Person.query
    
    # Apply filters
    if category_id:
        query = query.join(Person.categories).filter(Category.id == category_id)
    
    if status:
        query = query.filter(Person.status == status)
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            or_(
                Person.name.ilike(search_term),
                Person.nickname.ilike(search_term),
                Person.custom_id.ilike(search_term)
            )
        )
    
    persons = query.all()
    return jsonify([p.to_dict() for p in persons])


@dating_graph_bp.route('/api/persons/<int:person_id>', methods=['GET'])
@login_required
def get_person(person_id):
    """Get single person details"""
    person = Person.query.get_or_404(person_id)
    
    # Include categories and dates
    data = person.to_dict()
    data['dates'] = [d.to_dict() for d in person.dates.order_by(DateEvent.date.desc())]
    
    return jsonify(data)

@dating_graph_bp.route('/api/persons', methods=['POST'])
@login_required
def create_person():
    """Create a new person"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        # Generate custom_id if not provided
        if not data.get('custom_id'):
            # Get first category if exists
            category_ids = data.get('category_ids', [])
            if category_ids:
                category = Category.query.get(category_ids[0])
                prefix = category.name.upper()[:4] if category else 'GEN'
            else:
                prefix = 'GEN'
            
            # Find next available number
            count = Person.query.filter(Person.custom_id.like(f'{prefix}_%')).count()
            custom_id = f'{prefix}_{count + 1:03d}'
        else:
            custom_id = data['custom_id']
        
        # Check if custom_id already exists
        if Person.query.filter_by(custom_id=custom_id).first():
            return jsonify({'error': 'Custom ID already exists'}), 400
        
        # Create person
        person = Person(
            name=data['name'],
            nickname=data.get('nickname'),
            custom_id=custom_id,
            fun_fact=data.get('fun_fact'),
            story=data.get('story'),
            notes=data.get('notes'),
            status=data.get('status', 'unknown'),
            first_contact_date=datetime.fromisoformat(data['first_contact_date']) if data.get('first_contact_date') else None,
            position_x=data.get('position_x'),
            position_y=data.get('position_y')
        )
        
        # Add categories
        if data.get('category_ids'):
            categories = Category.query.filter(Category.id.in_(data['category_ids'])).all()
            person.categories.extend(categories)
        
        db.session.add(person)
        db.session.commit()
        
        return jsonify(person.to_dict()), 201
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@dating_graph_bp.route('/api/persons/<int:person_id>', methods=['PUT'])
@login_required
def update_person(person_id):
    """Update person details"""
    person = Person.query.get_or_404(person_id)
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        person.name = data['name']
    if 'nickname' in data:
        person.nickname = data['nickname']
    if 'fun_fact' in data:
        person.fun_fact = data['fun_fact']
    if 'story' in data:
        person.story = data['story']
    if 'notes' in data:
        person.notes = data['notes']
    if 'status' in data:
        person.status = data['status']
    if 'first_contact_date' in data:
        person.first_contact_date = datetime.fromisoformat(data['first_contact_date']) if data['first_contact_date'] else None
    if 'last_contact_date' in data:
        person.last_contact_date = datetime.fromisoformat(data['last_contact_date']) if data['last_contact_date'] else None
    if 'position_x' in data:
        person.position_x = data['position_x']
    if 'position_y' in data:
        person.position_y = data['position_y']
    
    # Update categories
    if 'category_ids' in data:
        person.categories = []
        categories = Category.query.filter(Category.id.in_(data['category_ids'])).all()
        person.categories.extend(categories)
    
    person.updated_at = datetime.now()
    db.session.commit()
    
    return jsonify(person.to_dict())


@dating_graph_bp.route('/api/persons/<int:person_id>', methods=['DELETE'])
@login_required
def delete_person(person_id):
    """Delete a person"""
    person = Person.query.get_or_404(person_id)
    db.session.delete(person)
    db.session.commit()
    return jsonify({'message': 'Person deleted successfully'})


# ============================================================================
# API ENDPOINTS - CATEGORIES
# ============================================================================

@dating_graph_bp.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all categories"""
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])


@dating_graph_bp.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    """Create a new category"""
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    # Check if category already exists
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Category already exists'}), 400
    
    category = Category(
        name=data['name'],
        type=data.get('type', 'platform'),
        color=data.get('color', '#667eea'),
        icon=data.get('icon'),
        description=data.get('description')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201


@dating_graph_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """Update category"""
    category = Category.query.get_or_404(category_id)
    data = request.get_json()
    
    if 'name' in data:
        category.name = data['name']
    if 'type' in data:
        category.type = data['type']
    if 'color' in data:
        category.color = data['color']
    if 'icon' in data:
        category.icon = data['icon']
    if 'description' in data:
        category.description = data['description']
    
    db.session.commit()
    return jsonify(category.to_dict())


@dating_graph_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Delete a category"""
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'message': 'Category deleted successfully'})


# ============================================================================
# API ENDPOINTS - DATES
# ============================================================================

@dating_graph_bp.route('/api/dates', methods=['GET'])
@login_required
def get_dates():
    """Get all dates, optionally filtered by person"""
    person_id = request.args.get('person_id', type=int)
    
    query = DateEvent.query
    if person_id:
        query = query.filter_by(person_id=person_id)
    
    dates = query.order_by(DateEvent.date.desc()).all()
    return jsonify([d.to_dict() for d in dates])


@dating_graph_bp.route('/api/dates', methods=['POST'])
@login_required
def create_date():
    """Create a new date event"""
    data = request.get_json()
    
    if not data.get('person_id') or not data.get('date'):
        return jsonify({'error': 'Person ID and date are required'}), 400
    
    date_event = DateEvent(
        person_id=data['person_id'],
        date=datetime.fromisoformat(data['date']).date(),
        title=data.get('title'),
        location=data.get('location'),
        description=data.get('description'),
        rating=data.get('rating')
    )
    
    # Update person's last_contact_date
    person = Person.query.get(data['person_id'])
    if person:
        if not person.last_contact_date or date_event.date > person.last_contact_date:
            person.last_contact_date = date_event.date
    
    db.session.add(date_event)
    db.session.commit()
    
    return jsonify(date_event.to_dict()), 201


@dating_graph_bp.route('/api/dates/<int:date_id>', methods=['DELETE'])
@login_required
def delete_date(date_id):
    """Delete a date event"""
    date_event = DateEvent.query.get_or_404(date_id)
    db.session.delete(date_event)
    db.session.commit()
    return jsonify({'message': 'Date deleted successfully'})


# ============================================================================
# API ENDPOINTS - STATISTICS
# ============================================================================
# ...existing code...

@dating_graph_bp.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get overall statistics"""
    total_persons = Person.query.count()
    total_categories = Category.query.count()
    total_dates = DateEvent.query.count()
    
    # Calculate total connections based on person-category relationships
    # Count all category assignments across all persons
    total_connections = db.session.query(func.count()).select_from(person_category).scalar()
    
    # Status breakdown
    status_counts = db.session.query(
        Person.status,
        func.count(Person.id)
    ).group_by(Person.status).all()
    
    # Category breakdown
    category_stats = []
    for category in Category.query.all():
        category_stats.append({
            'name': category.name,
            'count': category.persons.count(),
            'color': category.color
        })
    
    # Recent activity
    recent_dates = DateEvent.query.order_by(DateEvent.date.desc()).limit(5).all()
    
    return jsonify({
        'total_persons': total_persons,
        'total_categories': total_categories,
        'total_connections': total_connections, 
        'total_dates': total_dates,
        'status_breakdown': dict(status_counts),
        'category_stats': category_stats,
        'recent_dates': [d.to_dict() for d in recent_dates]
    })

# ============================================================================
# API ENDPOINTS - GRAPH DATA (UPDATED)
# ============================================================================
@dating_graph_bp.route('/api/graph-data', methods=['GET'])
@login_required
def get_graph_data():
    """Get complete graph data: categories as central nodes, persons connected to categories"""
    persons = Person.query.all()
    categories = Category.query.all()
    
    # Format for vis.js
    nodes = []
    edges = []
    
    # Add category nodes (central hubs) - LARGER AND MORE PROMINENT
    for category in categories:
        person_count = category.persons.count()
        nodes.append({
            'id': f'cat_{category.id}',
            'label': f"📁 {category.name}\n({person_count} {'Person' if person_count == 1 else 'Personen'})",
            'title': f"{category.name}\n{category.description or ''}\n{person_count} Personen",
            'type': 'category',
            'color': {
                'background': category.color,
                'border': category.color,
                'highlight': {
                    'background': category.color,
                    'border': '#1f2937'
                }
            },
            'shape': 'box',
            'size': 40,  # Larger than person nodes
            'font': {
                'size': 18,
                'color': '#ffffff',
                'bold': True,
                'multi': 'html'
            },
            'borderWidth': 3,
            'x': category.position_x,
            'y': category.position_y,
            'fixed': False,
            'icon': category.icon,
            'margin': 15
        })
    
    # Add person nodes
    for person in persons:
        # Get status icon
        status_icons = {
            'interested': '💖',
            'dating': '❤️',
            'friend': '😊',
            'no_connection': '😐',
            'ghosted': '👻',
            'unknown': '❓'
        }
        
        nodes.append({
            'id': f'person_{person.id}',
            'label': f"{status_icons.get(person.status, '❓')} {person.nickname or person.name}",
            'title': f"{person.name}\n{person.custom_id}\nStatus: {person.status}",
            'type': 'person',
            'status': person.status,
            'custom_id': person.custom_id,
            'person_id': person.id,
            'shape': 'box',
            'size': 20,
            'font': {
                'size': 14,
                'color': '#1f2937'
            },
            'x': person.position_x,
            'y': person.position_y,
            'fixed': False,
            'borderWidth': 2,
            'color': {
                'border': person.categories[0].color if person.categories else '#667eea',
                'background': '#ffffff',
                'highlight': {
                    'border': person.categories[0].color if person.categories else '#667eea',
                    'background': '#f0f0f0'
                }
            }
        })
        
        # Create edges from person to their categories
        for category in person.categories:
            edges.append({
                'from': f'person_{person.id}',
                'to': f'cat_{category.id}',
                'color': {
                    'color': category.color,
                    'opacity': 0.5
                },
                'width': 2,
                'smooth': {
                    'enabled': True,
                    'type': 'continuous'
                }
            })
    
    return jsonify({
        'nodes': nodes,
        'edges': edges
    })


@dating_graph_bp.route('/api/graph-data/save-positions', methods=['POST'])
@login_required
def save_positions():
    """Save node positions from graph"""
    data = request.get_json()
    positions = data.get('positions', {})
    
    for node_id, pos in positions.items():
        if node_id.startswith('person_'):
            person_id = int(node_id.replace('person_', ''))
            person = Person.query.get(person_id)
            if person:
                person.position_x = pos.get('x')
                person.position_y = pos.get('y')
        elif node_id.startswith('cat_'):
            category_id = int(node_id.replace('cat_', ''))
            category = Category.query.get(category_id)
            if category:
                category.position_x = pos.get('x')
                category.position_y = pos.get('y')
    
    db.session.commit()
    return jsonify({'message': 'Positions saved successfully'})

@dating_graph_bp.route('/api/quick-stats', methods=['GET'])
@login_required
def get_quick_stats():
    """Lightweight stats for cards view"""
    return jsonify({
        'total_persons': Person.query.count(),
        'total_categories': Category.query.count(),
        'total_dates': DateEvent.query.count()
    })



# ============================================================================
# API ENDPOINTS - SNAPSHOTS
# ============================================================================

@dating_graph_bp.route('/api/snapshots', methods=['GET'])
@login_required
def get_snapshots():
    """Get all saved graph snapshots"""
    snapshots = GraphSnapshot.query.all()
    return jsonify([s.to_dict() for s in snapshots])


@dating_graph_bp.route('/api/snapshots', methods=['POST'])
@login_required
def create_snapshot():
    """Save current graph layout"""
    data = request.get_json()
    
    snapshot = GraphSnapshot(
        name=data['name'],
        description=data.get('description'),
        layout_data=data['layout_data']
    )
    
    db.session.add(snapshot)
    db.session.commit()
    
    return jsonify(snapshot.to_dict()), 201


@dating_graph_bp.route('/api/snapshots/<int:snapshot_id>', methods=['DELETE'])
@login_required
def delete_snapshot(snapshot_id):
    """Delete a snapshot"""
    snapshot = GraphSnapshot.query.get_or_404(snapshot_id)
    db.session.delete(snapshot)
    db.session.commit()
    return jsonify({'message': 'Snapshot deleted successfully'})