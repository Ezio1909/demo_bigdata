// Chart Management for GitHub Events Dashboard
class ChartManager {
    constructor() {
        this.charts = new Map();
        this.chartDefaults = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: CONFIG.CHART_ANIMATION_DURATION
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                }
            }
        };
    }
    
    // Initialize all charts
    initializeCharts() {
        this.createTimeSeriesChart();
        this.createEventTypesChart();
    }
    
    // Create time series chart for events over time
    createTimeSeriesChart() {
        const ctx = document.getElementById('timeSeriesChart');
        if (!ctx) return;
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Events',
                    data: [],
                    borderColor: CONFIG.CHART_COLORS.primary,
                    backgroundColor: CONFIG.CHART_COLORS.primary + '20',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: CONFIG.CHART_COLORS.primary,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                ...this.chartDefaults,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MMM dd'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Events'
                        },
                        ticks: {
                            precision: 0
                        }
                    }
                },
                plugins: {
                    ...this.chartDefaults.plugins,
                    tooltip: {
                        callbacks: {
                            title: (tooltipItems) => {
                                return new Date(tooltipItems[0].parsed.x).toLocaleString();
                            },
                            label: (context) => {
                                return `Events: ${UTILS.formatNumber(context.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });
        
        this.charts.set('timeSeriesChart', chart);
    }
    
    // Create event types distribution chart
    createEventTypesChart() {
        const ctx = document.getElementById('eventTypesChart');
        if (!ctx) return;
        
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverBorderWidth: 3,
                    hoverOffset: 4
                }]
            },
            options: {
                ...this.chartDefaults,
                cutout: '60%',
                plugins: {
                    ...this.chartDefaults.plugins,
                    legend: {
                        display: true,
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${UTILS.formatNumber(value)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        this.charts.set('eventTypesChart', chart);
    }
    
    // Update time series chart with new data
    updateTimeSeriesChart(hourlyEvents) {
        const chart = this.charts.get('timeSeriesChart');
        if (!chart || !hourlyEvents) return;
        
        const labels = hourlyEvents.map(point => point.timestamp);
        const data = hourlyEvents.map(point => point.count);
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        
        chart.update('active');
    }
    
    // Update event types chart with new data
    updateEventTypesChart(eventTypeStats) {
        const chart = this.charts.get('eventTypesChart');
        if (!chart || !eventTypeStats) return;
        
        // Take top 10 event types to avoid overcrowding
        const topEventTypes = eventTypeStats.slice(0, 10);
        
        const labels = topEventTypes.map(stat => stat.event_type);
        const data = topEventTypes.map(stat => stat.count);
        const colors = this.generateColors(topEventTypes.length);
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = data;
        chart.data.datasets[0].backgroundColor = colors;
        
        chart.update('active');
    }
    
    // Generate colors for chart data
    generateColors(count) {
        const colors = Object.values(CONFIG.CHART_COLORS);
        const result = [];
        
        for (let i = 0; i < count; i++) {
            result.push(colors[i % colors.length]);
        }
        
        return result;
    }
    
    // Update all charts with dashboard stats
    updateCharts(dashboardStats) {
        if (!dashboardStats) return;
        
        try {
            this.updateTimeSeriesChart(dashboardStats.hourly_events);
            this.updateEventTypesChart(dashboardStats.event_type_stats);
        } catch (error) {
            console.error('Error updating charts:', error);
        }
    }
    
    // Export chart as image
    exportChart(chartId) {
        const chart = this.charts.get(chartId);
        if (!chart) {
            UTILS.showNotification('Chart not found', 'error');
            return;
        }
        
        try {
            // Get chart canvas
            const canvas = chart.canvas;
            
            // Create download link
            const link = document.createElement('a');
            link.download = `github-events-${chartId}-${new Date().toISOString().split('T')[0]}.png`;
            link.href = canvas.toDataURL('image/png');
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            UTILS.showNotification('Chart exported successfully', 'success');
            
        } catch (error) {
            console.error('Error exporting chart:', error);
            UTILS.showNotification('Failed to export chart', 'error');
        }
    }
    
    // Resize all charts (useful for responsive design)
    resizeCharts() {
        this.charts.forEach(chart => {
            chart.resize();
        });
    }
    
    // Destroy all charts
    destroyCharts() {
        this.charts.forEach(chart => {
            chart.destroy();
        });
        this.charts.clear();
    }
    
    // Get chart instance
    getChart(chartId) {
        return this.charts.get(chartId);
    }
}

// Global chart manager instance
const chartManager = new ChartManager();

// Export chart function (called from HTML)
function exportChart(chartId) {
    chartManager.exportChart(chartId);
}

// Handle window resize
window.addEventListener('resize', UTILS.debounce(() => {
    chartManager.resizeCharts();
}, CONFIG.DEBOUNCE_DELAY));
