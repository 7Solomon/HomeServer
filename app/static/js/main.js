/**
 * Hauptjavascript-Datei für Heim Speicher
 */
document.addEventListener('DOMContentLoaded', function () {
    // Flash-Nachrichten automatisch ausblenden mit Animation
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach((message, index) => {
        // Zeitversetzt anzeigen für bessere UX
        setTimeout(() => {
            message.classList.add('fade-in');
        }, index * 200);
        
        // Automatisch ausblenden nach 5 Sekunden
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000 + (index * 200));
    });

    // Aktiven Menüpunkt hervorheben
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');

    navLinks.forEach(link => {
        if (currentPath === link.getAttribute('href') || 
            (link.getAttribute('href') !== '/' && currentPath.startsWith(link.getAttribute('href')))) {
            link.classList.add('active');
        }
    });

    // Scroll-to-Top-Button hinzufügen
    const scrollToTopBtn = document.createElement('button');
    scrollToTopBtn.className = 'scroll-to-top';
    scrollToTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollToTopBtn.setAttribute('aria-label', 'Nach oben scrollen');
    scrollToTopBtn.setAttribute('data-tooltip', 'Nach oben scrollen');
    document.body.appendChild(scrollToTopBtn);

    // Scroll-to-Top-Button Funktionalität
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollToTopBtn.classList.add('visible');
        } else {
            scrollToTopBtn.classList.remove('visible');
        }
    });

    scrollToTopBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // Smooth scrolling für alle internen Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Moderne Eingabefeld-Animationen
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        // Fokus-Animationen
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });

    // Keyboard-Navigation für bessere Accessibility
    document.addEventListener('keydown', function(e) {
        // Esc-Taste schließt Modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            });
        }
    });

    // Lazy Loading für Bilder
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Prefers-reduced-motion Unterstützung
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
        document.documentElement.style.setProperty('--animation-duration', '0s');
    }

    // Performance-Optimierung: Debounce für Scroll-Events
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            document.body.classList.toggle('scrolling', window.scrollY > 50);
        }, 10);
    });

    // Theme-Umschaltung vorbereiten (falls gewünscht)
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    function handleThemeChange(e) {
        document.body.classList.toggle('dark-theme', e.matches);
    }
    mediaQuery.addListener(handleThemeChange);
    handleThemeChange(mediaQuery);

    // Moderne Notification-Funktionalität
    window.showNotification = function(message, type = 'info', duration = 5000) {
        const container = document.querySelector('.notification-container') || createNotificationContainer();
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    <i class="fas fa-${getIconForType(type)}"></i>
                </div>
                <div class="notification-message">${message}</div>
                <button class="notification-close" aria-label="Schließen">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Animation hinzufügen
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Auto-remove
        setTimeout(() => {
            notification.classList.add('fade');
            setTimeout(() => notification.remove(), 300);
        }, duration);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.classList.add('fade');
            setTimeout(() => notification.remove(), 300);
        });
    };

    function createNotificationContainer() {
        const container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    function getIconForType(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Verbesserte Ladeanimation
    window.addEventListener('beforeunload', function() {
        document.body.classList.add('page-loading');
    });

    // Mobile device detection and optimization
    function detectMobileDevice() {
        const isMobile = window.innerWidth <= 768;
        const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
        const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const isAndroid = /Android/.test(navigator.userAgent);
        
        // Add device classes to body
        document.body.classList.toggle('mobile', isMobile);
        document.body.classList.toggle('tablet', isTablet);
        document.body.classList.toggle('touch-device', isTouch);
        document.body.classList.toggle('ios', isIOS);
        document.body.classList.toggle('android', isAndroid);
        
        // Add viewport meta tag adjustments for mobile
        if (isMobile) {
            let viewport = document.querySelector('meta[name="viewport"]');
            if (viewport) {
                viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
            }
        }
        
        return { isMobile, isTablet, isTouch, isIOS, isAndroid };
    }
    
    // Initialize mobile detection
    const deviceInfo = detectMobileDevice();
    
    // Re-detect on resize (for device rotation)
    window.addEventListener('resize', debounce(detectMobileDevice, 250));
    
    // Mobile-specific optimizations
    if (deviceInfo.isMobile || deviceInfo.isTouch) {
        // Prevent iOS bounce scrolling
        document.body.addEventListener('touchmove', function(e) {
            if (e.target === document.body) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Improve touch scrolling
        document.body.style.webkitOverflowScrolling = 'touch';
        
        // Add mobile-specific classes for better styling
        document.documentElement.classList.add('mobile-optimized');
        
        // Optimize file list for mobile
        const fileItems = document.querySelectorAll('.file-item');
        fileItems.forEach(item => {
            item.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            });
            
            item.addEventListener('touchend', function() {
                this.classList.remove('touch-active');
            });
        });
    }
    
    // iOS-specific optimizations
    if (deviceInfo.isIOS) {
        // Fix iOS viewport issues
        window.addEventListener('orientationchange', function() {
            setTimeout(() => {
                window.scrollTo(0, 0);
            }, 100);
        });
        
        // Improve iOS form handling
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                // Prevent iOS zoom on focus
                this.style.fontSize = '16px';
            });
            
            input.addEventListener('blur', function() {
                this.style.fontSize = '';
            });
        });
    }
    
    // Android-specific optimizations
    if (deviceInfo.isAndroid) {
        // Improve Android performance
        document.body.classList.add('android-optimized');
        
        // Fix Android keyboard issues
        window.addEventListener('resize', function() {
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
                setTimeout(() => {
                    document.activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            }
        });
    }
    
    // Mobile navigation improvements
    if (deviceInfo.isMobile) {
        const nav = document.querySelector('nav');
        if (nav) {
            // Add touch-friendly swipe gestures (optional)
            let touchStartX = 0;
            let touchEndX = 0;
            
            nav.addEventListener('touchstart', function(e) {
                touchStartX = e.changedTouches[0].screenX;
            });
            
            nav.addEventListener('touchend', function(e) {
                touchEndX = e.changedTouches[0].screenX;
                // Could add swipe navigation here if needed
            });
        }
    }
    
    // Mobile-specific notification positioning
    if (deviceInfo.isMobile) {
        const originalShowNotification = window.showNotification;
        window.showNotification = function(message, type = 'info', duration = 5000) {
            const container = document.querySelector('.notification-container') || createNotificationContainer();
            
            // Position notifications at top on mobile
            if (!container.classList.contains('mobile-positioned')) {
                container.style.top = '10px';
                container.style.left = '10px';
                container.style.right = '10px';
                container.style.bottom = 'auto';
                container.classList.add('mobile-positioned');
            }
            
            // Use original function with mobile positioning
            originalShowNotification.call(this, message, type, duration);
        };
    }
    
    // Debounce utility function
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Mobile performance optimization
    if (deviceInfo.isMobile) {
        // Reduce animation complexity on mobile
        const style = document.createElement('style');
        style.textContent = `
            @media (max-width: 768px) {
                *, *::before, *::after {
                    animation-duration: 0.2s !important;
                    transition-duration: 0.2s !important;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // PWA-like features for mobile
    if (deviceInfo.isMobile) {
        // Add to home screen prompt (for supported browsers)
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            
            // Show install button or banner
            const installBtn = document.createElement('button');
            installBtn.textContent = 'App installieren';
            installBtn.className = 'btn btn-primary install-btn';
            installBtn.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 1000;
                box-shadow: var(--shadow-lg);
            `;
            
            installBtn.addEventListener('click', () => {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('App installation accepted');
                    }
                    deferredPrompt = null;
                    installBtn.remove();
                });
            });
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (installBtn.parentElement) {
                    installBtn.remove();
                }
            }, 10000);
            
            document.body.appendChild(installBtn);
        });
    }

    // Console-Nachricht für Entwickler
    console.log('%c🏠 Heim Speicher', 'font-size: 20px; color: #667eea; font-weight: bold;');
    console.log('%cModerne Benutzeroberfläche geladen ✨', 'color: #10b981; font-weight: bold;');
});
