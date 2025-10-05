function copyNewToken() {
    const tokenText = document.getElementById('newToken').textContent;
    const btn = event.target.closest('.copy-token-btn');
    
    copyToClipboard(tokenText, btn);
}

// Copy full token from cards
function copyFullToken(token, tokenId) {
    const btn = event.target.closest('.btn-copy');
    copyToClipboard(token, btn);
}

// Universal copy function with fallback
function copyToClipboard(text, btn) {
    // Try modern clipboard API first (works on HTTPS and localhost)
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function() {
            showCopySuccess(btn);
        }).catch(function(err) {
            console.warn('Clipboard API failed, using fallback:', err);
            fallbackCopyToClipboard(text, btn);
        });
    } else {
        // Fallback for HTTP connections
        fallbackCopyToClipboard(text, btn);
    }
}

// Fallback method using execCommand (works on HTTP)
function fallbackCopyToClipboard(text, btn) {
    // Create temporary textarea
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.top = '0';
    textarea.style.left = '0';
    textarea.style.width = '2em';
    textarea.style.height = '2em';
    textarea.style.padding = '0';
    textarea.style.border = 'none';
    textarea.style.outline = 'none';
    textarea.style.boxShadow = 'none';
    textarea.style.background = 'transparent';
    textarea.style.opacity = '0';
    
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopySuccess(btn);
        } else {
            showCopyError();
        }
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showCopyError();
    }
    
    document.body.removeChild(textarea);
}

// Show success feedback
function showCopySuccess(btn) {
    if (window.showNotification) {
        window.showNotification('Token in Zwischenablage kopiert!', 'success');
    }
    
    // Visual feedback
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Kopiert!';
    btn.classList.add('copied');
    
    setTimeout(() => {
        btn.innerHTML = originalContent;
        btn.classList.remove('copied');
    }, 2000);
}

// Show error feedback
function showCopyError() {
    if (window.showNotification) {
        window.showNotification('Fehler beim Kopieren des Tokens', 'error');
    } else {
        alert('Fehler beim Kopieren. Bitte Token manuell kopieren.');
    }
}
