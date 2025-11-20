# Company Credit Rating System

A web application that generates credit ratings for public companies using LLM-based methodology interpretation and Box platform integration.

## Features

- Generate credit ratings for public companies
- LLM-based methodology interpretation from PDF documents
- Integration with Box platform for document management
- Historical ratings tracking
- RESTful API with interactive documentation

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Box Custom Application (JWT authentication)
- OpenAI API key
- Financial data provider API key (e.g., Alpha Vantage)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd company-credit-rating
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up PostgreSQL database:
```bash
createdb credit_rating_db
```

6. Initialize the database:
```bash
python -c "from app.database import init_db; init_db()"
```

## Box MCP Server Setup

The application uses the self-hosted Box MCP server for Box integration. Follow these steps:

1. Install the Box MCP server following the official guide:
   https://developer.box.com/guides/box-mcp/self-hosted/

2. Configure your Box Custom Application:
   - Create a Custom App in Box Developer Console
   - Enable JWT authentication
   - Generate and download the configuration file
   - Grant necessary permissions (read/write files, manage folders)

3. Update `.env` with Box configuration:
   - `BOX_MCP_SERVER_PATH`: Path to the Box MCP server executable
   - `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, `BOX_ENTERPRISE_ID`: From Box app configuration
   - `BOX_METHODOLOGY_FOLDER_ID`: Box folder ID containing methodology PDFs
   - `BOX_RATINGS_FOLDER_ID`: Box folder ID for storing rating reports

## Running the Application

### Development Server

```bash
python app/main.py
```

The application will be available at `http://localhost:5000`

API documentation is available at `http://localhost:5000/api/docs`

### Using Flask CLI

```bash
export FLASK_APP=app.main:create_app
export FLASK_ENV=development
flask run
```

## Testing

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=app --cov=models --cov=services --cov-report=html
```

### Run only unit tests:
```bash
pytest tests/unit/
```

### Run only integration tests:
```bash
pytest tests/integration/ -v -s
```

### Run SEC to Box E2E test:
```bash
# Using the helper script
./scripts/test_sec_to_box.sh

# Or directly with pytest
pytest tests/integration/test_sec_to_box_e2e.py -v -s
```

### Run only property-based tests:
```bash
pytest tests/properties/
```

See `tests/integration/README.md` for detailed information about integration tests.

## Project Structure

```
company-credit-rating/
├── app/                    # Flask application
│   ├── __init__.py
│   ├── main.py            # Application factory
│   ├── config.py          # Configuration
│   ├── database.py        # Database setup
│   └── routes/            # API endpoints (to be created)
├── models/                # Data models
│   └── __init__.py
├── services/              # Business logic services
│   └── __init__.py
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── properties/       # Property-based tests
│   └── conftest.py       # Test configuration
├── .env.example          # Environment variables template
├── .gitignore
├── pyproject.toml        # Project configuration
└── README.md
```

## Configuration

Key configuration options in `.env`:

- **Flask**: `SECRET_KEY`, `FLASK_ENV`
- **Database**: `DATABASE_URL`
- **Box**: `BOX_MCP_SERVER_PATH`, `BOX_CLIENT_ID`, etc.
- **LLM**: `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`
- **Financial Data**: `FINANCIAL_DATA_PROVIDER`, `ALPHA_VANTAGE_API_KEY`
- **Application**: `MAX_RETRIES`, `REQUEST_TIMEOUT`, `DATA_AGE_THRESHOLD_MONTHS`

## Development

### Code Formatting

```bash
black .
```

### Type Checking

```bash
mypy app/ models/ services/
```

### Linting

```bash
flake8 app/ models/ services/
```

## License

[Your License Here]
