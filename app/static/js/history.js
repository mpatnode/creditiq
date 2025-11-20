// History page functionality

let timelineChart = null;

// Initialize history page
document.addEventListener('DOMContentLoaded', async () => {
    const companyId = getUrlParameter('company_id');
    
    if (!companyId) {
        showError('errorMessage', 'No company specified');
        hideLoading('loadingState');
        return;
    }
    
    await loadHistory(companyId);
});

// Load rating history
async function loadHistory(companyId) {
    const loadingState = document.getElementById('loadingState');
    const historyDisplay = document.getElementById('historyDisplay');
    const emptyState = document.getElementById('emptyState');
    
    try {
        const data = await apiCall(`/ratings/history/${encodeURIComponent(companyId)}`);
        
        hideLoading('loadingState');
        
        if (data.ratings && data.ratings.length > 0) {
            displayHistory(data.ratings);
            historyDisplay.classList.remove('d-none');
        } else {
            emptyState.classList.remove('d-none');
        }
    } catch (error) {
        hideLoading('loadingState');
        showError('errorMessage', error.message || 'Failed to load rating history');
    }
}

// Display history
function displayHistory(ratings) {
    // Sort by timestamp (newest first)
    ratings.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Display company info from first rating
    const firstRating = ratings[0];
    document.getElementById('companyName').textContent = firstRating.company_name;
    document.getElementById('companyTicker').textContent = firstRating.ticker;
    document.getElementById('companyId').textContent = firstRating.company_id;
    
    // Create timeline chart
    createTimelineChart(ratings);
    
    // Display ratings list
    displayRatingsList(ratings);
}

// Create timeline chart
function createTimelineChart(ratings) {
    const ctx = document.getElementById('timelineChart');
    
    if (timelineChart) {
        timelineChart.destroy();
    }
    
    // Sort by timestamp (oldest first for chart)
    const sortedRatings = [...ratings].sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
    );
    
    const labels = sortedRatings.map(r => formatDate(r.timestamp));
    const scores = sortedRatings.map(r => r.score);
    const ratingLabels = sortedRatings.map(r => r.rating);
    
    timelineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Credit Score',
                data: scores,
                borderColor: 'rgba(13, 110, 253, 1)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: 'rgba(13, 110, 253, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            return `Rating: ${ratingLabels[context.dataIndex]}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Score'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
}

// Display ratings list
function displayRatingsList(ratings) {
    const ratingsContainer = document.getElementById('ratingsContainer');
    
    ratingsContainer.innerHTML = ratings.map((rating, index) => `
        <div class="timeline-item">
            <div class="timeline-marker"></div>
            <div class="timeline-content">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h5 class="mb-1">
                            <span class="${getRatingColorClass(rating.rating)}">${rating.rating}</span>
                        </h5>
                        <p class="text-muted mb-0 small">${formatDate(rating.timestamp)}</p>
                    </div>
                    <div class="text-end">
                        <div class="badge bg-primary mb-1">Score: ${formatNumber(rating.score, 1)}</div>
                        ${rating.confidence ? `
                            <div class="badge bg-secondary">
                                Confidence: ${formatNumber(rating.confidence * 100, 0)}%
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                ${rating.reasoning ? `
                    <p class="mb-2 small">${rating.reasoning}</p>
                ` : ''}
                
                ${rating.breakdown && rating.breakdown.length > 0 ? `
                    <div class="mt-2">
                        <strong class="small">Key Metrics:</strong>
                        <div class="d-flex flex-wrap gap-2 mt-1">
                            ${rating.breakdown.slice(0, 3).map(item => `
                                <span class="badge bg-light text-dark">
                                    ${item.category}: ${formatNumber(item.score, 1)}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div class="mt-2">
                    ${rating.box_folder_id ? `
                        <a href="https://app.box.com/folder/${rating.box_folder_id}" 
                           target="_blank" 
                           class="btn btn-sm btn-outline-primary me-2">
                            View in Box
                        </a>
                    ` : ''}
                    ${rating.box_report_file_id ? `
                        <a href="https://app.box.com/file/${rating.box_report_file_id}" 
                           target="_blank" 
                           class="btn btn-sm btn-outline-secondary">
                            Download Report
                        </a>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}
