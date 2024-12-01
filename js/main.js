// Mobile Menu Toggle
const menuBtn = document.querySelector('.menu-btn');
const navLinks = document.querySelector('.nav-links');
const navbar = document.querySelector('.navbar');

menuBtn.addEventListener('click', () => {
    navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
});

// Mobile Menu Functionality
const menuBtnMobile = document.querySelector('.menu-btn-mobile');
const navLinksMobile = document.querySelector('.nav-links-mobile');
let menuOpen = false;

menuBtnMobile.addEventListener('click', () => {
    if (!menuOpen) {
        menuBtnMobile.classList.add('open');
        navLinksMobile.classList.add('active');
        document.body.style.overflow = 'hidden';
    } else {
        menuBtnMobile.classList.remove('open');
        navLinksMobile.classList.remove('active');
        document.body.style.overflow = '';
    }
    menuOpen = !menuOpen;
});

// Close menu when clicking outside
document.addEventListener('click', (e) => {
    if (menuOpen && !e.target.closest('.nav-links-mobile') && !e.target.closest('.menu-btn-mobile')) {
        menuBtnMobile.classList.remove('open');
        navLinksMobile.classList.remove('active');
        document.body.style.overflow = '';
        menuOpen = false;
    }
});

// Close menu when clicking a link
navLinksMobile.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        if (menuOpen) {
            menuBtnMobile.classList.remove('open');
            navLinksMobile.classList.remove('active');
            document.body.style.overflow = '';
            menuOpen = false;
        }
    });
});

// Navbar Scroll Effect
let lastScroll = 0;
window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll <= 0) {
        navbar.classList.remove('scroll-up');
        return;
    }
    
    if (currentScroll > lastScroll && !navbar.classList.contains('scroll-down')) {
        navbar.classList.remove('scroll-up');
        navbar.classList.add('scroll-down');
    } else if (currentScroll < lastScroll && navbar.classList.contains('scroll-down')) {
        navbar.classList.remove('scroll-down');
        navbar.classList.add('scroll-up');
    }
    lastScroll = currentScroll;
});

// Smooth Scrolling for Navigation Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        const navHeight = document.querySelector('.navbar').offsetHeight;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset;
        
        window.scrollTo({
            top: targetPosition - navHeight,
            behavior: 'smooth'
        });

        // Close mobile menu if open
        if (window.innerWidth <= 768) {
            navLinks.style.display = 'none';
        }
    });
});

// Form Submission
const contactForm = document.getElementById('contact-form');
contactForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Get form data
    const formData = new FormData(this);
    const data = Object.fromEntries(formData);
    
    // Here you would typically send the data to a server
    console.log('Form submitted:', data);
    
    // Show success message
    const button = this.querySelector('button[type="submit"]');
    const originalText = button.textContent;
    button.textContent = 'Message Sent!';
    button.classList.add('success');
    
    setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove('success');
        this.reset();
    }, 3000);
});

// Scroll Animation for Sections
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
            
            // Animate children with delay for cascade effect
            const children = entry.target.querySelectorAll('.project-card, .certification-card, .timeline-item, .skill-item');
            children.forEach((child, index) => {
                setTimeout(() => {
                    child.classList.add('animate');
                }, index * 100);
            });
        }
    });
}, observerOptions);

// Observe all sections and cards
document.querySelectorAll('section, .project-card, .certification-card, .timeline-item, .skill-item').forEach((section) => {
    observer.observe(section);
});

// Dynamic Year in Footer
document.querySelector('footer p').innerHTML = 
    `&copy; ${new Date().getFullYear()} Hossein Ghobadi. All rights reserved.`;

// Add active state to navigation links
function setActiveNavLink() {
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('.nav-links a');
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        const sectionHeight = section.clientHeight;
        const scroll = window.scrollY;
        
        if (scroll >= sectionTop && scroll < sectionTop + sectionHeight) {
            const id = section.getAttribute('id');
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${id}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}

window.addEventListener('scroll', setActiveNavLink);

// Scroll to Top Button
const scrollTopBtn = document.getElementById('scroll-top');

window.addEventListener('scroll', () => {
    if (window.pageYOffset > 300) {
        scrollTopBtn.classList.add('visible');
    } else {
        scrollTopBtn.classList.remove('visible');
    }
});

scrollTopBtn.addEventListener('click', () => {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

// Hero Section Particles
function createParticles() {
    const particles = document.querySelector('.hero-particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 5 + 2}px;
            height: ${Math.random() * 5 + 2}px;
            background: var(--primary-color);
            opacity: ${Math.random() * 0.5};
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation: float ${Math.random() * 10 + 5}s linear infinite;
        `;
        particles.appendChild(particle);
    }
}

// Initialize particles
createParticles();

// Language progress bar animation
const languageCards = document.querySelectorAll('.language-card');
const languageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
        }
    });
}, { threshold: 0.5 });

languageCards.forEach(card => {
    languageObserver.observe(card);
});

// Skills Animation
const skillBars = document.querySelectorAll('.skill-progress');
const skillCategories = document.querySelectorAll('.skill-category');

const observeSkills = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const progress = entry.target;
            const percentage = progress.getAttribute('data-progress');
            progress.style.width = percentage + '%';
        }
    });
}, {
    threshold: 0.5
});

skillBars.forEach(bar => {
    observeSkills.observe(bar);
});

// Achievement Counter Animation
const achievementNumbers = document.querySelectorAll('.achievement-number');

const animateCounter = (element, target) => {
    let current = 0;
    const increment = target / 100;
    const duration = 2000; // 2 seconds
    const stepTime = duration / (target / increment);

    const counter = setInterval(() => {
        current += increment;
        element.textContent = Math.round(current);

        if (current >= target) {
            element.textContent = target;
            clearInterval(counter);
        }
    }, stepTime);
};

const observeAchievements = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const target = parseInt(entry.target.getAttribute('data-target'));
            animateCounter(entry.target, target);
            observeAchievements.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.5
});

achievementNumbers.forEach(number => {
    observeAchievements.observe(number);
});

// Skill Tags Animation
const skillTags = document.querySelectorAll('.skill-tag');

skillTags.forEach(tag => {
    tag.addEventListener('click', () => {
        tag.classList.add('active');
        setTimeout(() => tag.classList.remove('active'), 500);
    });
});

// Fade In Animation
const fadeElements = document.querySelectorAll('.fade-in');
const scaleElements = document.querySelectorAll('.scale-in');

const observeFade = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, {
    threshold: 0.1
});

fadeElements.forEach(element => {
    observeFade.observe(element);
});

scaleElements.forEach(element => {
    observeFade.observe(element);
});

// Theme Toggle
const themeToggle = document.querySelector('.theme-toggle');
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

// Function to toggle theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update icon
    const icon = themeToggle.querySelector('i');
    icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// Initialize theme
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 
        (prefersDarkScheme.matches ? 'dark' : 'light');
    
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = themeToggle.querySelector('i');
    icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// Event listeners
themeToggle.addEventListener('click', toggleTheme);
prefersDarkScheme.addListener((e) => {
    const savedTheme = localStorage.getItem('theme');
    if (!savedTheme) {
        document.documentElement.setAttribute(
            'data-theme',
            e.matches ? 'dark' : 'light'
        );
    }
});

// Initialize theme on load
initializeTheme();

// Section Animations
const sections = document.querySelectorAll('section');
const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, {
    threshold: 0.2
});

sections.forEach(section => {
    sectionObserver.observe(section);
});

// Enhanced Form Interaction
const form = document.querySelector('.contact-form');
const formInputs = form.querySelectorAll('input, textarea');

formInputs.forEach(input => {
    // Add loading state
    input.addEventListener('focus', () => {
        input.classList.add('loading');
    });

    input.addEventListener('blur', () => {
        input.classList.remove('loading');
    });

    // Validate input
    input.addEventListener('input', () => {
        if (input.value.trim() !== '') {
            input.classList.add('valid');
        } else {
            input.classList.remove('valid');
        }
    });
});

// Smooth anchor scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const headerOffset = 100;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });

            // Update URL without scrolling
            history.pushState(null, null, this.getAttribute('href'));
        }
    });
});

// Project card interaction
const projectCards = document.querySelectorAll('.project-card');

projectCards.forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-10px) scale(1.02)';
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0) scale(1)';
    });
});

// Touch Device Detection
const isTouchDevice = () => {
    return (('ontouchstart' in window) ||
        (navigator.maxTouchPoints > 0) ||
        (navigator.msMaxTouchPoints > 0));
};

if (isTouchDevice()) {
    document.body.classList.add('touch-device');
}

// Responsive Image Loading
const lazyImages = document.querySelectorAll('img[data-src]');

const loadImage = (image) => {
    image.src = image.dataset.src;
    image.removeAttribute('data-src');
};

const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadImage(entry.target);
            observer.unobserve(entry.target);
        }
    });
}, {
    rootMargin: '50px'
});

lazyImages.forEach(img => imageObserver.observe(img));

// Enhanced Scroll Handling
let lastScrollTop = 0;
const header = document.querySelector('header');

window.addEventListener('scroll', () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    // Header show/hide
    if (scrollTop > lastScrollTop && scrollTop > 100) {
        header.style.transform = 'translateY(-100%)';
    } else {
        header.style.transform = 'translateY(0)';
    }
    
    lastScrollTop = scrollTop;
    
    // Parallax effect for hero section
    const hero = document.querySelector('.hero');
    if (hero) {
        const speed = 0.5;
        hero.style.backgroundPositionY = scrollTop * speed + 'px';
    }
});

// Typing Animation
const typingTexts = document.querySelectorAll('.typing-text');
let typingIndex = 0;

function typeText(element, text, i = 0) {
    if (i < text.length) {
        element.textContent += text.charAt(i);
        setTimeout(() => typeText(element, text, i + 1), 100);
    } else {
        typingIndex++;
        if (typingIndex < typingTexts.length) {
            setTimeout(() => {
                typingTexts[typingIndex].textContent = '';
                typeText(typingTexts[typingIndex], typingTexts[typingIndex].getAttribute('data-text'));
            }, 1000);
        }
    }
}

typingTexts.forEach(text => {
    text.setAttribute('data-text', text.textContent);
    text.textContent = '';
});

if (typingTexts.length > 0) {
    typeText(typingTexts[0], typingTexts[0].getAttribute('data-text'));
}

// Project Filtering
const filterBtns = document.querySelectorAll('.filter-btn');
const projectsGrid = document.querySelector('.projects-grid');
const projectCards = document.querySelectorAll('.project-card');

filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Update active button
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const filter = btn.getAttribute('data-filter');
        
        // Add filtering class for transition
        projectsGrid.classList.add('filtering');

        setTimeout(() => {
            projectCards.forEach(card => {
                const categories = card.getAttribute('data-categories').split(',');
                if (filter === 'all' || categories.includes(filter)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });

            // Remove filtering class
            projectsGrid.classList.remove('filtering');
        }, 300);
    });
});

// Scroll Progress Indicator
const scrollProgress = document.querySelector('.scroll-progress');

window.addEventListener('scroll', () => {
    const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (window.scrollY / windowHeight);
    scrollProgress.style.transform = `scaleX(${scrolled})`;
});

// Floating Contact Button
const floatingContact = document.querySelector('.floating-contact');

floatingContact.addEventListener('click', () => {
    const contactSection = document.querySelector('#contact');
    contactSection.scrollIntoView({ behavior: 'smooth' });
});

// Enhanced Project Card Interaction
projectCards.forEach(card => {
    const overlay = card.querySelector('.project-overlay');
    
    card.addEventListener('mouseenter', () => {
        overlay.style.opacity = '1';
    });
    
    card.addEventListener('mouseleave', () => {
        overlay.style.opacity = '0';
    });
    
    // Touch device handling
    card.addEventListener('touchstart', () => {
        overlay.style.opacity = '1';
    });
    
    card.addEventListener('touchend', () => {
        setTimeout(() => {
            overlay.style.opacity = '0';
        }, 1000);
    });
});

// Smooth Scroll for all anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const headerOffset = 80;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// Timeline Animation
const timelineItems = document.querySelectorAll('.timeline-item');

const observeTimeline = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.querySelector('.timeline-content').classList.add('visible');
        }
    });
}, {
    threshold: 0.5
});

timelineItems.forEach(item => {
    observeTimeline.observe(item);
});

// Publication Cards Animation
const publicationCards = document.querySelectorAll('.publication-card');

const observePublications = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, {
    threshold: 0.2
});

publicationCards.forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'all 0.6s ease';
    observePublications.observe(card);
});

// Publication Tags Filter
const publicationTags = document.querySelectorAll('.publication-tag');
const publicationFilters = document.querySelector('.publication-filters');

if (publicationFilters) {
    const tags = new Set();
    publicationTags.forEach(tag => tags.add(tag.textContent));

    const filterButtons = Array.from(tags).map(tag => {
        const button = document.createElement('button');
        button.classList.add('filter-btn');
        button.textContent = tag;
        button.addEventListener('click', () => filterPublications(tag));
        return button;
    });

    const allButton = document.createElement('button');
    allButton.classList.add('filter-btn', 'active');
    allButton.textContent = 'All';
    allButton.addEventListener('click', () => filterPublications('all'));

    publicationFilters.appendChild(allButton);
    filterButtons.forEach(button => publicationFilters.appendChild(button));
}

function filterPublications(tag) {
    const buttons = document.querySelectorAll('.publication-filters .filter-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    publicationCards.forEach(card => {
        const cardTags = Array.from(card.querySelectorAll('.publication-tag'))
            .map(tag => tag.textContent);
        
        if (tag === 'all' || cardTags.includes(tag)) {
            card.style.display = 'flex';
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 10);
        } else {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.display = 'none';
            }, 300);
        }
    });
}
