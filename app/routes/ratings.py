"""Ratings API endpoints."""
import logging
import asyncio
from flask import request
from flask_restx import Namespace, Resource, fields

from services.rating_engine import RatingEngine, RatingEngineError
from services.rating_storage import RatingStorage, RatingStorageError
from services.financial_data_retriever import FinancialDataRetriever, Company
from services.box_mcp_client import BoxMCPClient
from services.box_ai_service import BoxAIService
from services.methodology_loader import MethodologyLoader
from app.database import get_db_session
from app.config import Config


logger = logging.getLogger(__name__)

# Create namespace
ratings_ns = Namespace('ratings', description='Credit rating operations')

# Define API models
metric_breakdown_model = ratings_ns.model('MetricBreakdown', {
    'category': fields.String(required=True, description='Metric category'),
    'weight': fields.Float(required=True, description='Category weight'),
    'score': fields.Float(required=True, description='Category score'),
    'metrics': fields.Raw(description='Detailed metrics'),
    'reasoning': fields.String(description='Reasoning for the score'),
})

financial_metrics_model = ratings_ns.model('FinancialMetrics', {
    'debt_to_equity': fields.Float(description='Debt to equity ratio'),
    'debt_to_assets': fields.Float(description='Debt to assets ratio'),
    'interest_coverage': fields.Float(description='Interest coverage ratio'),
    'return_on_equity': fields.Float(description='Return on equity'),
    'return_on_assets': fields.Float(description='Return on assets'),
    'net_profit_margin': fields.Float(description='Net profit margin'),
    'operating_margin': fields.Float(description='Operating margin'),
    'current_ratio': fields.Float(description='Current ratio'),
    'quick_ratio': fields.Float(description='Quick ratio'),
    'cash_ratio': fields.Float(description='Cash ratio'),
    'asset_turnover': fields.Float(description='Asset turnover'),
    'inventory_turnover': fields.Float(description='Inventory turnover'),
    'market_cap': fields.Float(description='Market capitalization'),
    'price_to_earnings': fields.Float(description='Price to earnings ratio'),
    'price_to_book': fields.Float(description='Price to book ratio'),
})

rating_result_model = ratings_ns.model('RatingResult', {
    'id': fields.Integer(description='Database rating ID'),
    'company_id': fields.String(required=True, description='Company CIK identifier'),
    'company_name': fields.String(required=True, description='Company name'),
    'ticker': fields.String(required=True, description='Ticker symbol'),
    'rating': fields.String(required=True, description='Credit rating (e.g., AAA, AA, A)'),
    'score': fields.Float(required=True, description='Numerical score (0-100)'),
    'confidence': fields.Float(description='Confidence score'),
    'timestamp': fields.DateTime(required=True, description='Rating generation timestamp'),
    'methodology_version': fields.String(required=True, description='Methodology version used'),
    'reasoning': fields.String(description='Overall reasoning'),
    'metrics': fields.Nested(financial_metrics_model, description='Financial metrics'),
    'breakdown': fields.List(fields.Nested(metric_breakdown_model), description='Detailed breakdown'),
    'box_folder_id': fields.String(description='Box folder ID for rating package'),
    'box_report_file_id': fields.String(description='Box file ID for rating report'),
})

generate_request_model = ratings_ns.model('GenerateRequest', {
    'company_id': fields.String(description='Company CIK identifier'),
    'ticker': fields.String(description='Company ticker symbol'),
})

generate_response_model = ratings_ns.model('GenerateResponse', {
    'rating': fields.Nested(rating_result_model),
    'message': fields.String(description='Success message'),
})

history_response_model = ratings_ns.model('HistoryResponse', {
    'ratings': fields.List(fields.Nested(rating_result_model)),
    'count': fields.Integer(description='Number of historical ratings'),
})

error_model = ratings_ns.model('Error', {
    'error': fields.String(required=True, description='Error message'),
    'details': fields.String(description='Additional error details'),
})


def _get_services():
    """Initialize and return service instances.
    
    Returns:
        Tuple of (rating_engine, rating_storage, financial_data_retriever)
    """
    # Get configuration
    config = Config()
    
    # Initialize Box MCP client
    box_client = BoxMCPClient()
    
    # Initialize services
    financial_data_retriever = FinancialDataRetriever(
        timeout=config.REQUEST_TIMEOUT,
        max_retries=config.MAX_RETRIES,
        data_age_threshold_months=config.DATA_AGE_THRESHOLD_MONTHS
    )
    
    methodology_loader = MethodologyLoader(
        box_client=box_client,
        methodology_file_id=config.BOX_METHODOLOGY_FOLDER_ID
    )
    
    box_ai_service = BoxAIService(box_client=box_client)
    
    rating_engine = RatingEngine(
        box_client=box_client,
        financial_data_retriever=financial_data_retriever,
        methodology_loader=methodology_loader,
        box_ai_service=box_ai_service,
        temp_folder_id=config.BOX_RATINGS_FOLDER_ID,  # Use ratings folder as temp
        methodology_file_id=config.BOX_METHODOLOGY_FOLDER_ID
    )
    
    db_session = get_db_session()
    
    rating_storage = RatingStorage(
        db_session=db_session,
        box_client=box_client,
        ratings_root_folder_id=config.BOX_RATINGS_FOLDER_ID
    )
    
    return rating_engine, rating_storage, financial_data_retriever


@ratings_ns.route('/generate')
class RatingGenerate(Resource):
    """Rating generation endpoint."""
    
    @ratings_ns.doc('generate_rating')
    @ratings_ns.expect(generate_request_model)
    @ratings_ns.response(200, 'Success', generate_response_model)
    @ratings_ns.response(400, 'Invalid request', error_model)
    @ratings_ns.response(404, 'Company not found', error_model)
    @ratings_ns.response(500, 'Internal server error', error_model)
    def post(self):
        """Generate a credit rating for a company.
        
        Validates: Requirements 1.1, 1.2, 2.1, 2.2, 2.3
        """
        try:
            # Get request data
            data = request.get_json()
            
            if not data:
                return {
                    'error': 'Missing request body',
                    'details': 'Request must include company_id or ticker'
                }, 400
            
            company_id = data.get('company_id')
            ticker = data.get('ticker')
            
            if not company_id and not ticker:
                return {
                    'error': 'Missing required field',
                    'details': 'Request must include either company_id or ticker'
                }, 400
            
            identifier = ticker if ticker else company_id
            
            logger.info(f"Generating rating for company: {identifier}")
            
            # Initialize services
            rating_engine, rating_storage, financial_data_retriever = _get_services()
            
            # Search for company
            companies = financial_data_retriever.search_companies(identifier)
            
            if not companies:
                return {
                    'error': 'Company not found',
                    'details': f'No company found matching: {identifier}'
                }, 404
            
            # Use first match
            company = companies[0]
            
            logger.info(f"Found company: {company.name} ({company.ticker})")
            
            # Generate rating (async operation)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                rating_result = loop.run_until_complete(
                    rating_engine.calculate_rating(company)
                )
            finally:
                loop.close()
            
            logger.info(f"Rating generated: {rating_result.rating}")
            
            # Save rating to database
            db_rating = rating_storage.save_rating(rating_result)
            
            # Upload rating package to Box (async operation)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                package_info = loop.run_until_complete(
                    rating_storage.save_rating_package_to_box(
                        rating=rating_result,
                        company_id=company.id,
                        source_documents=rating_result.source_documents
                    )
                )
            finally:
                loop.close()
            
            # Update rating with Box information
            db_rating = rating_storage.update_rating_with_box_info(
                rating_id=db_rating.id,
                package_info=package_info
            )
            
            logger.info(f"Rating saved successfully (ID: {db_rating.id})")
            
            return {
                'rating': db_rating.to_dict(),
                'message': f'Credit rating generated successfully: {rating_result.rating}'
            }, 200
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {
                'error': 'Invalid input',
                'details': str(e)
            }, 400
        except RatingEngineError as e:
            logger.error(f"Rating engine error: {e}", exc_info=True)
            return {
                'error': 'Failed to generate rating',
                'details': 'An error occurred during rating calculation'
            }, 500
        except RatingStorageError as e:
            logger.error(f"Rating storage error: {e}", exc_info=True)
            return {
                'error': 'Failed to save rating',
                'details': 'An error occurred while saving the rating'
            }, 500
        except Exception as e:
            logger.error(f"Unexpected error generating rating: {e}", exc_info=True)
            return {
                'error': 'Internal server error',
                'details': 'An unexpected error occurred'
            }, 500


@ratings_ns.route('/history/<string:company_id>')
class RatingHistory(Resource):
    """Historical ratings endpoint."""
    
    @ratings_ns.doc('get_rating_history')
    @ratings_ns.response(200, 'Success', history_response_model)
    @ratings_ns.response(404, 'Company not found', error_model)
    @ratings_ns.response(500, 'Internal server error', error_model)
    def get(self, company_id: str):
        """Get historical ratings for a company.
        
        Validates: Requirements 6.2, 6.3, 6.4
        
        Args:
            company_id: Company CIK identifier
        """
        try:
            logger.info(f"Retrieving historical ratings for company: {company_id}")
            
            # Initialize rating storage
            _, rating_storage, _ = _get_services()
            
            # Get historical ratings
            ratings = rating_storage.get_historical_ratings(company_id)
            
            if not ratings:
                logger.info(f"No ratings found for company: {company_id}")
                return {
                    'ratings': [],
                    'count': 0
                }, 200
            
            # Convert to dict format
            ratings_data = [rating.to_dict() for rating in ratings]
            
            logger.info(f"Retrieved {len(ratings_data)} historical ratings")
            
            return {
                'ratings': ratings_data,
                'count': len(ratings_data)
            }, 200
            
        except RatingStorageError as e:
            logger.error(f"Rating storage error: {e}", exc_info=True)
            return {
                'error': 'Failed to retrieve ratings',
                'details': 'An error occurred while retrieving historical ratings'
            }, 500
        except Exception as e:
            logger.error(f"Unexpected error retrieving ratings: {e}", exc_info=True)
            return {
                'error': 'Internal server error',
                'details': 'An unexpected error occurred'
            }, 500
