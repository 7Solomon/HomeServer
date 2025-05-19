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
    curl -X POST \
         -H "Authorization: Bearer <your_admin_token>" \
         -F "file=@pfad/zu/deiner/song.json" \
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

## Predigten API (`/api/predigt_upload`)

Diese Endpunkte dienen zur Verwaltung von "Predigten" (Sermons), einschließlich des Herunterladens von YouTube, der Komprimierung und des FTP-Uploads.

**1. YouTube-Livestreams auflisten und Predigt-Einträge erstellen/aktualisieren:**

*   **Methode:** `POST`
*   **Endpunkt:** `/api/predigt_upload/get_youtube_list/<max_results>`
    *   `<max_results>`: Die maximale Anzahl der zu prüfenden YouTube-Videos.
*   **Authentifizierung:** Admin-Token (`Authorization: Bearer <your_admin_token>`)
*   **Beschreibung:** Ruft die neuesten Livestreams vom konfigurierten YouTube-Kanal ab und erstellt oder aktualisiert entsprechende Einträge in der `Predigt`-Datenbank. Die Antwort enthält eine Liste der gefundenen Videos und Informationen über erstellte Einträge. Die `id` der `Predigt`-Einträge kann für nachfolgende Operationen verwendet werden.
*   **Beispiel (`curl`):**
    ```bash
    curl -X POST \
         -H "Authorization: Bearer <your_admin_token>" \
         <your_server_url>/api/predigt_upload/get_youtube_list/10
    ```

**2. Predigt von YouTube herunterladen (Server-seitig):**

*   **Methode:** `POST`
*   **Endpunkt:** `/api/predigt_upload/download/<predigt_id>`
    *   `<predigt_id>`: Die eindeutige ID des `Predigt`-Eintrags (erhalten z.B. über den Endpunkt `get_youtube_list`).
*   **Authentifizierung:** Admin-Token (`Authorization: Bearer <your_admin_token>`)
*   **Beschreibung:** Weist den Server an, das Audio der Predigt vom entsprechenden `youtube_url` herunterzuladen und lokal zu speichern. Der Status des `Predigt`-Eintrags wird aktualisiert.
*   **Antwort:** JSON-Objekt mit einer Erfolgs-/Fehlermeldung und dem Pfad zur heruntergeladenen Datei auf dem Server.
    ```json
    {
      "message": "Video downloaded successfully",
      "path": "/path/to/downloaded/audio.mp3",
      "predigt_id": 123
    }
    ```
*   **Beispiel (`curl`):**
    ```bash
    curl -X POST \
         -H "Authorization: Bearer <your_admin_token>" \
         <your_server_url>/api/predigt_upload/download/123
    ```

**3. Heruntergeladene Predigt komprimieren und auf FTP hochladen:**

*   **Methode:** `POST`
*   **Endpunkt:** `/api/predigt_upload/upload_file/<predigt_id>`
    *   `<predigt_id>`: Die eindeutige ID des `Predigt`-Eintrags, der bereits heruntergeladen wurde.
*   **Authentifizierung:** Admin-Token (`Authorization: Bearer <your_admin_token>`)
*   **Body (JSON):** Optional, um `remote_file_name` und `remote_subdir` anzugeben.
    ```json
    {
      "remote_file_name": "MeinePredigt.mp3",
      "remote_subdir": "predigten/2025"
    }
    ```
*   **Beschreibung:** Komprimiert die lokal gespeicherte Audiodatei für die angegebene `predigt_id` und lädt sie dann auf den konfigurierten FTP-Server hoch. Der Status des `Predigt`-Eintrags wird entsprechend aktualisiert.
*   **Beispiel (`curl`):**
    ```bash
    curl -X POST \
         -H "Authorization: Bearer <your_admin_token>" \
         -H "Content-Type: application/json" \
         -d '{"remote_file_name": "Predigt_vom_Sonntag.mp3", "remote_subdir": "audio/sermons"}' \
         <your_server_url>/api/predigt_upload/upload_file/123
    ```

**Wichtige Hinweise für Predigten API:**
*   Ersetze `<your_admin_token>`, `<your_server_url>` und `<predigt_id>` mit den tatsächlichen Werten.
*   Stelle sicher, dass die entsprechenden Routen in `app/blueprints/predigt_upload.py` implementiert sind und die `Predigt.id` als primären Identifikator verwenden.

## Systemanforderungen

- Python 3.7+
- Flask 3.1.0+
- Weitere Abhängigkeiten siehe requirements.txt
