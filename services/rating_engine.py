"""Rating Engine component for orchestrating credit rating workflow."""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from services.box_ai_service import (
    BoxAIService,
    BoxAIResponse,
    CreditRating,
    MetricBreakdown,
    BoxAIServiceError,
)
from services.financial_data_retriever import (
    FinancialDataRetriever,
    FinancialData,
    Company,
)
from services.methodology_loader import MethodologyLoader
from services.box_mcp_client import BoxMCPClient, BoxMCPToolError


logger = logging.getLogger(__name__)


class RatingEngineError(Exception):
    """Base exception for Rating Engine errors."""
    pass


class RatingValidationError(RatingEngineError):
    """Exception raised when rating validation fails."""
    pass


@dataclass
class SourceDocument:
    """Source document for rating archival."""
    type: str  # 'financial_statements', 'market_data', or 'methodology_snapshot'
    content: bytes
    file_name: str
    metadata: Dict[str, Any]


class FinancialMetrics(BaseModel):
    """Financial metrics used in rating calculation."""
    # Leverage ratios
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    
    # Profitability ratios
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    net_profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    
    # Liquidity ratios
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    
    # Efficiency ratios
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    
    # Market metrics
    market_cap: Optional[float] = None
    price_to_earnings: Optional[float] = None
    price_to_book: Optional[float] = None


class RatingResult(BaseModel):
    """Complete rating result with all details."""
    company_id: str = Field(..., description="Company identifier (CIK)")
    company_name: str = Field(..., description="Company name")
    ticker: str = Field(..., description="Company ticker symbol")
    rating: str = Field(..., description="Credit rating letter grade")
    score: float = Field(..., description="Numerical score (0-100)")
    metrics: FinancialMetrics = Field(..., description="Financial metrics used")
    breakdown: List[MetricBreakdown] = Field(default_factory=list, description="Detailed breakdown by category")
    timestamp: datetime = Field(default_factory=datetime.now, description="Rating generation timestamp")
    confidence: float = Field(default=1.0, description="Confidence score")
    source_documents: List[SourceDocument] = Field(default_factory=list, description="Source documents for archival")
    methodology_version: str = Field(..., description="Methodology version used")
    reasoning: str = Field(default="", description="Overall reasoning for the rating")
    
    class Config:
        arbitrary_types_allowed = True


class RatingEngine:
    """Orchestrates the credit rating calculation workflow.
    
    This engine coordinates financial data retrieval, methodology loading,
    Box AI invocation, and rating result validation.
    """

    def __init__(
        self,
        box_client: BoxMCPClient,
        financial_data_retriever: FinancialDataRetriever,
        methodology_loader: MethodologyLoader,
        box_ai_service: BoxAIService,
        temp_folder_id: str,
        methodology_file_id: str,
    ):
        """Initialize Rating Engine.
        
        Args:
            box_client: BoxMCPClient for Box operations
            financial_data_retriever: Service for retrieving financial data
            methodology_loader: Service for loading methodology
            box_ai_service: Service for Box AI operations
            temp_folder_id: Box folder ID for temporary files
            methodology_file_id: Box file ID for methodology PDF
        """
        self.box_client = box_client
        self.financial_data_retriever = financial_data_retriever
        self.methodology_loader = methodology_loader
        self.box_ai_service = box_ai_service
        self.temp_folder_id = temp_folder_id
        self.methodology_file_id = methodology_file_id
        
        logger.info("Initialized RatingEngine")

    async def calculate_rating(self, company: Company) -> RatingResult:
        """Calculate credit rating for a company.
        
        This method orchestrates the complete rating workflow:
        1. Retrieve financial data
        2. Prepare financial data document
        3. Upload to Box temporary folder
        4. Invoke Box AI with methodology and financial data
        5. Validate and parse results
        6. Prepare source documents for archival
        7. Clean up temporary files
        
        Args:
            company: Company to rate
            
        Returns:
            RatingResult with complete rating information
            
        Raises:
            RatingEngineError: If rating calculation fails
        """
        logger.info(f"Starting rating calculation for {company.name} ({company.ticker})")
        
        financial_data_file_id = None
        
        try:
            # Step 1: Retrieve financial data
            logger.info("Retrieving financial data...")
            financial_data = self.financial_data_retriever.get_company_data(company.ticker)
            
            # Validate data quality
            quality_report = self.financial_data_retriever.validate_data_quality(financial_data)
            if not quality_report.is_complete:
                logger.warning(f"Financial data incomplete: {quality_report.missing_fields}")
            if not quality_report.is_fresh:
                logger.warning(f"Financial data is {quality_report.data_age_days} days old")
            
            # Step 2: Prepare financial data document
            logger.info("Preparing financial data document...")
            financial_data_content = self._prepare_financial_data_document(financial_data)
            
            # Step 3: Upload financial data to Box temporary folder
            logger.info("Uploading financial data to Box...")
            file_name = f"financial_data_{company.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            upload_result = await self.box_client.upload_file(
                folder_id=self.temp_folder_id,
                file_name=file_name,
                content=financial_data_content
            )
            
            if not upload_result.success:
                raise RatingEngineError(f"Failed to upload financial data: {upload_result.error}")
            
            # Extract file ID from upload result
            financial_data_file_id = self._extract_file_id_from_upload(upload_result.data)
            logger.info(f"Financial data uploaded (file_id: {financial_data_file_id})")
            
            # Step 4: Invoke Box AI with methodology and financial data
            logger.info("Invoking Box AI for rating analysis...")
            box_ai_response = await self.box_ai_service.apply_methodology(
                methodology_file_id=self.methodology_file_id,
                financial_data_file_id=financial_data_file_id
            )
            
            # Step 5: Validate rating output
            logger.info("Validating rating output...")
            rating_result = self._validate_and_create_rating_result(
                box_ai_response=box_ai_response,
                company=company,
                financial_data=financial_data
            )
            
            # Step 6: Prepare source documents for archival
            logger.info("Preparing source documents...")
            source_documents = await self._prepare_source_documents(
                financial_data=financial_data,
                methodology_file_id=self.methodology_file_id
            )
            rating_result.source_documents = source_documents
            
            logger.info(
                f"Rating calculation complete: {rating_result.rating} "
                f"(score: {rating_result.score})"
            )
            
            return rating_result
            
        except BoxAIServiceError as e:
            logger.error(f"Box AI service error: {e}")
            raise RatingEngineError(f"Rating calculation failed: {e}") from e
        except BoxMCPToolError as e:
            logger.error(f"Box MCP tool error: {e}")
            raise RatingEngineError(f"Box operation failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in rating calculation: {e}")
            raise RatingEngineError(f"Rating calculation failed: {e}") from e
        finally:
            # Step 7: Clean up temporary financial data file
            if financial_data_file_id:
                await self._cleanup_temp_file(financial_data_file_id)

    def _prepare_financial_data_document(self, financial_data: FinancialData) -> bytes:
        """Prepare financial data document in JSON format.
        
        Args:
            financial_data: Financial data to format
            
        Returns:
            JSON document as bytes
        """
        # Convert financial data to dictionary
        data_dict = {
            "company_id": financial_data.company_id,
            "company_name": financial_data.company_name,
            "ticker": financial_data.ticker,
            "data_date": financial_data.data_date.isoformat(),
            "financial_statements": {
                "balance_sheet": financial_data.financial_statements.balance_sheet,
                "income_statement": financial_data.financial_statements.income_statement,
                "cash_flow_statement": financial_data.financial_statements.cash_flow_statement,
            },
            "market_data": financial_data.market_data,
        }
        
        # Convert to JSON with pretty formatting
        json_str = json.dumps(data_dict, indent=2, default=str)
        
        return json_str.encode('utf-8')

    def _extract_file_id_from_upload(self, upload_data: Any) -> str:
        """Extract file ID from Box upload result.
        
        Args:
            upload_data: Upload result data from Box MCP
            
        Returns:
            File ID string
            
        Raises:
            RatingEngineError: If file ID cannot be extracted
        """
        # Handle different response formats from MCP
        if isinstance(upload_data, list):
            # MCP might return content as list of text content blocks
            for item in upload_data:
                if hasattr(item, 'text'):
                    text = item.text
                elif isinstance(item, dict) and 'text' in item:
                    text = item['text']
                elif isinstance(item, str):
                    text = item
                else:
                    continue
                
                # Try to parse as JSON
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and 'id' in data:
                        return data['id']
                except json.JSONDecodeError:
                    # Try to extract file ID from text
                    import re
                    match = re.search(r'file[_\s]id[:\s]+([0-9]+)', text, re.IGNORECASE)
                    if match:
                        return match.group(1)
        
        elif isinstance(upload_data, dict):
            if 'id' in upload_data:
                return upload_data['id']
            if 'file_id' in upload_data:
                return upload_data['file_id']
        
        elif isinstance(upload_data, str):
            # Try to parse as JSON
            try:
                data = json.loads(upload_data)
                if isinstance(data, dict) and 'id' in data:
                    return data['id']
            except json.JSONDecodeError:
                pass
        
        # If we can't extract file ID, raise error
        raise RatingEngineError(
            f"Could not extract file ID from upload result: {upload_data}"
        )

    def _validate_and_create_rating_result(
        self,
        box_ai_response: BoxAIResponse,
        company: Company,
        financial_data: FinancialData
    ) -> RatingResult:
        """Validate Box AI response and create RatingResult.
        
        Args:
            box_ai_response: Response from Box AI
            company: Company being rated
            financial_data: Financial data used
            
        Returns:
            Validated RatingResult
            
        Raises:
            RatingValidationError: If validation fails
        """
        try:
            # Validate rating is valid
            valid_ratings = [r.value for r in CreditRating]
            if box_ai_response.rating not in valid_ratings:
                raise RatingValidationError(
                    f"Invalid rating '{box_ai_response.rating}'. "
                    f"Must be one of: {', '.join(valid_ratings)}"
                )
            
            # Validate score is in range
            if not 0 <= box_ai_response.score <= 100:
                raise RatingValidationError(
                    f"Score {box_ai_response.score} is outside valid range [0, 100]"
                )
            
            # Extract financial metrics from Box AI response
            financial_metrics = FinancialMetrics(**box_ai_response.metrics)
            
            # Create rating result
            rating_result = RatingResult(
                company_id=company.id,
                company_name=company.name,
                ticker=company.ticker,
                rating=box_ai_response.rating,
                score=box_ai_response.score,
                metrics=financial_metrics,
                breakdown=box_ai_response.breakdown,
                timestamp=datetime.now(),
                confidence=1.0,  # Default confidence
                methodology_version=self.methodology_file_id,
                reasoning=box_ai_response.reasoning,
            )
            
            return rating_result
            
        except ValidationError as e:
            logger.error(f"Rating validation failed: {e}")
            raise RatingValidationError(f"Invalid rating data: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in rating validation: {e}")
            raise RatingValidationError(f"Rating validation failed: {e}") from e

    async def _prepare_source_documents(
        self,
        financial_data: FinancialData,
        methodology_file_id: str
    ) -> List[SourceDocument]:
        """Prepare source documents for archival.
        
        Args:
            financial_data: Financial data used in rating
            methodology_file_id: Methodology file ID
            
        Returns:
            List of source documents
        """
        source_documents = []
        
        # 1. Financial statements snapshot
        financial_snapshot = self._prepare_financial_data_document(financial_data)
        source_documents.append(SourceDocument(
            type="financial_statements",
            content=financial_snapshot,
            file_name=f"financial_statements_{financial_data.ticker}_{datetime.now().strftime('%Y%m%d')}.json",
            metadata={
                "company_id": financial_data.company_id,
                "ticker": financial_data.ticker,
                "data_date": financial_data.data_date.isoformat(),
            }
        ))
        
        # 2. Market data snapshot
        market_data_json = json.dumps(financial_data.market_data, indent=2, default=str)
        source_documents.append(SourceDocument(
            type="market_data",
            content=market_data_json.encode('utf-8'),
            file_name=f"market_data_{financial_data.ticker}_{datetime.now().strftime('%Y%m%d')}.json",
            metadata={
                "company_id": financial_data.company_id,
                "ticker": financial_data.ticker,
            }
        ))
        
        # 3. Methodology snapshot
        try:
            methodology_content = self.methodology_loader.get_methodology_content()
            source_documents.append(SourceDocument(
                type="methodology_snapshot",
                content=methodology_content.encode('utf-8'),
                file_name=f"methodology_snapshot_{datetime.now().strftime('%Y%m%d')}.txt",
                metadata={
                    "methodology_file_id": methodology_file_id,
                }
            ))
        except Exception as e:
            logger.warning(f"Could not get methodology content for snapshot: {e}")
            # Continue without methodology snapshot
        
        return source_documents

    async def _cleanup_temp_file(self, file_id: str) -> None:
        """Clean up temporary file from Box.
        
        Args:
            file_id: Box file ID to delete
        """
        try:
            logger.info(f"Cleaning up temporary file {file_id}")
            # Note: Box MCP doesn't have a delete_file tool in the standard set
            # We'll log this for now, but in production you might want to:
            # 1. Use a separate cleanup job
            # 2. Set file retention policies on the temp folder
            # 3. Implement a custom delete tool
            logger.warning(
                f"Temporary file cleanup not implemented. "
                f"File {file_id} should be manually deleted or use folder retention policy."
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_id}: {e}")
            # Don't raise - cleanup failure shouldn't fail the rating
