"""Simple MCP connection test to debug hanging issue."""

import os
import asyncio
import pytest
from dotenv import load_dotenv
from services.box_mcp_client import BoxMCPClient

load_dotenv()


@pytest.mark.asyncio
async def test_simple_mcp_connection():
    """Test basic MCP connection with timeout."""
    print("\n" + "="*70)
    print("Simple MCP Connection Test")
    print("="*70)
    
    server_url = os.getenv("BOX_MCP_SERVER_URL")
    print(f"\n🔌 Connecting to: {server_url}")
    
    client = BoxMCPClient(server_url=server_url)
    
    try:
        # Add a timeout to prevent hanging
        async with asyncio.timeout(10):
            print("  Attempting connection...")
            await client.connect_to_mcp()
            print("  ✓ Connected!")
            
            print("\n📋 Testing list_tools...")
            # Try to list available tools
            if client._session:
                result = await client._session.list_tools()
                print(f"  ✓ Available tools: {len(result.tools) if hasattr(result, 'tools') else 'unknown'}")
            
            await client.disconnect()
            print("  ✓ Disconnected")
            
    except asyncio.TimeoutError:
        print("  ✗ Connection timed out after 10 seconds")
        raise
    except Exception as e:
        print(f"  ✗ Error: {e}")
        raise
    finally:
        if client._connected:
            await client.disconnect()
    
    print("\n" + "="*70)
    print("✅ Test completed")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_simple_mcp_connection())
