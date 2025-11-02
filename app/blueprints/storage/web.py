import uuid
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
import os
from werkzeug.utils import secure_filename

from app.blueprints.storage.utils import file_icon, format_size, delete_directory_recursive, is_descendant
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp
from app.models.storage import Directory, File
from app.utils.auth import admin_required

SONG_DATA_FOLDER = os.path.abspath(os.path.normpath(os.path.join(UPLOAD_FOLDER, 'song_data')))
os.makedirs(SONG_DATA_FOLDER, exist_ok=True)

# Global file explorer - all authenticated users can see all files
@storage_bp.route('/files')
@login_required
def files():
    """Global file explorer - shows all files and directories with appropriate filtering"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all root directories - filter admin-only for non-admins
    if current_user.is_admin:
        directories = Directory.query.filter_by(parent_id=None).all()
    else:
        directories = Directory.query.filter_by(parent_id=None, is_admin_only=False).all()
    
    # Get all root files (no directory filtering needed for files)
    files = File.query.filter_by(directory_id=None).all()
    
    return render_template(
        'storage/files.html',
        files=files,
        directories=directories,
        path=[],
        current_dir=None,
        parent_dir=None,
        file_icon=file_icon,
        format_size=format_size,
        is_global_view=True
    )

@storage_bp.route('/directory/<int:dir_id>')
@login_required
def directory(dir_id):
    """Global directory view - shows any directory content with appropriate filtering"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))
    
    current_dir = Directory.query.get_or_404(dir_id)
    
    # Check admin-only access
    if current_dir.is_admin_only and not current_user.is_admin:
        flash('You do not have permission to access this directory', 'error')
        return redirect(url_for('storage.files'))
    
    # Build path from root to current directory
    path = []
    parent = current_dir.parent
    while parent:
        path.insert(0, parent)
        parent = parent.parent
    
    # Get subdirectories and files
    directories = Directory.query.filter_by(parent_id=dir_id).all()
    files = File.query.filter_by(directory_id=dir_id).all()
    
    # Filter admin-only for non-admins
    if not current_user.is_admin:
        directories = [d for d in directories if not d.is_admin_only]
    
    return render_template('storage/files.html',
                         current_dir=current_dir,
                         path=path,  # This is the breadcrumb path
                         parent_dir=current_dir.parent,
                         directories=directories,
                         files=files,
                         file_icon=file_icon,
                         format_size=format_size)

# A
@storage_bp.route('/upload', methods=['POST'])
@login_required
@admin_required
def upload_file():
    """Upload file(s) - admin only - supports multiple files"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))

    # Determine redirect URL based on directory_id
    directory_id_str = request.form.get('directory_id')
    redirect_url = url_for('storage.files')
    target_dir_id_for_db = None
    target_dir = None

    if directory_id_str and directory_id_str != "None" and directory_id_str.isdigit():
        directory_id = int(directory_id_str)
        target_dir = Directory.query.get_or_404(directory_id)
        target_dir_id_for_db = target_dir.id
        redirect_url = url_for('storage.directory', dir_id=target_dir.id)

    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(request.referrer or redirect_url)

    files = request.files.getlist('file')  # Get list of files
    
    if not files or all(f.filename == '' for f in files):
        flash('No selected files.', 'error')
        return redirect(request.referrer or redirect_url)

    uploaded_count = 0
    skipped_count = 0
    error_count = 0

    for file in files:
        if file.filename == '':
            continue
            
        original_filename = secure_filename(file.filename)
        
        # Check for duplicate file name within the same directory
        existing_file = File.query.filter_by(
            name=original_filename,
            directory_id=target_dir_id_for_db
        ).first()

        if existing_file:
            skipped_count += 1
            continue

        _, extension = os.path.splitext(original_filename)
        unique_filename_for_storage = str(uuid.uuid4()) + extension
        
        file_path_on_disk = os.path.join(SONG_DATA_FOLDER, unique_filename_for_storage)
        
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
            uploaded_count += 1
        except Exception as e:
            error_count += 1
            if os.path.exists(file_path_on_disk):
                try:
                    os.remove(file_path_on_disk)
                except OSError:
                    pass
    
    # Show summary message
    messages = []
    if uploaded_count > 0:
        messages.append(f'{uploaded_count} file(s) uploaded successfully')
    if skipped_count > 0:
        messages.append(f'{skipped_count} file(s) skipped (duplicates)')
    if error_count > 0:
        messages.append(f'{error_count} file(s) failed')
    
    if messages:
        flash('. '.join(messages) + '.', 'success' if error_count == 0 else 'warning')
    
    return redirect(redirect_url)

@storage_bp.route('/create-directory', methods=['POST'])
@login_required
@admin_required
def create_directory():
    """Create directory - admin only"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))

    name = request.form.get('name')
    parent_id_str = request.form.get('parent_id')
    is_admin_only = request.form.get('is_admin_only') == 'on'

    # Determine redirect URL
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
        parent_dir = Directory.query.get_or_404(parent_id)
        parent_id_for_db = parent_dir.id
    
    # Check for duplicate directory name within the same parent
    existing_directory = Directory.query.filter_by(
        name=name,
        parent_id=parent_id_for_db
    ).first()

    if existing_directory:
        flash(f'A directory named "{name}" already exists here.', 'error')
        return redirect(redirect_url)

    new_dir = Directory(
        name=name,
        user_id=current_user.id,
        parent_id=parent_id_for_db,
        is_admin_only=is_admin_only
    )
    db.session.add(new_dir)
    db.session.commit()
    
    admin_only_msg = " (Admin Only)" if is_admin_only else ""
    flash(f'Directory "{name}"{admin_only_msg} created successfully.', 'success')

    return redirect(redirect_url)

# Admin route to delete files
@storage_bp.route('/delete/file/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def delete_file(file_id):
    """Delete file - admin only"""
    file = File.query.get_or_404(file_id)

    # Delete physical file
    try:
        os.remove(os.path.join(SONG_DATA_FOLDER, file.path))
    except (OSError, FileNotFoundError):
        pass

    # Delete database entry
    db.session.delete(file)
    db.session.commit()

    flash('File deleted successfully.', 'success')

    # Redirect back to referring page
    referrer = request.referrer or url_for('storage.files')
    return redirect(referrer)

# Admin route to delete directories
@storage_bp.route('/delete/directory/<int:dir_id>', methods=['POST'])
@login_required
@admin_required
def delete_directory(dir_id):
    """Delete directory - admin only"""
    directory = Directory.query.get_or_404(dir_id)
    parent_id = directory.parent_id

    # Use recursive function to delete all contents
    delete_directory_recursive(directory)

    flash('Directory and all its contents deleted successfully.', 'success')

    # Redirect based on parent
    if parent_id:
        return redirect(url_for('storage.directory', dir_id=parent_id))
    else:
        return redirect(url_for('storage.files'))

# Admin route to move files
@storage_bp.route('/move/file/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def move_file(file_id):
    """Move file - admin only"""
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
    referrer = request.referrer or url_for('storage.files')
    return redirect(referrer)

# Admin route to move directories
@storage_bp.route('/move/directory/<int:dir_id>', methods=['POST'])
@login_required
@admin_required
def move_directory(dir_id):
    """Move directory - admin only"""
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
                referrer = request.referrer or url_for('storage.files')
                return redirect(referrer)
            directory.parent_id = target_dir.id
    else:
        directory.parent_id = None

    db.session.commit()
    flash('Directory moved successfully.', 'success')

    # Redirect back to referring page
    referrer = request.referrer or url_for('storage.files')
    return redirect(referrer)

# Admin route to change file/directory owner
@storage_bp.route('/change-owner/<string:type>/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def change_owner(type, item_id):
    """Change file/directory owner - admin only"""
    from app.models.user import User

    user_id = request.form.get('user_id')
    if not user_id:
        flash('No user selected.', 'error')
        return redirect(request.referrer or url_for('storage.files'))

    user = User.query.get_or_404(user_id)

    if type == 'file':
        item = File.query.get_or_404(item_id)
    else:
        item = Directory.query.get_or_404(item_id)

    item.user_id = user.id
    db.session.commit()

    flash(f'{type.capitalize()} ownership changed to {user.username}.', 'success')
    return redirect(request.referrer or url_for('storage.files'))

# Admin route to toggle admin-only status
@storage_bp.route('/toggle-admin-only/<int:dir_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin_only(dir_id):
    """Toggle admin-only status of directory - admin only"""
    directory = Directory.query.get_or_404(dir_id)
    directory.is_admin_only = not directory.is_admin_only
    db.session.commit()
    
    status = "Admin Only" if directory.is_admin_only else "Public"
    flash(f'Directory "{directory.name}" is now {status}.', 'success')
    
    return redirect(request.referrer or url_for('storage.files'))

# File download route - available to all authenticated users
@storage_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download file - available to all authenticated users"""
    if not current_user.is_approved:
        flash('Your account is pending approval.', 'error')
        return redirect(url_for('main.index'))
        
    file = File.query.get_or_404(file_id)
    
    # Check if file is in an admin-only directory
    if file.directory and file.directory.is_admin_only and not current_user.is_admin:
        flash('Permission denied - File is in admin-only directory.', 'error')
        return redirect(url_for('storage.files'))
    
    try:
        from flask import send_file
        # Construct full path - file.path is relative to SONG_DATA_FOLDER
        full_path = os.path.join(SONG_DATA_FOLDER, file.path)
        
        # Debug logging
        #print(f"Attempting to download file: {file.name}")
        #print(f"File path in DB: {file.path}")
        #print(f"Full path: {full_path}")
        #print(f"File exists: {os.path.exists(full_path)}")
        
        if not os.path.exists(full_path):
            flash('File not found on disk.', 'error')
            return redirect(request.referrer or url_for('storage.files'))
        
        return send_file(
            full_path,
            as_attachment=True, 
            download_name=file.name
        )
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('storage.files'))
