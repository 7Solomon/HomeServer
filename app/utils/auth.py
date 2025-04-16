from functools import wraps
from flask import request, jsonify, g, redirect, url_for, flash
from flask_login import current_user
from app.models.token import ApiToken
from app.models.user import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # Check if token is in request arguments
        if not token and 'token' in request.args:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
            # Find the token in database
            token_record = ApiToken.query.filter_by(token=token).first()
            
            if not token_record or not token_record.is_valid():
                return jsonify({'error': 'Token is invalid or expired!'}), 401
            
            # Get the user
            user = User.query.get(token_record.user_id)
            if not user:
                return jsonify({'error': 'User not found!'}), 401
                
            # Store user in flask g object for route functions to use
            g.current_user = user
            
        except Exception as e:
            return jsonify({'error': f'Token authentication error: {str(e)}'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator to restrict access to admin users only.
    Must be used after @login_required to ensure user is authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def approved_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Step 1: Extract token from request headers
        token = None
        if 'X-API-TOKEN' in request.headers:
            token = request.headers['X-API-TOKEN']
        
        # Step 2: Check if token exists
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        # Step 3: Validate the token from database    
        api_token = ApiToken.query.filter_by(token=token).first()
        if not api_token or api_token.is_expired():
            return jsonify({'error': 'Invalid or expired token!'}), 401
        
        # Step 4: Get associated user
        user = User.query.get(api_token.user_id)
        if not user:
            return jsonify({'error': 'User not found!'}), 401
        
        # Step 5: Check approval status - THIS IS THE KEY PART
        if not user.is_approved:
            return jsonify({'error': 'Account pending approval'}), 403
        
        # Step 6: Make user available to endpoint function
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function