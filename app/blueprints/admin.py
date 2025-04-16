from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.token import ApiToken
from app.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/pending', methods=['GET'])
@login_required
@admin_required
def pending_users():
    users = User.query.filter_by(is_approved=False).all()
    return render_template('admin/pending_users.html', users=users)

@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    # Generate API token for the newly approved user
    token = ApiToken(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    
    flash(f'User {user.username} has been approved')
    return redirect(url_for('admin.pending_users'))

@admin_bp.route('/api/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def api_approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    # Generate API token for the newly approved user
    token = ApiToken(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'User {user.username} has been approved',
        'token': token.token
    })

@admin_bp.route('/decline/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def decline_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Store username for the success message
    username = user.username
    
    # Delete the user from the database
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been declined and removed', 'warning')
    return redirect(url_for('admin.pending_users'))