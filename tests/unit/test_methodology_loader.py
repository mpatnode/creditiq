"""Unit tests for MethodologyLoader."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from io import BytesIO

from services.methodology_loader import MethodologyLoader, MethodologyLoaderError
from services.box_mcp_client import BoxMCPClient, MCPToolResult


@pytest.fixture
def mock_box_client():
    """Create a mock BoxMCPClient."""
    client = AsyncMock(spec=BoxMCPClient)
    return client


@pytest.fixture
def sample_pdf_bytes():
    """Create sample PDF bytes (content doesn't matter as we'll mock extraction)."""
    return b"%PDF-1.4\nSample PDF content"


@pytest.mark.asyncio
async def test_load_pdf_from_box_success(mock_box_client, sample_pdf_bytes):
    """Test successful PDF loading from Box."""
    # Setup
    file_id = "12345"
    mock_box_client.read_file.return_value = sample_pdf_bytes
    
    loader = MethodologyLoader(mock_box_client, methodology_file_id=file_id)
    
    # Mock the PDF extraction method
    expected_content = "Credit Rating Methodology\nVersion 1.0\nThis is a sample methodology."
    with patch.object(loader, '_extract_text_from_pdf', return_value=expected_content):
        # Execute
        content = await loader.load_pdf_from_box()
    
    # Verify
    assert content == expected_content
    assert len(content) > 0
    mock_box_client.read_file.assert_called_once_with(file_id)
    assert loader.is_cached


@pytest.mark.asyncio
async def test_load_pdf_from_box_with_explicit_file_id(mock_box_client, sample_pdf_bytes):
    """Test PDF loading with explicit file_id parameter."""
    # Setup
    file_id = "67890"
    mock_box_client.read_file.return_value = sample_pdf_bytes
    
    loader = MethodologyLoader(mock_box_client)
    
    # Mock the PDF extraction method
    expected_content = "Test methodology content"
    with patch.object(loader, '_extract_text_from_pdf', return_value=expected_content):
        # Execute
        content = await loader.load_pdf_from_box(file_id=file_id)
    
    # Verify
    assert content == expected_content
    mock_box_client.read_file.assert_called_once_with(file_id)


@pytest.mark.asyncio
async def test_load_pdf_from_box_no_file_id(mock_box_client):
    """Test that error is raised when no file_id is provided."""
    # Setup
    loader = MethodologyLoader(mock_box_client)
    
    # Execute & Verify
    with pytest.raises(MethodologyLoaderError, match="No methodology file ID provided"):
        await loader.load_pdf_from_box()


@pytest.mark.asyncio
async def test_load_pdf_from_box_box_error(mock_box_client):
    """Test handling of Box client errors."""
    # Setup
    from services.box_mcp_client import BoxMCPToolError
    
    file_id = "12345"
    mock_box_client.read_file.side_effect = BoxMCPToolError("Box service unavailable")
    
    loader = MethodologyLoader(mock_box_client, methodology_file_id=file_id)
    
    # Execute & Verify
    with pytest.raises(MethodologyLoaderError, match="Box operation failed"):
        await loader.load_pdf_from_box()


@pytest.mark.asyncio
async def test_get_methodology_content_cached(mock_box_client, sample_pdf_bytes):
    """Test retrieving cached methodology content."""
    # Setup
    file_id = "12345"
    mock_box_client.read_file.return_value = sample_pdf_bytes
    
    loader = MethodologyLoader(mock_box_client, methodology_file_id=file_id)
    
    # Mock the PDF extraction method
    expected_content = "Cached methodology content"
    with patch.object(loader, '_extract_text_from_pdf', return_value=expected_content):
        # Load content first
        await loader.load_pdf_from_box()
    
    # Execute
    cached_content = loader.get_methodology_content()
    
    # Verify
    assert cached_content == expected_content
    assert len(cached_content) > 0


def test_get_methodology_content_not_cached(mock_box_client):
    """Test error when trying to get content before loading."""
    # Setup
    loader = MethodologyLoader(mock_box_client)
    
    # Execute & Verify
    with pytest.raises(MethodologyLoaderError, match="No methodology content cached"):
        loader.get_methodology_content()


@pytest.mark.asyncio
async def test_get_latest_methodology_version(mock_box_client):
    """Test retrieving methodology version info from Box."""
    # Setup
    file_id = "12345"
    mock_file_info = {
        "id": file_id,
        "name": "methodology-v1.0.pdf",
        "modified_at": "2024-01-15T10:00:00Z",
    }
    mock_box_client.get_file_info.return_value = MCPToolResult(
        success=True,
        data=mock_file_info,
    )
    
    loader = MethodologyLoader(mock_box_client, methodology_file_id=file_id)
    
    # Execute
    version_info = await loader.get_latest_methodology_version()
    
    # Verify
    assert version_info is not None
    assert version_info["file_id"] == file_id
    assert "data" in version_info
    mock_box_client.get_file_info.assert_called_once_with(file_id)


@pytest.mark.asyncio
async def test_get_latest_methodology_version_no_file_id(mock_box_client):
    """Test error when getting version without file_id configured."""
    # Setup
    loader = MethodologyLoader(mock_box_client)
    
    # Execute & Verify
    with pytest.raises(MethodologyLoaderError, match="No methodology file ID configured"):
        await loader.get_latest_methodology_version()


@pytest.mark.asyncio
async def test_clear_cache(mock_box_client, sample_pdf_bytes):
    """Test clearing the methodology cache."""
    # Setup
    file_id = "12345"
    mock_box_client.read_file.return_value = sample_pdf_bytes
    
    loader = MethodologyLoader(mock_box_client, methodology_file_id=file_id)
    
    # Mock the PDF extraction method
    with patch.object(loader, '_extract_text_from_pdf', return_value="test content"):
        # Load content
        await loader.load_pdf_from_box()
    
    assert loader.is_cached
    
    # Execute
    loader.clear_cache()
    
    # Verify
    assert not loader.is_cached
    with pytest.raises(MethodologyLoaderError):
        loader.get_methodology_content()


def test_is_cached_property(mock_box_client):
    """Test is_cached property."""
    # Setup
    loader = MethodologyLoader(mock_box_client)
    
    # Initially not cached
    assert not loader.is_cached
    
    # Set cached content manually
    loader._cached_content = "test content"
    assert loader.is_cached
    
    # Clear cache
    loader.clear_cache()
    assert not loader.is_cached
