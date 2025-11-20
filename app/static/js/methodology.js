// Methodology page functionality

// Initialize methodology page
document.addEventListener('DOMContentLoaded', async () => {
    await loadMethodology();
});

// Load methodology information
async function loadMethodology() {
    const loadingState = document.getElementById('loadingState');
    const methodologyDisplay = document.getElementById('methodologyDisplay');
    
    try {
        const data = await apiCall('/methodology');
        
        hideLoading('loadingState');
        
        if (data) {
            displayMethodology(data);
            methodologyDisplay.classList.remove('d-none');
        } else {
            showError('errorMessage', 'Failed to load methodology information');
        }
    } catch (error) {
        hideLoading('loadingState');
        showError('errorMessage', error.message || 'Failed to load methodology information');
    }
}

// Display methodology information
function displayMethodology(data) {
    // Version
    document.getElementById('methodologyVersion').textContent = data.version || 'N/A';
    
    // File ID
    document.getElementById('methodologyFileId').textContent = data.file_id || 'N/A';
    
    // Status
    const statusElement = document.getElementById('methodologyStatus');
    if (data.is_cached) {
        statusElement.innerHTML = '<span class="badge bg-success">Cached</span>';
    } else {
        statusElement.innerHTML = '<span class="badge bg-warning">Not Cached</span>';
    }
    
    // Content preview
    if (data.content_preview) {
        document.getElementById('methodologyPreview').textContent = data.content_preview;
    } else {
        document.getElementById('methodologyPreview').textContent = 'No preview available';
    }
}
