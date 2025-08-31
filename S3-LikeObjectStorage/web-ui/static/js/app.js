// S3 Storage System - Main JavaScript

// Global variables
let currentAlert = null;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Add fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize file upload drag and drop
    initializeFileUpload();
    
    // Auto-hide alerts after 5 seconds
    autoHideAlerts();
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadModal = document.getElementById('uploadModal');
    
    if (fileInput && uploadModal) {
        // Drag and drop functionality
        const modalBody = uploadModal.querySelector('.modal-body');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            modalBody.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            modalBody.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            modalBody.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            modalBody.classList.add('dragover');
        }
        
        function unhighlight() {
            modalBody.classList.remove('dragover');
        }
        
        modalBody.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            fileInput.files = files;
            showSelectedFiles();
        }
    }
}

function autoHideAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
}

// Alert system
function showAlert(message, type = 'info', permanent = false) {
    // Remove existing alert if any
    if (currentAlert) {
        currentAlert.remove();
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show ${permanent ? 'alert-permanent' : ''}`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert alert at the top of main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
    }
    
    currentAlert = alertDiv;
    
    // Auto-hide after 5 seconds unless permanent
    if (!permanent) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('Copied to clipboard!', 'success');
    }, function(err) {
        showAlert('Failed to copy to clipboard', 'error');
    });
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Form validation
function validateBucketName(name) {
    const regex = /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/;
    
    if (!name) {
        return 'Bucket name is required';
    }
    
    if (name.length < 3 || name.length > 63) {
        return 'Bucket name must be between 3 and 63 characters';
    }
    
    if (!regex.test(name)) {
        return 'Bucket name must contain only lowercase letters, numbers, and hyphens';
    }
    
    if (name.startsWith('-') || name.endsWith('-')) {
        return 'Bucket name cannot start or end with a hyphen';
    }
    
    return null;
}

// Loading states
function showLoading(element, text = 'Loading...') {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    
    if (element) {
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            ${text}
        `;
        element.disabled = true;
    }
}

function hideLoading(element, originalText = '') {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

// File operations
function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    
    const iconMap = {
        // Text files
        'txt': 'bi-file-earmark-text',
        'md': 'bi-file-earmark-text',
        'rtf': 'bi-file-earmark-text',
        
        // Code files
        'js': 'bi-file-earmark-code',
        'html': 'bi-file-earmark-code',
        'css': 'bi-file-earmark-code',
        'php': 'bi-file-earmark-code',
        'py': 'bi-file-earmark-code',
        'java': 'bi-file-earmark-code',
        'cpp': 'bi-file-earmark-code',
        'c': 'bi-file-earmark-code',
        
        // Images
        'jpg': 'bi-file-earmark-image',
        'jpeg': 'bi-file-earmark-image',
        'png': 'bi-file-earmark-image',
        'gif': 'bi-file-earmark-image',
        'svg': 'bi-file-earmark-image',
        'bmp': 'bi-file-earmark-image',
        
        // Documents
        'pdf': 'bi-file-earmark-pdf',
        'doc': 'bi-file-earmark-word',
        'docx': 'bi-file-earmark-word',
        'xls': 'bi-file-earmark-excel',
        'xlsx': 'bi-file-earmark-excel',
        'ppt': 'bi-file-earmark-ppt',
        'pptx': 'bi-file-earmark-ppt',
        
        // Archives
        'zip': 'bi-file-earmark-zip',
        'rar': 'bi-file-earmark-zip',
        '7z': 'bi-file-earmark-zip',
        'tar': 'bi-file-earmark-zip',
        'gz': 'bi-file-earmark-zip',
        
        // Media
        'mp4': 'bi-file-earmark-play',
        'avi': 'bi-file-earmark-play',
        'mkv': 'bi-file-earmark-play',
        'mp3': 'bi-file-earmark-music',
        'wav': 'bi-file-earmark-music',
        'flac': 'bi-file-earmark-music'
    };
    
    return iconMap[extension] || 'bi-file-earmark';
}

// Progress tracking
function updateProgress(current, total, element) {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    
    const percentage = Math.round((current / total) * 100);
    
    if (element) {
        element.style.width = percentage + '%';
        element.setAttribute('aria-valuenow', percentage);
        element.textContent = percentage + '%';
    }
    
    return percentage;
}

// Confirmation dialogs
function confirmAction(message, callback, title = 'Confirm Action') {
    if (confirm(message)) {
        callback();
    }
}

// Session management
function checkSession() {
    // Check if user is still authenticated
    fetch('/api/health')
        .then(response => {
            if (response.status === 401) {
                showAlert('Session expired. Please log in again.', 'warning');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            }
        })
        .catch(error => {
            console.error('Session check failed:', error);
        });
}

// Check session every 5 minutes
setInterval(checkSession, 5 * 60 * 1000);

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + U for upload (when in bucket view)
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal && typeof showUploadModal === 'function') {
            showUploadModal();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }
});

// Theme management
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function getTheme() {
    return localStorage.getItem('theme') || 'light';
}

function toggleTheme() {
    const currentTheme = getTheme();
    setTheme(currentTheme === 'light' ? 'dark' : 'light');
}

// Initialize theme
setTheme(getTheme());

// Export functions for global use
window.S3UI = {
    showAlert,
    formatFileSize,
    formatDateTime,
    copyToClipboard,
    validateBucketName,
    showLoading,
    hideLoading,
    getFileIcon,
    updateProgress,
    confirmAction,
    setTheme,
    getTheme,
    toggleTheme
};

console.log('S3 Storage System UI initialized successfully');