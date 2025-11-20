"""Box AI Service for applying credit rating methodology using Box AI."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from services.box_mcp_client import BoxMCPClient, BoxMCPToolError
from app.exceptions import (
    BoxAIError,
    BoxAIUnavailableError,
    BoxAIResponseError,
    BoxAITimeoutError,
    RetryExhaustedError,
)


logger = logging.getLogger(__name__)


# Keep legacy exceptions for backward compatibility
class BoxAIServiceError(BoxAIError):
    """Base exception for Box AI Service errors."""
    pass


class BoxAIResponseParsingError(BoxAIResponseError):
    """Exception raised when Box AI response cannot be parsed."""
    pass


class CreditRating(str, Enum):
    """Credit rating letter grades."""
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    CCC_PLUS = "CCC+"
    CCC = "CCC"
    CCC_MINUS = "CCC-"
    CC = "CC"
    C = "C"
    D = "D"


class MetricBreakdown(BaseModel):
    """Breakdown of a single metric category."""
    category: str = Field(..., description="Category name (e.g., 'Leverage', 'Profitability')")
    weight: float = Field(..., description="Weight of this category in overall rating")
    score: float = Field(..., description="Score for this category")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Individual metrics in this category")
    reasoning: str = Field(default="", description="Explanation for the score")


class BoxAIResponse(BaseModel):
    """Structured response from Box AI rating analysis."""
    rating: str = Field(..., description="Credit rating letter grade")
    score: float = Field(..., description="Numerical score (0-100)")
    reasoning: str = Field(..., description="Overall reasoning for the rating")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Key financial metrics used")
    breakdown: List[MetricBreakdown] = Field(default_factory=list, description="Detailed breakdown by category")
    raw_response: str = Field(default="", description="Raw response from Box AI")
    completion_reason: str = Field(default="done", description="Completion reason from Box AI")


class StructuredMethodology(BaseModel):
    """Structured methodology format extracted from PDF."""
    version: str = Field(..., description="Methodology version")
    categories: List[Dict[str, Any]] = Field(default_factory=list, description="Methodology categories")
    rating_thresholds: List[Dict[str, Any]] = Field(default_factory=list, description="Rating thresholds")


class BoxAIService:
    """Interface with Box AI via MCP for methodology application.
    
    This service uses Box AI to analyze credit rating methodology PDFs
    and apply them to company financial data to generate credit ratings.
    """

    def __init__(self, box_client: BoxMCPClient):
        """Initialize Box AI service with Box MCP client.
        
        Args:
            box_client: BoxMCPClient instance for Box operations
        """
        self.box_client = box_client
        logger.info("Initialized BoxAIService")

    async def apply_methodology(
        self,
        methodology_file_id: str,
        financial_data_file_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> BoxAIResponse:
        """Apply methodology to financial data using Box AI.
        
        Uses Box AI to analyze the methodology PDF and financial data
        document to generate a credit rating.
        
        Args:
            methodology_file_id: Box file ID of the methodology PDF
            financial_data_file_id: Box file ID of the financial data document
            options: Optional configuration for Box AI query
            
        Returns:
            BoxAIResponse with rating, score, and detailed breakdown
            
        Raises:
            BoxAIServiceError: If Box AI query fails
            BoxAIResponseParsingError: If response cannot be parsed
        """
        logger.info(
            f"Applying methodology (file_id: {methodology_file_id}) "
            f"to financial data (file_id: {financial_data_file_id})"
        )
        
        # Construct prompt for Box AI
        prompt = self._construct_rating_prompt(options)
        
        # Query Box AI with both documents
        file_ids = [methodology_file_id, financial_data_file_id]
        
        try:
            result = await self.ask_box_ai(
                file_ids=file_ids,
                prompt=prompt,
                mode="multiple_item_qa"
            )
            
            # Parse and validate the response
            box_ai_response = self._parse_rating_response(result)
            
            logger.info(
                f"Successfully generated rating: {box_ai_response.rating} "
                f"(score: {box_ai_response.score})"
            )
            
            return box_ai_response
            
        except (BoxAIResponseParsingError, BoxAIUnavailableError, BoxAITimeoutError):
            raise
        except BoxMCPToolError as e:
            logger.error(f"Box AI query failed: {e}", exc_info=True)
            raise BoxAIServiceError(
                message=f"Failed to apply methodology: {e}",
                user_message="Unable to analyze documents. Please try again.",
                details={"methodology_file_id": methodology_file_id, "financial_data_file_id": financial_data_file_id}
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in apply_methodology: {e}", exc_info=True)
            raise BoxAIServiceError(
                message=f"Methodology application failed: {e}",
                user_message="Unable to calculate rating. Please try again.",
                details={"methodology_file_id": methodology_file_id, "financial_data_file_id": financial_data_file_id}
            ) from e

    def _construct_rating_prompt(self, options: Optional[Dict[str, Any]] = None) -> str:
        """Construct prompt for Box AI rating analysis.
        
        Args:
            options: Optional configuration for customizing the prompt
            
        Returns:
            Formatted prompt string for Box AI
        """
        prompt = """You are a credit rating analyst. Analyze the provided credit rating methodology document and the company's financial data to generate a comprehensive credit rating.

Please provide your analysis in the following JSON format:

{
  "rating": "<letter grade: AAA, AA+, AA, AA-, A+, A, A-, BBB+, BBB, BBB-, BB+, BB, BB-, B+, B, B-, CCC+, CCC, CCC-, CC, C, or D>",
  "score": <numerical score from 0 to 100>,
  "reasoning": "<overall explanation for the rating>",
  "metrics": {
    "<metric_name>": <value>,
    ...
  },
  "breakdown": [
    {
      "category": "<category name>",
      "weight": <weight as decimal, e.g., 0.3 for 30%>,
      "score": <category score 0-100>,
      "metrics": {
        "<metric_name>": <value>
      },
      "reasoning": "<explanation for this category>"
    },
    ...
  ]
}

Instructions:
1. Review the methodology document to understand the rating criteria, formulas, and thresholds
2. Extract relevant financial metrics from the company's financial data
3. Apply the methodology rules to calculate scores for each category
4. Determine the overall rating based on the methodology's rating thresholds
5. Provide detailed reasoning for your assessment

Ensure your response is valid JSON and includes all required fields."""

        # Allow customization via options
        if options and "additional_instructions" in options:
            prompt += f"\n\nAdditional instructions: {options['additional_instructions']}"
        
        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((BoxAIServiceError, BoxAIUnavailableError)),
    )
    async def ask_box_ai(
        self,
        file_ids: List[str],
        prompt: str,
        mode: str = "multiple_item_qa"
    ) -> Dict[str, Any]:
        """Ask Box AI a question about one or more documents.
        
        Args:
            file_ids: List of Box file IDs to query
            prompt: Question or instruction for Box AI
            mode: Query mode - "single_item_qa" or "multiple_item_qa"
            
        Returns:
            Dictionary containing Box AI response
            
        Raises:
            BoxAIServiceError: If Box AI query fails
            BoxAIUnavailableError: If Box AI service is unavailable
            BoxAITimeoutError: If Box AI request times out
            RetryExhaustedError: If all retries are exhausted
        """
        logger.debug(f"Querying Box AI with {len(file_ids)} file(s), mode: {mode}")
        
        try:
            result = await self.box_client.box_ai_ask(
                file_ids=file_ids,
                prompt=prompt,
                mode=mode
            )
            
            if not result.success:
                error_msg = result.error or "Unknown error"
                
                # Check for specific error types
                if "timeout" in error_msg.lower():
                    raise BoxAITimeoutError(
                        message=f"Box AI request timed out: {error_msg}",
                        user_message="Document analysis is taking longer than expected. Please try again.",
                        details={"file_ids": file_ids}
                    )
                elif "unavailable" in error_msg.lower() or "503" in error_msg:
                    raise BoxAIUnavailableError(
                        message=f"Box AI service unavailable: {error_msg}",
                        user_message="Document analysis service is temporarily unavailable. Please try again later.",
                        details={"file_ids": file_ids}
                    )
                
                raise BoxAIServiceError(
                    message=f"Box AI query failed: {error_msg}",
                    user_message="Unable to analyze documents. Please try again.",
                    details={"file_ids": file_ids}
                )
            
            # Extract response content
            response_data = self._extract_response_content(result.data)
            
            logger.debug("Box AI query completed successfully")
            
            return response_data
            
        except (BoxAITimeoutError, BoxAIUnavailableError, BoxAIServiceError):
            raise
        except RetryError as e:
            logger.error(f"Box AI query failed after all retries: {e}", exc_info=True)
            raise RetryExhaustedError(
                message=f"Box AI query failed after multiple attempts: {e}",
                user_message="Document analysis service is temporarily unavailable after multiple attempts. Please try again later.",
                details={"file_ids": file_ids, "max_attempts": 3}
            ) from e
        except BoxMCPToolError as e:
            logger.error(f"Box AI tool execution failed: {e}", exc_info=True)
            raise BoxAIServiceError(
                message=f"Box AI query failed: {e}",
                user_message="Unable to analyze documents. Please try again.",
                details={"file_ids": file_ids}
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in Box AI query: {e}", exc_info=True)
            raise BoxAIServiceError(
                message=f"Unexpected Box AI error: {e}",
                user_message="Unable to analyze documents. Please try again.",
                details={"file_ids": file_ids}
            ) from e

    def _extract_response_content(self, data: Any) -> Dict[str, Any]:
        """Extract content from Box AI response data.
        
        Args:
            data: Raw response data from Box MCP
            
        Returns:
            Dictionary with extracted content
        """
        # Handle different response formats from MCP
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            # MCP might return content as list of text content blocks
            content_text = ""
            for item in data:
                if hasattr(item, 'text'):
                    content_text += item.text
                elif isinstance(item, dict) and 'text' in item:
                    content_text += item['text']
                elif isinstance(item, str):
                    content_text += item
            
            return {
                "answer": content_text,
                "completion_reason": "done"
            }
        elif isinstance(data, str):
            return {
                "answer": data,
                "completion_reason": "done"
            }
        else:
            return {
                "answer": str(data),
                "completion_reason": "done"
            }

    def _parse_rating_response(self, response_data: Dict[str, Any]) -> BoxAIResponse:
        """Parse and validate Box AI response into structured format.
        
        Args:
            response_data: Raw response data from Box AI
            
        Returns:
            Validated BoxAIResponse object
            
        Raises:
            BoxAIResponseParsingError: If response cannot be parsed or validated
        """
        try:
            # Extract the answer text from response
            answer_text = response_data.get("answer", "")
            completion_reason = response_data.get("completion_reason", "done")
            
            if not answer_text:
                logger.error("Empty response from Box AI")
                raise BoxAIResponseParsingError(
                    message="Empty response from Box AI",
                    user_message="Document analysis produced no results. Please try again.",
                    details={}
                )
            
            # Try to extract JSON from the response
            # Box AI might wrap JSON in markdown code blocks
            json_str = self._extract_json_from_text(answer_text)
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Box AI response: {e}")
                logger.debug(f"Response text: {answer_text[:500]}")
                raise BoxAIResponseParsingError(
                    message=f"Invalid JSON in Box AI response: {e}",
                    user_message="Document analysis produced invalid results. Please try again.",
                    details={"error": str(e)}
                ) from e
            
            # Validate required fields
            if "rating" not in parsed_data:
                logger.error("Missing 'rating' field in Box AI response")
                raise BoxAIResponseParsingError(
                    message="Missing 'rating' field in response",
                    user_message="Document analysis is incomplete. Please try again.",
                    details={}
                )
            if "score" not in parsed_data:
                logger.error("Missing 'score' field in Box AI response")
                raise BoxAIResponseParsingError(
                    message="Missing 'score' field in response",
                    user_message="Document analysis is incomplete. Please try again.",
                    details={}
                )
            
            # Parse breakdown if present
            breakdown = []
            if "breakdown" in parsed_data and isinstance(parsed_data["breakdown"], list):
                for item in parsed_data["breakdown"]:
                    try:
                        breakdown.append(MetricBreakdown(**item))
                    except ValidationError as e:
                        logger.warning(f"Failed to parse breakdown item: {e}")
                        # Continue with other items
            
            # Create BoxAIResponse
            box_ai_response = BoxAIResponse(
                rating=parsed_data["rating"],
                score=float(parsed_data["score"]),
                reasoning=parsed_data.get("reasoning", ""),
                metrics=parsed_data.get("metrics", {}),
                breakdown=breakdown,
                raw_response=answer_text,
                completion_reason=completion_reason
            )
            
            # Validate rating is a valid credit rating
            self._validate_rating(box_ai_response.rating)
            
            # Validate score is in valid range
            if not 0 <= box_ai_response.score <= 100:
                logger.error(f"Score {box_ai_response.score} is outside valid range")
                raise BoxAIResponseParsingError(
                    message=f"Score {box_ai_response.score} is outside valid range [0, 100]",
                    user_message="Document analysis produced invalid score. Please try again.",
                    details={"score": box_ai_response.score}
                )
            
            return box_ai_response
            
        except BoxAIResponseParsingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing Box AI response: {e}", exc_info=True)
            raise BoxAIResponseParsingError(
                message=f"Failed to parse Box AI response: {e}",
                user_message="Document analysis produced invalid results. Please try again.",
                details={"error": str(e)}
            ) from e

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON string from text that might contain markdown or other formatting.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON string
            
        Raises:
            BoxAIResponseParsingError: If no JSON found
        """
        # Try to find JSON in markdown code blocks
        import re
        
        # Look for ```json ... ``` or ``` ... ```
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_block_pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Look for JSON object starting with { and ending with }
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Return the longest match (likely the complete JSON)
            return max(matches, key=len)
        
        # If no JSON found, return the original text and let JSON parser fail
        return text.strip()

    def _validate_rating(self, rating: str) -> None:
        """Validate that rating is a valid credit rating.
        
        Args:
            rating: Rating string to validate
            
        Raises:
            BoxAIResponseParsingError: If rating is invalid
        """
        valid_ratings = [r.value for r in CreditRating]
        if rating not in valid_ratings:
            logger.error(f"Invalid credit rating: {rating}")
            raise BoxAIResponseParsingError(
                message=f"Invalid credit rating '{rating}'. Must be one of: {', '.join(valid_ratings)}",
                user_message="Document analysis produced invalid rating. Please try again.",
                details={"rating": rating, "valid_ratings": valid_ratings}
            )

    async def extract_structured_data(
        self,
        file_id: str,
        fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract structured data from a document using Box AI Extract.
        
        Args:
            file_id: Box file ID
            fields: List of field definitions to extract
                   Each field should have: key, type, prompt, options (optional)
            
        Returns:
            Dictionary containing extracted structured data
            
        Raises:
            BoxAIServiceError: If extraction fails
        """
        logger.info(f"Extracting structured data from file {file_id}")
        
        try:
            result = await self.box_client.box_ai_extract(
                file_id=file_id,
                fields=fields
            )
            
            if not result.success:
                raise BoxAIServiceError(f"Box AI extraction failed: {result.error}")
            
            # Extract and parse the response
            extracted_data = self._extract_response_content(result.data)
            
            logger.info(f"Successfully extracted {len(fields)} fields")
            
            return extracted_data
            
        except BoxMCPToolError as e:
            logger.error(f"Box AI extract tool failed: {e}")
            raise BoxAIServiceError(f"Structured data extraction failed: {e}") from e

    async def convert_methodology_to_structured(
        self,
        methodology_file_id: str
    ) -> StructuredMethodology:
        """Convert PDF methodology to structured format using Box AI.
        
        Args:
            methodology_file_id: Box file ID of the methodology PDF
            
        Returns:
            StructuredMethodology object with extracted data
            
        Raises:
            BoxAIServiceError: If conversion fails
        """
        logger.info(f"Converting methodology PDF to structured format (file_id: {methodology_file_id})")
        
        # Define fields to extract from methodology
        fields = [
            {
                "key": "version",
                "type": "string",
                "prompt": "Extract the methodology version number or identifier"
            },
            {
                "key": "categories",
                "type": "array",
                "prompt": "Extract all rating categories with their weights, metrics, and formulas"
            },
            {
                "key": "rating_thresholds",
                "type": "array",
                "prompt": "Extract the rating thresholds that map scores to letter grades (e.g., AAA, AA, etc.)"
            }
        ]
        
        try:
            extracted_data = await self.extract_structured_data(
                file_id=methodology_file_id,
                fields=fields
            )
            
            # Validate and create StructuredMethodology
            structured_methodology = StructuredMethodology(
                version=extracted_data.get("version", "unknown"),
                categories=extracted_data.get("categories", []),
                rating_thresholds=extracted_data.get("rating_thresholds", [])
            )
            
            logger.info(
                f"Successfully converted methodology to structured format "
                f"(version: {structured_methodology.version})"
            )
            
            return structured_methodology
            
        except ValidationError as e:
            logger.error(f"Failed to validate structured methodology: {e}")
            raise BoxAIServiceError(
                f"Structured methodology validation failed: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to convert methodology: {e}")
            raise BoxAIServiceError(f"Methodology conversion failed: {e}") from e
