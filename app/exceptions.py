"""Custom exception classes for the Credit Rating System.

This module defines a hierarchy of custom exceptions for better error handling
and user-facing error messages throughout the application.
"""


class CreditRatingSystemError(Exception):
    """Base exception for all Credit Rating System errors.
    
    All custom exceptions should inherit from this base class.
    """
    
    def __init__(self, message: str, user_message: str = None, details: dict = None):
        """Initialize exception with message and optional user-facing message.
        
        Args:
            message: Technical error message for logging
            user_message: Sanitized message safe to show to users
            details: Additional error details for logging
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or self._sanitize_message(message)
        self.details = details or {}
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize error message for user display.
        
        Removes technical details, stack traces, and sensitive information.
        
        Args:
            message: Original error message
            
        Returns:
            Sanitized message safe for user display
        """
        # Default sanitization - subclasses can override
        return "An error occurred while processing your request"
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses.
        
        Returns:
            Dictionary with error information
        """
        return {
            "error": self.__class__.__name__,
            "message": self.user_message,
            "details": self.details
        }


# Financial Data Provider Errors

class FinancialDataError(CreditRatingSystemError):
    """Base exception for financial data retrieval errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to retrieve financial data"


class CompanyNotFoundError(FinancialDataError):
    """Exception raised when a company cannot be found."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Company not found. Please check the company name or ticker symbol"


class IncompleteDataError(FinancialDataError):
    """Exception raised when financial data is incomplete."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Financial data is incomplete. Some required information is missing"


class StaleDataError(FinancialDataError):
    """Exception raised when financial data is too old."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Financial data is outdated. The rating may not reflect current conditions"


class DataProviderUnavailableError(FinancialDataError):
    """Exception raised when financial data provider is unavailable."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Financial data service is temporarily unavailable. Please try again later"


class DataProviderRateLimitError(FinancialDataError):
    """Exception raised when rate limit is exceeded."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Too many requests. Please wait a moment and try again"


# Box Platform Errors

class BoxError(CreditRatingSystemError):
    """Base exception for Box platform errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to access document storage"


class BoxConnectionError(BoxError):
    """Exception raised when Box connection fails."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Document storage service is temporarily unavailable. Please try again later"


class BoxAuthenticationError(BoxError):
    """Exception raised when Box authentication fails."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Authentication with document storage failed. Please contact support"


class BoxFileNotFoundError(BoxError):
    """Exception raised when a Box file is not found."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Required document not found in storage"


class BoxUploadError(BoxError):
    """Exception raised when file upload to Box fails."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Failed to save document. Please try again"


class BoxPermissionError(BoxError):
    """Exception raised when Box permission is denied."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Insufficient permissions to access document"


# Box AI Errors

class BoxAIError(CreditRatingSystemError):
    """Base exception for Box AI errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to analyze documents"


class BoxAIUnavailableError(BoxAIError):
    """Exception raised when Box AI service is unavailable."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Document analysis service is temporarily unavailable. Please try again later"


class BoxAIResponseError(BoxAIError):
    """Exception raised when Box AI returns invalid response."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Document analysis produced invalid results. Please try again"


class BoxAITimeoutError(BoxAIError):
    """Exception raised when Box AI request times out."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Document analysis is taking longer than expected. Please try again"


# Rating Engine Errors

class RatingEngineError(CreditRatingSystemError):
    """Base exception for rating engine errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to calculate credit rating"


class RatingValidationError(RatingEngineError):
    """Exception raised when rating validation fails."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Rating calculation produced invalid results. Please try again"


class MethodologyError(RatingEngineError):
    """Exception raised when methodology cannot be loaded or applied."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to load rating methodology. Please contact support"


# Network and Retry Errors

class NetworkError(CreditRatingSystemError):
    """Base exception for network-related errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Network connection error. Please check your connection and try again"


class TimeoutError(NetworkError):
    """Exception raised when a request times out."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Request timed out. Please try again"


class RetryExhaustedError(NetworkError):
    """Exception raised when all retry attempts are exhausted."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Service is temporarily unavailable after multiple attempts. Please try again later"


# Validation Errors

class ValidationError(CreditRatingSystemError):
    """Base exception for validation errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Invalid input provided"


class InvalidCompanyIdentifierError(ValidationError):
    """Exception raised when company identifier is invalid."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Invalid company identifier. Please provide a valid company name or ticker symbol"


class InvalidRatingError(ValidationError):
    """Exception raised when rating value is invalid."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Invalid rating value"


# Database Errors

class DatabaseError(CreditRatingSystemError):
    """Base exception for database errors."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Database error occurred. Please try again"


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Unable to connect to database. Please try again later"


class RecordNotFoundError(DatabaseError):
    """Exception raised when a database record is not found."""
    
    def _sanitize_message(self, message: str) -> str:
        return "Requested record not found"
