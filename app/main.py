"""Main Flask application factory."""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api
from dotenv import load_dotenv

from app.logging_config import setup_logging
from app.exceptions import CreditRatingSystemError

# Load environment variables
load_dotenv()

# Set up logging
setup_logging()

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Enable CORS
    CORS(app)
    
    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='1.0',
        title='Company Credit Rating API',
        description='API for generating credit ratings for public companies',
        doc='/api/docs'
    )
    
    # Register blueprints/namespaces
    from app.routes import register_routes
    register_routes(api)
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Flask application created successfully")
    
    return app


def register_error_handlers(app: Flask) -> None:
    """Register custom error handlers.
    
    Args:
        app: Flask application instance
    """
    @app.errorhandler(CreditRatingSystemError)
    def handle_credit_rating_error(error: CreditRatingSystemError):
        """Handle custom Credit Rating System errors."""
        logger.error(
            f"{error.__class__.__name__}: {error.message}",
            extra={"details": error.details}
        )
        
        # Return sanitized user-facing message
        response = error.to_dict()
        
        # Determine HTTP status code based on error type
        status_code = 500
        
        # Import specific error types to determine status codes
        from app.exceptions import (
            CompanyNotFoundError,
            ValidationError,
            DataProviderUnavailableError,
            BoxConnectionError,
            NetworkError,
        )
        
        if isinstance(error, (CompanyNotFoundError,)):
            status_code = 404
        elif isinstance(error, (ValidationError,)):
            status_code = 400
        elif isinstance(error, (DataProviderUnavailableError, BoxConnectionError, NetworkError)):
            status_code = 503
        
        return jsonify(response), status_code
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        logger.warning(f"404 error: {error}")
        return jsonify({
            'error': 'NotFound',
            'message': 'The requested resource was not found',
            'details': {}
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"500 error: {error}", exc_info=True)
        return jsonify({
            'error': 'InternalServerError',
            'message': 'An unexpected error occurred. Please try again later.',
            'details': {}
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # Don't expose internal error details to users
        return jsonify({
            'error': 'InternalServerError',
            'message': 'An unexpected error occurred. Please try again later.',
            'details': {}
        }), 500


if __name__ == '__main__':
    app = create_app()
    logger.info("Starting Flask development server")
    app.run(debug=True, host='0.0.0.0', port=5000)
