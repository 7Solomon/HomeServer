# Home Server

Ein Vibe Coded Home Server (auch gennant Heim Speicher) mit ganz viel Ai slop, aber funktioniert erstaunlich gut.

Ist vor allem für die API-Endpunkte der P2PChords server stelle gedacht.

## Features

- Benutzerverwaltung über Admin user
- Dateiverwaltung mit Ordnerstruktur
- Admin-Panel zur Verwaltung aller Dateien und Benutzer
- API mit Token-Authentifizierung für programmatischen Zugriff

## Installation

1. Repository klonen:
```bash
git clone https://github.com/7Solomon/HomeServer.git
cd home_server
```

2. Venv erstellen und aktivieren:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

4. Admin-Benutzer erstellen:
```bash
flask create-admin <username> <password> <first_name> <last_name>
```

## Verwendung

Server starten:
```bash
python run.py
```

Der Server ist auf http://localhost:5000 erreichbar.

## Benutzerverwaltung

- Neue Benutzer können sich registrieren, müssen aber von Admin Usern genehmigt werden
- Admins können neue Benutzer über das Admin-Panel annehmen oder ablehnen

## Dateiverwaltung

- Benutzer können Dateien hochladen und Ordner erstellen
- Dateien können umbenannt, verschoben und gelöscht werden
- Admins haben Zugriff auf alle Dateien und können Eigentümer ändern

## API-Zugriff

Es gibt API-Endpunkte mit Token-Authentifizierung. Admin-Token können im Admin-Bereich generiert werden.

### JSON-Daten API (`/api/song_data`)

Diese Endpunkte dienen zum Verwalten von JSON-Dateien (z.B. Song-Metadaten) in einem speziellen Ordner (`uploads/song_data`).

**1. JSON-Dateien auflisten:**

*   **Methode:** `GET`
*   **Endpunkt:** `/api/song_data`
*   **Authentifizierung:** Standard-Benutzertoken (`Authorization: Bearer <your_token>`)
*   **Beispiel (`curl`):**
    ```bash
    curl -H "Authorization: Bearer <your_token>" <your_server_url>/api/song_data
    ```

**2. Spezifische JSON-Datei herunterladen:**

*   **Methode:** `GET`
*   **Endpunkt:** `/api/song_data/<filename>` (z.B. `/api/song_data/song1.json`)
*   **Authentifizierung:** Standard-Benutzertoken (`Authorization: Bearer <your_token>`)
*   **Beispiel (`curl`):**
    ```bash
    curl -H "Authorization: Bearer <your_token>" <your_server_url>/api/song_data/song1.json -o song1_downloaded.json
    ```

**3. JSON-Datei hochladen (Nur Admins):**

*   **Methode:** `POST`
*   **Endpunkt:** `/api/song_data`
*   **Authentifizierung:** Admin-Token (`Authorization: Bearer <your_admin_token>`)
*   **Body:** `multipart/form-data` mit einer Datei im Feld `file`.
*   **Beispiel (`curl`):**
    ```bash
    curl -X POST \\
         -H "Authorization: Bearer <your_admin_token>" \\
         -F "file=@pfad/zu/deiner/song.json" \\
         <your_server_url>/api/song_data
    ```

**4. JSON-Datei löschen (Nur Admins):**

*   **Methode:** `DELETE`
*   **Endpunkt:** `/api/song_data/<filename>` (z.B. `/api/song_data/song1.json`)
*   **Authentifizierung:** Admin-Token (`Authorization: Bearer <your_admin_token>`)
*   **Beispiel (`curl`):**
    ```bash
    curl -X DELETE -H "Authorization: Bearer <your_admin_token>" <your_server_url>/api/song_data/song1.json
    ```

**Wichtige Hinweise:**

*   Ersetze `<your_token>`, `<your_admin_token>`, `<your_server_url>`, `<filename>` und `pfad/zu/deiner/song.json` mit den tatsächlichen Werten.
*   `<your_server_url>` ist die URL, unter der deine Anwendung läuft (z.B. `http://127.0.0.1:5000`).
*   Tokens erhältst du über die Login-Endpunkte (`/auth/login`, `/auth/admin`).

## Systemanforderungen

- Python 3.7+
- Flask 3.1.0+
- Weitere Abhängigkeiten siehe requirements.txt
