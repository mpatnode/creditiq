#!/usr/bin/env python3
"""Test script to check if folder exists."""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.box_mcp_client import BoxMCPClient


async def test_folder_info():
    """Test getting folder info."""
    load_dotenv()
    
    ratings_folder_id = os.getenv("BOX_RATINGS_FOLDER_ID")
    if not ratings_folder_id:
        print("✗ BOX_RATINGS_FOLDER_ID not set in .env")
        return
    
    client = BoxMCPClient()
    
    try:
        await client.connect_to_mcp()
        print("✓ Connected to Box MCP server\n")
        
        # List root folder contents
        print(f"Listing root folder contents (ID: 0)\n")
        
        result = await client._call_tool("box_folder_items_list_tool", {"folder_id": "0"})
        
        print(f"Success: {result.success}")
        print(f"Error: {result.error}")
        print(f"Data type: {type(result.data)}")
        
        if isinstance(result.data, list):
            for item in result.data:
                if hasattr(item, 'text'):
                    print(f"\nResponse:\n{item.text}")
                    try:
                        parsed = json.loads(item.text)
                        print(f"\nParsed JSON:")
                        print(json.dumps(parsed, indent=2))
                    except:
                        pass
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_folder_info())
