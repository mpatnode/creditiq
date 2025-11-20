#!/usr/bin/env python3
"""Script to list all available MCP tools from the Box MCP server."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.box_mcp_client import BoxMCPClient


async def list_tools():
    """List all available MCP tools."""
    load_dotenv()
    
    client = BoxMCPClient()
    
    try:
        await client.connect_to_mcp()
        print("✓ Connected to Box MCP server\n")
        
        # List available tools
        tools = await client._session.list_tools()
        
        print(f"Found {len(tools.tools)} available tools:\n")
        print("=" * 80)
        
        for tool in tools.tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                print(f"Input Schema: {tool.inputSchema}")
            print("-" * 80)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(list_tools())
