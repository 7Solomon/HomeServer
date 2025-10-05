function openEditModal() {
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

function openPasswordModal() {
    document.getElementById('passwordModal').style.display = 'flex';
}

function closePasswordModal() {
    document.getElementById('passwordModal').style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    const editModal = document.getElementById('editModal');
    const passwordModal = document.getElementById('passwordModal');
    if (event.target == editModal) {
        closeEditModal();
    }
    if (event.target == passwordModal) {
        closePasswordModal();
    }
}