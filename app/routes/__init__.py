"""API routes package."""
from flask_restx import Api

from app.routes.companies import companies_ns
from app.routes.ratings import ratings_ns
from app.routes.methodology import methodology_ns


def register_routes(api: Api) -> None:
    """Register all API namespaces.
    
    Args:
        api: Flask-RESTX Api instance
    """
    api.add_namespace(companies_ns, path='/companies')
    api.add_namespace(ratings_ns, path='/ratings')
    api.add_namespace(methodology_ns, path='/methodology')
