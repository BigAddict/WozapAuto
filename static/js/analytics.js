/**
 * Analytics Dashboard JavaScript
 * Handles chart rendering, data fetching, and user interactions
 */

class AnalyticsDashboard {
    constructor(options) {
        this.apiUrl = options.apiUrl;
        this.currentDays = options.currentDays || 30;
        this.startDate = options.startDate;
        this.endDate = options.endDate;
        this.charts = {};
        this.isLoading = false;
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Time range buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const days = parseInt(e.target.dataset.days);
                this.setTimeRange(days);
            });
        });

        // Custom date range
        document.getElementById('apply-custom-range').addEventListener('click', () => {
            this.applyCustomRange();
        });

        // Chart type toggle
        const chartTypeBtn = document.getElementById('conversations-chart-type');
        if (chartTypeBtn) {
            chartTypeBtn.addEventListener('click', (e) => {
                this.toggleChartType('conversations');
            });
        }
    }

    setTimeRange(days) {
        // Update active button
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-days="${days}"]`).classList.add('active');

        this.currentDays = days;
        this.loadData();
    }

    applyCustomRange() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;

        if (!startDate || !endDate) {
            alert('Please select both start and end dates');
            return;
        }

        if (new Date(startDate) > new Date(endDate)) {
            alert('Start date must be before end date');
            return;
        }

        this.startDate = startDate;
        this.endDate = endDate;
        this.currentDays = null;
        this.loadData();
    }

    async loadInitialData() {
        await this.loadData();
    }

    async loadData() {
        if (this.isLoading) return;

        this.showLoading();
        this.isLoading = true;

        try {
            const params = new URLSearchParams();
            if (this.currentDays) {
                params.append('days', this.currentDays);
            } else {
                params.append('start_date', this.startDate);
                params.append('end_date', this.endDate);
            }

            const response = await fetch(`${this.apiUrl}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.updateDashboard(data);
        } catch (error) {
            console.error('Error loading analytics data:', error);
            this.showError('Failed to load analytics data. Please try again.');
        } finally {
            this.hideLoading();
            this.isLoading = false;
        }
    }

    updateDashboard(data) {
        this.updateOverviewCards(data);
        this.updateCharts(data);
        this.updateActivityTimeline(data);
    }

    updateOverviewCards(data) {
        // Update AI conversations
        const conversationsEl = document.getElementById('total-conversations');
        if (conversationsEl) {
            conversationsEl.textContent = data.ai_conversations?.stats?.total_conversations || 0;
        }

        // Update tokens
        const tokensEl = document.getElementById('total-tokens');
        if (tokensEl) {
            const tokens = data.ai_conversations?.stats?.total_tokens || 0;
            tokensEl.textContent = this.formatNumber(tokens);
        }

        // Update webhooks
        const webhooksEl = document.getElementById('total-webhooks');
        if (webhooksEl) {
            webhooksEl.textContent = data.webhook_activity?.stats?.total_webhooks || 0;
        }

        // Update documents
        const documentsEl = document.getElementById('total-documents');
        if (documentsEl) {
            documentsEl.textContent = data.knowledge_base?.stats?.total_documents || 0;
        }
    }

    updateCharts(data) {
        this.renderConversationsChart(data);
        this.renderTokensChart(data);
        this.renderWebhookChart(data);
        this.renderKnowledgeBaseChart(data);
    }

    renderConversationsChart(data) {
        const ctx = document.getElementById('conversationsChart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.charts.conversations) {
            this.charts.conversations.destroy();
        }

        const dailyData = data.ai_conversations?.daily_trends || [];
        const labels = dailyData.map(item => this.formatDate(item.date));
        const conversations = dailyData.map(item => item.conversations || 0);
        const tokens = dailyData.map(item => item.total_tokens || 0);

        this.charts.conversations = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Conversations',
                        data: conversations,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Tokens Used',
                        data: tokens,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Conversations'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Tokens'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    }
                }
            }
        });
    }

    renderTokensChart(data) {
        const ctx = document.getElementById('tokensChart');
        if (!ctx) return;

        if (this.charts.tokens) {
            this.charts.tokens.destroy();
        }

        const stats = data.ai_conversations?.stats || {};
        const inputTokens = stats.input_tokens || 0;
        const outputTokens = stats.output_tokens || 0;

        this.charts.tokens = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Input Tokens', 'Output Tokens'],
                datasets: [{
                    data: [inputTokens, outputTokens],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 99, 132, 0.8)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                return `${label}: ${value.toLocaleString()}`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderWebhookChart(data) {
        const ctx = document.getElementById('webhookChart');
        if (!ctx) return;

        if (this.charts.webhook) {
            this.charts.webhook.destroy();
        }

        const stats = data.webhook_activity?.stats || {};
        const processed = stats.processed_webhooks || 0;
        const failed = stats.failed_webhooks || 0;
        const pending = (stats.total_webhooks || 0) - processed - failed;

        this.charts.webhook = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Processed', 'Failed', 'Pending'],
                datasets: [{
                    data: [processed, failed, pending],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)'
                    ],
                    borderColor: [
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    renderKnowledgeBaseChart(data) {
        const ctx = document.getElementById('knowledgeBaseChart');
        if (!ctx) return;

        if (this.charts.knowledgeBase) {
            this.charts.knowledgeBase.destroy();
        }

        const stats = data.knowledge_base?.stats || {};
        const uploads = stats.total_uploads || 0;
        const searches = stats.total_searches || 0;

        this.charts.knowledgeBase = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Document Uploads', 'Searches'],
                datasets: [{
                    data: [uploads, searches],
                    backgroundColor: [
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ],
                    borderColor: [
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    }

    updateActivityTimeline(data) {
        const timelineEl = document.getElementById('activity-timeline');
        if (!timelineEl) return;

        // This would be populated with recent activity data
        // For now, we'll show a placeholder
        timelineEl.innerHTML = `
            <div class="activity-item">
                <div class="activity-icon ai">
                    <i class="bi bi-chat-dots"></i>
                </div>
                <div class="activity-content">
                    <h5 class="activity-title">AI Conversation</h5>
                    <p class="activity-description">Started a new conversation with your AI agent</p>
                    <p class="activity-time">Just now</p>
                </div>
            </div>
        `;
    }

    toggleChartType(chartName) {
        if (chartName === 'conversations' && this.charts.conversations) {
            const currentType = this.charts.conversations.config.type;
            const newType = currentType === 'line' ? 'bar' : 'line';
            this.charts.conversations.config.type = newType;
            this.charts.conversations.update();
            
            // Update button text
            const btn = document.getElementById('conversations-chart-type');
            if (btn) {
                btn.textContent = newType === 'line' ? 'Bar' : 'Line';
            }
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showError(message) {
        // You could implement a toast notification system here
        alert(message);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Chart.js defaults
    Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#6c757d';
});
