document.addEventListener("DOMContentLoaded", () => {
    // --- Loader Logic ---
    const loader = document.getElementById('loader');
    
    // Simulate initialization time to show off the loader
    setTimeout(() => {
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.visibility = 'hidden';
            loader.style.display = 'none';
        }, 800);
    }, 2000);

    // --- Navbar Scroll Effect ---
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // --- Intersection Observer for Scroll Animations ---
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Add an animation class or inline style
                entry.target.style.opacity = 1;
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Select elements to animate
    const animElements = document.querySelectorAll('.feature-card, .risk-item, .arch-card, .code-panel, .setup-content, .faq-card');
    animElements.forEach(el => {
        el.style.opacity = 0;
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        observer.observe(el);
    });

    // --- Smooth Scrolling for Anchor Links ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80, // Offset for navbar
                    behavior: 'smooth'
                });
            }
        });
    });
});

// --- Modal Logic ---
function openDownloadModal() {
    const modal = document.getElementById('downloadModal');
    modal.classList.add('show');
}

function closeDownloadModal() {
    const modal = document.getElementById('downloadModal');
    modal.classList.remove('show');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('downloadModal');
    if (event.target == modal) {
        closeDownloadModal();
    }
}

// Copy Installation Command
function copyInstallCmd() {
    const cmdText = document.getElementById('install-cmd').innerText;
    navigator.clipboard.writeText(cmdText).then(() => {
        const hint = document.getElementById('copy-hint');
        hint.innerText = "Copied!";
        hint.style.color = "var(--success)";
        setTimeout(() => {
            hint.innerText = "Copy";
            hint.style.color = "var(--primary)";
        }, 2000);
    });
}
