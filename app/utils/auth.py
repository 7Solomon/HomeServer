from functools import wraps
from flask import request, jsonify, g, redirect, url_for, flash
from flask_login import current_user
from app.models.token import ApiToken
from app.models.user import User


def _get_token_from_request():
    """Helper to extract token from request."""
    token = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    # Fallback to X-API-TOKEN or query param if needed
    # elif 'X-API-TOKEN' in request.headers:
    #     token = request.headers['X-API-TOKEN']
    # elif request.args.get('token'):
    #     token = request.args.get('token')
    return token

def valid_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_str = _get_token_from_request()

        if not token_str:
            return jsonify({'error': 'Token is missing!'}), 401

        token_record = ApiToken.query.filter_by(token=token_str).first()
        if not token_record or not token_record.is_valid():
            return jsonify({'error': 'Invalid or expired token!'}), 401

        user = None
        if token_record.user_id:
            user = User.query.get(token_record.user_id)
            if not user:
                 # Should not happen if DB is consistent, but handle it
                 return jsonify({'error': 'User associated with token not found!'}), 401

        # Set context for downstream use
        g.token_record = token_record
        g.current_user = user # Can be None if token has no user_id

        return f(*args, **kwargs)
    return decorated_function

def admin_token(f):
    @wraps(f)
    @valid_token # Run token validation first, sets g.token_record and g.current_user
    def decorated_function(*args, **kwargs):
        # Check if token has admin privileges
        # Use g.token_record set by valid_token
        if not g.token_record or not g.token_record.is_admin:
            return jsonify({'error': 'Admin privileges required!'}), 403

        # Optionally check if the associated user (if any) is also an admin
        # if g.current_user and not g.current_user.is_admin:
        #     return jsonify({'error': 'Admin user required!'}), 403

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

def login_required(f):
    """
    Decorator to ensure the current user is logged in.
    Redirects to the login page if the user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            # Replace 'auth.login' with your actual login route
            return redirect(url_for('auth.login', next=request.url)) 
        return f(*args, **kwargs)
    return decorated_function


def approved_user_required(f):
    @wraps(f)
    @valid_token # Run token validation first, sets g.token_record and g.current_user
    def decorated_function(*args, **kwargs):
        # valid_token already validated the token and fetched the user into g.current_user
        if not g.current_user:
            # This implies the token was valid but not associated with a user
            return jsonify({'error': 'Token not associated with a user!'}), 401

        # Check approval status - THIS IS THE KEY PART
        if not g.current_user.is_approved:
            return jsonify({'error': 'Account pending approval'}), 403

        # g.current_user is already set by valid_token
        return f(*args, **kwargs)
    return decorated_function