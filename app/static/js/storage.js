/**
 * JavaScript für die Dateiverwaltungsfunktionen
 */
document.addEventListener('DOMContentLoaded', function () {
    // Modal-Steuerung
    const modals = {
        upload: document.getElementById('upload-modal'),
        folder: document.getElementById('folder-modal'),
        rename: document.getElementById('rename-modal'),
        delete: document.getElementById('delete-modal')
    };

    const openModal = (modalId) => {
        modals[modalId].style.display = 'block';
    };

    const closeModal = (modalId) => {
        modals[modalId].style.display = 'none';
    };

    // Modals schließen, wenn auf X oder außerhalb geklickt wird
    document.querySelectorAll('.close, .close-btn').forEach(element => {
        element.addEventListener('click', function () {
            Object.keys(modals).forEach(key => {
                closeModal(key);
            });
        });
    });

    window.addEventListener('click', function (event) {
        Object.entries(modals).forEach(([key, modal]) => {
            if (event.target === modal) {
                closeModal(key);
            }
        });
    });

    // Upload-Modal öffnen
    document.getElementById('upload-btn')?.addEventListener('click', function () {
        openModal('upload');
    });

    // Neuer Ordner-Modal öffnen
    document.getElementById('new-folder-btn')?.addEventListener('click', function () {
        openModal('folder');
    });

    // Dateien hochladen
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(uploadForm);
            const progressBar = document.querySelector('.progress-fill');
            const progressText = document.querySelector('.progress-text');
            const uploadProgress = document.querySelector('.upload-progress');

            uploadProgress.style.display = 'block';

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/upload');

            // Token aus localStorage holen, falls vorhanden
            const token = localStorage.getItem('auth_token');
            if (token) {
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            }

            xhr.upload.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressText.textContent = percent + '%';
                }
            });

            xhr.addEventListener('load', function () {
                if (xhr.status === 200 || xhr.status === 201) {
                    const response = JSON.parse(xhr.responseText);
                    showNotification('Datei erfolgreich hochgeladen', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    let errorMsg = 'Fehler beim Hochladen der Datei';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        errorMsg = response.error || errorMsg;
                    } catch (e) { }
                    showNotification(errorMsg, 'error');
                }
            });

            xhr.addEventListener('error', function () {
                showNotification('Fehler beim Hochladen der Datei', 'error');
            });

            xhr.send(formData);
        });
    }

    // Ordner erstellen
    const folderForm = document.getElementById('folder-form');
    if (folderForm) {
        folderForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(folderForm);
            const data = {
                name: formData.get('name'),
                parent_id: formData.get('parent_id') || null
            };

            fetch('/api/directories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(data)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    showNotification('Ordner erfolgreich erstellt', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Erstellen des Ordners', 'error');
                });
        });
    }

    // Umbenennen-Modal aktivieren
    document.querySelectorAll('.rename-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const type = this.dataset.type;
            const id = this.dataset.id;
            const name = this.closest('.file-item').querySelector('.file-name').textContent.trim();

            document.getElementById('rename-type').value = type;
            document.getElementById('rename-id').value = id;
            document.getElementById('new-name').value = name;

            openModal('rename');
        });
    });

    // Löschen-Modal aktivieren
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const type = this.dataset.type;
            const id = this.dataset.id;
            const name = this.closest('.file-item').querySelector('.file-name').textContent.trim();

            document.getElementById('delete-type').value = type;
            document.getElementById('delete-id').value = id;
            document.getElementById('delete-name').textContent = name;

            openModal('delete');
        });
    });

    // Umbenennen durchführen
    const renameForm = document.getElementById('rename-form');
    if (renameForm) {
        renameForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const type = document.getElementById('rename-type').value;
            const id = document.getElementById('rename-id').value;
            const newName = document.getElementById('new-name').value;

            let endpoint = type === 'directory' ? `/api/directories/${id}` : `/api/files/${id}`;

            fetch(endpoint, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify({ name: newName })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    showNotification('Erfolgreich umbenannt', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Umbenennen', 'error');
                });
        });
    }

    // Löschen durchführen
    const deleteForm = document.getElementById('delete-form');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const type = document.getElementById('delete-type').value;
            const id = document.getElementById('delete-id').value;

            let endpoint = type === 'directory' ? `/api/directories/${id}` : `/api/files/${id}`;

            fetch(endpoint, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }

                    showNotification('Erfolgreich gelöscht', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Löschen', 'error');
                });
        });
    }

    // Benachrichtigungsfunktion
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `flash-message ${type}`;
        notification.textContent = message;

        const container = document.querySelector('.container');
        container.insertBefore(notification, container.firstChild);

        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 5000);
    }
});
