"""Debug SSE connection to see what messages are being exchanged."""

import os
import asyncio
import httpx
from httpx_sse import aconnect_sse
from dotenv import load_dotenv

load_dotenv()


async def debug_sse_connection():
    """Debug SSE connection to see raw messages."""
    url = os.getenv("BOX_MCP_SERVER_URL", "http://localhost:8005/mcp")
    
    print("\n" + "="*70)
    print("SSE Debug - Raw Message Inspection")
    print("="*70)
    print(f"\n🔌 Connecting to: {url}")
    
    async with httpx.AsyncClient() as client:
        print("\n📡 Opening SSE connection...")
        
        try:
            async with asyncio.timeout(15):
                async with aconnect_sse(client, "GET", url) as event_source:
                    print("✓ SSE connection established")
                    print("\n📨 Waiting for server messages...\n")
                    
                    message_count = 0
                    async for event in event_source.aiter_sse():
                        message_count += 1
                        print(f"Message #{message_count}:")
                        print(f"  Event: {event.event}")
                        print(f"  Data: {event.data}")
                        print(f"  ID: {event.id}")
                        print(f"  Retry: {event.retry}")
                        print()
                        
                        # Stop after 5 messages or 10 seconds
                        if message_count >= 5:
                            print("Received 5 messages, stopping...")
                            break
                            
        except asyncio.TimeoutError:
            print("⏱️  Timeout after 15 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Debug complete")
    print("="*70)


async def debug_mcp_protocol():
    """Debug MCP protocol initialization."""
    url = os.getenv("BOX_MCP_SERVER_URL", "http://localhost:8005/mcp")
    
    print("\n" + "="*70)
    print("MCP Protocol Debug - Initialization Handshake")
    print("="*70)
    print(f"\n🔌 Connecting to: {url}")
    
    # Try to manually send MCP initialization
    import json
    
    async with httpx.AsyncClient() as client:
        print("\n📡 Opening SSE connection...")
        
        try:
            async with asyncio.timeout(15):
                async with aconnect_sse(client, "GET", url) as event_source:
                    print("✓ SSE connection established")
                    
                    # The MCP protocol expects us to send an initialize request
                    # But SSE is unidirectional (server -> client only)
                    # So we need to understand how the MCP server expects to receive requests
                    
                    print("\n📨 Listening for server messages...")
                    print("(MCP servers typically send endpoint info or wait for POST requests)\n")
                    
                    message_count = 0
                    async for event in event_source.aiter_sse():
                        message_count += 1
                        print(f"Message #{message_count}:")
                        print(f"  Event type: '{event.event}'")
                        print(f"  Data: {event.data[:200] if len(event.data) > 200 else event.data}")
                        
                        # Try to parse as JSON
                        try:
                            data = json.loads(event.data)
                            print(f"  Parsed JSON: {json.dumps(data, indent=2)[:300]}")
                        except:
                            print(f"  (Not JSON)")
                        print()
                        
                        if message_count >= 10:
                            break
                            
        except asyncio.TimeoutError:
            print("⏱️  Timeout - no messages received")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)


async def test_http_post():
    """Test if MCP server expects POST requests instead of SSE."""
    url = os.getenv("BOX_MCP_SERVER_URL", "http://localhost:8005/mcp")
    
    print("\n" + "="*70)
    print("Testing HTTP POST for MCP Protocol")
    print("="*70)
    
    import json
    
    # MCP initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    print(f"\n📤 Sending initialize request to: {url}")
    print(f"Request: {json.dumps(initialize_request, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=initialize_request,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            print(f"\n📥 Response:")
            print(f"  Status: {response.status_code}")
            print(f"  Headers: {dict(response.headers)}")
            print(f"  Body: {response.text[:500]}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("Running SSE Debug Tests\n")
    
    # Test 1: Raw SSE messages
    print("\n" + "="*70)
    print("TEST 1: Raw SSE Messages")
    print("="*70)
    asyncio.run(debug_sse_connection())
    
    # Test 2: MCP Protocol
    print("\n\n" + "="*70)
    print("TEST 2: MCP Protocol Messages")
    print("="*70)
    asyncio.run(debug_mcp_protocol())
    
    # Test 3: HTTP POST
    print("\n\n" + "="*70)
    print("TEST 3: HTTP POST Method")
    print("="*70)
    asyncio.run(test_http_post())
