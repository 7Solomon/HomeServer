import uuid
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
import os
from werkzeug.utils import secure_filename

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
        'storage/files.html',  # Use the consolidated template
        files=files,
        directories=directories,
        path=[],
        current_dir=None,
        parent_dir=None,
        file_icon=file_icon,
        format_size=format_size,
        is_admin_view=True # Pass flag to template
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
        'storage/files.html', # Use the consolidated template
        files=files,
        directories=directories,
        path=path[:-1],
        current_dir=current_dir,
        parent_dir=current_dir.parent,
        file_icon=file_icon,
        format_size=format_size,
        is_admin_view=True # Pass flag to template
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


# User route to create a new directory
@storage_bp.route('/admin/directory/create', methods=['POST'])
@login_required
@admin_required
def create_directory():
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))

    name = request.form.get('name')
    parent_id_str = request.form.get('parent_id') # Will be string "None" or an ID

    # Determine redirect URL based on parent_id for error cases
    redirect_url = url_for('storage.files')
    if parent_id_str and parent_id_str != "None" and parent_id_str.isdigit():
        redirect_url = url_for('storage.directory', dir_id=int(parent_id_str))

    if not name or not name.strip():
        flash('Directory name cannot be empty.', 'error')
        return redirect(redirect_url)
    
    name = name.strip()

    parent_dir = None
    parent_id_for_db = None
    if parent_id_str and parent_id_str != "None" and parent_id_str.isdigit():
        parent_id = int(parent_id_str)
        parent_dir = Directory.query.filter_by(id=parent_id, user_id=current_user.id).first()
        if not parent_dir:
            flash('Parent directory not found or access denied.', 'error')
            return redirect(url_for('storage.files')) # Fallback to root if parent_id is problematic
        parent_id_for_db = parent_dir.id
    
    # Check for duplicate directory name within the same parent and for the same user
    existing_directory = Directory.query.filter_by(
        name=name,
        user_id=current_user.id,
        parent_id=parent_id_for_db
    ).first()

    if existing_directory:
        flash(f'A directory named "{name}" already exists here.', 'error')
        return redirect(redirect_url)

    new_dir = Directory(
        name=name,
        user_id=current_user.id,
        parent_id=parent_id_for_db
    )
    db.session.add(new_dir)
    db.session.commit()
    flash('Directory created successfully.', 'success')

    return redirect(redirect_url)

# User route to upload a new file
@storage_bp.route('/admin/file/upload', methods=['POST'])
@login_required
@admin_required
def upload_file():
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))

    # Determine redirect URL based on directory_id for error/success cases
    directory_id_str = request.form.get('directory_id') # Will be string "None" or an ID
    redirect_url = url_for('storage.files')
    target_dir_id_for_db = None
    target_dir = None

    if directory_id_str and directory_id_str != "None" and directory_id_str.isdigit():
        directory_id = int(directory_id_str)
        target_dir = Directory.query.filter_by(id=directory_id, user_id=current_user.id).first()
        if not target_dir:
            flash('Target directory not found or access denied.', 'error')
            return redirect(url_for('storage.files')) # Fallback to root
        target_dir_id_for_db = target_dir.id
        redirect_url = url_for('storage.directory', dir_id=target_dir.id)

    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(request.referrer or redirect_url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(request.referrer or redirect_url)

    if file:
        original_filename = secure_filename(file.filename)
        
        # Check for duplicate file name (original name) within the same directory and for the same user
        existing_file = File.query.filter_by(
            name=original_filename,
            user_id=current_user.id,
            directory_id=target_dir_id_for_db
        ).first()

        if existing_file:
            flash(f'A file named "{original_filename}" already exists in this location.', 'error')
            return redirect(redirect_url)

        _, extension = os.path.splitext(original_filename)
        unique_filename_for_storage = str(uuid.uuid4()) + extension
        
        file_path_on_disk = os.path.join(UPLOAD_FOLDER, unique_filename_for_storage)
        
        try:
            file.save(file_path_on_disk)
            file_size = os.path.getsize(file_path_on_disk)

            new_file_db = File(
                name=original_filename,
                path=unique_filename_for_storage,
                size=file_size,
                user_id=current_user.id,
                directory_id=target_dir_id_for_db
            )
            db.session.add(new_file_db)
            db.session.commit()
            flash('File uploaded successfully.', 'success')
        except Exception as e:
            if os.path.exists(file_path_on_disk): # Clean up orphaned file
                try:
                    os.remove(file_path_on_disk)
                except OSError:
                    pass # Ignore if removal fails, but log it
            flash(f'Error uploading file: {str(e)}', 'error')
            # Consider logging the error: app.logger.error(f"File upload failed: {e}")
        
        return redirect(redirect_url)

    # Fallback redirect
    return redirect(request.referrer or redirect_url)


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