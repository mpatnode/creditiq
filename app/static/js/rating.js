// Rating page functionality

let breakdownChart = null;

// Initialize rating page
document.addEventListener('DOMContentLoaded', async () => {
    const companyId = getUrlParameter('company_id');
    const ticker = getUrlParameter('ticker');
    
    if (!companyId && !ticker) {
        showError('errorMessage', 'No company specified');
        hideLoading('loadingState');
        return;
    }
    
    await generateRating(companyId, ticker);
});

// Generate rating
async function generateRating(companyId, ticker) {
    const loadingState = document.getElementById('loadingState');
    const ratingDisplay = document.getElementById('ratingDisplay');
    
    try {
        const requestBody = {};
        if (ticker) requestBody.ticker = ticker;
        if (companyId) requestBody.company_id = companyId;
        
        const data = await apiCall('/ratings/generate', {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
        
        hideLoading('loadingState');
        
        if (data.rating) {
            displayRating(data.rating);
            ratingDisplay.classList.remove('d-none');
        } else {
            showError('errorMessage', 'Failed to generate rating');
        }
    } catch (error) {
        hideLoading('loadingState');
        showError('errorMessage', error.message || 'Failed to generate rating. Please try again.');
    }
}

// Display rating
function displayRating(rating) {
    // Company info
    document.getElementById('companyName').textContent = rating.company_name;
    document.getElementById('companyTicker').textContent = rating.ticker;
    document.getElementById('companyId').textContent = rating.company_id;
    
    // Rating grade with color
    const ratingGrade = document.getElementById('ratingGrade');
    ratingGrade.textContent = rating.rating;
    ratingGrade.className = `display-1 fw-bold mb-3 ${getRatingColorClass(rating.rating)}`;
    
    // Rating score
    document.getElementById('ratingScore').textContent = `Score: ${formatNumber(rating.score, 1)}`;
    
    // Timestamp
    document.getElementById('ratingTimestamp').textContent = formatDate(rating.timestamp);
    
    // Reasoning
    if (rating.reasoning) {
        document.getElementById('reasoningText').textContent = rating.reasoning;
    } else {
        document.getElementById('reasoningCard').classList.add('d-none');
    }
    
    // Financial metrics
    if (rating.metrics) {
        displayMetrics(rating.metrics);
    }
    
    // Breakdown
    if (rating.breakdown && rating.breakdown.length > 0) {
        displayBreakdown(rating.breakdown);
    }
    
    // Metadata
    document.getElementById('methodologyVersion').textContent = rating.methodology_version || 'N/A';
    document.getElementById('confidenceScore').textContent = rating.confidence 
        ? `${formatNumber(rating.confidence * 100, 0)}%` 
        : 'N/A';
    
    // Box links
    if (rating.box_folder_id) {
        const folderLink = document.getElementById('boxFolderLink');
        folderLink.href = `https://app.box.com/folder/${rating.box_folder_id}`;
    }
    
    if (rating.box_report_file_id) {
        const reportLink = document.getElementById('boxReportLink');
        reportLink.href = `https://app.box.com/file/${rating.box_report_file_id}`;
    }
    
    // History link
    const historyLink = document.getElementById('viewHistoryLink');
    historyLink.href = `/history?company_id=${encodeURIComponent(rating.company_id)}`;
}

// Display financial metrics
function displayMetrics(metrics) {
    const metricsContainer = document.getElementById('metricsContainer');
    
    const metricsList = [
        { label: 'Debt to Equity', value: metrics.debt_to_equity, format: 'ratio' },
        { label: 'Current Ratio', value: metrics.current_ratio, format: 'ratio' },
        { label: 'ROE', value: metrics.return_on_equity, format: 'percent' },
        { label: 'ROA', value: metrics.return_on_assets, format: 'percent' },
        { label: 'Net Profit Margin', value: metrics.net_profit_margin, format: 'percent' },
        { label: 'Interest Coverage', value: metrics.interest_coverage, format: 'ratio' },
        { label: 'Quick Ratio', value: metrics.quick_ratio, format: 'ratio' },
        { label: 'P/E Ratio', value: metrics.price_to_earnings, format: 'ratio' },
    ];
    
    metricsContainer.innerHTML = metricsList.map(metric => {
        let displayValue = 'N/A';
        if (metric.value !== null && metric.value !== undefined) {
            if (metric.format === 'percent') {
                displayValue = `${formatNumber(metric.value * 100, 1)}%`;
            } else {
                displayValue = formatNumber(metric.value, 2);
            }
        }
        
        return `
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="metric-card">
                    <div class="metric-label">${metric.label}</div>
                    <div class="metric-value">${displayValue}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Display breakdown
function displayBreakdown(breakdown) {
    const breakdownContainer = document.getElementById('breakdownContainer');
    
    breakdownContainer.innerHTML = breakdown.map(item => `
        <div class="breakdown-item">
            <div class="breakdown-category">${item.category}</div>
            <div class="mb-2">
                <span class="breakdown-score">Score: ${formatNumber(item.score, 1)}</span>
                <span class="breakdown-weight ms-2">Weight: ${formatNumber(item.weight * 100, 0)}%</span>
            </div>
            ${item.reasoning ? `<div class="breakdown-reasoning">${item.reasoning}</div>` : ''}
        </div>
    `).join('');
    
    // Create chart
    createBreakdownChart(breakdown);
}

// Create breakdown chart
function createBreakdownChart(breakdown) {
    const ctx = document.getElementById('breakdownChart');
    
    if (breakdownChart) {
        breakdownChart.destroy();
    }
    
    const labels = breakdown.map(item => item.category);
    const scores = breakdown.map(item => item.score);
    const weights = breakdown.map(item => item.weight * 100);
    
    breakdownChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Score',
                    data: scores,
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: 'Weight (%)',
                    data: weights,
                    backgroundColor: 'rgba(108, 117, 125, 0.7)',
                    borderColor: 'rgba(108, 117, 125, 1)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Score'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Weight (%)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}
