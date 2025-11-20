"""Unit tests for API endpoints."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.financial_data_retriever import Company
from services.rating_engine import RatingResult, FinancialMetrics, MetricBreakdown


@pytest.fixture
def mock_company():
    """Create a mock company for testing."""
    return Company(
        id="0000320193",
        name="Apple Inc.",
        ticker="AAPL",
        exchange="NASDAQ",
        sector="Technology",
        industry="Consumer Electronics"
    )


@pytest.fixture
def mock_rating_result(mock_company):
    """Create a mock rating result for testing."""
    return RatingResult(
        company_id=mock_company.id,
        company_name=mock_company.name,
        ticker=mock_company.ticker,
        rating="AAA",
        score=95.0,
        metrics=FinancialMetrics(
            debt_to_equity=0.5,
            return_on_equity=0.25,
            current_ratio=1.5
        ),
        breakdown=[
            MetricBreakdown(
                category="Leverage",
                weight=0.3,
                score=90.0,
                metrics={"debt_to_equity": 0.5},
                reasoning="Strong leverage position"
            )
        ],
        timestamp=datetime.now(),
        confidence=1.0,
        methodology_version="v1.0",
        reasoning="Excellent financial position"
    )


class TestCompaniesAPI:
    """Tests for companies API endpoints."""
    
    def test_search_companies_success(self, client, mock_company):
        """Test successful company search."""
        with patch('app.routes.companies.FinancialDataRetriever') as mock_retriever_class:
            # Setup mock
            mock_retriever = Mock()
            mock_retriever.search_companies.return_value = [mock_company]
            mock_retriever_class.return_value = mock_retriever
            
            # Make request
            response = client.post(
                '/api/companies/search',
                data=json.dumps({'query': 'Apple'}),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'companies' in data
            assert 'count' in data
            assert data['count'] == 1
            assert data['companies'][0]['ticker'] == 'AAPL'
            assert data['companies'][0]['name'] == 'Apple Inc.'
    
    def test_search_companies_missing_query(self, client):
        """Test company search with missing query."""
        response = client.post(
            '/api/companies/search',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'query' in data['error'].lower()
    
    def test_search_companies_empty_query(self, client):
        """Test company search with empty query."""
        response = client.post(
            '/api/companies/search',
            data=json.dumps({'query': ''}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_search_companies_no_results(self, client):
        """Test company search with no results."""
        with patch('app.routes.companies.FinancialDataRetriever') as mock_retriever_class:
            # Setup mock
            mock_retriever = Mock()
            mock_retriever.search_companies.return_value = []
            mock_retriever_class.return_value = mock_retriever
            
            # Make request
            response = client.post(
                '/api/companies/search',
                data=json.dumps({'query': 'NonExistentCompany'}),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['count'] == 0
            assert data['companies'] == []


class TestRatingsAPI:
    """Tests for ratings API endpoints."""
    
    def test_generate_rating_success(self, client, mock_company, mock_rating_result):
        """Test successful rating generation."""
        with patch('app.routes.ratings._get_services') as mock_get_services:
            # Setup mocks
            mock_engine = Mock()
            mock_storage = Mock()
            mock_retriever = Mock()
            
            mock_retriever.search_companies.return_value = [mock_company]
            
            # Mock async calculate_rating
            async def mock_calculate():
                return mock_rating_result
            mock_engine.calculate_rating = Mock(return_value=mock_calculate())
            
            # Mock database rating
            mock_db_rating = Mock()
            mock_db_rating.id = 1
            mock_db_rating.to_dict.return_value = {
                'id': 1,
                'company_id': mock_company.id,
                'company_name': mock_company.name,
                'ticker': mock_company.ticker,
                'rating': 'AAA',
                'score': 95.0,
                'timestamp': datetime.now().isoformat()
            }
            
            mock_storage.save_rating.return_value = mock_db_rating
            
            # Mock async save_rating_package_to_box
            mock_package_info = Mock()
            mock_package_info.rating_report_file_id = "12345"
            mock_package_info.source_document_file_ids = ["67890"]
            mock_package_info.folder_id = "folder123"
            
            async def mock_save_package(*args, **kwargs):
                return mock_package_info
            mock_storage.save_rating_package_to_box = Mock(return_value=mock_save_package())
            
            mock_storage.update_rating_with_box_info.return_value = mock_db_rating
            
            mock_get_services.return_value = (mock_engine, mock_storage, mock_retriever)
            
            # Make request
            response = client.post(
                '/api/ratings/generate',
                data=json.dumps({'ticker': 'AAPL'}),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'rating' in data
            assert 'message' in data
            assert data['rating']['ticker'] == 'AAPL'
    
    def test_generate_rating_missing_identifier(self, client):
        """Test rating generation with missing identifier."""
        response = client.post(
            '/api/ratings/generate',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_generate_rating_company_not_found(self, client):
        """Test rating generation for non-existent company."""
        with patch('app.routes.ratings._get_services') as mock_get_services:
            # Setup mocks
            mock_engine = Mock()
            mock_storage = Mock()
            mock_retriever = Mock()
            
            mock_retriever.search_companies.return_value = []
            
            mock_get_services.return_value = (mock_engine, mock_storage, mock_retriever)
            
            # Make request
            response = client.post(
                '/api/ratings/generate',
                data=json.dumps({'ticker': 'INVALID'}),
                content_type='application/json'
            )
            
            # Verify response
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
            assert 'not found' in data['error'].lower()
    
    def test_get_rating_history_success(self, client):
        """Test successful retrieval of rating history."""
        with patch('app.routes.ratings._get_services') as mock_get_services:
            # Setup mocks
            mock_engine = Mock()
            mock_storage = Mock()
            mock_retriever = Mock()
            
            # Mock historical ratings
            mock_rating1 = Mock()
            mock_rating1.to_dict.return_value = {
                'id': 1,
                'company_id': '0000320193',
                'ticker': 'AAPL',
                'rating': 'AAA',
                'timestamp': '2024-01-01T00:00:00'
            }
            
            mock_rating2 = Mock()
            mock_rating2.to_dict.return_value = {
                'id': 2,
                'company_id': '0000320193',
                'ticker': 'AAPL',
                'rating': 'AA+',
                'timestamp': '2023-12-01T00:00:00'
            }
            
            mock_storage.get_historical_ratings.return_value = [mock_rating1, mock_rating2]
            
            mock_get_services.return_value = (mock_engine, mock_storage, mock_retriever)
            
            # Make request
            response = client.get('/api/ratings/history/0000320193')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'ratings' in data
            assert 'count' in data
            assert data['count'] == 2
            assert len(data['ratings']) == 2
    
    def test_get_rating_history_no_ratings(self, client):
        """Test retrieval of rating history with no ratings."""
        with patch('app.routes.ratings._get_services') as mock_get_services:
            # Setup mocks
            mock_engine = Mock()
            mock_storage = Mock()
            mock_retriever = Mock()
            
            mock_storage.get_historical_ratings.return_value = []
            
            mock_get_services.return_value = (mock_engine, mock_storage, mock_retriever)
            
            # Make request
            response = client.get('/api/ratings/history/0000320193')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['count'] == 0
            assert data['ratings'] == []


class TestMethodologyAPI:
    """Tests for methodology API endpoints."""
    
    def test_get_methodology_info_success(self, client):
        """Test successful retrieval of methodology information."""
        with patch('app.routes.methodology.BoxMCPClient') as mock_box_client_class, \
             patch('app.routes.methodology.MethodologyLoader') as mock_loader_class:
            
            # Setup mocks
            mock_box_client = Mock()
            mock_box_client_class.return_value = mock_box_client
            
            mock_loader = Mock()
            mock_loader.is_cached = False
            mock_loader.get_methodology_content.return_value = "This is the methodology content..."
            
            # Mock async load_pdf_from_box
            async def mock_load():
                return "This is the methodology content..."
            mock_loader.load_pdf_from_box = Mock(return_value=mock_load())
            
            mock_loader_class.return_value = mock_loader
            
            # Make request
            response = client.get('/api/methodology')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'file_id' in data
            assert 'content_preview' in data
            assert 'is_cached' in data
    
    def test_get_methodology_info_cached(self, client):
        """Test retrieval of cached methodology information."""
        with patch('app.routes.methodology.BoxMCPClient') as mock_box_client_class, \
             patch('app.routes.methodology.MethodologyLoader') as mock_loader_class:
            
            # Setup mocks
            mock_box_client = Mock()
            mock_box_client_class.return_value = mock_box_client
            
            mock_loader = Mock()
            mock_loader.is_cached = True
            mock_loader.get_methodology_content.return_value = "Cached methodology content..."
            
            mock_loader_class.return_value = mock_loader
            
            # Make request
            response = client.get('/api/methodology')
            
            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'content_preview' in data
            assert data['is_cached'] is True
