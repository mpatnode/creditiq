"""Methodology API endpoints."""
import logging
import asyncio
from flask_restx import Namespace, Resource, fields

from services.methodology_loader import MethodologyLoader, MethodologyLoaderError
from services.box_mcp_client import BoxMCPClient
from app.config import Config


logger = logging.getLogger(__name__)

# Create namespace
methodology_ns = Namespace('methodology', description='Methodology information')

# Define API models
methodology_info_model = methodology_ns.model('MethodologyInfo', {
    'file_id': fields.String(required=True, description='Box file ID of methodology'),
    'version': fields.String(description='Methodology version'),
    'content_preview': fields.String(description='Preview of methodology content'),
    'is_cached': fields.Boolean(description='Whether content is cached'),
})

error_model = methodology_ns.model('Error', {
    'error': fields.String(required=True, description='Error message'),
    'details': fields.String(description='Additional error details'),
})


@methodology_ns.route('')
class MethodologyInfo(Resource):
    """Methodology information endpoint."""
    
    @methodology_ns.doc('get_methodology_info')
    @methodology_ns.response(200, 'Success', methodology_info_model)
    @methodology_ns.response(500, 'Internal server error', error_model)
    def get(self):
        """Get information about the credit rating methodology.
        
        Validates: Requirements 2.4, 3.1
        """
        try:
            logger.info("Retrieving methodology information")
            
            # Get configuration
            config = Config()
            
            # Initialize Box MCP client
            box_client = BoxMCPClient()
            
            # Initialize methodology loader
            methodology_loader = MethodologyLoader(
                box_client=box_client,
                methodology_file_id=config.BOX_METHODOLOGY_FOLDER_ID
            )
            
            # Get methodology content if not cached
            if not methodology_loader.is_cached:
                logger.info("Loading methodology from Box")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content = loop.run_until_complete(
                        methodology_loader.load_pdf_from_box()
                    )
                finally:
                    loop.close()
            else:
                content = methodology_loader.get_methodology_content()
            
            # Create preview (first 500 characters)
            preview = content[:500] + "..." if len(content) > 500 else content
            
            logger.info("Methodology information retrieved successfully")
            
            return {
                'file_id': config.BOX_METHODOLOGY_FOLDER_ID,
                'version': config.BOX_METHODOLOGY_FOLDER_ID,  # Using file ID as version
                'content_preview': preview,
                'is_cached': methodology_loader.is_cached,
            }, 200
            
        except MethodologyLoaderError as e:
            logger.error(f"Methodology loader error: {e}", exc_info=True)
            return {
                'error': 'Failed to load methodology',
                'details': 'An error occurred while loading the methodology'
            }, 500
        except Exception as e:
            logger.error(f"Unexpected error retrieving methodology: {e}", exc_info=True)
            return {
                'error': 'Internal server error',
                'details': 'An unexpected error occurred'
            }, 500
