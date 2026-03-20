// SCOPE System Documentation JavaScript

// Global variables
let searchResults = [];
let currentSearchTerm = '';
let isSearchVisible = false;
let tocItems = [];
let activeSection = '';

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap 5 components
    if (typeof bootstrap !== 'undefined') {
        // Initialize all dropdowns
        const dropdowns = document.querySelectorAll('.dropdown-toggle');
        dropdowns.forEach(function(dropdown) {
            new bootstrap.Dropdown(dropdown);
        });
    }
    
    initializeDocumentation();
});

/**
 * Initialize all documentation features
 */
function initializeDocumentation() {
    initializeNavigation();
    initializeSearch();
    initializeTableOfContents();
    initializeSmoothScrolling();
    initializeCodeHighlighting();
    initializeProgressIndicator();
    initializeKeyboardShortcuts();
    initializePrintOptimization();
    initializeAccessibility();
    initializeAnalytics();
    
    // Set dark mode by default
    document.body.classList.add('dark-mode');
    
    // Handle initial hash after a short delay
    setTimeout(handleInitialHash, 200);
    
    console.log('SCOPE Documentation initialized successfully');
}

/**
 * Navigation functionality
 */
function initializeNavigation() {
    // Active navigation highlighting
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    const sections = document.querySelectorAll('.content-section');
    
    // Intersection Observer for section tracking
    const observerOptions = {
        root: null,
        rootMargin: '-100px 0px -70% 0px',
        threshold: 0
    };
    
    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const sectionId = entry.target.id;
                updateActiveNavigation(sectionId);
                updateProgressBar(sectionId);
            }
        });
    }, observerOptions);
    
    // Observe all sections
    sections.forEach(section => {
        sectionObserver.observe(section);
    });
    
    // Handle navigation clicks
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                e.preventDefault();
                scrollToSection(targetSection);
                updateActiveNavigation(targetId);
                
                // Update URL hash without jumping
                history.pushState(null, null, `#${targetId}`);
            }
        });
    });
    
    // Handle initial hash
    if (window.location.hash) {
        const initialSection = document.getElementById(window.location.hash.substring(1));
        if (initialSection) {
            setTimeout(() => {
                scrollToSection(initialSection);
            }, 100);
        }
    }
}

/**
 * Update active navigation item
 */
function updateActiveNavigation(sectionId) {
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${sectionId}`) {
            link.classList.add('active');
        }
    });
    
    activeSection = sectionId;
}

/**
 * Smooth scroll to section
 */
function scrollToSection(section) {
    // Get current scroll position
    const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
    
    // Get navbar height
    const navbar = document.querySelector('.navbar');
    const navbarHeight = navbar ? navbar.offsetHeight : 0;
    const scrollMargin = 10; // Reduced margin for better accuracy
    
    // Calculate target position
    let targetPosition = 0;
    
    if (section && typeof section === 'object') {
        // Section is an element object
        const rect = section.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        targetPosition = rect.top + scrollTop - navbarHeight - scrollMargin;
    } else if (typeof section === 'string') {
        // Section is an ID string
        const targetElement = document.getElementById(section);
        if (targetElement) {
            const rect = targetElement.getBoundingClientRect();
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            targetPosition = rect.top + scrollTop - navbarHeight - scrollMargin;
        }
    } else {
        // Fallback to top
        targetPosition = 0;
    }
    
    // Only scroll if target is different from current position
    if (Math.abs(targetPosition - currentScroll) > 5) { // Reduced threshold
        // Smooth scroll with fallback
        try {
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
        } catch (error) {
            // Fallback for browsers that don't support smooth scrolling
            window.scrollTo(0, targetPosition);
        }
    }
    
    // Update URL hash
    const sectionId = section.id || (typeof section === 'string' ? section : section.getAttribute('id'));
    if (sectionId) {
        history.pushState(null, null, `#${sectionId}`);
    }
}

/**
 * Search functionality
 */
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = searchInput.nextElementSibling;
    
    if (!searchInput) return;
    
    // Create search results container
    const searchResultsContainer = document.createElement('div');
    searchResultsContainer.className = 'search-results';
    searchResultsContainer.style.display = 'none';
    searchInput.parentNode.appendChild(searchResultsContainer);
    
    // Search input event listeners
    searchInput.addEventListener('input', debounce(handleSearch, 300));
    searchInput.addEventListener('focus', () => showSearchResults());
    searchInput.addEventListener('keydown', handleSearchKeydown);
    
    // Search button click
    searchButton.addEventListener('click', () => {
        performSearch(searchInput.value);
    });
    
    // Click outside to close
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResultsContainer.contains(e.target)) {
            hideSearchResults();
        }
    });
    
    // Build search index
    buildSearchIndex();
}

/**
 * Build search index from content
 */
function buildSearchIndex() {
    const sections = document.querySelectorAll('.content-section');
    
    sections.forEach(section => {
        const title = section.querySelector('h2, h3');
        const content = section.textContent || section.innerText;
        
        if (title) {
            searchResults.push({
                id: section.id,
                title: title.textContent.trim(),
                content: content.substring(0, 500), // First 500 chars
                section: section,
                keywords: extractKeywords(content)
            });
        }
    });
}

/**
 * Extract keywords from content
 */
function extractKeywords(content) {
    const words = content.toLowerCase()
        .replace(/[^\w\s]/g, '')
        .split(/\s+/)
        .filter(word => word.length > 3)
        .filter((word, index, array) => array.indexOf(word) === index);
    
    return words.slice(0, 20); // Top 20 keywords
}

/**
 * Handle search input
 */
function handleSearch(e) {
    const searchTerm = e.target.value.trim();
    
    if (searchTerm.length < 2) {
        hideSearchResults();
        return;
    }
    
    performSearch(searchTerm);
}

/**
 * Perform search
 */
function performSearch(searchTerm) {
    currentSearchTerm = searchTerm.toLowerCase();
    const results = searchResults.filter(item => {
        return item.title.toLowerCase().includes(currentSearchTerm) ||
               item.content.toLowerCase().includes(currentSearchTerm) ||
               item.keywords.some(keyword => keyword.includes(currentSearchTerm));
    });
    
    displaySearchResults(results);
}

/**
 * Display search results
 */
function displaySearchResults(results) {
    const container = document.querySelector('.search-results');
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="search-result-item">
                <div class="search-result-title">No results found</div>
                <div class="search-result-excerpt">Try searching for different keywords</div>
            </div>
        `;
    } else {
        container.innerHTML = results.map(result => `
            <div class="search-result-item" onclick="navigateToSection('${result.id}')">
                <div class="search-result-title">${highlightSearchTerm(result.title)}</div>
                <div class="search-result-excerpt">${highlightSearchTerm(result.content.substring(0, 200))}...</div>
            </div>
        `).join('');
    }
    
    showSearchResults();
}

/**
 * Highlight search term in text
 */
function highlightSearchTerm(text) {
    if (!currentSearchTerm) return text;
    
    const regex = new RegExp(`(${currentSearchTerm})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

/**
 * Navigate to section from search
 */
function navigateToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        hideSearchResults();
        scrollToSection(section); // Pass the element directly
        document.getElementById('searchInput').value = '';
    }
}

/**
 * Show/hide search results
 */
function showSearchResults() {
    const container = document.querySelector('.search-results');
    if (container) {
        container.style.display = 'block';
        isSearchVisible = true;
    }
}

function hideSearchResults() {
    const container = document.querySelector('.search-results');
    if (container) {
        container.style.display = 'none';
        isSearchVisible = false;
    }
}

/**
 * Handle search keyboard navigation
 */
function handleSearchKeydown(e) {
    if (!isSearchVisible) return;
    
    const items = document.querySelectorAll('.search-result-item');
    let currentIndex = -1;
    
    // Find current selected item
    items.forEach((item, index) => {
        if (item.classList.contains('selected')) {
            currentIndex = index;
        }
    });
    
    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            currentIndex = Math.min(currentIndex + 1, items.length - 1);
            updateSearchSelection(items, currentIndex);
            break;
            
        case 'ArrowUp':
            e.preventDefault();
            currentIndex = Math.max(currentIndex - 1, 0);
            updateSearchSelection(items, currentIndex);
            break;
            
        case 'Enter':
            e.preventDefault();
            if (currentIndex >= 0 && items[currentIndex]) {
                items[currentIndex].click();
            }
            break;
            
        case 'Escape':
            hideSearchResults();
            break;
    }
}

/**
 * Update search selection
 */
function updateSearchSelection(items, selectedIndex) {
    items.forEach((item, index) => {
        item.classList.toggle('selected', index === selectedIndex);
        if (index === selectedIndex) {
            item.scrollIntoView({ block: 'nearest' });
        }
    });
}

/**
 * Table of Contents
 */
function initializeTableOfContents() {
    const sections = document.querySelectorAll('.content-section h2, .content-section h3');
    const tocContainer = document.createElement('div');
    tocContainer.className = 'toc';
    tocContainer.innerHTML = '<h3>Table of Contents</h3><ul></ul>';
    
    // Insert after hero section
    const heroSection = document.querySelector('.hero-section');
    if (heroSection && heroSection.nextElementSibling) {
        heroSection.parentNode.insertBefore(tocContainer, heroSection.nextElementSibling);
    }
    
    const tocList = tocContainer.querySelector('ul');
    
    sections.forEach((section, index) => {
        const level = section.tagName.toLowerCase() === 'h3' ? 2 : 1;
        const sectionId = section.textContent.toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-');
        
        // Add ID if not present
        if (!section.id) {
            section.id = sectionId;
        }
        
        const li = document.createElement('li');
        li.className = `toc-level-${level}`;
        
        const link = document.createElement('a');
        link.href = `#${section.id}`;
        link.textContent = section.textContent.trim();
        link.addEventListener('click', (e) => {
            e.preventDefault();
            scrollToSection(section); // Pass to element directly
            updateActiveTOC(section.id);
        });
        
        li.appendChild(link);
        tocList.appendChild(li);
        
        tocItems.push({
            element: section,
            link: link,
            level: level,
            id: section.id
        });
    });
    
    // Initialize TOC intersection observer
    initializeTOCObserver();
}

/**
 * Initialize TOC intersection observer
 */
function initializeTOCObserver() {
    const observerOptions = {
        root: null,
        rootMargin: '-100px 0px -70% 0px',
        threshold: 0
    };
    
    const tocObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                updateActiveTOC(entry.target.id);
            }
        });
    }, observerOptions);
    
    tocItems.forEach(item => {
        tocObserver.observe(item.element);
    });
}

/**
 * Update active TOC item
 */
function updateActiveTOC(sectionId) {
    tocItems.forEach(item => {
        item.link.classList.toggle('active', item.id === sectionId);
    });
}

/**
 * Smooth scrolling
 */
function initializeSmoothScrolling() {
    // Enable smooth scrolling for all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = anchor.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                scrollToSection(targetElement);
                updateActiveNavigation(targetId);
            }
        });
    });
    
    // Handle hash changes on page load
    handleInitialHash();
}

/**
 * Handle initial hash on page load
 */
function handleInitialHash() {
    const hash = window.location.hash;
    if (hash) {
        const targetId = hash.substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            // Wait for page to fully render before scrolling
            setTimeout(() => {
                scrollToSection(targetElement);
                updateActiveNavigation(targetId);
            }, 300);
        }
    }
}

/**
 * Code highlighting
 */
function initializeCodeHighlighting() {
    // Add copy buttons to code blocks
    document.querySelectorAll('.code-block pre').forEach(block => {
        const button = document.createElement('button');
        button.className = 'btn btn-sm btn-outline-primary copy-btn';
        button.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
        button.style.position = 'absolute';
        button.style.top = '0.5rem';
        button.style.right = '0.5rem';
        
        block.style.position = 'relative';
        block.appendChild(button);
        
        button.addEventListener('click', () => {
            const text = block.textContent || block.innerText;
            navigator.clipboard.writeText(text).then(() => {
                button.innerHTML = '<i class="bi bi-check"></i> Copied!';
                setTimeout(() => {
                    button.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
                }, 2000);
            });
        });
    });
}

/**
 * Progress indicator
 */
function initializeProgressIndicator() {
    const progressBar = document.createElement('div');
    progressBar.className = 'reading-progress';
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--accent-color) 100%);
        z-index: 9999;
        transition: width 0.3s ease;
    `;
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', () => {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight - windowHeight;
        const scrolled = window.pageYOffset;
        const progress = (scrolled / documentHeight) * 100;
        
        progressBar.style.width = `${Math.min(progress, 100)}%`;
    });
}

/**
 * Update progress bar based on section
 */
function updateProgressBar(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    const sections = Array.from(document.querySelectorAll('.content-section'));
    const currentIndex = sections.indexOf(section);
    const totalSections = sections.length;
    const progress = ((currentIndex + 1) / totalSections) * 100;
    
    const progressBar = document.querySelector('.reading-progress');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
}

/**
 * Keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only handle shortcuts when not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        switch (e.key) {
            case '/':
                e.preventDefault();
                document.getElementById('searchInput').focus();
                break;
                
            case 'Escape':
                hideSearchResults();
                document.getElementById('searchInput').blur();
                break;
                
            case 'ArrowUp':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    navigateToPreviousSection();
                }
                break;
                
            case 'ArrowDown':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    navigateToNextSection();
                }
                break;
        }
    });
}

/**
 * Navigate to previous section
 */
function navigateToPreviousSection() {
    const sections = Array.from(document.querySelectorAll('.content-section'));
    const currentIndex = sections.findIndex(section => section.id === activeSection);
    
    if (currentIndex > 0) {
        const previousSection = sections[currentIndex - 1];
        scrollToSection(previousSection);
    }
}

/**
 * Navigate to next section
 */
function navigateToNextSection() {
    const sections = Array.from(document.querySelectorAll('.content-section'));
    const currentIndex = sections.findIndex(section => section.id === activeSection);
    
    if (currentIndex < sections.length - 1) {
        const nextSection = sections[currentIndex + 1];
        scrollToSection(nextSection);
    }
}

/**
 * Print optimization
 */
function initializePrintOptimization() {
    window.addEventListener('beforeprint', () => {
        // Expand all collapsed content for printing
        document.querySelectorAll('.accordion-collapse:not(.show)').forEach(collapse => {
            collapse.classList.add('show');
        });
        
        // Hide navigation and other non-essential elements
        document.querySelector('.sidebar').style.display = 'none';
        document.querySelector('.navbar').style.display = 'none';
    });
    
    window.addEventListener('afterprint', () => {
        // Restore collapsed state
        document.querySelectorAll('.accordion-collapse.show').forEach(collapse => {
            collapse.classList.remove('show');
        });
        
        // Show navigation again
        document.querySelector('.sidebar').style.display = '';
        document.querySelector('.navbar').style.display = '';
    });
}

/**
 * Accessibility improvements
 */
function initializeAccessibility() {
    // Add ARIA labels to dynamic elements
    document.querySelectorAll('.code-block').forEach((block, index) => {
        block.setAttribute('role', 'region');
        block.setAttribute('aria-label', `Code block ${index + 1}`);
    });
    
    // Focus management for search
    const searchInput = document.getElementById('searchInput');
    searchInput.setAttribute('aria-label', 'Search documentation');
    
    // Skip to main content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'skip-link';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 6px;
        background: var(--primary-color);
        color: white;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        z-index: 10000;
    `;
    
    skipLink.addEventListener('focus', () => {
        skipLink.style.top = '6px';
    });
    
    skipLink.addEventListener('blur', () => {
        skipLink.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Add main content id to main content area
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.id = 'main-content';
    }
}

/**
 * Analytics tracking
 */
function initializeAnalytics() {
    // Track section views
    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                trackSectionView(entry.target.id);
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('.content-section').forEach(section => {
        sectionObserver.observe(section);
    });
    
    // Track search usage
    let searchTimeout;
    document.getElementById('searchInput')?.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            trackSearchUsage();
        }, 1000);
    });
}

/**
 * Track section view (placeholder for analytics)
 */
function trackSectionView(sectionId) {
    // This would integrate with your analytics service
    console.log('Section viewed:', sectionId);
    
    // Example: gtag('config', 'GA_MEASUREMENT_ID', {
    //     page_path: `#${sectionId}`
    // });
}

/**
 * Track search usage (placeholder for analytics)
 */
function trackSearchUsage() {
    const searchTerm = document.getElementById('searchInput').value;
    if (searchTerm.length > 2) {
        console.log('Search performed:', searchTerm);
        
        // Example: gtag('event', 'search', {
        //     search_term: searchTerm
        // });
    }
}

/**
 * Utility functions
 */

/**
 * Debounce function
 */
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

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Get element offset
 */
function getElementOffset(element) {
    const rect = element.getBoundingClientRect();
    return {
        top: rect.top + window.pageYOffset,
        left: rect.left + window.pageXOffset
    };
}

/**
 * Check if element is in viewport
 */
function isElementInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Format bytes
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Get time ago string
 */
function timeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + ' years ago';
    
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + ' months ago';
    
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + ' days ago';
    
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + ' hours ago';
    
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + ' minutes ago';
    
    return 'Just now';
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="bi bi-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="bi bi-x"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, duration);
}

/**
 * Get notification icon
 */
function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'x-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Export functions for global use
 */
window.ScopeDocs = {
    navigateToSection,
    showNotification,
    hideSearchResults,
    performSearch,
    updateActiveNavigation,
    scrollToSection,
    debounce,
    throttle,
    formatBytes,
    timeAgo,
    printDocumentation,
    showQuickGuide,
    closeQuickGuide,
    toggleFabMenu,
    scrollToTop,
    toggleFullscreen,
    downloadPDF,
    shareDocumentation,
    openWebApp,
    openGitHub
};

/**
 * Open GitHub Repository
 */
function openGitHub() {
    window.open('https://github.com/SarveshwarSenthilKumar/Engineering-Idol', '_blank');
    showNotification('Opening GitHub repository...', 'info', 2000);
}

/**
 * Print Documentation
 */
function printDocumentation() {
    // Show print dialog
    window.print();
    showNotification('Print dialog opened', 'info', 2000);
}

/**
 * Show Quick Guide
 */
function showQuickGuide() {
    // Create modal if it doesn't exist
    let modal = document.querySelector('.quick-guide-modal');
    
    if (!modal) {
        modal = createQuickGuideModal();
        document.body.appendChild(modal);
    }
    
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

/**
 * Create Quick Guide Modal
 */
function createQuickGuideModal() {
    const modal = document.createElement('div');
    modal.className = 'quick-guide-modal';
    modal.innerHTML = `
        <div class="quick-guide-content">
            <div class="quick-guide-header">
                <h3 class="quick-guide-title">Quick Guide</h3>
                <button class="close-btn" onclick="closeQuickGuide()">
                    <i class="bi bi-x"></i>
                </button>
            </div>
            
            <div class="guide-section">
                <h4>🔍 Navigation</h4>
                <ul>
                    <li>Use the sidebar menu to jump between sections</li>
                    <li>Click on any section title for smooth scrolling</li>
                    <li>Use <code>/</code> to quickly focus search</li>
                    <li>Use <code>↑</code> and <code>↓</code> arrows to navigate sections</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>🔎 Search</h4>
                <ul>
                    <li>Type in the search box to find content</li>
                    <li>Use arrow keys to navigate search results</li>
                    <li>Press <code>Enter</code> to jump to a result</li>
                    <li>Press <code>Escape</code> to close search</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>🎨 Interface Features</h4>
                <ul>
                    <li>Click the moon icon to toggle dark mode</li>
                    <li>Click the printer icon to print documentation</li>
                    <li>Use the floating action button for quick actions</li>
                    <li>Click the back-to-top arrow to scroll up</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>⌨️ Keyboard Shortcuts</h4>
                <ul>
                    <li><code>/</code> - Focus search</li>
                    <li><code>Escape</code> - Close search/modals</li>
                    <li><code>Ctrl + ↑</code> - Previous section</li>
                    <li><code>Ctrl + ↓</code> - Next section</li>
                    <li><code>F11</code> - Toggle fullscreen</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>📱 Mobile</h4>
                <ul>
                    <li>Swipe to navigate between sections</li>
                    <li>Tap menu icon to show/hide sidebar</li>
                    <li>Pinch to zoom for better readability</li>
                    <li>Use touch-friendly buttons and controls</li>
                </ul>
            </div>
        </div>
    `;
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeQuickGuide();
        }
    });
    
    return modal;
}

/**
 * Close Quick Guide
 */
function closeQuickGuide() {
    const modal = document.querySelector('.quick-guide-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
}

/**
 * Toggle FAB Menu
 */
function toggleFabMenu() {
    const fabMain = document.querySelector('.fab-main');
    const fabOptions = document.querySelector('.fab-options');
    
    fabMain.classList.toggle('active');
    fabOptions.classList.toggle('show');
}

/**
 * Scroll to Top
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
    showNotification('Scrolled to top', 'info', 1000);
}

/**
 * Toggle Fullscreen
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
            showNotification('Fullscreen mode enabled', 'info', 2000);
        }).catch(err => {
            showNotification('Error enabling fullscreen', 'error', 3000);
        });
    } else {
        document.exitFullscreen().then(() => {
            showNotification('Fullscreen mode disabled', 'info', 2000);
        }).catch(err => {
            showNotification('Error exiting fullscreen', 'error', 3000);
        });
    }
    
    // Close FAB menu
    const fabOptions = document.querySelector('.fab-options');
    const fabMain = document.querySelector('.fab-main');
    fabOptions.classList.remove('show');
    fabMain.classList.remove('active');
}

/**
 * Download PDF (placeholder)
 */
function downloadPDF() {
    // In a real implementation, this would generate a PDF
    // For now, we'll trigger the print dialog which can save as PDF
    showNotification('Preparing PDF download...', 'info', 2000);
    
    setTimeout(() => {
        printDocumentation();
        showNotification('Use browser print dialog to save as PDF', 'info', 3000);
    }, 1000);
    
    // Close FAB menu
    const fabOptions = document.querySelector('.fab-options');
    const fabMain = document.querySelector('.fab-main');
    fabOptions.classList.remove('show');
    fabMain.classList.remove('active');
}

/**
 * Open SCOPE Web App
 */
function openWebApp() {
    const webAppUrl = 'http://localhost:5000';
    
    // Check if the web app is running
    fetch(webAppUrl, { method: 'HEAD', mode: 'no-cors' })
        .then(() => {
            // Open in new tab
            window.open(webAppUrl, '_blank');
            showNotification('Opening SCOPE Web App...', 'success', 2000);
        })
        .catch(() => {
            // If fetch fails, still try to open (might be CORS issue)
            window.open(webAppUrl, '_blank');
            showNotification('Opening SCOPE Web App...', 'info', 2000);
        });
    
    // Close FAB menu if called from there
    const fabOptions = document.querySelector('.fab-options');
    const fabMain = document.querySelector('.fab-main');
    if (fabOptions && fabMain) {
        fabOptions.classList.remove('show');
        fabMain.classList.remove('active');
    }
}

/**
 * Share Documentation
 */
function shareDocumentation() {
    const url = window.location.href;
    const title = 'SCOPE System Documentation';
    
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url
        }).then(() => {
            showNotification('Documentation shared successfully', 'success', 2000);
        }).catch(err => {
            showNotification('Error sharing documentation', 'error', 3000);
        });
    } else {
        // Fallback: Copy to clipboard
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Link copied to clipboard', 'success', 2000);
        }).catch(err => {
            showNotification('Error copying link', 'error', 3000);
        });
    }
    
    // Close FAB menu
    const fabOptions = document.querySelector('.fab-options');
    const fabMain = document.querySelector('.fab-main');
    fabOptions.classList.remove('show');
    fabMain.classList.remove('active');
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('Documentation error:', e.error);
    showNotification('An error occurred. Please refresh the page.', 'error');
});

// Performance monitoring
window.addEventListener('load', () => {
    const loadTime = performance.now();
    console.log(`Documentation loaded in ${loadTime.toFixed(2)}ms`);
    
    // Track performance if analytics is available
    if (typeof gtag !== 'undefined') {
        gtag('event', 'page_load_time', {
            value: Math.round(loadTime)
        });
    }
});

// Service Worker registration for offline support (if available)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// ==================== SCORING PLAYGROUND ====================

/**
 * Initialize scoring playground functionality
 */
function initializeScoringPlayground() {
    // Check if scoring elements exist on the page
    if (document.getElementById('peopleCount')) {
        updateScoringDisplay();
        console.log('Scoring playground initialized');
    }
}

/**
 * Update scoring display based on current slider values
 */
function updateScoringDisplay() {
    const peopleCount = parseInt(document.getElementById('peopleCount').value);
    const noiseLevel = parseInt(document.getElementById('noiseLevel').value);
    const aqiLevel = parseInt(document.getElementById('aqiLevel').value);
    const vocLevel = parseInt(document.getElementById('vocLevel').value);
    const pm25Level = parseInt(document.getElementById('pm25Level').value);
    const timeOfDay = document.getElementById('timeOfDay').value;
    const environmentType = document.getElementById('environmentType').value;
    
    // Update display values
    document.getElementById('peopleValue').textContent = peopleCount;
    document.getElementById('noiseValue').textContent = noiseLevel;
    document.getElementById('aqiValue').textContent = aqiLevel;
    document.getElementById('vocValue').textContent = vocLevel;
    document.getElementById('pm25Value').textContent = pm25Level;
    
    // Calculate individual scores
    const peopleScore = Math.min(peopleCount * 2, 100);
    const noiseScore = Math.min((noiseLevel / 120) * 100, 100);
    const aqiScore = Math.min((aqiLevel / 500) * 100, 100);
    const vocScore = Math.min((vocLevel / 1000) * 100, 100);
    const pm25Score = Math.min((pm25Level / 500) * 100, 100);
    
    // Calculate weighted total
    let totalScore = (peopleScore * 0.3) + (noiseScore * 0.2) + (aqiScore * 0.2) + 
                   (vocScore * 0.15) + (pm25Score * 0.15);
    
    // Apply time and environment modifiers
    if (timeOfDay === 'night') totalScore *= 1.2;
    if (timeOfDay === 'evening') totalScore *= 1.1;
    if (environmentType === 'classroom') totalScore *= 0.8;
    if (environmentType === 'library') totalScore *= 0.7;
    if (environmentType === 'cafeteria') totalScore *= 1.2;
    if (environmentType === 'outdoor') totalScore *= 1.1;
    
    totalScore = Math.min(Math.round(totalScore), 100);
    
    // Update display
    document.getElementById('threatScore').textContent = totalScore;
    document.getElementById('peopleScore').textContent = Math.round(peopleScore);
    document.getElementById('noiseScore').textContent = Math.round(noiseScore);
    document.getElementById('aqiScore').textContent = Math.round(aqiScore);
    document.getElementById('vocScore').textContent = Math.round(vocScore);
    document.getElementById('pm25Score').textContent = Math.round(pm25Score);
    
    // Update threat level badge and recommendation
    const threatBadge = document.getElementById('threatBadge');
    const recommendationBox = document.getElementById('recommendationBox');
    const recommendationText = document.getElementById('recommendationText');
    
    let status, badgeClass, alertClass, recommendation;
    
    if (totalScore < 25) {
        status = 'LOW';
        badgeClass = 'bg-success';
        alertClass = 'alert-success';
        recommendation = 'Normal monitoring - conditions are within acceptable parameters';
    } else if (totalScore < 50) {
        status = 'MODERATE';
        badgeClass = 'bg-warning';
        alertClass = 'alert-warning';
        recommendation = 'Increased attention required - monitor for changes';
    } else if (totalScore < 75) {
        status = 'HIGH';
        badgeClass = 'bg-danger';
        alertClass = 'alert-danger';
        recommendation = 'Immediate investigation needed - potential threat detected';
    } else {
        status = 'CRITICAL';
        badgeClass = 'bg-dark';
        alertClass = 'alert-dark';
        recommendation = 'Emergency response required - critical threat level';
    }
    
    threatBadge.className = `badge ${badgeClass}`;
    threatBadge.textContent = status;
    
    recommendationBox.className = `alert ${alertClass}`;
    recommendationText.textContent = recommendation;
    
    // Add animation effect
    const scoreElement = document.getElementById('threatScore');
    scoreElement.style.transform = 'scale(1.1)';
    setTimeout(() => {
        scoreElement.style.transform = 'scale(1)';
    }, 200);
}

/**
 * Reset scoring values to defaults
 */
function resetScoringValues() {
    document.getElementById('peopleCount').value = 5;
    document.getElementById('noiseLevel').value = 40;
    document.getElementById('aqiLevel').value = 50;
    document.getElementById('vocLevel').value = 100;
    document.getElementById('pm25Level').value = 25;
    document.getElementById('timeOfDay').value = 'morning';
    document.getElementById('environmentType').value = 'classroom';
    
    updateScoringDisplay();
    
    // Visual feedback
    const resetButton = event.target;
    resetButton.innerHTML = '<i class="bi bi-check-circle me-2"></i>Reset Complete!';
    setTimeout(() => {
        resetButton.innerHTML = '<i class="bi bi-arrow-clockwise me-2"></i>Reset Values';
    }, 1500);
}

// Initialize scoring playground when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add scoring playground initialization to the existing initializeDocumentation function
    if (typeof initializeDocumentation === 'function') {
        const originalInit = initializeDocumentation;
        initializeDocumentation = function() {
            originalInit();
            initializeScoringPlayground();
        };
    } else {
        initializeScoringPlayground();
    }
});

// Make functions globally accessible
window.updateScoringDisplay = updateScoringDisplay;
window.resetScoringValues = resetScoringValues;
