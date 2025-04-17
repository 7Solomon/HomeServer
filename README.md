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

## Systemanforderungen

- Python 3.7+
- Flask 3.1.0+
- Weitere Abhängigkeiten siehe requirements.txt
