from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from app import db
from app.models.user import User
from app.models.token import ApiToken

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
@auth_bp.route('/api/token', methods=['POST'])
def get_token():
    """Get API token with username/password"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate a new token
    token_value = secrets.token_hex(32)
    token = ApiToken(token=token_value, user_id=user.id)
    
    db.session.add(token)
    db.session.commit()
    
    return jsonify({
        'token': token_value,
        'user_id': user.id,
        'username': user.username
    })

@auth_bp.route('/api/register', methods=['POST'])
def register_api():
    """Register a new user via API"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data or 'first_name' not in data or 'last_name' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    

    user = User(username=data['username'])
    user.set_password(data['password'])
    user.first_name = data.get('first_name', '')
    user.last_name = data.get('last_name', '')
    user.is_approved = False
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Registration successful! Your account is pending admin approval.',
        'user_id': user.id
    })
    ## Create user
    #user = User(
    #    username=data['username'],
    #    password_hash=generate_password_hash(data['password']),
    #    email=data.get('email', '')
    #)
    #
    #db.session.add(user)
    #db.session.commit()
    #
    ## Generate a token for the new user
    #token_value = secrets.token_hex(32)
    #token = ApiToken(token=token_value, user_id=user.id)
    #
    #db.session.add(token)
    #db.session.commit()
    #
    #return jsonify({
    #    'message': 'User created successfully',
    #    'token': token_value,
    #    'user_id': user.id,
    #    'username': user.username
    #}), 201
