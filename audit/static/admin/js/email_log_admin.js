// Custom JavaScript for Email Log Admin Interface

document.addEventListener('DOMContentLoaded', function() {
    // Add click handlers for action buttons
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            handleActionClick(this);
        });
    });
    
    // Add tooltips to status badges
    const statusBadges = document.querySelectorAll('.status-badge');
    statusBadges.forEach(badge => {
        badge.title = 'Click to filter by this status';
        badge.style.cursor = 'pointer';
        badge.addEventListener('click', function() {
            filterByStatus(this.textContent.trim());
        });
    });
    
    // Add tooltips to email type badges
    const typeBadges = document.querySelectorAll('.email-type-badge');
    typeBadges.forEach(badge => {
        badge.title = 'Click to filter by this email type';
        badge.style.cursor = 'pointer';
        badge.addEventListener('click', function() {
            filterByType(this.textContent.trim());
        });
    });
    
    // Auto-refresh functionality for pending emails
    const pendingEmails = document.querySelectorAll('.status-pending');
    if (pendingEmails.length > 0) {
        // Refresh page every 30 seconds if there are pending emails
        setTimeout(() => {
            window.location.reload();
        }, 30000);
    }
    
    // Add search functionality
    const searchInput = document.querySelector('#searchbar');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterTable(this.value);
        });
    }
});

function handleActionClick(button) {
    const action = button.dataset.action;
    const emailId = button.dataset.emailId;
    
    switch(action) {
        case 'view_error':
            showErrorModal(emailId);
            break;
        case 'view_user':
            // Already handled by href
            break;
        case 'resend':
            resendEmail(emailId);
            break;
        case 'view_context':
            showContextModal(emailId);
            break;
    }
}

function filterByStatus(status) {
    const url = new URL(window.location);
    url.searchParams.set('status', status.toLowerCase());
    window.location.href = url.toString();
}

function filterByType(type) {
    const url = new URL(window.location);
    url.searchParams.set('email_type', type.toLowerCase().replace(' ', '_'));
    window.location.href = url.toString();
}

function filterTable(searchTerm) {
    const rows = document.querySelectorAll('#result_list tbody tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function showErrorModal(emailId) {
    // This would typically make an AJAX call to get error details
    // For now, we'll show a simple alert
    alert('Error details for email ID: ' + emailId);
}

function showContextModal(emailId) {
    // This would typically make an AJAX call to get context data
    // For now, we'll show a simple alert
    alert('Context data for email ID: ' + emailId);
}

function resendEmail(emailId) {
    if (confirm('Are you sure you want to resend this email?')) {
        // This would typically make an AJAX call to resend the email
        // For now, we'll show a simple alert
        alert('Resending email ID: ' + emailId);
    }
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+F to focus search
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.querySelector('#searchbar');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.querySelector('#searchbar');
        if (searchInput && searchInput.value) {
            searchInput.value = '';
            filterTable('');
        }
    }
});

// Add export functionality
function exportEmailLogs(format) {
    const url = new URL(window.location);
    url.searchParams.set('export', format);
    window.open(url.toString(), '_blank');
}

// Add bulk actions
function selectAllEmails() {
    const checkboxes = document.querySelectorAll('#result_list tbody input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
}

function deselectAllEmails() {
    const checkboxes = document.querySelectorAll('#result_list tbody input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}

// Add statistics display
function showStatistics() {
    // This would typically make an AJAX call to get statistics
    // For now, we'll show a simple alert
    alert('Email statistics would be displayed here');
}
