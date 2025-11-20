// Search page functionality

let searchTimeout = null;

// Initialize search page
document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('companySearch');
    const autocompleteResults = document.getElementById('autocompleteResults');
    
    // Handle form submission
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await performSearch();
    });
    
    // Handle autocomplete
    searchInput.addEventListener('input', debounce(async (e) => {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            autocompleteResults.classList.add('d-none');
            return;
        }
        
        await showAutocomplete(query);
    }, 300));
    
    // Hide autocomplete when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !autocompleteResults.contains(e.target)) {
            autocompleteResults.classList.add('d-none');
        }
    });
});

// Show autocomplete suggestions
async function showAutocomplete(query) {
    const autocompleteResults = document.getElementById('autocompleteResults');
    
    try {
        const data = await apiCall('/companies/search', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        
        if (data.companies && data.companies.length > 0) {
            renderAutocomplete(data.companies);
            autocompleteResults.classList.remove('d-none');
        } else {
            autocompleteResults.classList.add('d-none');
        }
    } catch (error) {
        console.error('Autocomplete failed:', error);
    }
}

// Render autocomplete results
function renderAutocomplete(companies) {
    const autocompleteResults = document.getElementById('autocompleteResults');
    
    autocompleteResults.innerHTML = companies.slice(0, 5).map(company => `
        <a href="#" class="list-group-item list-group-item-action" 
           data-company-id="${company.id}"
           data-company-ticker="${company.ticker}"
           onclick="selectCompany(event, '${company.id}', '${company.ticker}')">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${company.name}</strong>
                    <br>
                    <small class="text-muted">${company.ticker}</small>
                </div>
                <span class="badge bg-secondary">${company.exchange || 'N/A'}</span>
            </div>
        </a>
    `).join('');
}

// Select company from autocomplete
function selectCompany(event, companyId, ticker) {
    event.preventDefault();
    
    // Navigate to rating generation page
    window.location.href = `/rating?company_id=${encodeURIComponent(companyId)}&ticker=${encodeURIComponent(ticker)}`;
}

// Perform search
async function performSearch() {
    const searchInput = document.getElementById('companySearch');
    const searchSpinner = document.getElementById('searchSpinner');
    const resultsContainer = document.getElementById('resultsContainer');
    const searchResults = document.getElementById('searchResults');
    
    const query = searchInput.value.trim();
    
    if (!query) {
        showError('errorMessage', 'Please enter a company name or ticker');
        return;
    }
    
    hideError('errorMessage');
    searchSpinner.classList.remove('d-none');
    
    try {
        const data = await apiCall('/companies/search', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        
        searchSpinner.classList.add('d-none');
        
        if (data.companies && data.companies.length > 0) {
            renderSearchResults(data.companies);
            searchResults.classList.remove('d-none');
        } else {
            showError('errorMessage', 'No companies found matching your search');
            searchResults.classList.add('d-none');
        }
    } catch (error) {
        searchSpinner.classList.add('d-none');
        showError('errorMessage', error.message || 'Failed to search companies');
    }
}

// Render search results
function renderSearchResults(companies) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    resultsContainer.innerHTML = companies.map(company => `
        <div class="card company-card mb-3" 
             onclick="selectCompany(event, '${company.id}', '${company.ticker}')">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">${company.name}</h5>
                        <p class="card-text text-muted mb-2">
                            <strong>${company.ticker}</strong> | ${company.exchange || 'N/A'}
                        </p>
                        ${company.sector ? `<p class="card-text small mb-0">
                            <span class="badge bg-light text-dark">${company.sector}</span>
                            ${company.industry ? `<span class="badge bg-light text-dark">${company.industry}</span>` : ''}
                        </p>` : ''}
                    </div>
                    <button class="btn btn-primary">
                        Generate Rating
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}
