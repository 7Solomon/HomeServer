from app.blueprints.storage import storage_bp
from flask import redirect, url_for
from flask_login import login_required
import socket, subprocess, time, shutil, os
from flask_login import current_user
from flask import render_template
from flask import flash, redirect, url_for

from app.workables.config.manager import get_config


from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import bcrypt
import logging
from datetime import datetime

OVERLEAF_PATH = r"C:\Users\Johan\Documents\programme\overleaf"
OVERLEAF_PORT = 80

def is_port_open(host, port):
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        return True
    except:
        return False

def js_alert(message, redirect_url="/"):
    safe = (message or "").replace("<", "&lt;").replace("'", "\\'")[:500]
    return f"""
    <html><head><meta charset='utf-8'></head>
    <body><script>
    alert('{safe}');
    window.location.href = {redirect_url!r};
    </script></body></html>
    """

def docker_compose_available():
    return shutil.which("docker-compose") is not None or shutil.which("docker") is not None

def start_overleaf_service():
    """
    Start Overleaf using docker-compose (non-blocking version).
    Returns immediately after starting docker-compose.
    """
    if not os.path.exists(OVERLEAF_PATH):
        return False, f"Overleaf Verzeichnis nicht gefunden: {OVERLEAF_PATH}"
    
    compose_file = os.path.join(OVERLEAF_PATH, "docker-compose.yml")
    if not os.path.exists(compose_file):
        return False, "docker-compose.yml nicht gefunden in Overleaf Verzeichnis."
    
    try:
        # Try docker compose (newer) first, then docker-compose (older)
        if shutil.which("docker"):
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=OVERLEAF_PATH,
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=OVERLEAF_PATH,
                capture_output=True,
                text=True,
                timeout=30
            )
    except FileNotFoundError:
        return False, "Docker/Docker-Compose nicht gefunden."
    except subprocess.TimeoutExpired:
        return False, "Docker-Compose Start Timeout."
    
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if "daemon" in err.lower() or "pipe" in err.lower():
            return False, "Docker Engine nicht gestartet (Docker Desktop öffnen)."
        return False, f"Docker Fehler: {err[:220]}"
    
    # Don't wait - just return success after docker-compose starts
    logger.info("Docker compose command executed successfully")
    return True, ""

@storage_bp.route("/start_overleaf")
@login_required
def start_overleaf():
    flash('Overleaf Integration ist derzeit noch nicht implementiert.', 'info')
    return redirect(url_for('main.index'))
    cfg = get_config() or {}
    vps_ip = cfg.get("vps_ip", "127.0.0.1")
    #vps_ip = "127.0.0.1"
    logger.info(f"Start Overleaf for user {current_user.username}")
    
    # Check if already running on port 80
    if not is_port_open("127.0.0.1", OVERLEAF_PORT):
        if not docker_compose_available():
            return js_alert("Docker nicht gefunden. Bitte installieren.", "/")
        
        logger.info("Starting Overleaf service...")
        ok, err = start_overleaf_service()
        if not ok:
            logger.error(f"Failed to start Overleaf: {err}")
            return js_alert(err, "/")
        
        logger.info("Docker compose started, showing loading page")
        return render_template('overleaf.html', vps_ip=vps_ip, port=OVERLEAF_PORT)

    # Overleaf is already running
    logger.info("Overleaf already running, checking user status")
    return redirect(url_for('storage.check_overleaf_ready'))

@storage_bp.route("/check_overleaf_ready")
@login_required
def check_overleaf_ready():
    """Check if user exists in Overleaf and redirect appropriately"""
    from flask_login import current_user
    cfg = get_config() or {}
    vps_ip = cfg.get("vps_ip", "127.0.0.1")
    #vps_ip = "127.0.0.1"
    # Check if user exists in Overleaf
    try:
        db = get_overleaf_db()
        if db:
            email = f"{current_user.username}@homeserver.local"
            existing = db.users.find_one({"email": email})
            
            if not existing:
                logger.info(f"User {current_user.username} not found in Overleaf, showing registration page")
                # Show registration instructions (change port to 80)
                return f"""
                <html><head><meta charset='utf-8'></head>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        padding: 50px 20px; 
                        max-width: 700px; 
                        margin: auto;
                        background: #f5f7fa;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 15px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    h2 {{ color: #667eea; margin-bottom: 20px; }}
                    .info-box {{
                        background: #f0f4ff;
                        border-left: 4px solid #667eea;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 5px;
                    }}
                    .credentials {{
                        background: #fff9e6;
                        border: 2px dashed #ffa500;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 8px;
                        font-family: monospace;
                    }}
                    .emoji {{ font-size: 2rem; }}
                    ul {{ text-align: left; line-height: 1.8; }}
                    .timer {{
                        font-size: 1.2rem;
                        color: #667eea;
                        font-weight: bold;
                        margin-top: 20px;
                    }}
                </style>
                </head><body>
                <div class="container">
                    <div class="emoji">👋</div>
                    <h2>Willkommen bei Overleaf!</h2>
                    <p>Du wirst gleich zu Overleaf weitergeleitet.</p>
                    
                    <div class="info-box">
                        <strong>⚠️ Wichtig:</strong> Du musst dich zuerst bei Overleaf registrieren!
                    </div>
                    
                    <div class="credentials">
                        <strong>📧 Registrierungsdaten:</strong><br><br>
                        <strong>E-Mail:</strong> {current_user.username}@homeserver.local<br>
                        <strong>Vorname:</strong> {current_user.first_name}<br>
                        <strong>Nachname:</strong> {current_user.last_name}<br>
                        <strong>Passwort:</strong> Verwende das gleiche Passwort wie für HomeServer
                    </div>
                    
                    <p><strong>Schritte:</strong></p>
                    <ul>
                        <li>Klicke auf "Register" bei Overleaf</li>
                        <li>Verwende die oben angegebene E-Mail</li>
                        <li>Setze dein HomeServer-Passwort</li>
                        <li>Bestätige die Registrierung</li>
                    </ul>
                    
                    <div class="timer" id="countdown">Weiterleitung in 10 Sekunden...</div>
                </div>
                <script>
                    let seconds = 10;
                    const countdownEl = document.getElementById('countdown');
                    
                    const timer = setInterval(() => {{
                        seconds--;
                        if (seconds <= 0) {{
                            clearInterval(timer);
                            window.location.href = 'http://{vps_ip}/register';
                        }} else {{
                            countdownEl.textContent = `Weiterleitung in ${{seconds}} Sekunden...`;
                        }}
                    }}, 1000);
                </script>
                </body></html>
                """
            else:
                logger.info(f"User {current_user.username} found in Overleaf, redirecting")
    except Exception as e:
        logger.warning(f"Could not check Overleaf user: {str(e)}")

    # User exists or check failed - redirect to port 80
    return redirect(f"http://{vps_ip}")


logger = logging.getLogger(__name__)
MONGO_URI = "mongodb://localhost:27017"
OVERLEAF_DB = "sharelatex"

def get_overleaf_db():
    """Connect to Overleaf's MongoDB"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        # Test connection
        client.server_info()
        return client[OVERLEAF_DB]
    except ConnectionFailure:
        logger.warning("Could not connect to Overleaf MongoDB")
        return None

def hash_password_for_overleaf(password):
    """Hash password in Overleaf's format (bcrypt)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def sync_user_to_overleaf(user, plain_password):
    """
    Sync a HomeServer user to Overleaf.
    Returns (success, message)
    """
    try:
        db = get_overleaf_db()
        if not db:
            return False, "Overleaf nicht verfügbar"
        
        users_collection = db.users
        
        #  Overleaf requires email
        email = f"{user.username}@homeserver.local"
        
        # Check if user already exists
        existing = users_collection.find_one({"email": email})
        
        if existing:
            # Update password if user exists
            users_collection.update_one(
                {"email": email},
                {"$set": {
                    "hashedPassword": hash_password_for_overleaf(plain_password),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }}
            )
            return True, "Overleaf Benutzer aktualisiert"
        
        # Create new Overleaf user
        overleaf_user = {
            "email": email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "hashedPassword": hash_password_for_overleaf(plain_password),
            "isAdmin": user.is_admin,
            "signUpDate": datetime.now(),
            "holdingAccount": False,
        }
        
        users_collection.insert_one(overleaf_user)
        logger.info(f"Synced user {user.username} to Overleaf")
        return True, "Benutzer zu Overleaf hinzugefügt"
        
    except Exception as e:
        logger.error(f"Error syncing user to Overleaf: {str(e)}")
        return False, f"Fehler beim Synchronisieren: {str(e)}"

def delete_user_from_overleaf(username):
    """Delete user from Overleaf"""
    try:
        db = get_overleaf_db()
        if not db:
            return False, "Overleaf nicht verfügbar"
        
        email = f"{username}@homeserver.local"
        result = db.users.delete_one({"email": email})
        
        if result.deleted_count > 0:
            return True, "Benutzer aus Overleaf gelöscht"
        return False, "Benutzer nicht in Overleaf gefunden"
        
    except Exception as e:
        logger.error(f"Error deleting user from Overleaf: {str(e)}")
        return False, f"Fehler beim Löschen: {str(e)}"