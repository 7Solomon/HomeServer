from app.blueprints.storage import storage_bp

from flask import redirect
import socket, subprocess, time, shutil

from app.workables.config.manager import get_config


def is_port_open(host, port):
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        return True
    except:
        return False

def js_alert(message, redirect_url="/"):
    # Keep message short (avoid huge stderr dump)
    safe = (message or "").replace("<", "&lt;")[:500]
    return f"""
    <html><head><meta charset='utf-8'></head>
    <body><script>
    alert({safe!r});
    window.location.href = {redirect_url!r};
    </script></body></html>
    """

def docker_available():
    return shutil.which("docker") is not None

def start_container(name, timeout_sec=25):
    """
    Try to start a container; return (ok, err_str).
    """
    try:
        result = subprocess.run(
            ["docker", "start", name],
            capture_output=True,
            text=True,
            timeout=10
        )
    except FileNotFoundError:
        return False, "Docker CLI nicht gefunden (Docker Desktop installiert/gestartet?)."
    except subprocess.TimeoutExpired:
        return False, "Docker start Befehl Timeout."
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if "pipe" in err.lower():
            return False, "Docker Engine nicht gestartet (Docker Desktop öffnen)."
        return False, f"Docker Fehler: {err[:220]}"
    # Wait for service port
    start = time.time()
    while time.time() - start < timeout_sec:
        if is_port_open("127.0.0.1", 3000):
            return True, ""
        time.sleep(1)
    return False, "Overleaf Dienst-Port wurde nicht erreichbar (Timeout)."

@storage_bp.route("/start_overleaf")
def start_overleaf():
    cfg = get_config() or {}
    vps_ip = cfg.get("vps_ip")

    if not vps_ip:
        return js_alert("Overleaf: VPS IP nicht konfiguriert.", "/")

    # Already up?
    if not is_port_open("127.0.0.1", 3000):
        if not docker_available():
            return js_alert("Docker nicht gefunden. Bitte installieren / PATH prüfen.", "/")
        ok, err = start_container("overleaf")
        if not ok:
            return js_alert(err, "/")

    return redirect(f"http://{vps_ip}:3000")
