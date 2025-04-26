from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
import secrets
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
    
    # Get the token from session if it exists, then remove it
    token = session.pop('token', None)
    
    # Change the template path to use the existing template
    return render_template('auth/admin.html', users=users, token=token)

@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    # Commit user approval first
    db.session.commit()

    # Generate API token for the newly approved user - WITH user_id
    token = ApiToken(
        token=secrets.token_hex(32),
        user_id=user.id, # Associate token with the user
        is_active=True
    )
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

@admin_bp.route('/generate_admin_token', methods=['POST'])
@login_required
@admin_required
def generate_admin_token():
    # Generate a secure token
    token_value = secrets.token_hex(32)

    # Create the token with admin privileges and associate with the admin user
    token = ApiToken(
        token=token_value,
        user_id=current_user.id, # Associate with the admin generating it
        is_active=True,
        is_admin=True
    )

    db.session.add(token)
    db.session.commit()

    # Store token temporarily in session to display it once
    # Use a different session key to avoid conflict with auth blueprint
    session['generated_admin_token'] = token_value
    flash('Admin token generated successfully', 'success')

    # Redirect to the token management page instead
    return redirect(url_for('admin.manage_tokens'))

@admin_bp.route('/tokens', methods=['GET'])
@login_required
@admin_required
def manage_tokens():
    """Show all admin tokens"""
    from datetime import datetime

    # Fetch the generated token from session if it exists
    generated_token = session.pop('generated_admin_token', None)

    tokens = ApiToken.query.filter_by(is_admin=True).order_by(ApiToken.created_at.desc()).all()
    users = User.query.all()

    # Create a dictionary of users for easier lookups
    user_dict = {user.id: user for user in users}

    return render_template('admin/tokens.html', tokens=tokens, users=user_dict, now=datetime.utcnow(), generated_token=generated_token)

@admin_bp.route('/tokens/delete/<int:token_id>', methods=['POST'])
@login_required
@admin_required
def delete_token(token_id):
    """Delete an admin token"""
    token = ApiToken.query.get_or_404(token_id)
    
    db.session.delete(token)
    db.session.commit()
    
    flash('Token was successfully deleted', 'success')
    return redirect(url_for('admin.manage_tokens'))