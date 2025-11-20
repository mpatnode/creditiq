# API Usage Guide

This document provides examples of how to use the Company Credit Rating API endpoints.

## Base URL

When running locally: `http://localhost:5000`

## API Documentation

Interactive API documentation is available at: `http://localhost:5000/api/docs`

## Endpoints

### 1. Search Companies

Search for companies by name or ticker symbol.

**Endpoint:** `POST /api/companies/search`

**Request Body:**
```json
{
  "query": "Apple"
}
```

**Response (200 OK):**
```json
{
  "companies": [
    {
      "id": "0000320193",
      "name": "Apple Inc.",
      "ticker": "AAPL",
      "exchange": "",
      "sector": "",
      "industry": ""
    }
  ],
  "count": 1
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:5000/api/companies/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Apple"}'
```

### 2. Generate Credit Rating

Generate a credit rating for a company.

**Endpoint:** `POST /api/ratings/generate`

**Request Body:**
```json
{
  "ticker": "AAPL"
}
```

Or using company ID:
```json
{
  "company_id": "0000320193"
}
```

**Response (200 OK):**
```json
{
  "rating": {
    "id": 1,
    "company_id": "0000320193",
    "company_name": "Apple Inc.",
    "ticker": "AAPL",
    "rating": "AAA",
    "score": 95.0,
    "confidence": 1.0,
    "timestamp": "2024-01-15T10:30:00",
    "methodology_version": "v1.0",
    "reasoning": "Excellent financial position...",
    "metrics": {
      "debt_to_equity": 0.5,
      "return_on_equity": 0.25,
      "current_ratio": 1.5
    },
    "breakdown": [
      {
        "category": "Leverage",
        "weight": 0.3,
        "score": 90.0,
        "metrics": {"debt_to_equity": 0.5},
        "reasoning": "Strong leverage position"
      }
    ],
    "box_folder_id": "123456",
    "box_report_file_id": "789012"
  },
  "message": "Credit rating generated successfully: AAA"
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:5000/api/ratings/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

### 3. Get Historical Ratings

Retrieve historical ratings for a company.

**Endpoint:** `GET /api/ratings/history/<company_id>`

**Response (200 OK):**
```json
{
  "ratings": [
    {
      "id": 2,
      "company_id": "0000320193",
      "company_name": "Apple Inc.",
      "ticker": "AAPL",
      "rating": "AAA",
      "score": 95.0,
      "timestamp": "2024-01-15T10:30:00",
      "methodology_version": "v1.0"
    },
    {
      "id": 1,
      "company_id": "0000320193",
      "company_name": "Apple Inc.",
      "ticker": "AAPL",
      "rating": "AA+",
      "score": 92.0,
      "timestamp": "2023-12-01T09:15:00",
      "methodology_version": "v1.0"
    }
  ],
  "count": 2
}
```

**Example using curl:**
```bash
curl http://localhost:5000/api/ratings/history/0000320193
```

### 4. Get Methodology Information

Get information about the credit rating methodology.

**Endpoint:** `GET /api/methodology`

**Response (200 OK):**
```json
{
  "file_id": "methodology_file_id",
  "version": "v1.0",
  "content_preview": "This methodology defines the process for calculating credit ratings...",
  "is_cached": true
}
```

**Example using curl:**
```bash
curl http://localhost:5000/api/methodology
```

## Error Responses

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "error": "Invalid input",
  "details": "Request must include either company_id or ticker"
}
```

**404 Not Found:**
```json
{
  "error": "Company not found",
  "details": "No company found matching: INVALID"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error",
  "details": "An unexpected error occurred"
}
```

## Running the Server

To start the Flask development server:

```bash
python app/main.py
```

Or using Flask CLI:

```bash
export FLASK_APP=app.main:create_app
flask run
```

## Testing

Run the API endpoint tests:

```bash
pytest tests/unit/test_api_endpoints.py -v
```

## Requirements Validation

The implemented API endpoints validate the following requirements:

- **Requirements 1.1, 1.2**: Company search and rating generation
- **Requirements 2.1, 2.2, 2.3**: Display rating with metrics and breakdown
- **Requirements 2.4**: Methodology information endpoint
- **Requirements 5.1, 5.2, 5.3, 5.4**: Company search functionality
- **Requirements 6.2, 6.3, 6.4**: Historical ratings retrieval
