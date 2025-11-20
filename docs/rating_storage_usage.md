# Rating Storage Component Usage

## Overview

The Rating Storage component provides functionality for persisting credit ratings to both PostgreSQL (for metadata and quick access) and Box (for detailed reports and source documents).

## Components

### 1. Database Model (`models/rating.py`)

The `Rating` model stores rating metadata in PostgreSQL:

```python
from models.rating import Rating

# Fields include:
# - company_id, company_name, ticker
# - rating, score, confidence
# - timestamp, methodology_version
# - metrics (JSONB), breakdown (JSONB)
# - reasoning (Text)
# - box_folder_id, box_report_file_id, box_source_document_ids
```

### 2. Rating Storage Service (`services/rating_storage.py`)

The `RatingStorage` class provides methods for:

#### Saving Ratings to Database

```python
from services.rating_storage import RatingStorage
from services.rating_engine import RatingResult

storage = RatingStorage(
    db_session=db_session,
    box_client=box_client,
    ratings_root_folder_id="folder123"
)

# Save rating metadata to database
db_rating = storage.save_rating(rating_result)
```

#### Uploading Rating Packages to Box

```python
# Upload rating report and source documents to Box
package_info = await storage.save_rating_package_to_box(
    rating=rating_result,
    company_id="0000320193",
    source_documents=source_documents
)

# Update database record with Box file IDs
storage.update_rating_with_box_info(
    rating_id=db_rating.id,
    package_info=package_info
)
```

#### Retrieving Historical Ratings

```python
# Get all historical ratings for a company
ratings = storage.get_historical_ratings("0000320193")

# Get latest rating only
latest = storage.get_latest_rating("0000320193")

# Get with limit
recent_ratings = storage.get_historical_ratings("0000320193", limit=5)
```

#### Downloading from Box

```python
# Download rating report
report_content = await storage.get_rating_report_from_box("file123")

# Download source document
source_content = await storage.get_source_document_from_box("file456")
```

## Box Folder Structure

The component creates the following folder structure in Box:

```
/Credit Ratings/
  /Companies/
    /AAPL - Apple Inc/
      /2024-01-15/
        rating_report_AAPL_20240115.json
        financial_statements_AAPL_20240115.json
        market_data_AAPL_20240115.json
        methodology_snapshot_20240115.txt
```

## Database Initialization

To create the database tables:

```bash
python scripts/init_db.py
```

Or programmatically:

```python
from app.database import init_db

init_db()
```

## Complete Workflow Example

```python
import asyncio
from sqlalchemy.orm import Session
from services.box_mcp_client import BoxMCPClient
from services.rating_storage import RatingStorage
from services.rating_engine import RatingResult, SourceDocument

async def save_complete_rating(
    rating_result: RatingResult,
    source_documents: list[SourceDocument],
    db_session: Session,
    box_client: BoxMCPClient,
    ratings_folder_id: str
):
    """Save complete rating to database and Box."""
    
    # Initialize storage
    storage = RatingStorage(
        db_session=db_session,
        box_client=box_client,
        ratings_root_folder_id=ratings_folder_id
    )
    
    # Step 1: Save metadata to database
    db_rating = storage.save_rating(rating_result)
    print(f"Saved rating to database with ID: {db_rating.id}")
    
    # Step 2: Upload to Box
    package_info = await storage.save_rating_package_to_box(
        rating=rating_result,
        company_id=rating_result.company_id,
        source_documents=source_documents
    )
    print(f"Uploaded to Box: {package_info.folder_path}")
    
    # Step 3: Update database with Box references
    storage.update_rating_with_box_info(db_rating.id, package_info)
    print(f"Updated database with Box file IDs")
    
    return db_rating
```

## Error Handling

The component raises `RatingStorageError` for all failures:

```python
from services.rating_storage import RatingStorageError

try:
    storage.save_rating(rating_result)
except RatingStorageError as e:
    print(f"Failed to save rating: {e}")
```

## Testing

Unit tests are available in `tests/unit/test_rating_storage.py`:

```bash
pytest tests/unit/test_rating_storage.py -v
```
