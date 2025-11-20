# Frontend Interface Usage Guide

## Overview

The Company Credit Rating System includes a web-based frontend interface built with Flask templates, Bootstrap 5, and Chart.js. The interface provides an intuitive way to search for companies, generate credit ratings, view historical ratings, and understand the methodology.

## Pages

### 1. Home Page (`/`)

The landing page provides an overview of the system and quick access to key features:
- Introduction to the credit rating system
- Quick navigation to search functionality
- Feature highlights (Search, Analyze, Track)

### 2. Company Search Page (`/search`)

Search for companies by name or ticker symbol:
- **Autocomplete**: Type-ahead suggestions as you search
- **Search Results**: Displays matching companies with details
- **Generate Rating**: Click on a company to generate a credit rating

**Features:**
- Real-time autocomplete (triggers after 2 characters)
- Displays company name, ticker, exchange, sector, and industry
- Loading states during search
- Error handling for failed searches

### 3. Rating Display Page (`/rating`)

Displays the generated credit rating for a company:
- **Rating Grade**: Large, color-coded letter grade (AAA to D)
- **Score**: Numerical score (0-100)
- **Analysis Summary**: AI-generated reasoning for the rating
- **Financial Metrics**: Key ratios displayed in cards
- **Methodology Breakdown**: Visual breakdown with Chart.js
- **Rating Information**: Metadata including methodology version and confidence
- **Box Integration**: Links to view files in Box

**URL Parameters:**
- `company_id`: Company CIK identifier
- `ticker`: Company ticker symbol

**Features:**
- Loading state while generating rating
- Color-coded ratings (green for high grades, red for low grades)
- Interactive chart showing category scores and weights
- Links to historical ratings
- Links to Box folder and report

### 4. Historical Ratings Page (`/history`)

View all historical ratings for a company:
- **Timeline Chart**: Line chart showing rating scores over time
- **Ratings List**: Detailed list of all historical ratings
- **Rating Details**: Each entry shows grade, score, date, and key metrics

**URL Parameters:**
- `company_id`: Company CIK identifier

**Features:**
- Interactive timeline chart with Chart.js
- Reverse chronological ordering (newest first)
- Links to Box folders and reports for each rating
- Empty state when no ratings exist

### 5. Methodology Page (`/methodology`)

Information about the credit rating methodology:
- **Overview**: Description of the methodology approach
- **Methodology Details**: Version and file information
- **Content Preview**: Preview of methodology content
- **Key Components**: List of financial metrics used
- **Rating Scale**: Explanation of rating grades

**Features:**
- Displays methodology version and status
- Shows whether methodology is cached
- Lists all financial metric categories
- Rating scale reference table

## Technical Details

### Frontend Stack

- **Templates**: Jinja2 templates with Bootstrap 5
- **CSS Framework**: Bootstrap 5.3.0
- **Charts**: Chart.js 4.4.0
- **JavaScript**: Vanilla JavaScript (no framework)
- **Icons**: Bootstrap Icons (referenced in CSS)

### File Structure

```
app/
├── templates/
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Home page
│   ├── search.html         # Company search
│   ├── rating.html         # Rating display
│   ├── history.html        # Historical ratings
│   └── methodology.html    # Methodology info
└── static/
    ├── css/
    │   └── style.css       # Custom styles
    └── js/
        ├── main.js         # Utility functions
        ├── search.js       # Search page logic
        ├── rating.js       # Rating page logic
        ├── history.js      # History page logic
        └── methodology.js  # Methodology page logic
```

### API Integration

The frontend communicates with the backend API using the Fetch API:

- `POST /api/companies/search` - Search for companies
- `POST /api/ratings/generate` - Generate a credit rating
- `GET /api/ratings/history/{company_id}` - Get historical ratings
- `GET /api/methodology` - Get methodology information

### Color Coding

Ratings are color-coded for visual clarity:
- **AAA, AA**: Green (highest quality)
- **A, BBB**: Blue (good quality)
- **BB, B**: Orange (speculative)
- **CCC, CC, C, D**: Red (high risk)

### Loading States

All pages include loading states to provide feedback during:
- Company search
- Rating generation (can take up to a minute)
- Historical data loading
- Methodology loading

### Error Handling

The frontend includes comprehensive error handling:
- User-friendly error messages
- Network error handling
- Invalid input validation
- Empty state displays

## Usage Examples

### Generating a Rating

1. Navigate to the Search page
2. Enter a company name or ticker (e.g., "Apple" or "AAPL")
3. Select a company from the autocomplete or search results
4. Wait for the rating to generate (loading indicator shown)
5. View the rating, metrics, and breakdown
6. Click "View History" to see past ratings

### Viewing Historical Ratings

1. From a rating page, click "View History"
2. Or navigate to `/history?company_id={CIK}`
3. View the timeline chart showing rating trends
4. Scroll through the detailed ratings list
5. Click Box links to view stored reports

### Understanding the Methodology

1. Navigate to the Methodology page from the navigation bar
2. Read the overview and key components
3. View the rating scale reference
4. Check the methodology version and status

## Browser Compatibility

The frontend is compatible with modern browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Responsive Design

The interface is fully responsive and works on:
- Desktop (1920px+)
- Laptop (1024px - 1919px)
- Tablet (768px - 1023px)
- Mobile (320px - 767px)

## Accessibility

The frontend follows accessibility best practices:
- Semantic HTML
- ARIA labels where appropriate
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly

## Performance

- Minimal JavaScript dependencies (only Chart.js)
- CDN-hosted libraries for fast loading
- Debounced search for reduced API calls
- Cached methodology content
- Optimized chart rendering

## Future Enhancements

Potential improvements for the frontend:
- Real-time rating updates via WebSockets
- Export ratings to PDF
- Compare multiple companies side-by-side
- Advanced filtering and sorting
- Dark mode support
- Customizable dashboards
