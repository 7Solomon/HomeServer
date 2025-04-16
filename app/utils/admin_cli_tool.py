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
    # Import, Important because circular import issue
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