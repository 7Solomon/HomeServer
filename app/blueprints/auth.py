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

