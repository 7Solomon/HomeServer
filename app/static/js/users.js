function openCreateModal() {
    document.getElementById('createModal').style.display = 'flex';
}

function closeCreateModal() {
    document.getElementById('createModal').style.display = 'none';
}

function openEditModal(userId, username, firstName, lastName, role, isApproved) {
    document.getElementById('editForm').action = `/admin/users/edit/${userId}`;
    document.getElementById('edit_username').value = username;
    document.getElementById('edit_first_name').value = firstName;
    document.getElementById('edit_last_name').value = lastName;
    document.getElementById('edit_role').value = role;
    document.getElementById('edit_is_approved').checked = isApproved;
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    const createModal = document.getElementById('createModal');
    const editModal = document.getElementById('editModal');
    if (event.target == createModal) {
        closeCreateModal();
    }
    if (event.target == editModal) {
        closeEditModal();
    }
}
