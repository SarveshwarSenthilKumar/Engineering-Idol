// SCOPE System Documentation JavaScript

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDocumentation();
});

function initializeDocumentation() {
    // Initialize navigation
    initializeNavigation();
    
    // Initialize search
    initializeSearch();
    
    // Initialize scoring playground
    initializeScoringPlayground();
    
    // Initialize floating action button
    initializeFAB();
    
    // Initialize smooth scrolling
    initializeSmoothScroll();
    
    // Initialize theme toggle
    initializeThemeToggle();
    
    // Show quick guide on first visit
    showQuickGuideOnFirstVisit();
}

// Navigation functionality
function initializeNavigation() {
    // Add smooth scrolling to navigation links
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active state
                navLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
    
    // Highlight current section in sidebar
    highlightCurrentSection();
}

function highlightCurrentSection() {
    const sections = document.querySelectorAll('.content-section');
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
    
    const observerOptions = {
        root: null,
        rootMargin: '-20% 0px -70% 0px',
        threshold: 0
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                sidebarLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${id}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, observerOptions);
    
    sections.forEach(section => observer.observe(section));
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(e.target.value);
        }, 300);
    });
    
    // Add keyboard shortcut 's' for search
    document.addEventListener('keydown', function(e) {
        if (e.key === 's' && !e.ctrlKey && !e.metaKey && 
            document.activeElement.tagName !== 'INPUT' && 
            document.activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

function performSearch(query) {
    if (!query.trim()) {
        hideSearchResults();
        return;
    }
    
    const content = document.body.textContent.toLowerCase();
    const queryLower = query.toLowerCase();
    
    if (content.includes(queryLower)) {
        showSearchResults(query);
    } else {
        showNoResults();
    }
}

function showSearchResults(query) {
    // Remove existing results
    hideSearchResults();
    
    const sections = document.querySelectorAll('.content-section, .card');
    const results = [];
    
    sections.forEach(section => {
        const text = section.textContent.toLowerCase();
        if (text.includes(query.toLowerCase())) {
            const title = section.querySelector('h2, h3, h4, h5, h6');
            if (title) {
                results.push({
                    element: section,
                    title: title.textContent,
                    id: section.id || ''
                });
            }
        }
    });
    
    if (results.length > 0) {
        createSearchResultsPopup(results, query);
    }
}

function createSearchResultsPopup(results, query) {
    const popup = document.createElement('div');
    popup.className = 'search-results';
    popup.innerHTML = `
        <div class="search-results-header">
            <h6>Search Results (${results.length})</h6>
            <button class="close-search" onclick="hideSearchResults()">×</button>
        </div>
        <div class="search-results-list">
            ${results.map(result => `
                <div class="search-result-item" onclick="scrollToSection('${result.id}')">
                    <div class="search-result-title">${highlightText(result.title, query)}</div>
                    <div class="search-result-excerpt">${highlightText(getExcerpt(result.element), query)}</div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Position popup near search input
    const searchInput = document.getElementById('searchInput');
    const rect = searchInput.getBoundingClientRect();
    popup.style.position = 'fixed';
    popup.style.top = `${rect.bottom + 10}px`;
    popup.style.left = `${rect.left}px`;
    popup.style.width = `${rect.width}px`;
    popup.style.zIndex = '1050';
    
    document.body.appendChild(popup);
}

function highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

function getExcerpt(element) {
    const text = element.textContent;
    const maxLength = 150;
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function scrollToSection(id) {
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
        hideSearchResults();
    }
}

function hideSearchResults() {
    const existingResults = document.querySelector('.search-results');
    if (existingResults) {
        existingResults.remove();
    }
}

function showNoResults() {
    const popup = document.createElement('div');
    popup.className = 'search-results';
    popup.innerHTML = `
        <div class="search-results-header">
            <h6>No Results Found</h6>
            <button class="close-search" onclick="hideSearchResults()">×</button>
        </div>
        <div class="search-results-list">
            <div class="search-result-item">
                <div class="search-result-title">No matching content found</div>
                <div class="search-result-excerpt">Try different keywords or check the navigation menu.</div>
            </div>
        </div>
    `;
    
    const searchInput = document.getElementById('searchInput');
    const rect = searchInput.getBoundingClientRect();
    popup.style.position = 'fixed';
    popup.style.top = `${rect.bottom + 10}px`;
    popup.style.left = `${rect.left}px`;
    popup.style.width = `${rect.width}px`;
    popup.style.zIndex = '1050';
    
    document.body.appendChild(popup);
}

// Scoring Playground
function initializeScoringPlayground() {
    const sliders = {
        count: document.getElementById('countSlider'),
        behavior: document.getElementById('behaviorSlider'),
        vital: document.getElementById('vitalSlider'),
        aqi: document.getElementById('aqiSlider'),
        noise: document.getElementById('noiseSlider')
    };
    
    const values = {
        count: document.getElementById('countValue'),
        behavior: document.getElementById('behaviorValue'),
        vital: document.getElementById('vitalValue'),
        aqi: document.getElementById('aqiValue'),
        noise: document.getElementById('noiseValue')
    };
    
    const scores = {
        count: document.getElementById('countScore'),
        behavior: document.getElementById('behaviorScore'),
        vital: document.getElementById('vitalScore'),
        aqi: document.getElementById('aqiScore'),
        noise: document.getElementById('noiseScore')
    };
    
    const weights = {
        count: 0.15,
        behavior: 0.45,
        vital: 0.15,
        aqi: 0.15,
        noise: 0.10
    };
    
    // Add event listeners
    Object.keys(sliders).forEach(key => {
        if (sliders[key]) {
            sliders[key].addEventListener('input', function() {
                updateScoringDisplay(key, this.value, values, scores, weights);
            });
        }
    });
    
    // Initialize display
    Object.keys(sliders).forEach(key => {
        if (sliders[key]) {
            updateScoringDisplay(key, sliders[key].value, values, scores, weights);
        }
    });
}

function updateScoringDisplay(component, value, values, scores, weights) {
    // Update value display
    if (values[component]) {
        values[component].textContent = value;
    }
    
    // Calculate component score (normalize to 0-100)
    let componentScore = parseInt(value);
    if (component === 'count') {
        componentScore = Math.min((value / 20) * 100, 100);
    }
    
    // Update score display
    if (scores[component]) {
        scores[component].textContent = Math.round(componentScore);
    }
    
    // Calculate overall threat
    calculateOverallThreat(weights);
}

function calculateOverallThreat(weights) {
    const sliders = {
        count: document.getElementById('countSlider'),
        behavior: document.getElementById('behaviorSlider'),
        vital: document.getElementById('vitalSlider'),
        aqi: document.getElementById('aqiSlider'),
        noise: document.getElementById('noiseSlider')
    };
    
    let overallThreat = 0;
    
    Object.keys(weights).forEach(key => {
        if (sliders[key]) {
            let value = parseInt(sliders[key].value);
            if (key === 'count') {
                value = Math.min((value / 20) * 100, 100);
            }
            overallThreat += value * weights[key];
        }
    });
    
    overallThreat = Math.round(overallThreat);
    
    // Update display
    const threatDisplay = document.getElementById('overallThreat');
    const threatBar = document.getElementById('threatBar');
    const recommendationBox = document.getElementById('recommendationBox');
    const recommendationText = document.getElementById('recommendationText');
    
    if (threatDisplay) {
        threatDisplay.textContent = overallThreat;
    }
    
    if (threatBar) {
        threatBar.style.width = `${overallThreat}%`;
        threatBar.className = 'progress-bar';
        if (overallThreat > 80) {
            threatBar.classList.add('bg-danger');
        } else if (overallThreat > 60) {
            threatBar.classList.add('bg-warning');
        } else if (overallThreat > 40) {
            threatBar.classList.add('bg-info');
        } else {
            threatBar.classList.add('bg-success');
        }
    }
    
    if (recommendationBox && recommendationText) {
        let recommendation = 'Normal monitoring';
        let alertClass = 'alert-success';
        
        if (overallThreat > 80) {
            recommendation = 'CRITICAL: Immediate attention required. Check all systems and alert authorities if necessary.';
            alertClass = 'alert-danger';
        } else if (overallThreat > 60) {
            recommendation = 'HIGH: Increased monitoring recommended. Investigate potential threats.';
            alertClass = 'alert-warning';
        } else if (overallThreat > 40) {
            recommendation = 'MODERATE: Enhanced monitoring advised. Review security protocols.';
            alertClass = 'alert-info';
        } else if (overallThreat > 20) {
            recommendation = 'ELEVATED: Maintain awareness and continue standard monitoring.';
            alertClass = 'alert-primary';
        }
        
        recommendationText.textContent = recommendation;
        recommendationBox.className = `alert ${alertClass}`;
    }
}

// Floating Action Button
function initializeFAB() {
    const fabMain = document.querySelector('.fab-main');
    const fabOptions = document.querySelector('.fab-options');
    
    if (!fabMain || !fabOptions) return;
    
    fabMain.addEventListener('click', function() {
        this.classList.toggle('active');
        fabOptions.classList.toggle('show');
    });
    
    // Close FAB when clicking outside
    document.addEventListener('click', function(e) {
        if (!fabMain.contains(e.target) && !fabOptions.contains(e.target)) {
            fabMain.classList.remove('active');
            fabOptions.classList.remove('show');
        }
    });
}

// Smooth scrolling
function initializeSmoothScroll() {
    // Already handled in navigation initialization
}

// Theme toggle
function initializeThemeToggle() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('scope-theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }
    
    // Add theme toggle button if not exists
    if (!document.querySelector('.theme-toggle')) {
        const themeToggle = document.createElement('button');
        themeToggle.className = 'theme-toggle btn btn-sm btn-outline-secondary position-fixed';
        themeToggle.style.cssText = 'top: 20px; right: 20px; z-index: 1000;';
        themeToggle.innerHTML = '<i class="bi bi-moon-stars"></i>';
        themeToggle.title = 'Toggle dark mode';
        
        themeToggle.addEventListener('click', toggleTheme);
        document.body.appendChild(themeToggle);
    }
}

function toggleTheme() {
    const body = document.body;
    const themeToggle = document.querySelector('.theme-toggle');
    
    body.classList.toggle('dark-mode');
    
    if (body.classList.contains('dark-mode')) {
        localStorage.setItem('scope-theme', 'dark');
        if (themeToggle) themeToggle.innerHTML = '<i class="bi bi-sun"></i>';
    } else {
        localStorage.setItem('scope-theme', 'light');
        if (themeToggle) themeToggle.innerHTML = '<i class="bi bi-moon-stars"></i>';
    }
}

// Quick Guide
function showQuickGuide() {
    // Remove existing modal
    hideQuickGuide();
    
    const modal = document.createElement('div');
    modal.className = 'quick-guide-modal';
    modal.innerHTML = `
        <div class="quick-guide-content">
            <div class="quick-guide-header">
                <h3 class="quick-guide-title">Quick Guide</h3>
                <button class="close-btn" onclick="hideQuickGuide()">×</button>
            </div>
            
            <div class="guide-section">
                <h4>Navigation</h4>
                <ul>
                    <li><strong>Sidebar:</strong> Use the left sidebar for quick navigation between sections</li>
                    <li><strong>Dropdown Menu:</strong> Access all sections from the Navigation dropdown</li>
                    <li><strong>Search:</strong> Press 'S' key or use the search bar to find content</li>
                    <li><strong>Smooth Scrolling:</strong> All navigation links provide smooth scrolling</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>Interactive Features</h4>
                <ul>
                    <li><strong>Scoring Playground:</strong> Adjust sliders to see real-time threat calculations</li>
                    <li><strong>Code Examples:</strong> Syntax highlighting for all code blocks</li>
                    <li><strong>Responsive Design:</strong> Works on desktop, tablet, and mobile devices</li>
                    <li><strong>Dark Mode:</strong> Toggle dark/light theme using the button in top-right</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>Keyboard Shortcuts</h4>
                <ul>
                    <li><code>S</code> - Activate search</li>
                    <li><code>ESC</code> - Close modals and search results</li>
                    <li><code>↑</code> - Scroll to top (when using floating action button)</li>
                    <li><code>F</code> - Toggle fullscreen (when using floating action button)</li>
                </ul>
            </div>
            
            <div class="guide-section">
                <h4>Getting Started</h4>
                <ul>
                    <li>Start with the <strong>System Overview</strong> to understand SCOPE architecture</li>
                    <li>Review <strong>Hardware Components</strong> for sensor information</li>
                    <li>Explore <strong>Software Components</strong> for implementation details</li>
                    <li>Try the <strong>Scoring Playground</strong> to understand threat calculations</li>
                    <li><strong>Launch SCOPE App</strong> to see the system in action</li>
                </ul>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Show with animation
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
    
    // Close on ESC key
    const handleEscape = function(e) {
        if (e.key === 'Escape') {
            hideQuickGuide();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
    
    // Close on background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            hideQuickGuide();
        }
    });
}

function hideQuickGuide() {
    const modal = document.querySelector('.quick-guide-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

function showQuickGuideOnFirstVisit() {
    const hasVisited = localStorage.getItem('scope-docs-visited');
    if (!hasVisited) {
        setTimeout(() => {
            showQuickGuide();
        }, 2000);
        localStorage.setItem('scope-docs-visited', 'true');
    }
}

// Action functions
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

function downloadPDF() {
    // In a real implementation, this would generate a PDF
    // For now, we'll show a message
    showNotification('PDF download feature coming soon!', 'info');
}

function shareDocumentation() {
    if (navigator.share) {
        navigator.share({
            title: 'SCOPE System Documentation',
            text: 'Comprehensive documentation for the SCOPE environmental monitoring system',
            url: window.location.href
        });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(window.location.href).then(() => {
            showNotification('Documentation link copied to clipboard!', 'success');
        });
    }
}

function printDocumentation() {
    window.print();
}

function openGitHub() {
    window.open('https://github.com/SarveshwarSenthilKumar/Engineering-Idol', '_blank');
}

function openWebApp() {
    window.open('http://localhost:5000', '_blank');
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <p>${message}</p>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
    
    // Remove on click
    notification.addEventListener('click', function() {
        this.remove();
    });
}

// Utility functions
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

// Handle window resize
window.addEventListener('resize', debounce(() => {
    // Re-initialize position-dependent elements
    const searchResults = document.querySelector('.search-results');
    if (searchResults) {
        hideSearchResults();
    }
}, 250));

// Handle escape key for closing modals
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideSearchResults();
    }
});

// Performance monitoring
if (window.performance) {
    window.addEventListener('load', function() {
        setTimeout(() => {
            const perfData = window.performance.timing;
            const loadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log(`Documentation loaded in ${loadTime}ms`);
        }, 0);
    });
}
