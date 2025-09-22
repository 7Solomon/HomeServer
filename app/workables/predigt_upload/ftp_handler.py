import os
import json
from ftplib import FTP, error_perm

import requests

from app.workables.config.manager import get_config
import ftplib
import socket
import logging

def list_ftp_files():
    """
    Return (status_code, [filenames]) and never raise.
    Accepts config keys: server_url | server | ftp_host, name | ftp_user, password | ftp_pass.
    """
    cfg = get_config() or {}
    host = cfg.get("server_url") or cfg.get("server") or cfg.get("ftp_host")
    user = cfg.get("name") or cfg.get("ftp_user")
    pwd  = cfg.get("password") or cfg.get("ftp_pass")

    if not host or not user or not pwd:
        msg = "Missing FTP credentials (server/name/password)."
        logging.error(msg)
        return 400, []

    try:
        with ftplib.FTP(host, timeout=15) as ftp:
            ftp.login(user=user, passwd=pwd)
            files = ftp.nlst()  # or a specific directory if needed
            return 200, files
    except (ftplib.all_errors, socket.error) as e:
        logging.error(f"FTP error: {e}")
        return 502, []
    except Exception as e:
        logging.exception("Unexpected FTP error")
        return 500, []

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

    server_url = ftp_config['server']
    username = ftp_config['name']
    password = ftp_config['password']
    target_path = remote_subdir if remote_subdir is not None else ftp_config.get('default_remote_path', '/')


    try:
        with FTP(server_url) as ftp:
            ftp.login(user=username, passwd=password)
            print(f"Successfully connected to FTP server: {server_url} for upload.")

            if target_path and target_path != '/':
                try:
                    ftp.cwd(target_path)
                    print(f"Changed directory to: {target_path} for upload.")
                except error_perm as e:
                    # Attempt to create directory if it doesn't exist
                    print(f"Directory '{target_path}' not found or permission error: {e}. Attempting to create it.")
                    try:
                        # ftplib doesn't have a direct way to create nested dirs,
                        # so this will only work for one level or if parent exists.
                        ftp.mkd(target_path)
                        print(f"Created directory: {target_path}")
                        ftp.cwd(target_path)
                    except error_perm as e_mkd:
                        print(f"ERROR: Could not create or change to directory '{target_path}': {e_mkd}")
                        return False
            
            remote_full_path = os.path.join(ftp.pwd(), remote_file_name).replace('\\', '/') # Ensure forward slashes

            with open(local_file_path, 'rb') as f_local:
                print(f"Uploading '{local_file_path}' to '{remote_full_path}'...")
                ftp.storbinary(f'STOR {remote_file_name}', f_local)
            
            print(f"File '{remote_file_name}' uploaded successfully to '{ftp.pwd()}'.")
            return True
    except ftplib.all_errors as e:
        print(f"FTP error during upload: {e}")
        return False
    except FileNotFoundError: # Should be caught by pre-check, but good to have
        print(f"ERROR: Local file not found during FTP operation: {local_file_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during FTP upload: {e}")
        return False


def refresh_website():
    """
    Makes an HTTP request to the update_url from config to refresh/rebuild the website.
    Returns True if successful, False otherwise.
    """
    try:
        config = get_config()
        if not config:
            print("ERROR: No config available for website refresh.")
            return False
        
        update_url = config.get('update_url')
        if not update_url:
            print("WARNING: No 'update_url' found in config. Skipping website refresh.")
            return False
        
        print(f"Triggering website refresh: {update_url}")
        
        response = requests.get(update_url, timeout=30)
        
        if response.status_code == 200:
            print("Website refresh triggered successfully.")
            return True
        else:
            print(f"Website refresh failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("ERROR: Website refresh request timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Website refresh request failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error during website refresh: {e}")
        return False