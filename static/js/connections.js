/**
 * Simplified Connection Management JavaScript for WozapAuto
 * Handles basic form interactions without API calls or WebSockets
 */

class ConnectionManager {
    constructor(container) {
        this.container = container;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // Form submission
        this.container.addEventListener('submit', this.handleFormSubmit.bind(this));
        
        // Button clicks
        this.container.addEventListener('click', this.handleButtonClick.bind(this));
        
        // Connection method selection
        this.container.addEventListener('change', this.handleMethodChange.bind(this));
    }

    async handleFormSubmit(event) {
        if (!event.target.matches('[data-form="connection-setup"]')) return;
        
        event.preventDefault();
        // Let Django handle the form submission
        event.target.submit();
    }

    handleButtonClick(event) {
        const button = event.target.closest('[data-action]');
        if (!button) return;

        const action = button.dataset.action;

        switch (action) {
            case 'manage':
                this.handleManageConnection(button);
                break;
            case 'test':
                this.handleTestConnection(button);
                break;
            case 'delete':
                this.handleDeleteConnection(button);
                break;
        }
    }

    handleMethodChange(event) {
        if (!event.target.matches('[name="connection_method"]')) return;
        
        const method = event.target.value;
        this.updateMethodUI(method);
    }

    updateMethodUI(method) {
        // Show/hide relevant sections based on connection method
        const qrSection = this.container.querySelector('[data-method="qr"]');
        const codeSection = this.container.querySelector('[data-method="code"]');
        
        if (method === 'qr') {
            if (qrSection) qrSection.style.display = 'block';
            if (codeSection) codeSection.style.display = 'none';
        } else if (method === 'code') {
            if (qrSection) qrSection.style.display = 'none';
            if (codeSection) codeSection.style.display = 'block';
        }
    }

    handleManageConnection(button) {
        // Redirect to manage page
        window.location.href = '/connections/';
    }

    handleTestConnection(button) {
        // Show a simple alert since we don't have API endpoints
        alert('Test connection functionality is not available in this simplified version.');
    }

    handleDeleteConnection(button) {
        // Show confirmation dialog
        if (confirm('Are you sure you want to delete this connection? This action cannot be undone.')) {
            // Redirect to delete page or show message
            alert('Delete functionality is not available in this simplified version.');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.connection-wizard, .connection-container');
    if (container) {
        new ConnectionManager(container);
    }
});