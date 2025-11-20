"""Application configuration."""
import os
from typing import Optional


class Config:
    """Base configuration class."""
    
    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://localhost/credit_rating_db')
    
    # Box MCP
    BOX_MCP_SERVER_PATH: Optional[str] = os.getenv('BOX_MCP_SERVER_PATH')
    BOX_CLIENT_ID: Optional[str] = os.getenv('BOX_CLIENT_ID')
    BOX_CLIENT_SECRET: Optional[str] = os.getenv('BOX_CLIENT_SECRET')
    BOX_ENTERPRISE_ID: Optional[str] = os.getenv('BOX_ENTERPRISE_ID')
    BOX_METHODOLOGY_FOLDER_ID: Optional[str] = os.getenv('BOX_METHODOLOGY_FOLDER_ID')
    BOX_RATINGS_FOLDER_ID: Optional[str] = os.getenv('BOX_RATINGS_FOLDER_ID')
    
    # LLM
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    LLM_MODEL: str = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
    LLM_TEMPERATURE: float = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    LLM_MAX_TOKENS: int = int(os.getenv('LLM_MAX_TOKENS', '4000'))
    LLM_TIMEOUT: int = int(os.getenv('LLM_TIMEOUT', '60'))
    
    # Financial Data Provider
    FINANCIAL_DATA_PROVIDER: str = os.getenv('FINANCIAL_DATA_PROVIDER', 'sec_edgar')
    # SEC EDGAR requires User-Agent with contact info
    SEC_USER_AGENT: str = os.getenv('SEC_USER_AGENT', 'CompanyCreditRating/1.0 (contact@example.com)')
    
    # Application Settings
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF_FACTOR: int = int(os.getenv('RETRY_BACKOFF_FACTOR', '2'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    DATA_AGE_THRESHOLD_MONTHS: int = int(os.getenv('DATA_AGE_THRESHOLD_MONTHS', '12'))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestConfig(Config):
    """Test configuration."""
    TESTING = True
    DATABASE_URL = 'postgresql://localhost/credit_rating_test_db'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
    'default': DevelopmentConfig
}
