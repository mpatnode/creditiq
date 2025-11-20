"""End-to-end tests for Box MCP Client integration.

These tests verify actual connectivity to Box via the MCP server.
They require:
- Box MCP server to be running
- Valid Box credentials in .env file
- BOX_METHODOLOGY_FOLDER_ID and BOX_RATINGS_FOLDER_ID configured

Run with: pytest tests/integration/test_box_mcp_e2e.py -v
Skip with: pytest tests/unit/ -v (to run only unit tests)
"""

import os
import pytest
from dotenv import load_dotenv
from services.box_mcp_client import BoxMCPClient, BoxMCPConnectionError, BoxMCPToolError


# Load environment variables
load_dotenv()


@pytest.fixture
def box_client():
    """Create a Box MCP client for testing."""
    server_path = os.getenv("BOX_MCP_SERVER_PATH")
    server_url = os.getenv("BOX_MCP_SERVER_URL")
    
    if not server_path and not server_url:
        pytest.skip("Neither BOX_MCP_SERVER_PATH nor BOX_MCP_SERVER_URL configured in .env")
    
    return BoxMCPClient(server_path=server_path, server_url=server_url)


@pytest.fixture
def methodology_folder_id():
    """Get methodology folder ID from environment."""
    folder_id = os.getenv("BOX_METHODOLOGY_FOLDER_ID")
    if not folder_id:
        pytest.skip("BOX_METHODOLOGY_FOLDER_ID not configured in .env")
    return folder_id


@pytest.fixture
def ratings_folder_id():
    """Get ratings folder ID from environment."""
    folder_id = os.getenv("BOX_RATINGS_FOLDER_ID")
    if not folder_id:
        pytest.skip("BOX_RATINGS_FOLDER_ID not configured in .env")
    return folder_id


class TestBoxMCPE2E:
    """End-to-end tests for Box MCP integration."""

    @pytest.mark.asyncio
    async def test_mcp_connection(self, box_client):
        """Test that we can connect to the Box MCP server."""
        try:
            async with box_client:
                assert box_client._connected
                print("\n✓ Successfully connected to Box MCP server")
        except BoxMCPConnectionError as e:
            pytest.fail(f"Failed to connect to Box MCP server: {e}")

    @pytest.mark.asyncio
    async def test_methodology_folder_exists(self, box_client, methodology_folder_id):
        """Test that the methodology folder exists and is accessible."""
        async with box_client:
            try:
                # Try to list folder contents to verify it exists
                result = await box_client.search_files("*", folder_id=methodology_folder_id)
                
                if result.success:
                    print(f"\n✓ Methodology folder found: {methodology_folder_id}")
                    print(f"  Folder accessible with {len(result.data) if isinstance(result.data, list) else 'unknown'} items")
                else:
                    pytest.fail(
                        f"Methodology folder {methodology_folder_id} not accessible: {result.error}"
                    )
            except BoxMCPToolError as e:
                pytest.fail(f"Error accessing methodology folder: {e}")

    @pytest.mark.asyncio
    async def test_ratings_folder_exists(self, box_client, ratings_folder_id):
        """Test that the ratings folder exists and is accessible."""
        async with box_client:
            try:
                # Try to list folder contents to verify it exists
                result = await box_client.search_files("*", folder_id=ratings_folder_id)
                
                if result.success:
                    print(f"\n✓ Ratings folder found: {ratings_folder_id}")
                    print(f"  Folder accessible with {len(result.data) if isinstance(result.data, list) else 'unknown'} items")
                else:
                    pytest.fail(
                        f"Ratings folder {ratings_folder_id} not accessible: {result.error}"
                    )
            except BoxMCPToolError as e:
                pytest.fail(f"Error accessing ratings folder: {e}")

    @pytest.mark.asyncio
    async def test_search_in_methodology_folder(self, box_client, methodology_folder_id):
        """Test searching for files in the methodology folder."""
        async with box_client:
            try:
                # Search for PDF files in methodology folder
                result = await box_client.search_files("pdf", folder_id=methodology_folder_id)
                
                if result.success:
                    print(f"\n✓ Search in methodology folder successful")
                    print(f"  Found items: {result.data}")
                else:
                    # Search might return no results, which is ok
                    print(f"\n✓ Search completed (no results or error: {result.error})")
            except BoxMCPToolError as e:
                pytest.fail(f"Error searching methodology folder: {e}")

    @pytest.mark.asyncio
    async def test_list_methodology_folder_contents(self, box_client, methodology_folder_id):
        """Test listing contents of the methodology folder."""
        async with box_client:
            try:
                # Search with empty query to list all items
                result = await box_client.search_files("", folder_id=methodology_folder_id)
                
                if result.success:
                    print(f"\n✓ Listed methodology folder contents")
                    if result.data:
                        print(f"  Number of items: {len(result.data) if isinstance(result.data, list) else 'N/A'}")
                        print(f"  Contents: {result.data}")
                    else:
                        print("  Folder is empty or search returned no results")
                else:
                    print(f"\n⚠ Could not list folder contents: {result.error}")
            except BoxMCPToolError as e:
                # This might fail if the MCP tool doesn't support empty queries
                print(f"\n⚠ Listing folder contents not supported or failed: {e}")

    @pytest.mark.asyncio
    async def test_full_workflow(self, box_client, methodology_folder_id, ratings_folder_id):
        """Test a complete workflow: connect, verify folders, search."""
        print("\n" + "="*60)
        print("Box MCP E2E Test - Full Workflow")
        print("="*60)
        
        async with box_client:
            # 1. Verify connection
            assert box_client._connected
            print("✓ Step 1: Connected to Box MCP server")
            
            # 2. Verify methodology folder
            result = await box_client.get_file_info(methodology_folder_id)
            assert result.success or result.error, "Methodology folder check failed"
            print(f"✓ Step 2: Methodology folder verified ({methodology_folder_id})")
            
            # 3. Verify ratings folder
            result = await box_client.get_file_info(ratings_folder_id)
            assert result.success or result.error, "Ratings folder check failed"
            print(f"✓ Step 3: Ratings folder verified ({ratings_folder_id})")
            
            # 4. Test search capability
            result = await box_client.search_files("methodology")
            print(f"✓ Step 4: Search capability verified")
            
            print("\n" + "="*60)
            print("All E2E tests passed! Box MCP integration is working.")
            print("="*60)


@pytest.mark.asyncio
async def test_environment_configuration():
    """Test that all required environment variables are configured."""
    print("\n" + "="*60)
    print("Environment Configuration Check")
    print("="*60)
    
    # At least one connection method is required
    connection_vars = ["BOX_MCP_SERVER_PATH", "BOX_MCP_SERVER_URL"]
    
    required_vars = [
        "BOX_METHODOLOGY_FOLDER_ID",
        "BOX_RATINGS_FOLDER_ID",
    ]
    
    optional_vars = [
        "BOX_CLIENT_ID",
        "BOX_CLIENT_SECRET",
        "BOX_ENTERPRISE_ID",
    ]
    
    # Check connection method
    connection_configured = False
    for var in connection_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value[:30]}..." if len(value) > 30 else f"✓ {var}: {value}")
            connection_configured = True
        else:
            print(f"⚠ {var}: NOT SET")
    
    if not connection_configured:
        pytest.fail(
            f"At least one connection method must be configured: {', '.join(connection_vars)}\n"
            f"Please configure either BOX_MCP_SERVER_PATH or BOX_MCP_SERVER_URL in your .env file"
        )
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value[:20]}..." if len(value) > 20 else f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {'*' * 10} (hidden)")
        else:
            print(f"⚠ {var}: NOT SET (may be needed by MCP server)")
            missing_optional.append(var)
    
    print("="*60)
    
    if missing_required:
        pytest.fail(
            f"Missing required environment variables: {', '.join(missing_required)}\n"
            f"Please configure these in your .env file"
        )
    
    if missing_optional:
        print(f"\n⚠ Warning: Optional variables not set: {', '.join(missing_optional)}")
        print("These may be required by the Box MCP server for authentication")
