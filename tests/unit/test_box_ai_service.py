"""Unit tests for Box AI Service."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from services.box_ai_service import (
    BoxAIService,
    BoxAIServiceError,
    BoxAIResponseParsingError,
    BoxAIResponse,
    MetricBreakdown,
    CreditRating,
    StructuredMethodology,
)
from services.box_mcp_client import BoxMCPClient, MCPToolResult


class TestBoxAIService:
    """Test suite for BoxAIService."""

    @pytest.fixture
    def mock_box_client(self):
        """Create a mock Box MCP client."""
        client = Mock(spec=BoxMCPClient)
        return client

    @pytest.fixture
    def box_ai_service(self, mock_box_client):
        """Create BoxAIService instance with mock client."""
        return BoxAIService(mock_box_client)

    def test_init(self, mock_box_client):
        """Test BoxAIService initialization."""
        service = BoxAIService(mock_box_client)
        assert service.box_client is mock_box_client

    @pytest.mark.asyncio
    async def test_ask_box_ai_success(self, box_ai_service, mock_box_client):
        """Test ask_box_ai with successful response."""
        # Mock successful Box AI response
        mock_result = MCPToolResult(
            success=True,
            data={"answer": "Test response", "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        result = await box_ai_service.ask_box_ai(
            file_ids=["file123"],
            prompt="Test prompt"
        )
        
        assert result["answer"] == "Test response"
        assert result["completion_reason"] == "done"
        mock_box_client.box_ai_ask.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_box_ai_failure(self, box_ai_service, mock_box_client):
        """Test ask_box_ai with failed response."""
        # Mock failed Box AI response
        from tenacity import RetryError
        mock_result = MCPToolResult(
            success=False,
            data=None,
            error="Box AI error"
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        # ask_box_ai has retry logic, so it will raise RetryError after retries
        with pytest.raises(RetryError):
            await box_ai_service.ask_box_ai(
                file_ids=["file123"],
                prompt="Test prompt"
            )

    @pytest.mark.asyncio
    async def test_apply_methodology_success(self, box_ai_service, mock_box_client):
        """Test apply_methodology with valid response."""
        # Create a valid JSON response
        response_json = {
            "rating": "AAA",
            "score": 95.5,
            "reasoning": "Strong financial position",
            "metrics": {
                "debt_to_equity": 0.3,
                "current_ratio": 2.5
            },
            "breakdown": [
                {
                    "category": "Leverage",
                    "weight": 0.3,
                    "score": 90.0,
                    "metrics": {"debt_to_equity": 0.3},
                    "reasoning": "Low debt levels"
                }
            ]
        }
        
        # Mock Box AI response
        mock_result = MCPToolResult(
            success=True,
            data={
                "answer": json.dumps(response_json),
                "completion_reason": "done"
            }
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        result = await box_ai_service.apply_methodology(
            methodology_file_id="method123",
            financial_data_file_id="data456"
        )
        
        assert isinstance(result, BoxAIResponse)
        assert result.rating == "AAA"
        assert result.score == 95.5
        assert result.reasoning == "Strong financial position"
        assert len(result.breakdown) == 1
        assert result.breakdown[0].category == "Leverage"

    @pytest.mark.asyncio
    async def test_apply_methodology_with_markdown_json(self, box_ai_service, mock_box_client):
        """Test apply_methodology with JSON wrapped in markdown."""
        response_json = {
            "rating": "AA",
            "score": 85.0,
            "reasoning": "Good financial health"
        }
        
        # Wrap JSON in markdown code block
        markdown_response = f"```json\n{json.dumps(response_json)}\n```"
        
        mock_result = MCPToolResult(
            success=True,
            data={"answer": markdown_response, "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        result = await box_ai_service.apply_methodology(
            methodology_file_id="method123",
            financial_data_file_id="data456"
        )
        
        assert result.rating == "AA"
        assert result.score == 85.0

    @pytest.mark.asyncio
    async def test_apply_methodology_invalid_json(self, box_ai_service, mock_box_client):
        """Test apply_methodology with invalid JSON response."""
        mock_result = MCPToolResult(
            success=True,
            data={"answer": "This is not JSON", "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        with pytest.raises(BoxAIResponseParsingError, match="Invalid JSON"):
            await box_ai_service.apply_methodology(
                methodology_file_id="method123",
                financial_data_file_id="data456"
            )

    @pytest.mark.asyncio
    async def test_apply_methodology_missing_rating(self, box_ai_service, mock_box_client):
        """Test apply_methodology with missing rating field."""
        response_json = {
            "score": 85.0,
            "reasoning": "Missing rating"
        }
        
        mock_result = MCPToolResult(
            success=True,
            data={"answer": json.dumps(response_json), "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        with pytest.raises(BoxAIResponseParsingError, match="Missing 'rating' field"):
            await box_ai_service.apply_methodology(
                methodology_file_id="method123",
                financial_data_file_id="data456"
            )

    @pytest.mark.asyncio
    async def test_apply_methodology_invalid_rating(self, box_ai_service, mock_box_client):
        """Test apply_methodology with invalid rating value."""
        response_json = {
            "rating": "INVALID",
            "score": 85.0,
            "reasoning": "Invalid rating"
        }
        
        mock_result = MCPToolResult(
            success=True,
            data={"answer": json.dumps(response_json), "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        with pytest.raises(BoxAIResponseParsingError, match="Invalid credit rating"):
            await box_ai_service.apply_methodology(
                methodology_file_id="method123",
                financial_data_file_id="data456"
            )

    @pytest.mark.asyncio
    async def test_apply_methodology_score_out_of_range(self, box_ai_service, mock_box_client):
        """Test apply_methodology with score outside valid range."""
        response_json = {
            "rating": "AAA",
            "score": 150.0,  # Invalid: > 100
            "reasoning": "Score too high"
        }
        
        mock_result = MCPToolResult(
            success=True,
            data={"answer": json.dumps(response_json), "completion_reason": "done"}
        )
        mock_box_client.box_ai_ask = AsyncMock(return_value=mock_result)
        
        with pytest.raises(BoxAIResponseParsingError, match="outside valid range"):
            await box_ai_service.apply_methodology(
                methodology_file_id="method123",
                financial_data_file_id="data456"
            )

    @pytest.mark.asyncio
    async def test_extract_structured_data_success(self, box_ai_service, mock_box_client):
        """Test extract_structured_data with successful response."""
        fields = [
            {"key": "version", "type": "string", "prompt": "Extract version"},
            {"key": "categories", "type": "array", "prompt": "Extract categories"}
        ]
        
        mock_result = MCPToolResult(
            success=True,
            data={
                "version": "1.0",
                "categories": [{"name": "Leverage", "weight": 0.3}]
            }
        )
        mock_box_client.box_ai_extract = AsyncMock(return_value=mock_result)
        
        result = await box_ai_service.extract_structured_data(
            file_id="file123",
            fields=fields
        )
        
        assert result["version"] == "1.0"
        assert len(result["categories"]) == 1
        mock_box_client.box_ai_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_structured_data_failure(self, box_ai_service, mock_box_client):
        """Test extract_structured_data with failed response."""
        fields = [{"key": "version", "type": "string", "prompt": "Extract version"}]
        
        mock_result = MCPToolResult(
            success=False,
            data=None,
            error="Extraction failed"
        )
        mock_box_client.box_ai_extract = AsyncMock(return_value=mock_result)
        
        with pytest.raises(BoxAIServiceError, match="Box AI extraction failed"):
            await box_ai_service.extract_structured_data(
                file_id="file123",
                fields=fields
            )

    @pytest.mark.asyncio
    async def test_convert_methodology_to_structured(self, box_ai_service, mock_box_client):
        """Test convert_methodology_to_structured."""
        mock_result = MCPToolResult(
            success=True,
            data={
                "version": "2.0",
                "categories": [
                    {"name": "Leverage", "weight": 0.3, "metrics": []}
                ],
                "rating_thresholds": [
                    {"rating": "AAA", "min_score": 90, "max_score": 100}
                ]
            }
        )
        mock_box_client.box_ai_extract = AsyncMock(return_value=mock_result)
        
        result = await box_ai_service.convert_methodology_to_structured(
            methodology_file_id="method123"
        )
        
        assert isinstance(result, StructuredMethodology)
        assert result.version == "2.0"
        assert len(result.categories) == 1
        assert len(result.rating_thresholds) == 1

    def test_extract_json_from_text_with_markdown(self, box_ai_service):
        """Test _extract_json_from_text with markdown code block."""
        json_obj = {"rating": "AAA", "score": 95}
        text = f"Here is the result:\n```json\n{json.dumps(json_obj)}\n```\nEnd"
        
        result = box_ai_service._extract_json_from_text(text)
        parsed = json.loads(result)
        
        assert parsed["rating"] == "AAA"
        assert parsed["score"] == 95

    def test_extract_json_from_text_plain_json(self, box_ai_service):
        """Test _extract_json_from_text with plain JSON."""
        json_obj = {"rating": "AA", "score": 85}
        text = json.dumps(json_obj)
        
        result = box_ai_service._extract_json_from_text(text)
        parsed = json.loads(result)
        
        assert parsed["rating"] == "AA"
        assert parsed["score"] == 85

    def test_validate_rating_valid(self, box_ai_service):
        """Test _validate_rating with valid ratings."""
        # Should not raise for valid ratings
        box_ai_service._validate_rating("AAA")
        box_ai_service._validate_rating("AA+")
        box_ai_service._validate_rating("BBB-")
        box_ai_service._validate_rating("D")

    def test_validate_rating_invalid(self, box_ai_service):
        """Test _validate_rating with invalid rating."""
        with pytest.raises(BoxAIResponseParsingError, match="Invalid credit rating"):
            box_ai_service._validate_rating("INVALID")

    def test_construct_rating_prompt(self, box_ai_service):
        """Test _construct_rating_prompt generates valid prompt."""
        prompt = box_ai_service._construct_rating_prompt()
        
        assert "credit rating" in prompt.lower()
        assert "json" in prompt.lower()
        assert "methodology" in prompt.lower()

    def test_construct_rating_prompt_with_options(self, box_ai_service):
        """Test _construct_rating_prompt with additional options."""
        options = {"additional_instructions": "Focus on liquidity ratios"}
        prompt = box_ai_service._construct_rating_prompt(options)
        
        assert "Focus on liquidity ratios" in prompt

    def test_extract_response_content_dict(self, box_ai_service):
        """Test _extract_response_content with dict input."""
        data = {"answer": "test", "completion_reason": "done"}
        result = box_ai_service._extract_response_content(data)
        
        assert result == data

    def test_extract_response_content_string(self, box_ai_service):
        """Test _extract_response_content with string input."""
        data = "test response"
        result = box_ai_service._extract_response_content(data)
        
        assert result["answer"] == "test response"
        assert result["completion_reason"] == "done"

    def test_extract_response_content_list(self, box_ai_service):
        """Test _extract_response_content with list input."""
        data = [
            {"text": "part 1 "},
            {"text": "part 2"}
        ]
        result = box_ai_service._extract_response_content(data)
        
        assert result["answer"] == "part 1 part 2"

    def test_credit_rating_enum(self):
        """Test CreditRating enum has all expected values."""
        assert CreditRating.AAA.value == "AAA"
        assert CreditRating.AA_PLUS.value == "AA+"
        assert CreditRating.D.value == "D"
        
        # Check all ratings are present
        all_ratings = [r.value for r in CreditRating]
        assert "AAA" in all_ratings
        assert "BBB" in all_ratings
        assert "D" in all_ratings

    def test_metric_breakdown_model(self):
        """Test MetricBreakdown Pydantic model."""
        breakdown = MetricBreakdown(
            category="Leverage",
            weight=0.3,
            score=85.0,
            metrics={"debt_to_equity": 0.5},
            reasoning="Good leverage ratios"
        )
        
        assert breakdown.category == "Leverage"
        assert breakdown.weight == 0.3
        assert breakdown.score == 85.0

    def test_box_ai_response_model(self):
        """Test BoxAIResponse Pydantic model."""
        response = BoxAIResponse(
            rating="AAA",
            score=95.0,
            reasoning="Excellent",
            metrics={"debt_to_equity": 0.3},
            breakdown=[],
            raw_response="raw",
            completion_reason="done"
        )
        
        assert response.rating == "AAA"
        assert response.score == 95.0
        assert response.completion_reason == "done"

    def test_structured_methodology_model(self):
        """Test StructuredMethodology Pydantic model."""
        methodology = StructuredMethodology(
            version="1.0",
            categories=[{"name": "Leverage"}],
            rating_thresholds=[{"rating": "AAA", "min": 90}]
        )
        
        assert methodology.version == "1.0"
        assert len(methodology.categories) == 1
        assert len(methodology.rating_thresholds) == 1
