import os
import json
import ftplib
from ftplib import FTP, error_perm

from app.workables.config.manager import get_config

def list_ftp_files(remote_subdir=None):
    """
    Lists files and directories on the FTP server in a specified subdirectory.

    Args:
        remote_subdir (str, optional): The subdirectory on the FTP server to list.
                                       If None, uses 'default_remote_path' from config or root.

    Returns:
        list: A list of file/directory names. Returns an empty list on error.
    """
    ftp_config = get_config()
    if not ftp_config:
        return  500, []

    server_url = ftp_config['server_url']
    username = ftp_config['username']
    password = ftp_config['password']
    target_path = remote_subdir if remote_subdir is not None else ftp_config.get('default_remote_path', '/')

    try:
        with FTP(server_url) as ftp:
            ftp.login(user=username, passwd=password)
            print(f"Successfully connected to FTP server: {server_url}")

            if target_path and target_path != '/':
                try:
                    ftp.cwd(target_path)
                    print(f"Changed directory to: {target_path}")
                except error_perm as e:
                    print(f"ERROR: Could not change to directory '{target_path}': {e}. Listing root instead.")
                    # Optionally, list root or return error
                    # For now, we'll try listing the current directory (which might be root)
                    pass # Fall through to nlst() in current directory

            files = ftp.nlst()
            print(f"Files in '{ftp.pwd()}': {files}")
            return 200, files
    except ftplib.all_errors as e:
        print(f"FTP error during listing files: {e}")
        return 500, []
    except Exception as e:
        print(f"An unexpected error occurred during FTP listing: {e}")
        return  500, []

def upload_file_ftp(local_file_path, remote_file_name, remote_subdir=None):
    """
    Uploads a local file to the FTP server in a specified subdirectory.

    Args:
        local_file_path (str): The path to the local file to upload.
        remote_file_name (str): The name to give the file on the FTP server.
        remote_subdir (str, optional): The subdirectory on the FTP server to upload to.
                                       If None, uses 'default_remote_path' from config or root.

    Returns:
        bool: True if upload was successful, False otherwise.
    """
    ftp_config = get_config()
    if not ftp_config:
        return False

    if not os.path.exists(local_file_path):
        print(f"ERROR: Local file not found: {local_file_path}")
        return False

    server_url = ftp_config['server_url']
    username = ftp_config['username']
    password = ftp_config['password']
    target_path = remote_subdir if remote_subdir is not None else ftp_config.get('default_remote_path', '/')

    print(f"Uploading '{local_file_path}' to FTP server: {server_url}")
    print('NOT YET IMPLEMENTED!')
    print('BUT NO ERRORS!')
    #try:
    #    with FTP(server_url) as ftp:
    #        ftp.login(user=username, passwd=password)
    #        print(f"Successfully connected to FTP server: {server_url} for upload.")
#
    #        if target_path and target_path != '/':
    #            try:
    #                ftp.cwd(target_path)
    #                print(f"Changed directory to: {target_path} for upload.")
    #            except error_perm as e:
    #                # Attempt to create directory if it doesn't exist
    #                print(f"Directory '{target_path}' not found or permission error: {e}. Attempting to create it.")
    #                try:
    #                    # ftplib doesn't have a direct way to create nested dirs,
    #                    # so this will only work for one level or if parent exists.
    #                    ftp.mkd(target_path)
    #                    print(f"Created directory: {target_path}")
    #                    ftp.cwd(target_path)
    #                except error_perm as e_mkd:
    #                    print(f"ERROR: Could not create or change to directory '{target_path}': {e_mkd}")
    #                    return False
    #        
    #        remote_full_path = os.path.join(ftp.pwd(), remote_file_name).replace('\\', '/') # Ensure forward slashes
#
    #        with open(local_file_path, 'rb') as f_local:
    #            print(f"Uploading '{local_file_path}' to '{remote_full_path}'...")
    #            ftp.storbinary(f'STOR {remote_file_name}', f_local)
    #        
    #        print(f"File '{remote_file_name}' uploaded successfully to '{ftp.pwd()}'.")
    #        return True
    #except ftplib.all_errors as e:
    #    print(f"FTP error during upload: {e}")
    #    return False
    #except FileNotFoundError: # Should be caught by pre-check, but good to have
    #    print(f"ERROR: Local file not found during FTP operation: {local_file_path}")
    #    return False
    #except Exception as e:
    #    print(f"An unexpected error occurred during FTP upload: {e}")
    #    return False
