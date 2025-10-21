from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from app import db
from app.models.user import User
from app.models.token import ApiToken
from app.utils.auth import admin_required

auth_bp = Blueprint('auth', __name__)

# Web interface routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login through web interface"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_approved:
                flash('Your account is pending admin approval.')
                return redirect(url_for('auth.login'))
            login_user(user, remember=True)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration through web interface"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validation
        if not username or not password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
            
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
            

        # Ask for 
        user = User(username=username, first_name=first_name, last_name=last_name)
        user.set_password(password)
        # Don't automatically approve users
        user.is_approved = False

        db.session.add(user)
        db.session.commit()

        flash('Registrierung erfolgreich! Bitte warten Sie auf die Genehmigung.', 'success')

    
    # GET request - show the form
    return render_template('auth/register.html')

# API authentication routes
@auth_bp.route('/api/request', methods=['POST'])
def request_token():
    """Request API token with name"""
    data = request.get_json()

    # Generate a new token
    token_value = secrets.token_hex(32)
    token = ApiToken(token=token_value)
    
    db.session.add(token)
    db.session.commit()
    
    return jsonify({
        'token': token_value,
        'message': 'Token erfolgreich eingerichtet, warte auf Genehmigung..'
    })

# Admin token generation routes
@auth_bp.route('/admin/token', methods=['GET'])
@login_required
@admin_required
def admin_token_page():
    """Show admin token generation page"""
    return render_template('auth/admin_token.html')

@auth_bp.route('/admin/token/generate', methods=['POST'])
@login_required
@admin_required
def generate_admin_token():
    """Generate a new admin token"""
    # Generate a secure token
    token_value = secrets.token_hex(32)
    
    # Create the token with admin privileges - using only fields that exist in the model
    token = ApiToken(
        token=token_value,
        is_active=True,
        is_admin=True
    )
    
    db.session.add(token)
    db.session.commit()
    
    # Store token in session to display it once
    session['token'] = token_value
    flash('Admin token generated successfully', 'success')
    
    return redirect(url_for('admin.pending_users'))

# API endpoint for programmatic admin token generation
@auth_bp.route('/api/admin/token', methods=['POST'])
@login_required
@admin_required
def api_generate_admin_token():
    """API endpoint to generate an admin token"""
    token_value = secrets.token_hex(32)
    
    token = ApiToken(
        token=token_value,
        user_id=current_user.id,
        is_active=True,
        is_admin=True
    )
    
    db.session.add(token)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Admin token generated successfully',
        'token': token_value
    })

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page - redirect to register if not logged in"""
    if not current_user.is_authenticated:
        flash('Bitte registrieren Sie sich oder melden Sie sich an', 'info')
        return redirect(url_for('auth.register'))
    
    from datetime import datetime, timezone
    from app.models.token import ApiToken
    
    # Get user's tokens
    user_tokens = ApiToken.query.filter_by(user_id=current_user.id).order_by(ApiToken.created_at.desc()).all()
    
    # Get user's file/directory counts
    from app.models.storage import File, Directory
    file_count = File.query.filter_by(user_id=current_user.id).count()
    directory_count = Directory.query.filter_by(user_id=current_user.id).count()
    
    return render_template('auth/profile.html', 
                         user_tokens=user_tokens,
                         file_count=file_count,
                         directory_count=directory_count,
                         now=datetime.now(timezone.utc))

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if first_name:
        current_user.first_name = first_name
    if last_name:
        current_user.last_name = last_name
    
    try:
        db.session.commit()
        flash('Profil erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren des Profils: {str(e)}', 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validation
    if not all([current_password, new_password, confirm_password]):
        flash('Alle Felder sind erforderlich', 'error')
        return redirect(url_for('auth.profile'))
    
    if not current_user.check_password(current_password):
        flash('Aktuelles Passwort ist falsch', 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('Neue Passwörter stimmen nicht überein', 'error')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('Passwort muss mindestens 6 Zeichen lang sein', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Passwort erfolgreich geändert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Ändern des Passworts: {str(e)}', 'error')
    
    return redirect(url_for('auth.profile'))

