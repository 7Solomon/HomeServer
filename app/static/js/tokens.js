function copyNewToken() {
    const tokenText = document.getElementById('newToken').textContent;
    const btn = event.target.closest('.copy-token-btn');
    
    navigator.clipboard.writeText(tokenText).then(function() {
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
    }).catch(function(err) {
        console.error('Could not copy token: ', err);
        if (window.showNotification) {
            window.showNotification('Fehler beim Kopieren des Tokens', 'error');
        }
    });
}

// Copy full token from cards
function copyFullToken(token, tokenId) {
    const btn = event.target.closest('.btn-copy');
    
    navigator.clipboard.writeText(token).then(function() {
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
    }).catch(function(err) {
        console.error('Could not copy token: ', err);
        if (window.showNotification) {
            window.showNotification('Fehler beim Kopieren des Tokens', 'error');
        }
    });
}
