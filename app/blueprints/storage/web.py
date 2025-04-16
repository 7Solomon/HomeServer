from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
import os

from app.blueprints.storage.utils import file_icon, format_size
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp
from app.models.storage import Directory, File
from app.utils.auth import admin_required



# Admin view to manage all files in system
@storage_bp.route('/admin/files')
@login_required
@admin_required
def admin_files():
    """Admin view to see all files regardless of user"""
    directories = Directory.query.filter_by(parent_id=None).all()
    files = File.query.filter_by(directory_id=None).all()
    
    return render_template(
        'storage/admin_files.html', 
        files=files, 
        directories=directories,
        path=[],
        current_dir=None,
        parent_dir=None,
        file_icon=file_icon,
        format_size=format_size
    )

@storage_bp.route('/admin/directory/<int:dir_id>')
@login_required
@admin_required
def admin_directory(dir_id):
    """Admin view for any directory regardless of owner"""
    current_dir = Directory.query.get_or_404(dir_id)
    
    # Calculate directory path
    path = []
    parent = current_dir
    while parent:
        path.insert(0, parent)
        parent = parent.parent
    
    # Get subdirectories and files
    directories = Directory.query.filter_by(parent_id=dir_id).all()
    files = File.query.filter_by(directory_id=dir_id).all()
    
    return render_template(
        'storage/admin_files.html', 
        files=files, 
        directories=directories,
        path=path[:-1],
        current_dir=current_dir,
        parent_dir=current_dir.parent,
        file_icon=file_icon,
        format_size=format_size
    )

# Admin route to delete files
@storage_bp.route('/admin/delete/file/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_file(file_id):
    """Admin route to delete any file"""
    file = File.query.get_or_404(file_id)
    
    # Delete physical file
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, file.path))
    except (OSError, FileNotFoundError):
        pass  # Ignore errors if file doesn't exist
    
    # Delete database entry
    db.session.delete(file)
    db.session.commit()
    
    flash('File deleted successfully.', 'success')
    
    # Redirect back to referring page
    referrer = request.referrer or url_for('storage.admin_files')
    return redirect(referrer)

# Admin route to delete directories
@storage_bp.route('/admin/delete/directory/<int:dir_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_directory(dir_id):
    """Admin route to delete any directory and its contents"""
    directory = Directory.query.get_or_404(dir_id)
    parent_id = directory.parent_id
    
    # Use recursive function to delete all contents
    delete_directory_recursive(directory)
    
    flash('Directory and all its contents deleted successfully.', 'success')
    
    # Redirect based on parent
    if parent_id:
        return redirect(url_for('storage.admin_directory', dir_id=parent_id))
    else:
        return redirect(url_for('storage.admin_files'))

# Admin route to move files
@storage_bp.route('/admin/move/file/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def admin_move_file(file_id):
    """Move a file to another directory"""
    file = File.query.get_or_404(file_id)
    target_dir_id = request.form.get('directory_id')
    
    if target_dir_id:
        if target_dir_id == "root":
            file.directory_id = None
        else:
            target_dir = Directory.query.get_or_404(target_dir_id)
            file.directory_id = target_dir.id
    else:
        file.directory_id = None
    
    db.session.commit()
    flash('File moved successfully.', 'success')
    
    # Redirect back to referring page
    referrer = request.referrer or url_for('storage.admin_files')
    return redirect(referrer)

# Admin route to move directories
@storage_bp.route('/admin/move/directory/<int:dir_id>', methods=['POST'])
@login_required
@admin_required
def admin_move_directory(dir_id):
    """Move a directory to another directory"""
    directory = Directory.query.get_or_404(dir_id)
    target_dir_id = request.form.get('parent_id')
    
    # Prevent circular references
    if target_dir_id:
        if target_dir_id == "root":
            directory.parent_id = None
        else:
            target_dir = Directory.query.get_or_404(target_dir_id)
            # Check that target is not a child of current directory
            if is_descendant(target_dir, directory):
                flash('Cannot move a directory into its own subdirectory.', 'error')
                referrer = request.referrer or url_for('storage.admin_files')
                return redirect(referrer)
            directory.parent_id = target_dir.id
    else:
        directory.parent_id = None
    
    db.session.commit()
    flash('Directory moved successfully.', 'success')
    
    # Redirect back to referring page
    referrer = request.referrer or url_for('storage.admin_files')
    return redirect(referrer)

# Admin route to change file owner
@storage_bp.route('/admin/change-owner/<string:type>/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_change_owner(type, item_id):
    """Change the owner of a file or directory"""
    from app.models.user import User
    
    user_id = request.form.get('user_id')
    if not user_id:
        flash('No user selected.', 'error')
        return redirect(request.referrer or url_for('storage.admin_files'))
    
    user = User.query.get_or_404(user_id)
    
    if type == 'file':
        item = File.query.get_or_404(item_id)
    else:
        item = Directory.query.get_or_404(item_id)
    
    item.user_id = user.id
    db.session.commit()
    
    flash(f'{type.capitalize()} ownership changed to {user.username}.', 'success')
    return redirect(request.referrer or url_for('storage.admin_files'))

# User view to manage own files
@storage_bp.route('/files')
@login_required
def files():
    """User view to see own root directories and files"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))
    directories = Directory.query.filter_by(parent_id=None, user_id=current_user.id).all()
    files = File.query.filter_by(directory_id=None, user_id=current_user.id).all()
    return render_template(
        'storage/files.html',
        files=files,
        directories=directories,
        path=[],
        current_dir=None,
        parent_dir=None,
        file_icon=file_icon,
        format_size=format_size
    )

@storage_bp.route('/directory/<int:dir_id>')
@login_required
def directory(dir_id):
    """User view for a directory"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))
    current_dir = Directory.query.get_or_404(dir_id)
    if current_dir.user_id != current_user.id:
        flash('Permission denied.', 'error')
        return redirect(url_for('storage.files'))
    # Build breadcrumb path
    path = []
    parent = current_dir
    while parent:
        path.insert(0, parent)
        parent = parent.parent
    directories = Directory.query.filter_by(parent_id=dir_id, user_id=current_user.id).all()
    files = File.query.filter_by(directory_id=dir_id, user_id=current_user.id).all()
    return render_template(
        'storage/files.html',
        files=files,
        directories=directories,
        path=path[:-1],
        current_dir=current_dir,
        parent_dir=current_dir.parent,
        file_icon=file_icon,
        format_size=format_size
    )

# Helper functions for admin routes
def delete_directory_recursive(directory):
    """Recursively delete a directory and all its contents"""
    # First delete all files in this directory
    for file in File.query.filter_by(directory_id=directory.id).all():
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, file.path))
        except (OSError, FileNotFoundError):
            pass
        db.session.delete(file)
    
    # Then recursively delete all subdirectories
    for subdir in Directory.query.filter_by(parent_id=directory.id).all():
        delete_directory_recursive(subdir)
    
    # Finally delete this directory
    db.session.delete(directory)
    db.session.commit()

def is_descendant(possible_descendant, ancestor):
    """Check if possible_descendant is a descendant of ancestor"""
    if possible_descendant.id == ancestor.id:
        return True
        
    parent = possible_descendant.parent
    while parent:
        if parent.id == ancestor.id:
            return True
        parent = parent.parent
        
    return False