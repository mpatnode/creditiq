"""Pytest configuration and fixtures."""
import pytest
from hypothesis import settings, Verbosity

# Configure Hypothesis
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
settings.load_profile("default")


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from app.main import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def db_session():
    """Create database session for testing."""
    from app.database import SessionLocal, Base, engine
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
