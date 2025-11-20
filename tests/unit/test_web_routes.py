"""Unit tests for web routes."""
import pytest
from flask import Flask
from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """Test index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Company Credit Rating System' in response.data


def test_search_route(client):
    """Test search page loads."""
    response = client.get('/search')
    assert response.status_code == 200
    assert b'Search Companies' in response.data


def test_rating_route(client):
    """Test rating page loads."""
    response = client.get('/rating')
    assert response.status_code == 200


def test_history_route(client):
    """Test history page loads."""
    response = client.get('/history')
    assert response.status_code == 200


def test_methodology_route(client):
    """Test methodology page loads."""
    response = client.get('/methodology')
    assert response.status_code == 200
    assert b'Credit Rating Methodology' in response.data
