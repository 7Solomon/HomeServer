from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
import secrets
import os
import json

from flask_login import current_user # Added import
from app import db
from app.models.user import User
from app.models.token import ApiToken
from app.utils.auth import admin_required, login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

CONFIG_FILENAME = 'config.json'

def get_config_file_path():
    return os.path.join(current_app.instance_path, CONFIG_FILENAME)

@admin_bp.route('/config', methods=['GET'])
@login_required
@admin_required
def config_page():
    config_content = ""
    config_file_path = get_config_file_path()
    try:
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
    except Exception as e:
        flash(f"Error reading config file: {e}", "error")
    return render_template('admin/config_page.html', config_content=config_content)

@admin_bp.route('/config/upload', methods=['POST'])
@login_required
@admin_required
def upload_config():
    if 'config_file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('admin.config_page'))

    file = request.files['config_file']
    if file.filename == '':
        flash('No file selected for uploading.', 'error')
        return redirect(url_for('admin.config_page'))

    if file and file.filename.endswith('.json'):
        config_file_path = get_config_file_path()
        try:
            # Ensure instance directory exists
            os.makedirs(current_app.instance_path, exist_ok=True)
            file.save(config_file_path)
            flash('Configuration file uploaded successfully.', 'success')
        except Exception as e:
            flash(f"Error saving uploaded config file: {e}", "error")
    else:
        flash('Invalid file type. Please upload a .json file.', 'error')

    return redirect(url_for('admin.config_page'))

@admin_bp.route('/config/save', methods=['POST'])
@login_required
@admin_required
def save_config():
    config_data = request.form.get('config_content')
    if config_data is None:
        flash('No content received to save.', 'error')
        return redirect(url_for('admin.config_page'))

    config_file_path = get_config_file_path()
    try:
        # Validate if it's valid JSON before saving
        json.loads(config_data) # This will raise an error if not valid JSON
        
        # Ensure instance directory exists
        os.makedirs(current_app.instance_path, exist_ok=True)
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(config_data)
        flash('Configuration saved successfully.', 'success')
    except json.JSONDecodeError:
        flash('Invalid JSON content. Please correct it before saving.', 'error')
    except Exception as e:
        flash(f"Error saving configuration: {e}", "error")
        
    return redirect(url_for('admin.config'))

@admin_bp.route('/pending', methods=['GET'])
@login_required
@admin_required
def pending_users():
    users = User.query.filter_by(is_approved=False).all()
    
    # Get the token from session if it exists, then remove it
    token = session.pop('token', None)
    
    # Change the template path to use the existing template
    return render_template('admin/admin.html', users=users, token=token)

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
    """Show all tokens (admin and user tokens)"""
    # Fetch the generated token from session if it exists
    generated_token = session.pop('generated_admin_token', None)

    # Get ALL tokens, ordered by creation date (newest first)
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    users = User.query.all()

    # Create a dictionary of users for easier lookups
    user_dict = {user.id: user for user in users}

    # Remove 'now' from here since it's injected globally
    return render_template('admin/tokens.html', 
                         tokens=tokens, 
                         users=user_dict, 
                         generated_token=generated_token)

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

@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def manage_users():
    """Show all users with search and filter capabilities"""
    from datetime import datetime, timezone
    
    # Get search query
    search_query = request.args.get('search', '').strip()
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')  # all, approved, pending
    role_filter = request.args.get('role', 'all')  # all, admin, user, predigt
    
    # Start with base query
    query = User.query
    
    # Apply search filter
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status_filter == 'approved':
        query = query.filter_by(is_approved=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_approved=False)
    
    # Apply role filter
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    # Get all users ordered by creation date
    users = query.order_by(User.id.desc()).all()
    
    # Get token counts per user
    token_counts = {}
    for user in users:
        token_counts[user.id] = ApiToken.query.filter_by(user_id=user.id).count()
    
    return render_template('admin/users.html', 
                         users=users, 
                         token_counts=token_counts,
                         search_query=search_query,
                         status_filter=status_filter,
                         role_filter=role_filter,
                         now=datetime.now(timezone.utc))

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    username = request.form.get('username')
    password = request.form.get('password')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    role = request.form.get('role', 'user')
    is_approved = request.form.get('is_approved') == 'on'
    
    # Validation
    if not all([username, password, first_name, last_name]):
        flash('Alle Felder sind erforderlich', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        flash('Benutzername existiert bereits', 'error')
        return redirect(url_for('admin.manage_users'))
    
    try:
        # Create new user
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_approved=is_approved
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Benutzer {username} erfolgreich erstellt', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Erstellen des Benutzers: {e}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent editing yourself
    from flask_login import current_user
    if user.id == current_user.id:
        flash('Sie können Ihr eigenes Konto nicht bearbeiten', 'warning')
        return redirect(url_for('admin.manage_users'))
    
    user.first_name = request.form.get('first_name', user.first_name)
    user.last_name = request.form.get('last_name', user.last_name)
    user.role = request.form.get('role', user.role)
    user.is_approved = request.form.get('is_approved') == 'on'
    
    # Update password if provided
    new_password = request.form.get('password')
    if new_password:
        user.set_password(new_password)
    
    try:
        db.session.commit()
        flash(f'Benutzer {user.username} erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren des Benutzers: {e}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user and all associated data"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    from flask_login import current_user
    if user.id == current_user.id:
        flash('Sie können Ihr eigenes Konto nicht löschen', 'error')
        return redirect(url_for('admin.manage_users'))
    
    username = user.username
    
    try:
        # Delete associated tokens
        ApiToken.query.filter_by(user_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Benutzer {username} und alle zugehörigen Daten wurden gelöscht', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen des Benutzers: {e}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/toggle-approval/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_approval(user_id):
    """Toggle user approval status"""
    user = User.query.get_or_404(user_id)
    
    user.is_approved = not user.is_approved
    
    try:
        db.session.commit()
        status = "genehmigt" if user.is_approved else "gesperrt"
        flash(f'Benutzer {user.username} wurde {status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Ändern des Status: {e}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    from app.models.token import ApiToken
    
    # Get user's tokens
    user_tokens = ApiToken.query.filter_by(user_id=current_user.id).order_by(ApiToken.created_at.desc()).all()
    
    # Get user's file/directory counts
    from app.models.storage import File, Directory
    file_count = File.query.filter_by(user_id=current_user.id).count()
    directory_count = Directory.query.filter_by(user_id=current_user.id).count()
    
    # Remove 'now' from here
    return render_template('auth/profile.html', 
                         user_tokens=user_tokens,
                         file_count=file_count,
                         directory_count=directory_count)