#!/usr/bin/env python3
"""Test script to check folder creation response format."""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.box_mcp_client import BoxMCPClient


async def test_folder_create():
    """Test folder creation and inspect response."""
    load_dotenv()
    
    ratings_folder_id = os.getenv("BOX_RATINGS_FOLDER_ID")
    if not ratings_folder_id:
        print("✗ BOX_RATINGS_FOLDER_ID not set in .env")
        return
    
    client = BoxMCPClient()
    
    try:
        await client.connect_to_mcp()
        print("✓ Connected to Box MCP server\n")
        
        # Create a test folder
        test_folder_name = "Test_Folder_Debug"
        print(f"Creating folder: {test_folder_name}")
        print(f"Parent folder ID: {ratings_folder_id}\n")
        
        result = await client.create_folder(
            parent_folder_id=ratings_folder_id,
            folder_name=test_folder_name
        )
        
        print(f"Success: {result.success}")
        print(f"Error: {result.error}")
        print(f"Data type: {type(result.data)}")
        print(f"Data: {result.data}\n")
        
        # Try to parse the data
        if isinstance(result.data, list):
            print("Data is a list:")
            for i, item in enumerate(result.data):
                print(f"  Item {i}: {type(item)}")
                if hasattr(item, 'text'):
                    print(f"    Text: {item.text}")
                    try:
                        parsed = json.loads(item.text)
                        print(f"    Parsed JSON: {json.dumps(parsed, indent=2)}")
                        if 'id' in parsed:
                            print(f"    ✓ Found folder ID: {parsed['id']}")
                    except:
                        pass
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_folder_create())
