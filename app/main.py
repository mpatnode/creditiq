"""Main Flask application factory."""
import os
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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
    
    # Register blueprints/namespaces here
    # from app.routes import register_routes
    # register_routes(api)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
