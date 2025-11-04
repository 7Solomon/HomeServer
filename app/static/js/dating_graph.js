// ================================================================
// DATING GRAPH HYBRID - JavaScript (Deutsche Version)
// ================================================================


let network = null;
let currentView = 'cards';
let persons = [];
let categories = [];
let currentPerson = null;
let filteredPersons = [];


// ================================================================
// INITIALIZATION
// ================================================================
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});


async function initializeApp() {
    // Load data
    await loadCategories();
    await loadPersons();
    await loadStatistics();


    // Setup UI
    setupEventListeners();
    populateFilters();
    
    // Render initial view
    renderCardsView();
    
    // Smart default view
    const recommendedView = getRecommendedView();
    if (recommendedView === 'graph') {
        switchView('graph');
    }
}


// ================================================================
// DATA LOADING
// ================================================================
async function loadPersons() {
    try {
        const response = await fetch('/dating_graph/api/persons');
        persons = await response.json();
        filteredPersons = [...persons];
        return persons;
    } catch (error) {
        console.error('Error loading persons:', error);
        showNotification('Fehler beim Laden der Personen', 'error');
    }
}


async function loadCategories() {
    try {
        const response = await fetch('/dating_graph/api/categories');
        categories = await response.json();
        return categories;
    } catch (error) {
        console.error('Error loading categories:', error);
        showNotification('Fehler beim Laden der Kategorien', 'error');
    }
}


async function loadStatistics() {
    try {
        const response = await fetch('/dating_graph/api/statistics');
        const stats = await response.json();
        updateStatistics(stats);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}


function updateStatistics(stats) {
    document.getElementById('cards-stat-persons').textContent = stats.total_persons || 0;
    document.getElementById('cards-stat-categories').textContent = stats.total_categories || 0;
    document.getElementById('cards-stat-dates').textContent = stats.total_dates || 0;
}


// ================================================================
// VIEW MANAGEMENT
// ================================================================
function getRecommendedView() {
    const personCount = persons.length;
    const isMobile = window.innerWidth < 768;
    
    if (isMobile) {
        return personCount < 10 ? 'graph' : 'cards';
    }
    return 'cards'; // Default to cards for ease of use
}


function switchView(viewName) {
    currentView = viewName;
    
    // Update tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        }
    });
    
    // Update view containers
    document.querySelectorAll('.view-container').forEach(container => {
        container.classList.remove('active');
    });
    
    const activeView = document.getElementById(`${viewName}-view`);
    if (activeView) {
        activeView.classList.add('active');
    }
    
    // Initialize graph if switching to graph view
    if (viewName === 'graph' && !network) {
        initializeNetwork();
    }
    
    // Render cards if switching to cards
    if (viewName === 'cards') {
        renderCardsView();
    }
}


// ================================================================
// CARDS VIEW RENDERING
// ================================================================
function renderCardsView() {
    const container = document.getElementById('cards-container');
    const emptyState = document.getElementById('cards-empty-state');
    
    if (filteredPersons.length === 0) {
        container.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    // Group persons by category
    const personsByCategory = {};
    
    filteredPersons.forEach(person => {
        if (person.categories && person.categories.length > 0) {
            person.categories.forEach(category => {
                if (!personsByCategory[category.id]) {
                    personsByCategory[category.id] = {
                        category: category,
                        persons: []
                    };
                }
                personsByCategory[category.id].persons.push(person);
            });
        } else {
            // Uncategorized
            if (!personsByCategory['uncategorized']) {
                personsByCategory['uncategorized'] = {
                    category: { id: 'uncategorized', name: 'Ohne Kategorie', color: '#64748b' },
                    persons: []
                };
            }
            personsByCategory['uncategorized'].persons.push(person);
        }
    });
    
    // Render sections
    container.innerHTML = Object.values(personsByCategory).map(({ category, persons }) => `
        <div class="category-section" data-category-id="${category.id}">
            <div class="category-header">
                <div class="category-title">
                    <div class="category-icon" style="background: ${category.color};">
                        ${category.icon ? `<i class="fas ${category.icon}"></i>` : '📁'}
                    </div>
                    <div class="category-name-group">
                        <h3>${category.name}</h3>
                        <div class="category-count">${persons.length} ${persons.length === 1 ? 'Person' : 'Personen'}</div>
                    </div>
                </div>
                <div class="category-actions">
                    <button class="btn-icon" onclick="focusGraphOnCategory(${category.id})" title="Im Netzwerk ansehen">
                        <i class="fas fa-project-diagram"></i>
                    </button>
                </div>
            </div>
            <div class="person-cards-grid">
                ${persons.map(person => renderPersonCard(person, category)).join('')}
            </div>
        </div>
    `).join('');
}


function renderPersonCard(person, category) {
    const statusLabels = {
        'interested': { icon: '💖', text: 'Interessiert' },
        'dating': { icon: '❤️', text: 'Dating' },
        'friend': { icon: '😊', text: 'Freund/in' },
        'no_connection': { icon: '😐', text: 'Keine Verbindung' },
        'ghosted': { icon: '👻', text: 'Geghostet' },
        'unknown': { icon: '❓', text: 'Unbekannt' }
    };
    
    const status = statusLabels[person.status] || statusLabels['unknown'];
    
    // Calculate days since last contact
    let lastContactText = '';
    if (person.last_contact_date) {
        const days = Math.floor((new Date() - new Date(person.last_contact_date)) / (1000 * 60 * 60 * 24));
        lastContactText = days === 0 ? 'Heute' : days === 1 ? 'vor 1 Tag' : `vor ${days} Tagen`;
    }
    
    const preview = person.fun_fact || person.story || person.notes || 'Noch keine Details';
    
    return `
        <div class="person-card" style="border-left-color: ${category.color}" onclick="showPersonDetails(${person.id})">
            <div class="person-card-header">
                <div class="person-name-section">
                    <h4 class="person-name">${person.nickname || person.name}</h4>
                    <div class="person-id">${person.custom_id}</div>
                </div>
                <div class="person-status-icon">${status.icon}</div>
            </div>
            
            <div class="person-card-meta">
                ${lastContactText ? `
                    <span class="meta-badge">
                        <i class="fas fa-clock"></i>
                        ${lastContactText}
                    </span>
                ` : ''}
                <span class="meta-badge">
                    <i class="fas fa-heart"></i>
                    ${status.text}
                </span>
            </div>
            
            <div class="person-card-preview">
                ${preview}
            </div>
            
            <div class="person-card-actions" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-secondary" onclick="focusGraphOnPerson(${person.id})">
                    <i class="fas fa-project-diagram"></i>
                    Netzwerk ansehen
                </button>
                <button class="btn btn-sm btn-primary" onclick="editPerson(${person.id})">
                    <i class="fas fa-edit"></i>
                    Bearbeiten
                </button>
            </div>
        </div>
    `;
}


// ================================================================
// GRAPH VIEW (VIS.JS)
// ================================================================
async function initializeNetwork() {
    const container = document.getElementById('network-canvas');
    
    try {
        const response = await fetch('/dating_graph/api/graph-data');
        const graphData = await response.json();
        
        const nodes = new vis.DataSet(graphData.nodes);
        const edges = new vis.DataSet(graphData.edges);
        
        const options = {
            physics: {
                enabled: true,
                stabilization: { enabled: true, iterations: 200 },
                barnesHut: {
                    gravitationalConstant: -20000,
                    springConstant: 0.001,
                    springLength: 250,
                    avoidOverlap: 0.8
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                navigationButtons: false,
                zoomView: true,
                dragView: true
            },
            nodes: {
                shape: 'box',
                margin: 10,
                widthConstraint: { minimum: 80, maximum: 200 },
                borderWidth: 2,
                shadow: { enabled: true, size: 8 },
                font: { size: 14, face: 'Inter, sans-serif' }
            },
            edges: {
                width: 2,
                smooth: { enabled: true, type: 'continuous', roundness: 0.5 }
            }
        };
        
        network = new vis.Network(container, { nodes, edges }, options);
        
        // Event handlers
        network.on('click', function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                if (nodeId.startsWith('person_')) {
                    const personId = parseInt(nodeId.replace('person_', ''));
                    showPersonDetails(personId);
                }
            }
        });
        
        network.on('doubleClick', function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                if (nodeId.startsWith('person_')) {
                    const personId = parseInt(nodeId.replace('person_', ''));
                    editPerson(personId);
                }
            }
        });
        
        network.once('stabilizationIterationsDone', function() {
            network.setOptions({ physics: false });
        });
    } catch (error) {
        console.error('Error initializing network:', error);
        showNotification('Fehler beim Laden des Netzwerks', 'error');
    }
}


function focusGraphOnPerson(personId) {
    switchView('graph');
    if (!network) {
        setTimeout(() => focusGraphOnPerson(personId), 500);
        return;
    }
    network.focus(`person_${personId}`, { scale: 1.5, animation: true });
    network.selectNodes([`person_${personId}`]);
}


function focusGraphOnCategory(categoryId) {
    if (categoryId === 'uncategorized') return;
    switchView('graph');
    if (!network) {
        setTimeout(() => focusGraphOnCategory(categoryId), 500);
        return;
    }
    network.focus(`cat_${categoryId}`, { scale: 1.2, animation: true });
    network.selectNodes([`cat_${categoryId}`]);
}


async function refreshNetwork() {
    if (!network) return;
    await loadPersons();
    await loadCategories();
    const response = await fetch('/dating_graph/api/graph-data');
    const graphData = await response.json();
    network.setData({ nodes: graphData.nodes, edges: graphData.edges });
    showNotification('Netzwerk aktualisiert', 'success');
}


function togglePhysics() {
    if (!network) return;
    const currentPhysics = network.physics.options.enabled;
    network.setOptions({ physics: { enabled: !currentPhysics } });
    showNotification(currentPhysics ? 'Physik deaktiviert' : 'Physik aktiviert', 'success');
}


// ================================================================
// FILTERS
// ================================================================
function setupEventListeners() {
    // View switcher tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchView(btn.dataset.view));
    });
    
    // Toggle filters button
    document.getElementById('toggle-filters-btn').addEventListener('click', () => {
        document.getElementById('filters-panel').classList.toggle('collapsed');
    });
    
    // Filter inputs
    document.getElementById('search-input').addEventListener('input', applyFilters);
    document.getElementById('category-filter').addEventListener('change', applyFilters);
    document.getElementById('status-filter').addEventListener('change', applyFilters);
}


function populateFilters() {
    const categoryFilter = document.getElementById('category-filter');
    categoryFilter.innerHTML = '<option value="">Alle Kategorien</option>' +
        categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
}


function applyFilters() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const categoryId = document.getElementById('category-filter').value;
    const status = document.getElementById('status-filter').value;
    
    filteredPersons = persons.filter(person => {
        // Search filter
        if (searchTerm) {
            const matchesSearch = 
                person.name.toLowerCase().includes(searchTerm) ||
                (person.nickname && person.nickname.toLowerCase().includes(searchTerm)) ||
                person.custom_id.toLowerCase().includes(searchTerm);
            if (!matchesSearch) return false;
        }
        
        // Category filter
        if (categoryId) {
            const hasCategory = person.categories.some(cat => cat.id === parseInt(categoryId));
            if (!hasCategory) return false;
        }
        
        // Status filter
        if (status && person.status !== status) {
            return false;
        }
        
        return true;
    });
    
    renderCardsView();
}


function clearFilters() {
    document.getElementById('search-input').value = '';
    document.getElementById('category-filter').value = '';
    document.getElementById('status-filter').value = '';
    applyFilters();
}


// ================================================================
// PERSON DETAILS PANEL
// ================================================================
async function showPersonDetails(personId) {
    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');
    
    try {
        const response = await fetch(`/dating_graph/api/persons/${personId}`);
        const person = await response.json();
        currentPerson = person;
        
        const statusLabels = {
            'interested': { icon: '💖', text: 'Interessiert' },
            'dating': { icon: '❤️', text: 'Dating' },
            'friend': { icon: '😊', text: 'Freund/in' },
            'no_connection': { icon: '😐', text: 'Keine Verbindung' },
            'ghosted': { icon: '👻', text: 'Geghostet' },
            'unknown': { icon: '❓', text: 'Unbekannt' }
        };
        
        const status = statusLabels[person.status] || statusLabels['unknown'];
        
        content.innerHTML = `
            <div class="detail-section">
                <h3><i class="fas fa-user"></i> Grundinformationen</h3>
                <div class="detail-field">
                    <label>Name</label>
                    <p>${person.name}</p>
                </div>
                ${person.nickname ? `
                    <div class="detail-field">
                        <label>Spitzname</label>
                        <p>${person.nickname}</p>
                    </div>
                ` : ''}
                <div class="detail-field">
                    <label>ID</label>
                    <p><code>${person.custom_id}</code></p>
                </div>
                <div class="detail-field">
                    <label>Status</label>
                    <p><span class="status-badge status-${person.status}">${status.icon} ${status.text}</span></p>
                </div>
            </div>
            
            ${person.categories && person.categories.length > 0 ? `
                <div class="detail-section">
                    <h3><i class="fas fa-folder"></i> Kategorien</h3>
                    <div class="category-badges">
                        ${person.categories.map(cat => `
                            <span class="category-chip" style="background: ${cat.color}">
                                ${cat.name}
                            </span>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${person.fun_fact ? `
                <div class="detail-section">
                    <h3><i class="fas fa-lightbulb"></i> Fun Fact</h3>
                    <p>${person.fun_fact}</p>
                </div>
            ` : ''}
            
            ${person.story ? `
                <div class="detail-section">
                    <h3><i class="fas fa-book"></i> Geschichte</h3>
                    <p>${person.story}</p>
                </div>
            ` : ''}
            
            ${person.notes ? `
                <div class="detail-section">
                    <h3><i class="fas fa-sticky-note"></i> Notizen</h3>
                    <p>${person.notes}</p>
                </div>
            ` : ''}
            
            ${person.dates && person.dates.length > 0 ? `
                <div class="detail-section">
                    <h3><i class="fas fa-calendar"></i> Dates (${person.dates.length})</h3>
                    <div class="date-list">
                        ${person.dates.map(date => `
                            <div class="date-item">
                                <div class="date">${new Date(date.date).toLocaleDateString('de-DE')}</div>
                                ${date.title ? `<strong>${date.title}</strong>` : ''}
                                ${date.location ? `<p><i class="fas fa-map-marker-alt"></i> ${date.location}</p>` : ''}
                                ${date.description ? `<p>${date.description}</p>` : ''}
                                ${date.rating ? `<div class="rating">${'⭐'.repeat(date.rating)}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="action-buttons">
                <button class="btn btn-primary" onclick="editPerson(${person.id})">
                    <i class="fas fa-edit"></i> Bearbeiten
                </button>
                <button class="btn btn-danger" onclick="deletePerson(${person.id})">
                    <i class="fas fa-trash"></i> Löschen
                </button>
            </div>
        `;
        
        panel.classList.add('open');
    } catch (error) {
        console.error('Error loading person details:', error);
        showNotification('Fehler beim Laden der Details', 'error');
    }
}


function closeDetailPanel() {
    document.getElementById('detail-panel').classList.remove('open');
}


// ================================================================
// PERSON MODAL (CRUD)
// ================================================================
function openPersonModal(personId = null) {
    const modal = document.getElementById('person-modal');
    const form = document.getElementById('person-form');
    const title = document.getElementById('person-modal-title');
    
    form.reset();
    currentPerson = null;
    
    // Populate categories
    const categorySelect = document.getElementById('person-categories');
    categorySelect.innerHTML = categories.map(c => 
        `<option value="${c.id}">${c.name}</option>`
    ).join('');
    
    if (personId) {
        const person = persons.find(p => p.id === personId);
        if (person) {
            title.textContent = 'Person bearbeiten';
            currentPerson = person;
            
            document.getElementById('person-name').value = person.name || '';
            document.getElementById('person-nickname').value = person.nickname || '';
            document.getElementById('person-custom-id').value = person.custom_id || '';
            document.getElementById('person-status').value = person.status || 'unknown';
            document.getElementById('person-first-contact').value = person.first_contact_date || '';
            document.getElementById('person-fun-fact').value = person.fun_fact || '';
            document.getElementById('person-story').value = person.story || '';
            document.getElementById('person-notes').value = person.notes || '';
            
            if (person.categories) {
                Array.from(categorySelect.options).forEach(option => {
                    option.selected = person.categories.some(c => c.id === parseInt(option.value));
                });
            }
        }
    } else {
        title.textContent = 'Person hinzufügen';
    }
    
    modal.classList.add('show');
}


function editPerson(personId) {
    closeDetailPanel();
    openPersonModal(personId);
}


async function handlePersonSubmit(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('person-name').value,
        nickname: document.getElementById('person-nickname').value,
        custom_id: document.getElementById('person-custom-id').value,
        status: document.getElementById('person-status').value,
        first_contact_date: document.getElementById('person-first-contact').value,
        fun_fact: document.getElementById('person-fun-fact').value,
        story: document.getElementById('person-story').value,
        notes: document.getElementById('person-notes').value,
        category_ids: Array.from(document.getElementById('person-categories').selectedOptions)
            .map(o => parseInt(o.value))
    };
    
    try {
        const url = currentPerson 
            ? `/dating_graph/api/persons/${currentPerson.id}`
            : '/dating_graph/api/persons';
        const method = currentPerson ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showNotification(currentPerson ? 'Person aktualisiert' : 'Person hinzugefügt', 'success');
            closeAllModals();
            await loadPersons();
            await loadStatistics();
            renderCardsView();
            if (network) refreshNetwork();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Fehler beim Speichern', 'error');
        }
    } catch (error) {
        console.error('Error saving person:', error);
        showNotification('Fehler beim Speichern', 'error');
    }
}


async function deletePerson(personId) {
    if (!confirm('Diese Person wirklich löschen?')) return;
    
    try {
        const response = await fetch(`/dating_graph/api/persons/${personId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Person gelöscht', 'success');
            closeDetailPanel();
            await loadPersons();
            await loadStatistics();
            renderCardsView();
            if (network) refreshNetwork();
        } else {
            showNotification('Fehler beim Löschen', 'error');
        }
    } catch (error) {
        console.error('Error deleting person:', error);
        showNotification('Fehler beim Löschen', 'error');
    }
}


// ================================================================
// CATEGORY MODAL
// ================================================================
function openCategoryModal() {
    const modal = document.getElementById('category-modal');
    document.getElementById('category-form').reset();
    modal.classList.add('show');
}


async function handleCategorySubmit(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('category-name').value,
        type: document.getElementById('category-type').value,
        color: document.getElementById('category-color').value,
        icon: document.getElementById('category-icon').value,
        description: document.getElementById('category-description').value
    };
    
    try {
        const response = await fetch('/dating_graph/api/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showNotification('Kategorie hinzugefügt', 'success');
            closeAllModals();
            await loadCategories();
            populateFilters();
            renderCardsView();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Fehler beim Speichern', 'error');
        }
    } catch (error) {
        console.error('Error saving category:', error);
        showNotification('Fehler beim Speichern', 'error');
    }
}


// ================================================================
// UTILITY FUNCTIONS
// ================================================================
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('show');
    });
}


function showNotification(message, type = 'success') {
    const toast = document.getElementById('notification-toast');
    const messageEl = document.getElementById('notification-message');
    
    messageEl.textContent = message;
    toast.className = 'notification-toast show';
    
    if (type === 'error') {
        toast.classList.add('error');
    }
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.classList.remove('error'), 300);
    }, 3000);
}


// Close modals on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeAllModals();
    }
});
