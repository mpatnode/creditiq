"""Unit tests for Rating Storage."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from services.rating_storage import (
    RatingStorage,
    RatingStorageError,
    RatingPackageInfo,
)
from services.rating_engine import (
    RatingResult,
    SourceDocument,
    FinancialMetrics,
    MetricBreakdown,
)
from services.box_mcp_client import BoxMCPClient, MCPToolResult
from models.rating import Rating


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def mock_box_client():
    """Create mock Box MCP client."""
    client = Mock(spec=BoxMCPClient)
    client.upload_file = AsyncMock()
    client.create_folder = AsyncMock()
    client.search_files = AsyncMock()
    client.update_file_metadata = AsyncMock()
    client.read_file = AsyncMock()
    return client


@pytest.fixture
def sample_rating_result():
    """Create sample rating result."""
    return RatingResult(
        company_id="0000320193",
        company_name="Apple Inc.",
        ticker="AAPL",
        rating="AAA",
        score=95.5,
        metrics=FinancialMetrics(
            debt_to_equity=1.5,
            current_ratio=2.0,
            return_on_equity=0.45,
        ),
        breakdown=[
            MetricBreakdown(
                category="Leverage",
                weight=0.3,
                score=90.0,
                metrics={"debt_to_equity": 1.5},
                reasoning="Strong leverage position"
            )
        ],
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        confidence=0.95,
        methodology_version="v1.0",
        reasoning="Excellent financial position with strong metrics across all categories."
    )


@pytest.fixture
def sample_source_documents():
    """Create sample source documents."""
    return [
        SourceDocument(
            type="financial_statements",
            content=b'{"balance_sheet": {}}',
            file_name="financial_statements_AAPL_20240115.json",
            metadata={"company_id": "0000320193", "ticker": "AAPL"}
        ),
        SourceDocument(
            type="market_data",
            content=b'{"market_cap": 3000000000000}',
            file_name="market_data_AAPL_20240115.json",
            metadata={"company_id": "0000320193", "ticker": "AAPL"}
        ),
    ]


class TestRatingStorage:
    """Test suite for RatingStorage."""

    def test_init(self, mock_db_session, mock_box_client):
        """Test RatingStorage initialization."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        assert storage.db_session == mock_db_session
        assert storage.box_client == mock_box_client
        assert storage.ratings_root_folder_id == "folder123"

    def test_save_rating_success(self, mock_db_session, mock_box_client, sample_rating_result):
        """Test saving rating to database."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Mock the refresh to set an ID
        def mock_refresh(obj):
            obj.id = 1
        mock_db_session.refresh.side_effect = mock_refresh
        
        result = storage.save_rating(sample_rating_result)
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        
        # Verify the added object is a Rating instance
        added_rating = mock_db_session.add.call_args[0][0]
        assert isinstance(added_rating, Rating)
        assert added_rating.company_id == "0000320193"
        assert added_rating.company_name == "Apple Inc."
        assert added_rating.ticker == "AAPL"
        assert added_rating.rating == "AAA"
        assert added_rating.score == 95.5

    def test_save_rating_rollback_on_error(self, mock_db_session, mock_box_client, sample_rating_result):
        """Test save_rating rolls back on error."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Make commit raise an exception
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(RatingStorageError, match="Database save failed"):
            storage.save_rating(sample_rating_result)
        
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_rating_package_to_box_success(
        self,
        mock_db_session,
        mock_box_client,
        sample_rating_result,
        sample_source_documents
    ):
        """Test uploading rating package to Box."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Mock folder creation
        mock_box_client.search_files.return_value = MCPToolResult(
            success=True,
            data=[]
        )
        mock_box_client.create_folder.return_value = MCPToolResult(
            success=True,
            data='{"id": "company_folder_123"}'
        )
        
        # Mock file uploads
        mock_box_client.upload_file.side_effect = [
            MCPToolResult(success=True, data='{"id": "report_file_123"}'),
            MCPToolResult(success=True, data='{"id": "source_file_1"}'),
            MCPToolResult(success=True, data='{"id": "source_file_2"}'),
        ]
        
        # Mock metadata updates
        mock_box_client.update_file_metadata.return_value = MCPToolResult(
            success=True,
            data={}
        )
        
        result = await storage.save_rating_package_to_box(
            rating=sample_rating_result,
            company_id="0000320193",
            source_documents=sample_source_documents
        )
        
        # Verify result
        assert isinstance(result, RatingPackageInfo)
        assert result.rating_report_file_id == "report_file_123"
        assert len(result.source_document_file_ids) == 2
        assert result.folder_id == "company_folder_123"
        
        # Verify Box operations
        assert mock_box_client.create_folder.call_count >= 1
        assert mock_box_client.upload_file.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_company_folder_creates_new(self, mock_db_session, mock_box_client):
        """Test ensure_company_folder creates new folder."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Mock search returns no results
        mock_box_client.search_files.return_value = MCPToolResult(
            success=True,
            data=[]
        )
        
        # Mock folder creation
        mock_box_client.create_folder.return_value = MCPToolResult(
            success=True,
            data='{"id": "new_folder_123"}'
        )
        
        folder_id = await storage.ensure_company_folder(
            company_id="0000320193",
            company_name="Apple Inc.",
            ticker="AAPL"
        )
        
        assert folder_id == "new_folder_123"
        mock_box_client.create_folder.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_rating_folder_creates_new(self, mock_db_session, mock_box_client):
        """Test ensure_rating_folder creates new folder."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Mock folder creation
        mock_box_client.create_folder.return_value = MCPToolResult(
            success=True,
            data='{"id": "rating_folder_123"}'
        )
        
        rating_date = datetime(2024, 1, 15)
        folder_id = await storage.ensure_rating_folder(
            company_folder_id="company_folder_123",
            rating_date=rating_date
        )
        
        assert folder_id == "rating_folder_123"
        mock_box_client.create_folder.assert_called_once()
        
        # Verify folder name format
        call_args = mock_box_client.create_folder.call_args
        assert call_args[1]["folder_name"] == "2024-01-15"

    def test_get_historical_ratings(self, mock_db_session, mock_box_client):
        """Test retrieving historical ratings."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        # Mock query results
        mock_rating1 = Mock(spec=Rating)
        mock_rating1.timestamp = datetime(2024, 1, 15)
        mock_rating2 = Mock(spec=Rating)
        mock_rating2.timestamp = datetime(2024, 1, 10)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_rating1, mock_rating2]
        
        mock_db_session.query.return_value = mock_query
        
        ratings = storage.get_historical_ratings("0000320193")
        
        assert len(ratings) == 2
        assert ratings[0] == mock_rating1
        assert ratings[1] == mock_rating2
        
        # Verify query was constructed correctly
        mock_db_session.query.assert_called_once_with(Rating)
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()

    def test_get_historical_ratings_with_limit(self, mock_db_session, mock_box_client):
        """Test retrieving historical ratings with limit."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db_session.query.return_value = mock_query
        
        storage.get_historical_ratings("0000320193", limit=5)
        
        mock_query.limit.assert_called_once_with(5)

    def test_get_latest_rating(self, mock_db_session, mock_box_client):
        """Test retrieving latest rating."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_rating = Mock(spec=Rating)
        mock_rating.rating = "AAA"
        mock_rating.timestamp = datetime(2024, 1, 15)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_rating
        
        mock_db_session.query.return_value = mock_query
        
        rating = storage.get_latest_rating("0000320193")
        
        assert rating == mock_rating
        mock_query.first.assert_called_once()

    def test_get_latest_rating_none(self, mock_db_session, mock_box_client):
        """Test get_latest_rating returns None when no ratings exist."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        
        mock_db_session.query.return_value = mock_query
        
        rating = storage.get_latest_rating("0000320193")
        
        assert rating is None

    @pytest.mark.asyncio
    async def test_get_rating_report_from_box(self, mock_db_session, mock_box_client):
        """Test downloading rating report from Box."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_box_client.read_file.return_value = b'{"rating": "AAA"}'
        
        content = await storage.get_rating_report_from_box("file123")
        
        assert content == b'{"rating": "AAA"}'
        mock_box_client.read_file.assert_called_once_with("file123")

    @pytest.mark.asyncio
    async def test_get_source_document_from_box(self, mock_db_session, mock_box_client):
        """Test downloading source document from Box."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_box_client.read_file.return_value = b'{"data": "test"}'
        
        content = await storage.get_source_document_from_box("file123")
        
        assert content == b'{"data": "test"}'
        mock_box_client.read_file.assert_called_once_with("file123")

    def test_update_rating_with_box_info(self, mock_db_session, mock_box_client):
        """Test updating rating with Box information."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_rating = Mock(spec=Rating)
        mock_rating.id = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_rating
        
        mock_db_session.query.return_value = mock_query
        
        package_info = RatingPackageInfo(
            rating_report_file_id="report123",
            source_document_file_ids=["source1", "source2"],
            folder_path="/path/to/folder",
            folder_id="folder123"
        )
        
        result = storage.update_rating_with_box_info(1, package_info)
        
        assert result == mock_rating
        assert mock_rating.box_folder_id == "folder123"
        assert mock_rating.box_report_file_id == "report123"
        assert mock_rating.box_source_document_ids == ["source1", "source2"]
        
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_update_rating_with_box_info_not_found(self, mock_db_session, mock_box_client):
        """Test update_rating_with_box_info raises when rating not found."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        mock_db_session.query.return_value = mock_query
        
        package_info = RatingPackageInfo(
            rating_report_file_id="report123",
            source_document_file_ids=[],
            folder_path="/path",
            folder_id="folder123"
        )
        
        with pytest.raises(RatingStorageError, match="Rating 999 not found"):
            storage.update_rating_with_box_info(999, package_info)

    def test_generate_rating_report(self, mock_db_session, mock_box_client, sample_rating_result):
        """Test generating rating report content."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        content = storage._generate_rating_report(sample_rating_result)
        
        assert isinstance(content, bytes)
        
        # Verify it's valid JSON
        import json
        report = json.loads(content.decode('utf-8'))
        
        assert report['company_name'] == "Apple Inc."
        assert report['ticker'] == "AAPL"
        assert report['rating'] == "AAA"
        assert report['score'] == 95.5
        assert 'metrics' in report
        assert 'breakdown' in report

    def test_extract_file_id_from_dict(self, mock_db_session, mock_box_client):
        """Test extracting file ID from dictionary."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        data = {"id": "file123", "name": "test.pdf"}
        file_id = storage._extract_file_id(data)
        
        assert file_id == "file123"

    def test_extract_file_id_from_json_string(self, mock_db_session, mock_box_client):
        """Test extracting file ID from JSON string."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        data = '{"id": "file456", "name": "test.pdf"}'
        file_id = storage._extract_file_id(data)
        
        assert file_id == "file456"

    def test_extract_file_id_raises_on_invalid_data(self, mock_db_session, mock_box_client):
        """Test _extract_file_id raises on invalid data."""
        storage = RatingStorage(
            db_session=mock_db_session,
            box_client=mock_box_client,
            ratings_root_folder_id="folder123"
        )
        
        with pytest.raises(RatingStorageError, match="Could not extract file ID"):
            storage._extract_file_id({"invalid": "data"})
