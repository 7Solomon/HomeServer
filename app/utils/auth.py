from functools import wraps
from flask import request, jsonify, g, redirect, url_for, flash
from flask_login import current_user
from app.models.token import ApiToken
from app.models.user import User


def valid_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Or from request parameters
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        # Check if token exists and is valid
        token_record = ApiToken.query.filter_by(token=token).first()
        if not token_record or not token_record.is_valid():
            return jsonify({'message': 'Invalid or expired token!'}), 401
            
        # Maybe add token refresh stuff
        # request.token = token_record
            
        return f(*args, **kwargs)
    return decorated_function

def admin_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First validate the token
        token_validator = valid_token(lambda: None)
        result = token_validator()
        if result is not None:
            return result  # Return error from token validation
            
        # Now check if token has admin privileges
        if not request.token.is_admin:
            return jsonify({'message': 'Admin privileges required!'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

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