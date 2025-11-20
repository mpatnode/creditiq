"""Unit tests for Flask application setup."""
import pytest


def test_app_creation(app):
    """Test that Flask application is created successfully."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_app_has_secret_key(app):
    """Test that application has a secret key configured."""
    assert 'SECRET_KEY' in app.config
    assert app.config['SECRET_KEY'] is not None


def test_client_creation(client):
    """Test that Flask test client is created successfully."""
    assert client is not None
