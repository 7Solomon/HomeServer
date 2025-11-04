from datetime import datetime, timedelta, timezone
import secrets
import click
from flask.cli import with_appcontext


@click.command('create-admin')
@click.argument('username')
@click.argument('password')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def create_admin(username, password, first_name, last_name):
    """Create an admin user."""
    from app import db
    from app.models.user import User
    
    
    user = User.query.filter_by(username=username).first()
    if user:
        click.echo(f'User {username} already exists.')
        return
        
    user = User(username=username, role='admin', first_name=first_name, last_name=last_name, is_approved=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Admin user {username} created successfully.')


@click.command('create-api-token')
@click.option('--admin', is_flag=True, help="Create an admin-level API token.")
@click.option('--days-valid', default=30, type=int, help="Number of days the token will be valid.")
@with_appcontext
def create_api_token(admin, days_valid):
    """Generates a new API token and stores it in the ApiToken table."""
    from app import db
    from app.models.token import ApiToken # Import your ApiToken model

    token_string = secrets.token_urlsafe(32) # Generates a URL-safe text string, 43 characters long

    new_api_token = ApiToken(
        token=token_string,
        is_admin=admin,
        is_active=True, # Activate the token immediately
        expires_at=datetime.now(timezone.utc) + timedelta(days=days_valid)
    )

    db.session.add(new_api_token)
    db.session.commit()

    click.echo(f"API Token created successfully!")
    click.echo(f"{token_string}")
    click.echo(f"Admin privileges: {'Yes' if admin else 'No'}")
    click.echo(f"Expires at: {new_api_token.expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    click.echo("Store this token securely. It will not be shown again.")


@click.command('create-predigt-user')
@click.argument('username')
@click.argument('password')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def create_predigt_user(username, password, first_name, last_name):
    """Create a user with 'predigt' role."""
    from app import db
    from app.models.user import User
    
    user = User.query.filter_by(username=username).first()
    if user:
        click.echo(f'User {username} already exists.')
        return
        
    user = User(username=username, role='predigt', first_name=first_name, last_name=last_name, is_approved=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Predigt user {username} created successfully.')


@click.command('create-ocr-user')
@click.argument('username')
@click.argument('password')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def create_ocr_user(username, password, first_name, last_name):
    """Create a user with 'ocr' role."""
    from app import db
    from app.models.user import User
    
    user = User.query.filter_by(username=username).first()
    if user:
        click.echo(f'User {username} already exists.')
        return
        
    user = User(username=username, role='ocr', first_name=first_name, last_name=last_name, is_approved=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'OCR user {username} created successfully.')

@click.command('create-dating-graph-user')
@click.argument('username')
@click.argument('password')
@click.argument('first_name')
@click.argument('last_name')
@with_appcontext
def create_dating_graph_user(username, password, first_name, last_name):
    """Create a user with 'dating_graph' role."""
    from app import db
    from app.models.user import User
    
    user = User.query.filter_by(username=username).first()
    if user:
        click.echo(f'User {username} already exists.')
        return
        
    user = User(username=username, role='dating_graph', first_name=first_name, last_name=last_name, is_approved=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Dating Graph user {username} created successfully.')