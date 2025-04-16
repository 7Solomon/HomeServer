/**
 * Hauptjavascript-Datei für Home Server
 */
document.addEventListener('DOMContentLoaded', function () {
    // Flash-Nachrichten automatisch ausblenden
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Aktiven Menüpunkt hervorheben
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');

    navLinks.forEach(link => {
        if (currentPath.startsWith(link.getAttribute('href'))) {
            link.classList.add('active');
        }
    });
});
