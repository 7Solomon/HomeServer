/**
 * Simple admin file management functionality
 */
document.addEventListener('DOMContentLoaded', function () {
    // ===== Modal Management =====
    const modals = {
        upload: document.getElementById('upload-modal'),
        folder: document.getElementById('folder-modal'),
        delete: document.getElementById('delete-modal'),
        move: document.getElementById('move-modal'),
        owner: document.getElementById('owner-modal')
    };

    // Open/close modal functions
    function openModal(modalId) {
        if (modals[modalId]) modals[modalId].style.display = 'block';
    }

    function closeAllModals() {
        Object.values(modals).forEach(modal => {
            if (modal) modal.style.display = 'none';
        });
    }

    // Close buttons and background click
    document.querySelectorAll('.close, .close-btn').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });

    window.addEventListener('click', function (event) {
        Object.values(modals).forEach(modal => {
            if (event.target === modal) modal.style.display = 'none';
        });
    });

    // ===== File Upload =====
    document.getElementById('upload-btn')?.addEventListener('click', () => openModal('upload'));

    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);
            const progressBar = document.querySelector('.progress-fill');
            const progressText = document.querySelector('.progress-text');

            fetch('/api/upload', {
                method: 'POST',
                body: formData,
                headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    showNotification('Datei erfolgreich hochgeladen', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Hochladen', 'error');
                });
        });
    }

    // ===== Create Folder =====
    document.getElementById('new-folder-btn')?.addEventListener('click', () => openModal('folder'));

    const folderForm = document.getElementById('folder-form');
    if (folderForm) {
        folderForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch('/api/directory/create', {
                method: 'POST',
                body: formData,
                headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    showNotification('Ordner erfolgreich erstellt', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Erstellen des Ordners', 'error');
                });
        });
    }

    // ===== Delete Files/Folders =====
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

    const deleteForm = document.getElementById('delete-form');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const type = document.getElementById('delete-type').value;
            const id = document.getElementById('delete-id').value;

            // Use the admin routes for deletion
            let endpoint = type === 'directory' ?
                `/api/admin/delete/directory/${id}` :
                `/api/admin/delete/file/${id}`;

            fetch(endpoint, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    showNotification('Erfolgreich gelöscht', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Löschen', 'error');
                });
        });
    }

    // ===== Move Files/Folders =====
    document.querySelectorAll('.move-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const type = this.dataset.type;
            const id = this.dataset.id;

            document.getElementById('move-type').value = type;
            document.getElementById('move-id').value = id;

            fetch(`/api/directories/list?exclude=${type === 'directory' ? id : ''}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            })
                .then(response => response.json())
                .then(data => {
                    const select = document.getElementById('target-directory');
                    select.innerHTML = '<option value="root">Root-Verzeichnis</option>';

                    (data.directories || []).forEach(dir => {
                        const option = document.createElement('option');
                        option.value = dir.id;
                        option.textContent = dir.path;
                        select.appendChild(option);
                    });

                    openModal('move');
                })
                .catch(error => {
                    showNotification('Fehler beim Laden der Verzeichnisse', 'error');
                });
        });
    });

    const moveForm = document.getElementById('move-form');
    if (moveForm) {
        moveForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const type = document.getElementById('move-type').value;
            const id = document.getElementById('move-id').value;
            const targetDirId = document.getElementById('target-directory').value;

            let endpoint = type === 'directory' ?
                `/api/admin/move/directory/${id}` :
                `/api/admin/move/file/${id}`;

            const formData = new FormData();
            formData.append(type === 'directory' ? 'parent_id' : 'directory_id', targetDirId);

            fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    showNotification('Erfolgreich verschoben', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                })
                .catch(error => {
                    showNotification(error.message || 'Fehler beim Verschieben', 'error');
                });
        });
    }

    // Helper function for notifications
    function showNotification(message, type = 'info') {
        // Check if notification container exists, create if not
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        // Add to container
        container.appendChild(notification);

        // Remove after timeout
        setTimeout(() => {
            notification.classList.add('fade');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
});