"""Tests for error handling and logging functionality."""

import pytest
from app.exceptions import (
    CreditRatingSystemError,
    CompanyNotFoundError,
    BoxConnectionError,
    BoxAIError,
    RatingEngineError,
    ValidationError,
    NetworkError,
)


class TestExceptionHierarchy:
    """Test custom exception hierarchy."""
    
    def test_base_exception_creation(self):
        """Test creating base exception with message."""
        error = CreditRatingSystemError(
            message="Technical error message",
            user_message="User-friendly message",
            details={"key": "value"}
        )
        
        assert error.message == "Technical error message"
        assert error.user_message == "User-friendly message"
        assert error.details == {"key": "value"}
    
    def test_base_exception_sanitization(self):
        """Test that base exception sanitizes messages."""
        error = CreditRatingSystemError(message="Technical error with sensitive data")
        
        # User message should be sanitized
        assert "sensitive data" not in error.user_message.lower()
        assert "error occurred" in error.user_message.lower()
    
    def test_company_not_found_error(self):
        """Test CompanyNotFoundError."""
        error = CompanyNotFoundError(
            message="Company XYZ not found in database",
            details={"query": "XYZ"}
        )
        
        assert "Company not found" in error.user_message
        assert "check the company name" in error.user_message.lower()
    
    def test_box_connection_error(self):
        """Test BoxConnectionError."""
        error = BoxConnectionError(
            message="Failed to connect to Box API",
            details={"endpoint": "https://api.box.com"}
        )
        
        assert "temporarily unavailable" in error.user_message.lower()
        assert "try again later" in error.user_message.lower()
    
    def test_box_ai_error(self):
        """Test BoxAIError."""
        error = BoxAIError(
            message="Box AI service returned 503",
            details={"status_code": 503}
        )
        
        assert "unable to analyze" in error.user_message.lower()
    
    def test_rating_engine_error(self):
        """Test RatingEngineError."""
        error = RatingEngineError(
            message="Failed to calculate rating due to missing data",
            details={"company": "AAPL"}
        )
        
        assert "unable to calculate" in error.user_message.lower()
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(
            message="Invalid company identifier format",
            details={"identifier": "123-ABC"}
        )
        
        assert "invalid input" in error.user_message.lower()
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError(
            message="Connection timeout after 30 seconds",
            details={"timeout": 30}
        )
        
        assert "network" in error.user_message.lower()
        assert "connection" in error.user_message.lower()
    
    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = CompanyNotFoundError(
            message="Company not found",
            user_message="Custom user message",
            details={"query": "TEST"}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error"] == "CompanyNotFoundError"
        assert error_dict["message"] == "Custom user message"
        assert error_dict["details"] == {"query": "TEST"}
    
    def test_exception_inheritance(self):
        """Test that custom exceptions inherit from base."""
        assert issubclass(CompanyNotFoundError, CreditRatingSystemError)
        assert issubclass(BoxConnectionError, CreditRatingSystemError)
        assert issubclass(BoxAIError, CreditRatingSystemError)
        assert issubclass(RatingEngineError, CreditRatingSystemError)
        assert issubclass(ValidationError, CreditRatingSystemError)
        assert issubclass(NetworkError, CreditRatingSystemError)


class TestLoggingConfiguration:
    """Test logging configuration."""
    
    def test_logging_setup(self):
        """Test that logging can be set up."""
        from app.logging_config import setup_logging
        import logging
        
        # Setup logging with test configuration
        setup_logging(
            log_level="DEBUG",
            log_to_console=True,
            log_to_file=False
        )
        
        # Verify logger is configured
        logger = logging.getLogger("test_logger")
        assert logger.level <= logging.DEBUG
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        from app.logging_config import get_logger
        
        logger = get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_sanitizing_formatter(self):
        """Test that sensitive information is sanitized."""
        from app.logging_config import SanitizingFormatter
        import logging
        
        formatter = SanitizingFormatter()
        
        # Create a log record with sensitive information
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User logged in with password=secret123 and api_key=abc123",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Sensitive values should be replaced
        assert "secret123" not in formatted
        assert "abc123" not in formatted
        assert "***" in formatted


class TestErrorHandlerIntegration:
    """Test Flask error handler integration."""
    
    def test_credit_rating_error_handler(self):
        """Test that custom errors are handled correctly."""
        from app.main import create_app
        from flask import jsonify
        
        app = create_app()
        
        with app.test_client() as client:
            # Test 404 error
            response = client.get('/nonexistent')
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data
            assert 'message' in data
    
    def test_error_response_format(self):
        """Test that error responses have correct format."""
        error = CompanyNotFoundError(
            message="Technical message",
            user_message="User message",
            details={"key": "value"}
        )
        
        error_dict = error.to_dict()
        
        # Verify response structure
        assert "error" in error_dict
        assert "message" in error_dict
        assert "details" in error_dict
        
        # Verify user message is used, not technical message
        assert error_dict["message"] == "User message"
