// WozapAuto - Interactive JavaScript

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

document.addEventListener('DOMContentLoaded', function() {
    if (!prefersReducedMotion && document.querySelector('.scroll-animate')) {
        initScrollAnimations();
    }

    if (!prefersReducedMotion && document.querySelector('.floating-card')) {
        initFloatingCards();
    }

    if (!prefersReducedMotion && document.querySelector('.hero-section')) {
        initParticleEffect();
    }

    if (!prefersReducedMotion && document.querySelector('[data-typing]')) {
        initTypingEffect();
    }

    if (!prefersReducedMotion && document.querySelector('.stat-number')) {
        initCounterAnimations();
    }

    if (!prefersReducedMotion && document.querySelector('[data-parallax]')) {
        initParallaxEffect();
    }

    if (!prefersReducedMotion && document.querySelector('a[href^="#"]')) {
        initSmoothScrolling();
    }

    if (document.querySelector('[data-loading-button]')) {
        initLoadingStates();
    }

    initMobileNavigation();

    if (document.querySelector('#notificationsDropdown')) {
        initNotificationDropdown();
        initNotificationCenter();
    }

    if (document.querySelectorAll('input, textarea').length) {
        initFormEnhancements();
    }

    initPasswordToggles();

    if (document.querySelector('.mini-chart')) {
        initMiniCharts();
    }
});

// Scroll Animations
function initScrollAnimations() {
    if (prefersReducedMotion) return;
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
            }
        });
    }, observerOptions);

    // Observe all elements with scroll-animate class
    document.querySelectorAll('.scroll-animate').forEach(el => {
        observer.observe(el);
    });
}

// Floating Cards Animation
function initFloatingCards() {
    if (prefersReducedMotion) return;
    const cards = document.querySelectorAll('.floating-card');
    
    cards.forEach((card, index) => {
        // Add random floating animation
        const delay = index * 2;
        const duration = 6 + Math.random() * 2;
        
        card.style.animationDelay = `${delay}s`;
        card.style.animationDuration = `${duration}s`;
        
        // Add hover effects
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-15px) scale(1.05)';
            this.style.zIndex = '10';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.zIndex = '';
        });
    });
}

// Particle Effect
function initParticleEffect() {
    if (prefersReducedMotion) return;
    const heroSection = document.querySelector('.hero-section');
    if (!heroSection) return;

    const canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '1';
    
    heroSection.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    let particles = [];
    
    function resizeCanvas() {
        canvas.width = heroSection.offsetWidth;
        canvas.height = heroSection.offsetHeight;
    }
    
    function createParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            size: Math.random() * 2 + 1,
            opacity: Math.random() * 0.5 + 0.2
        };
    }
    
    function initParticles() {
        particles = [];
        for (let i = 0; i < 50; i++) {
            particles.push(createParticle());
        }
    }
    
    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        particles.forEach(particle => {
            particle.x += particle.vx;
            particle.y += particle.vy;
            
            if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
            if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
            
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(37, 211, 102, ${particle.opacity})`;
            ctx.fill();
        });
        
        requestAnimationFrame(animateParticles);
    }
    
    resizeCanvas();
    initParticles();
    animateParticles();
    
    window.addEventListener('resize', () => {
        resizeCanvas();
        initParticles();
    });
}

// Typing Effect
function initTypingEffect() {
    if (prefersReducedMotion) return;
    const typingElements = document.querySelectorAll('[data-typing]');
    
    typingElements.forEach(element => {
        const text = element.textContent;
        element.textContent = '';
        element.style.borderRight = '2px solid var(--primary-color)';
        
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 100);
            } else {
                setTimeout(() => {
                    element.style.borderRight = 'none';
                }, 1000);
            }
        };
        
        // Start typing when element is visible
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setTimeout(typeWriter, 500);
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(element);
    });
}

// Counter Animations
function initCounterAnimations() {
    if (prefersReducedMotion) return;
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent.replace(/[^\d]/g, ''));
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= target) {
                            current = target;
                            clearInterval(timer);
                        }
                        
                        if (counter.textContent.includes('%')) {
                            counter.textContent = current.toFixed(1) + '%';
                        } else if (counter.textContent.includes('s')) {
                            counter.textContent = current.toFixed(1) + 's';
                        } else {
                            counter.textContent = Math.floor(current).toLocaleString();
                        }
                    }, 16);
                    
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(counter);
    });
}

// Parallax Effect
function initParallaxEffect() {
    if (prefersReducedMotion) return;
    const parallaxElements = document.querySelectorAll('[data-parallax]');
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        
        parallaxElements.forEach(element => {
            const speed = element.dataset.parallax || 0.5;
            const yPos = -(scrolled * speed);
            element.style.transform = `translateY(${yPos}px)`;
        });
    });
}

// Smooth Scrolling
function initSmoothScrolling() {
    if (prefersReducedMotion) return;
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Loading States
function initLoadingStates() {
    const buttons = document.querySelectorAll('[data-loading-button]');
    if (!buttons.length) return;
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            this.classList.add('loading');
            this.setAttribute('aria-busy', 'true');
            this.disabled = true;
            
            const timeout = Number(this.dataset.loadingButton) || 3000;

            setTimeout(() => {
                this.classList.remove('loading');
                this.removeAttribute('aria-busy');
                this.disabled = false;
            }, timeout);
        });
    });
}

// Password Visibility Toggle
function initPasswordToggles() {
    const wrappers = document.querySelectorAll('.password-input');
    if (!wrappers.length) return;

    wrappers.forEach(wrapper => {
        const input = wrapper.querySelector('input');
        if (!input || input.dataset.passwordToggle === 'initialized') {
            return;
        }

        let button = wrapper.querySelector('.password-input__toggle');
        if (!button) {
            button = document.createElement('button');
            button.type = 'button';
            button.className = 'password-input__toggle';
            button.setAttribute('aria-label', 'Show password');
            button.setAttribute('aria-pressed', 'false');
            button.innerHTML = '<i class="bi bi-eye"></i><span class="visually-hidden">Toggle password visibility</span>';
            wrapper.appendChild(button);
        } else {
            if (!button.querySelector('.visually-hidden')) {
                const sr = document.createElement('span');
                sr.className = 'visually-hidden';
                sr.textContent = 'Toggle password visibility';
                button.appendChild(sr);
            }
        }

        const icon = button.querySelector('i') || document.createElement('i');
        if (!icon.parentElement) {
            icon.className = 'bi bi-eye';
            button.insertBefore(icon, button.firstChild);
        }

        const setState = (visible) => {
            button.setAttribute('aria-pressed', visible ? 'true' : 'false');
            button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
            icon.className = `bi ${visible ? 'bi-eye-slash' : 'bi-eye'}`;
        };

        setState(input.type === 'text');

        button.addEventListener('click', () => {
            const shouldShow = input.type === 'password';
            input.type = shouldShow ? 'text' : 'password';
            setState(shouldShow);
        });

        input.dataset.passwordToggle = 'initialized';
    });
}

window.initPasswordToggles = initPasswordToggles;

// Chart Animations
function animateCharts() {
    const chartBars = document.querySelectorAll('.chart-bar');
    
    chartBars.forEach((bar, index) => {
        setTimeout(() => {
            bar.style.animation = 'growUp 1s ease-out forwards';
        }, index * 200);
    });
}

// Initialize charts when visible
const chartObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateCharts();
            chartObserver.unobserve(entry.target);
        }
    });
});

document.querySelectorAll('.mini-chart').forEach(chart => {
    chartObserver.observe(chart);
});

// Mouse Follower Effect - Removed
// The green dot cursor effect has been removed as requested

// Form Enhancements
function initFormEnhancements() {
    const inputs = document.querySelectorAll('input, textarea');
    
    inputs.forEach(input => {
        // Add floating label effect
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
        
        // Add ripple effect on click
        input.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(37, 211, 102, 0.3);
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
            ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// Initialize form enhancements
initFormEnhancements();

// Add ripple animation CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Performance optimization
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

// Optimize scroll events
const optimizedScrollHandler = debounce(() => {
    // Scroll-based animations here
}, 16);

window.addEventListener('scroll', optimizedScrollHandler);

// Mobile Navigation
function initMobileNavigation() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    const mobileNavMenu = document.querySelector('#mobileNavMenu');
    
    if (!navbarToggler || !navbarCollapse || !mobileNavMenu) return;
    
    // Handle mobile menu toggle
    navbarToggler.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (window.innerWidth <= 991.98) {
            const isCollapsed = navbarCollapse.classList.contains('show');
            
            if (isCollapsed) {
                // Close menu
                navbarCollapse.classList.remove('show');
                document.body.style.overflow = '';
            } else {
                // Open menu
                navbarCollapse.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
    });
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 991.98 && 
            navbarCollapse.classList.contains('show') &&
            !navbarCollapse.contains(e.target) && 
            !navbarToggler.contains(e.target)) {
            navbarCollapse.classList.remove('show');
            document.body.style.overflow = '';
        }
    });
    
    // Close mobile menu when clicking on nav links
    const mobileNavLinks = mobileNavMenu.querySelectorAll('.nav-link');
    mobileNavLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 991.98) {
                navbarCollapse.classList.remove('show');
                document.body.style.overflow = '';
            }
        });
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 991.98) {
            navbarCollapse.classList.remove('show');
            document.body.style.overflow = '';
        }
    });
}

// Notification Dropdown
function initNotificationDropdown() {
    const notificationsDropdown = document.querySelector('#notificationsDropdown');
    const dropdownMenu = notificationsDropdown?.nextElementSibling;
    
    if (!notificationsDropdown || !dropdownMenu) return;
    // If Bootstrap dropdown is active via data attribute, let Bootstrap handle it
    if (notificationsDropdown.hasAttribute('data-bs-toggle')) return;
    
    // Handle dropdown toggle
    notificationsDropdown.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const isOpen = dropdownMenu.classList.contains('show');
        
        if (isOpen) {
            dropdownMenu.classList.remove('show');
            notificationsDropdown.setAttribute('aria-expanded', 'false');
        } else {
            dropdownMenu.classList.add('show');
            notificationsDropdown.setAttribute('aria-expanded', 'true');
        }
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!notificationsDropdown.contains(e.target) && 
            !dropdownMenu.contains(e.target) &&
            dropdownMenu.classList.contains('show')) {
            dropdownMenu.classList.remove('show');
            notificationsDropdown.setAttribute('aria-expanded', 'false');
        }
    });
    
    // Handle keyboard navigation
    notificationsDropdown.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && dropdownMenu.classList.contains('show')) {
            dropdownMenu.classList.remove('show');
            notificationsDropdown.setAttribute('aria-expanded', 'false');
            notificationsDropdown.focus();
        }
    });
    
    // Focus management for dropdown items
    const dropdownItems = dropdownMenu.querySelectorAll('.dropdown-item');
    dropdownItems.forEach((item, index) => {
        item.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextItem = dropdownItems[index + 1];
                if (nextItem) nextItem.focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevItem = dropdownItems[index - 1];
                if (prevItem) prevItem.focus();
            } else if (e.key === 'Escape') {
                dropdownMenu.classList.remove('show');
                notificationsDropdown.setAttribute('aria-expanded', 'false');
                notificationsDropdown.focus();
            }
        });
    });
}

// Notification detail modal
function initNotificationCenter() {
    const modalElement = document.getElementById('notificationModal');
    const dropdownTrigger = document.getElementById('notificationsDropdown');

    if (!modalElement || !dropdownTrigger || !window.bootstrap) return;

    const modalInstance = new bootstrap.Modal(modalElement, {
        focus: true,
    });

    const loadingState = modalElement.querySelector('[data-notification-loading]');
    const contentState = modalElement.querySelector('[data-notification-content]');
    const errorAlert = modalElement.querySelector('[data-notification-error]');
    const typeEl = modalElement.querySelector('[data-notification-type]');
    const subjectEl = modalElement.querySelector('[data-notification-subject]');
    const createdEl = modalElement.querySelector('[data-notification-created]');
    const sentWrapper = modalElement.querySelector('[data-notification-sent-wrapper]');
    const sentEl = modalElement.querySelector('[data-notification-sent]');
    const readWrapper = modalElement.querySelector('[data-notification-read-wrapper]');
    const readEl = modalElement.querySelector('[data-notification-read]');
    const statusEl = modalElement.querySelector('[data-notification-status]');
    const contextEl = modalElement.querySelector('[data-notification-context]');
    const unreadBadge = document.getElementById('notificationsUnreadBadge');

    const formatDateTime = (iso) => {
        if (!iso) return null;
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) return null;
        return date.toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short'
        });
    };

    const setLoadingState = (isLoading) => {
        if (isLoading) {
            loadingState.classList.remove('d-none');
            contentState.classList.add('d-none');
            errorAlert.classList.add('d-none');
            errorAlert.textContent = '';
        } else {
            loadingState.classList.add('d-none');
        }
    };

    const updateUnreadBadge = (currentItem) => {
        currentItem.classList.remove('notification-item--unread');
        const badge = currentItem.querySelector('.badge');
        if (badge) {
            badge.remove();
        }

        if (!unreadBadge) return;
        const currentValue = parseInt(unreadBadge.textContent, 10);
        if (!Number.isNaN(currentValue)) {
            const nextValue = Math.max(currentValue - 1, 0);
            if (nextValue === 0) {
                unreadBadge.remove();
            } else {
                unreadBadge.textContent = nextValue;
            }
        }
    };

    const showError = (message) => {
        errorAlert.textContent = message || 'Unable to load notification details. Please try again later.';
        errorAlert.classList.remove('d-none');
    };

    document.querySelectorAll('[data-notification-id]').forEach((item) => {
        item.addEventListener('click', (event) => {
            event.preventDefault();

            const notificationId = item.dataset.notificationId;
            if (!notificationId) return;

            const wasUnread = item.classList.contains('notification-item--unread');

            const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownTrigger);
            if (dropdownInstance) {
                dropdownInstance.hide();
            }

            modalInstance.show();
            setLoadingState(true);

            fetch(`/audit/notifications/${notificationId}/detail/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Request failed with status ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    setLoadingState(false);

                    typeEl.textContent = data.type || 'Notification';
                    subjectEl.textContent = data.subject || 'No subject';
                    createdEl.textContent = formatDateTime(data.created_at) || '—';
                    statusEl.textContent = data.status || 'Unknown status';

                    if (data.sent_at) {
                        sentEl.textContent = formatDateTime(data.sent_at);
                        sentWrapper.classList.remove('d-none');
                    } else {
                        sentWrapper.classList.add('d-none');
                        sentEl.textContent = '';
                    }

                    if (data.read_at) {
                        readEl.textContent = formatDateTime(data.read_at);
                        readWrapper.classList.remove('d-none');
                    } else {
                        readWrapper.classList.add('d-none');
                        readEl.textContent = '';
                    }

                    const context = data.context && Object.keys(data.context).length
                        ? JSON.stringify(data.context, null, 2)
                        : 'No additional context available.';
                    contextEl.textContent = context;

                    contentState.classList.remove('d-none');

                    if (data.is_read && wasUnread) {
                        updateUnreadBadge(item);
                    }
                })
                .catch((error) => {
                    setLoadingState(false);
                    showError(error.message);
                    console.error('Failed to load notification detail', error);
                });
        });
    });
}
