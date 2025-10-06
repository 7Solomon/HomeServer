// State Management
let currentImage = null;
let currentPdfDoc = null;
let currentPdfPage = 1;
let totalPdfPages = 0;
let allSections = {}; // Store sections per page: { pageNum: [sections] }
let sections = []; // Current page sections
let isDrawing = false;
let startPos = null;
let canvas = null;
let ctx = null;
let showSections = true;
let selectedSection = null;

pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

const colors = [
    'rgba(255, 99, 132, 0.3)',
    'rgba(54, 162, 235, 0.3)',
    'rgba(255, 206, 86, 0.3)',
    'rgba(75, 192, 192, 0.3)',
    'rgba(153, 102, 255, 0.3)',
    'rgba(255, 159, 64, 0.3)',
];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    canvas = document.getElementById('imageCanvas');
    if (!canvas) {
        console.error('Canvas element not found');
        return;
    }
    
    ctx = canvas.getContext('2d');
    
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', handleImageUpload);
    }
    
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    
    const toggleBtn = document.getElementById('toggleSectionsBtn');
    if (toggleBtn) toggleBtn.addEventListener('click', toggleSections);
    
    const clearBtn = document.getElementById('clearAllBtn');
    if (clearBtn) clearBtn.addEventListener('click', clearAll);
    
    const finalizeBtn = document.getElementById('finalizeBtn');
    if (finalizeBtn) finalizeBtn.addEventListener('click', finalizeSong);

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn) prevBtn.addEventListener('click', () => changePdfPage(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => changePdfPage(1));
});

async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const fileType = file.type;
    
    if (fileType === 'application/pdf') {
        await loadPdf(file);
    } else {
        loadImage(file);
    }
}

function loadImage(file) {
    const reader = new FileReader();
    reader.onload = function(event) {
        const img = new Image();
        img.onload = function() {
            currentImage = img;
            currentPdfDoc = null;
            document.getElementById('pdfNavigation').classList.add('d-none');
            
            canvas.width = img.width;
            canvas.height = img.height;
            redrawCanvas();
            
            document.getElementById('uploadArea').classList.add('d-none');
            document.getElementById('canvasArea').classList.remove('d-none');
            
            showToast('Image loaded successfully', 'success');
        };
        img.src = event.target.result;
    };
    reader.readAsDataURL(file);
}

async function loadPdf(file) {
    try {
        showToast('Loading PDF...', 'info');
        
        const arrayBuffer = await file.arrayBuffer();
        const loadingTask = pdfjsLib.getDocument({data: arrayBuffer});
        const pdf = await loadingTask.promise;
        
        currentPdfDoc = pdf;
        totalPdfPages = pdf.numPages;
        currentPdfPage = 1;
        
        document.getElementById('pdfNavigation').classList.remove('d-none');
        updatePdfPageInfo();
        
        await renderPdfPage(currentPdfPage);
        
        document.getElementById('uploadArea').classList.add('d-none');
        document.getElementById('canvasArea').classList.remove('d-none');
        
        showToast(`PDF loaded: ${totalPdfPages} page(s)`, 'success');
    } catch (error) {
        console.error('Error loading PDF:', error);
        showToast('Failed to load PDF: ' + error.message, 'danger');
    }
}

async function renderPdfPage(pageNum) {
    if (!currentPdfDoc) return;
    
    try {
        const page = await currentPdfDoc.getPage(pageNum);
        const scale = 2.0;
        const viewport = page.getViewport({scale: scale});
        
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
        currentImage = await createImageFromCanvas();
        redrawCanvas();
        
    } catch (error) {
        console.error('Error rendering PDF page:', error);
        showToast('Failed to render PDF page', 'danger');
    }
}

function createImageFromCanvas() {
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.src = canvas.toDataURL();
    });
}

function changePdfPage(delta) {
    if (!currentPdfDoc) return;
    
    const newPage = currentPdfPage + delta;
    if (newPage < 1 || newPage > totalPdfPages) return;
    
    // Save current page sections
    saveCurrentPageSections();
    
    // Change page
    currentPdfPage = newPage;
    updatePdfPageInfo();
    renderPdfPage(currentPdfPage);
    
    // Load sections for new page
    loadPageSections(currentPdfPage);
}

function saveCurrentPageSections() {
    if (currentPdfDoc) {
        allSections[currentPdfPage] = [...sections]; // Deep copy
    }
}

function loadPageSections(pageNum) {
    sections = allSections[pageNum] || [];
    selectedSection = null;
    updateSectionsList();
    redrawCanvas();
    document.getElementById('sectionDetails').classList.add('d-none');
}

function updatePdfPageInfo() {
    const pageIndicator = document.getElementById('pageInfo');
    pageIndicator.textContent = `Page ${currentPdfPage} / ${totalPdfPages}`;
    
    // Show section count for this page
    const currentPageSections = allSections[currentPdfPage] || [];
    const totalSectionsAcrossPages = Object.values(allSections).reduce((sum, pageSections) => sum + pageSections.length, 0);
    
    if (totalSectionsAcrossPages > currentPageSections.length) {
        pageIndicator.textContent += ` (${currentPageSections.length} sections on this page, ${totalSectionsAcrossPages} total)`;
    }
    
    document.getElementById('prevPageBtn').disabled = currentPdfPage <= 1;
    document.getElementById('nextPageBtn').disabled = currentPdfPage >= totalPdfPages;
}

function redrawCanvas() {
    if (!currentImage) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0);

    if (showSections) {
        sections.forEach(section => {
            ctx.fillStyle = section.color;
            ctx.fillRect(section.x, section.y, section.width, section.height);
            
            ctx.strokeStyle = section.color.replace('0.3', '1');
            ctx.lineWidth = 2;
            ctx.strokeRect(section.x, section.y, section.width, section.height);
            
            ctx.fillStyle = section.color.replace('0.3', '0.8');
            ctx.fillRect(section.x, section.y, 150, 30);
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 14px Arial';
            ctx.fillText(section.name, section.x + 5, section.y + 20);
        });
    }
}

function getCanvasCoordinates(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY
    };
}

function handleMouseDown(e) {
    startPos = getCanvasCoordinates(e);
    isDrawing = true;
}

function handleMouseMove(e) {
    if (!isDrawing) return;

    const currentPos = getCanvasCoordinates(e);
    redrawCanvas();

    ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(
        Math.min(startPos.x, currentPos.x),
        Math.min(startPos.y, currentPos.y),
        Math.abs(currentPos.x - startPos.x),
        Math.abs(currentPos.y - startPos.y)
    );
    ctx.setLineDash([]);
}

async function handleMouseUp(e) {
    if (!isDrawing) return;
    isDrawing = false;

    const endPos = getCanvasCoordinates(e);
    const width = Math.abs(endPos.x - startPos.x);
    const height = Math.abs(endPos.y - startPos.y);

    if (width > 10 && height > 10) {
        const songKey = document.getElementById('songKey').value.trim();
        if (!songKey) {
            showToast('Please enter the song key first!', 'warning');
            startPos = null;
            return;
        }

        const sectionName = prompt('Enter section name (e.g., Verse 1, Chorus):');
        if (sectionName) {
            const section = {
                id: Date.now(),
                name: sectionName,
                x: Math.min(startPos.x, endPos.x),
                y: Math.min(startPos.y, endPos.y),
                width: width,
                height: height,
                color: colors[sections.length % colors.length],
                ocrResult: null,
                processing: true,
                pageNumber: currentPdfDoc ? currentPdfPage : null
            };
            
            sections.push(section);
            saveCurrentPageSections(); // Save after adding
            updateSectionsList();
            redrawCanvas();
            
            // Auto-process the section
            await processSection(section.id);
        }
    }

    startPos = null;
}

function updateSectionsList() {
    const list = document.getElementById('sectionsList');
    const count = document.getElementById('sectionCount');
    
    // Count all sections across all pages
    const totalSections = Object.values(allSections).reduce((sum, pageSections) => sum + pageSections.length, 0);
    count.textContent = totalSections;

    if (sections.length === 0) {
        const pageInfo = currentPdfDoc ? ` on page ${currentPdfPage}` : '';
        list.innerHTML = `<div class="list-group-item text-center text-muted">No sections${pageInfo}. Draw on the image to create sections.</div>`;
        
        // Check if there are sections on other pages
        const allProcessed = Object.values(allSections).every(pageSections => 
            pageSections.every(s => s.ocrResult && !s.processing)
        );
        document.getElementById('finalizeBtn').disabled = !allProcessed || totalSections === 0;
        return;
    }

    const allProcessed = Object.values(allSections).every(pageSections => 
        pageSections.every(s => s.ocrResult && !s.processing)
    );
    document.getElementById('finalizeBtn').disabled = !allProcessed || totalSections === 0;
    
    list.innerHTML = sections.map(section => {
        let statusBadge = '';
        if (section.processing) {
            statusBadge = '<span class="badge bg-warning"><i class="bi bi-hourglass-split"></i> Processing...</span>';
        } else if (section.ocrResult) {
            statusBadge = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Ready</span>';
        } else {
            statusBadge = '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Failed</span>';
        }

        return `
            <div class="list-group-item section-item ${selectedSection?.id === section.id ? 'active' : ''}" 
                 onclick="selectSection(${section.id})">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="d-flex align-items-center gap-2">
                        <span class="section-color-indicator rounded" style="background-color: ${section.color}"></span>
                        <strong>${section.name}</strong>
                        ${section.pageNumber ? `<span class="badge bg-secondary">p.${section.pageNumber}</span>` : ''}
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="event.stopPropagation(); reprocessSection(${section.id})" 
                                ${section.processing ? 'disabled' : ''} title="Reprocess">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="event.stopPropagation(); deleteSection(${section.id})" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
                <div>${statusBadge}</div>
            </div>
        `;
    }).join('');
}

function selectSection(sectionId) {
    selectedSection = sections.find(s => s.id === sectionId);
    updateSectionsList();
    showSectionDetails(selectedSection);
}
function showSectionDetails(section) {
    const detailsCard = document.getElementById('sectionDetails');
    const detailName = document.getElementById('detailSectionName');
    const detailContent = document.getElementById('detailContent');

    detailsCard.classList.remove('d-none');
    detailName.textContent = section.name;

    if (section.processing) {
        detailContent.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Processing...</span>
                </div>
                <p class="mt-3 text-muted">Processing OCR...</p>
            </div>
        `;
    } else if (section.ocrResult) {
        // Build preview with proper formatting
        let previewHtml = '';
        
        if (section.ocrResult.structured_data && section.ocrResult.structured_data.lines) {
            // Use structured data to build preview (more accurate)
            section.ocrResult.structured_data.lines.forEach(line => {
                if (line.type === 'chords') {
                    // Reconstruct chord line with proper spacing
                    const chordItems = line.content || [];
                    
                    if (chordItems.length > 0) {
                        // Find min position for relative positioning
                        const positions = chordItems.map(item => item.position_x);
                        const minPos = Math.min(...positions);
                        const avgCharWidth = 10;
                        
                        let chordLine = '';
                        let lastCharPos = 0;
                        
                        chordItems.forEach(item => {
                            const pixelPos = item.position_x;
                            const charPos = Math.floor((pixelPos - minPos) / avgCharWidth);
                            const spacesNeeded = Math.max(0, charPos - lastCharPos);
                            
                            chordLine += ' '.repeat(spacesNeeded) + item.chord;
                            lastCharPos = charPos + item.chord.length;
                        });
                        
                        previewHtml += `<div class="preview-line text-primary fw-bold">${escapeHtml(chordLine)}</div>`;
                    }
                } else if (line.type === 'lyrics') {
                    // Concatenate lyric content
                    const lyricText = (line.content || []).map(item => item.text).join(' ');
                    previewHtml += `<div class="preview-line">${escapeHtml(lyricText)}</div>`;
                }
            });
        } else if (section.ocrResult.text) {
            // Fallback: Use plain text with preserved spacing
            const lines = section.ocrResult.text.split('\n');
            previewHtml = lines.map(line => {
                // Better chord line detection - check if it's mostly short tokens or numbers
                const tokens = line.trim().split(/\s+/);
                const avgTokenLength = tokens.length > 0 
                    ? tokens.reduce((sum, t) => sum + t.length, 0) / tokens.length 
                    : 0;
                const isChordLine = tokens.length > 0 && avgTokenLength < 4 && 
                    tokens.some(t => /^[\d#bmaug\-dim°ø+()\/]+$/.test(t) || !isNaN(t));
                
                const lineClass = isChordLine ? 'text-primary fw-bold' : '';
                return `<div class="preview-line ${lineClass}">${escapeHtml(line) || '&nbsp;'}</div>`;
            }).join('');
        }

        detailContent.innerHTML = `
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>OCR Result:</strong>
                    <button class="btn btn-sm btn-outline-primary" onclick="editSection(${section.id})">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                </div>
                <div class="ocr-preview bg-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">
                    ${previewHtml}
                </div>
            </div>
            <div class="mb-2">
                <strong>Confidence:</strong> ${(section.ocrResult.confidence * 100).toFixed(1)}%
            </div>
            <div class="mb-2">
                <strong>Position:</strong> (${Math.round(section.x)}, ${Math.round(section.y)})
            </div>
            <div>
                <strong>Size:</strong> ${Math.round(section.width)} × ${Math.round(section.height)}px
            </div>
        `;
    } else {
        detailContent.innerHTML = '<div class="alert alert-danger">OCR processing failed. Click reprocess to try again.</div>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function editSection(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (!section || !section.ocrResult) return;

    const detailContent = document.getElementById('detailContent');
    const currentText = section.ocrResult.text || '';

    detailContent.innerHTML = `
        <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>Edit OCR Result:</strong>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-success" onclick="saveEdit(${section.id})">
                        <i class="bi bi-check-lg"></i> Save
                    </button>
                    <button class="btn btn-secondary" onclick="cancelEdit(${section.id})">
                        <i class="bi bi-x-lg"></i> Cancel
                    </button>
                </div>
            </div>
            <textarea id="editTextArea" class="form-control font-monospace" rows="15" style="font-size: 14px;">${escapeHtml(currentText)}</textarea>
            <small class="text-muted mt-2 d-block">
                <i class="bi bi-info-circle"></i> 
                Keep chord lines and lyric lines on separate lines. Maintain spacing for chord positions.
            </small>
        </div>
    `;

    // Focus the textarea
    document.getElementById('editTextArea').focus();
}

async function saveEdit(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (!section) return;

    const textarea = document.getElementById('editTextArea');
    const newText = textarea.value;
    const songKey = document.getElementById('songKey').value.trim();

    if (!songKey) {
        showToast('Please enter the song key first!', 'warning');
        return;
    }

    try {
        showToast('Updating section...', 'info');
        
        // Send to backend for proper parsing
        const response = await fetch('/ocr/api/section/edit', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + (localStorage.getItem('token') || ''),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: newText,
                section_name: section.name,
                key: songKey
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update the section with properly parsed data
            section.ocrResult.text = data.text;
            section.ocrResult.structured_data = data.structured_data;
            
            showToast(`✓ "${section.name}" updated`, 'success');
            showSectionDetails(section);
            updateSectionsList();
            
            // Save to page sections
            saveCurrentPageSections();
        } else {
            throw new Error(data.error || 'Update failed');
        }
        
    } catch (error) {
        console.error('Error updating section:', error);
        showToast('Error updating section: ' + error.message, 'danger');
    }
}

function cancelEdit(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (section) {
        showSectionDetails(section);
    }
}

async function processSection(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (!section) return;

    const songKey = document.getElementById('songKey').value.trim();
    if (!songKey) {
        showToast('Please enter the song key first!', 'warning');
        section.processing = false;
        updateSectionsList();
        return;
    }

    section.processing = true;
    updateSectionsList();

    try {
        // Extract section from canvas
        const imageData = ctx.getImageData(section.x, section.y, section.width, section.height);
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = section.width;
        tempCanvas.height = section.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.putImageData(imageData, 0, 0);

        const blob = await new Promise(resolve => tempCanvas.toBlob(resolve));
        
        // Upload
        const formData = new FormData();
        formData.append('file', blob, 'section.png');
        
        const uploadResponse = await fetch('/ocr/api/upload', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + (localStorage.getItem('token') || '')
            },
            body: formData
        });
        
        const uploadData = await uploadResponse.json();
        
        if (uploadData.success) {
            // Process OCR
            const processResponse = await fetch('/ocr/api/process', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + (localStorage.getItem('token') || ''),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_id: uploadData.file_id,
                    language: document.getElementById('language').value,
                    section_name: section.name,
                    song_key: songKey
                })
            });
            
            const processData = await processResponse.json();
            
            if (processData.success) {
                section.ocrResult = processData;
                section.processing = false;
                updateSectionsList();
                showToast(`✓ "${section.name}" processed`, 'success');
                
                if (selectedSection?.id === section.id) {
                    showSectionDetails(section);
                }
            } else {
                throw new Error(processData.error || 'Processing failed');
            }
        } else {
            throw new Error(uploadData.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(`Failed: "${section.name}" - ${error.message}`, 'danger');
        section.processing = false;
        section.ocrResult = null;
        updateSectionsList();
    }
}

async function reprocessSection(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (section) {
        section.ocrResult = null;
        await processSection(sectionId);
    }
}

function deleteSection(sectionId) {
    if (confirm('Delete this section?')) {
        sections = sections.filter(s => s.id !== sectionId);
        saveCurrentPageSections(); // Save after deleting
        
        if (selectedSection?.id === sectionId) {
            selectedSection = null;
            document.getElementById('sectionDetails').classList.add('d-none');
        }
        updateSectionsList();
        redrawCanvas();
        showToast('Section deleted', 'info');
    }
}

function toggleSections() {
    showSections = !showSections;
    redrawCanvas();
}

function clearAll() {
    if (confirm('Clear all sections from ALL pages and start over?')) {
        sections = [];
        allSections = {};
        selectedSection = null;
        updateSectionsList();
        redrawCanvas();
        document.getElementById('sectionDetails').classList.add('d-none');
        showToast('All sections cleared', 'info');
    }
}

async function finalizeSong() {
    const songName = document.getElementById('songName').value.trim();
    const songKey = document.getElementById('songKey').value.trim();
    
    if (!songName || !songKey) {
        showToast('Please enter song name and key', 'warning');
        return;
    }
    
    // Save current page before finalizing
    saveCurrentPageSections();
    
    // Collect all sections from all pages
    const allSectionsFlat = [];
    Object.keys(allSections).sort((a, b) => parseInt(a) - parseInt(b)).forEach(pageNum => {
        allSectionsFlat.push(...allSections[pageNum]);
    });
    
    const unprocessed = allSectionsFlat.filter(s => !s.ocrResult || s.processing);
    if (unprocessed.length > 0) {
        showToast(`${unprocessed.length} section(s) not ready. Please wait or reprocess.`, 'warning');
        return;
    }
    
    const sectionsData = allSectionsFlat.map(s => ({
        section_name: s.name,
        structured_data: s.ocrResult.structured_data,
        page_number: s.pageNumber
    }));
    
    try {
        showToast('Finalizing song...', 'info');
        
        const response = await fetch('/ocr/api/finalize-song', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + (localStorage.getItem('token') || ''),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sections: sectionsData,
                title: songName,
                key: songKey,
                authors: []
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const blob = new Blob([JSON.stringify(data.song, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${songName.replace(/\s+/g, '_')}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            showToast('🎵 Song finalized and downloaded!', 'success');
        } else {
            throw new Error(data.error || 'Finalization failed');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to finalize: ' + error.message, 'danger');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}