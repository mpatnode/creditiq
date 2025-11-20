"""Unit tests for Financial Data Retriever."""
import pytest
from datetime import datetime, timedelta
from services.financial_data_retriever import (
    FinancialDataRetriever,
    Company,
    FinancialData,
    DataQualityReport
)


class TestFinancialDataRetriever:
    """Test suite for FinancialDataRetriever."""
    
    def test_initialization(self):
        """Test retriever initialization."""
        retriever = FinancialDataRetriever()
        assert retriever.sec_api_base == "https://data.sec.gov"
        assert retriever.sec_files_base == "https://www.sec.gov"
        assert retriever.timeout == 30
        assert retriever.max_retries == 3
    
    def test_search_companies_by_ticker(self):
        """Test searching companies by ticker symbol."""
        retriever = FinancialDataRetriever()
        results = retriever.search_companies("AAPL")
        
        assert len(results) > 0
        assert any(c.ticker == "AAPL" for c in results)
        
        # Check Apple Inc is in results
        apple = next((c for c in results if c.ticker == "AAPL"), None)
        assert apple is not None
        assert "APPLE" in apple.name.upper()
        assert apple.id  # CIK should be populated
    
    def test_search_companies_by_name(self):
        """Test searching companies by name."""
        retriever = FinancialDataRetriever()
        results = retriever.search_companies("Microsoft")
        
        assert len(results) > 0
        assert any("MICROSOFT" in c.name.upper() for c in results)
    
    def test_search_companies_no_match(self):
        """Test searching with no matches."""
        from app.exceptions import CompanyNotFoundError
        
        retriever = FinancialDataRetriever()
        
        with pytest.raises(CompanyNotFoundError) as exc_info:
            retriever.search_companies("NONEXISTENTCOMPANY12345")
        
        assert "not found" in exc_info.value.user_message.lower()
    
    def test_get_company_data_by_ticker(self):
        """Test retrieving company data by ticker."""
        retriever = FinancialDataRetriever()
        data = retriever.get_company_data("AAPL")
        
        assert data is not None
        assert data.ticker == "AAPL"
        assert "APPLE" in data.company_name.upper()
        assert data.company_id  # CIK
        
        # Check financial statements structure
        assert data.financial_statements is not None
        assert data.financial_statements.balance_sheet is not None
        assert data.financial_statements.income_statement is not None
        assert data.financial_statements.cash_flow_statement is not None
        
        # Check data date
        assert data.data_date is not None
        assert isinstance(data.data_date, datetime)
    
    def test_get_company_data_invalid_ticker(self):
        """Test retrieving data for invalid ticker."""
        from app.exceptions import CompanyNotFoundError
        
        retriever = FinancialDataRetriever()
        
        with pytest.raises(CompanyNotFoundError, match="No companies found"):
            retriever.get_company_data("INVALIDTICKER12345")
    
    def test_validate_data_quality_complete_fresh(self):
        """Test data quality validation with complete and fresh data."""
        retriever = FinancialDataRetriever()
        data = retriever.get_company_data("MSFT")
        
        report = retriever.validate_data_quality(data)
        
        assert isinstance(report, DataQualityReport)
        assert isinstance(report.is_complete, bool)
        assert isinstance(report.is_fresh, bool)
        assert isinstance(report.missing_fields, list)
        assert isinstance(report.data_age_days, int)
        assert isinstance(report.warnings, list)
    
    def test_validate_data_quality_stale_data(self):
        """Test data quality validation with stale data."""
        retriever = FinancialDataRetriever(data_age_threshold_months=1)
        data = retriever.get_company_data("AAPL")
        
        # Manually set old date
        data.data_date = datetime.now() - timedelta(days=400)
        
        report = retriever.validate_data_quality(data)
        
        assert report.is_fresh is False
        assert report.data_age_days > 365
        assert len(report.warnings) > 0
        assert any("days old" in w for w in report.warnings)
