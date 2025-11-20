"""Companies API endpoints."""
import logging
from flask import request
from flask_restx import Namespace, Resource, fields

from services.financial_data_retriever import FinancialDataRetriever


logger = logging.getLogger(__name__)

# Create namespace
companies_ns = Namespace('companies', description='Company search operations')

# Define API models for request/response validation
company_model = companies_ns.model('Company', {
    'id': fields.String(required=True, description='Company CIK identifier'),
    'name': fields.String(required=True, description='Company name'),
    'ticker': fields.String(required=True, description='Ticker symbol'),
    'exchange': fields.String(description='Stock exchange'),
    'sector': fields.String(description='Business sector'),
    'industry': fields.String(description='Industry classification'),
})

search_request_model = companies_ns.model('SearchRequest', {
    'query': fields.String(required=True, description='Company name or ticker to search'),
})

search_response_model = companies_ns.model('SearchResponse', {
    'companies': fields.List(fields.Nested(company_model)),
    'count': fields.Integer(description='Number of results'),
})

error_model = companies_ns.model('Error', {
    'error': fields.String(required=True, description='Error message'),
    'details': fields.String(description='Additional error details'),
})


@companies_ns.route('/search')
class CompanySearch(Resource):
    """Company search endpoint."""
    
    @companies_ns.doc('search_companies')
    @companies_ns.expect(search_request_model)
    @companies_ns.response(200, 'Success', search_response_model)
    @companies_ns.response(400, 'Invalid request', error_model)
    @companies_ns.response(500, 'Internal server error', error_model)
    def post(self):
        """Search for companies by name or ticker.
        
        Validates: Requirements 1.1, 5.1, 5.2, 5.3, 5.4
        """
        try:
            # Get request data
            data = request.get_json()
            
            if not data or 'query' not in data:
                return {
                    'error': 'Missing required field: query',
                    'details': 'Request must include a query field'
                }, 400
            
            query = data['query'].strip()
            
            if not query:
                return {
                    'error': 'Invalid query',
                    'details': 'Query cannot be empty'
                }, 400
            
            logger.info(f"Searching for companies with query: {query}")
            
            # Create financial data retriever
            retriever = FinancialDataRetriever()
            
            # Search for companies
            companies = retriever.search_companies(query)
            
            # Convert to dict format
            companies_data = [
                {
                    'id': company.id,
                    'name': company.name,
                    'ticker': company.ticker,
                    'exchange': company.exchange,
                    'sector': company.sector,
                    'industry': company.industry,
                }
                for company in companies
            ]
            
            logger.info(f"Found {len(companies_data)} matching companies")
            
            return {
                'companies': companies_data,
                'count': len(companies_data),
            }, 200
            
        except Exception as e:
            logger.error(f"Error searching companies: {e}", exc_info=True)
            return {
                'error': 'Failed to search companies',
                'details': 'An internal error occurred while searching'
            }, 500
