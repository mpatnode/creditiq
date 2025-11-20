"""Box MCP Client for interacting with Box via MCP server."""

import os
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


logger = logging.getLogger(__name__)


@dataclass
class MCPToolResult:
    """Result from an MCP tool call."""

    success: bool
    data: Any
    error: Optional[str] = None


class BoxMCPClientError(Exception):
    """Base exception for Box MCP Client errors."""

    pass


class BoxMCPConnectionError(BoxMCPClientError):
    """Exception raised when MCP connection fails."""

    pass


class BoxMCPToolError(BoxMCPClientError):
    """Exception raised when MCP tool execution fails."""

    pass


class BoxMCPClient:
    """Client for interacting with Box via MCP server.
    
    This client connects to a self-hosted Box MCP server and provides
    wrapper methods for Box operations using MCP tools.
    """

    def __init__(
        self,
        server_path: Optional[str] = None,
        server_url: Optional[str] = None,
        max_retries: Optional[int] = None,
    ):
        """Initialize Box MCP Client.
        
        Args:
            server_path: Path to the Box MCP server executable (for stdio)
            server_url: URL to the Box MCP server (for SSE, e.g., http://localhost:8005/sse)
            max_retries: Maximum number of retries for failed operations
        """
        self.server_path = server_path or os.getenv("BOX_MCP_SERVER_PATH")
        self.server_url = server_url or os.getenv("BOX_MCP_SERVER_URL")
        self.max_retries = max_retries or int(os.getenv("MAX_RETRIES", "3"))
        
        # Must have either server_path or server_url
        if not self.server_path and not self.server_url:
            raise BoxMCPClientError(
                "Either BOX_MCP_SERVER_PATH or BOX_MCP_SERVER_URL must be configured"
            )
        
        # Prefer SSE if URL is provided
        self.connection_type = "sse" if self.server_url else "stdio"
        
        self._session: Optional[ClientSession] = None
        self._connected = False
        self._context = None
        
        if self.connection_type == "sse":
            logger.info(f"Initialized BoxMCPClient with SSE server URL: {self.server_url}")
        else:
            logger.info(f"Initialized BoxMCPClient with stdio server path: {self.server_path}")

    async def connect_to_mcp(self) -> None:
        """Establish connection to MCP server.
        
        Raises:
            BoxMCPConnectionError: If connection fails
        """
        if self._connected and self._session:
            logger.debug("Already connected to MCP server")
            return
        
        try:
            if self.connection_type == "sse":
                await self._connect_sse()
            else:
                await self._connect_stdio()
            
            self._connected = True
            logger.info(f"Successfully connected to Box MCP server via {self.connection_type}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Box MCP server: {e}")
            raise BoxMCPConnectionError(f"MCP connection failed: {e}") from e

    async def _connect_sse(self) -> None:
        """Connect to MCP server via SSE."""
        logger.info(f"Connecting to Box MCP server via SSE at {self.server_url}...")
        
        # Create SSE client context
        self._context = sse_client(self.server_url)
        self._read, self._write = await self._context.__aenter__()
        
        # Create session
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        
        # Initialize the session
        await self._session.initialize()

    async def _connect_stdio(self) -> None:
        """Connect to MCP server via stdio."""
        logger.info(f"Connecting to Box MCP server via stdio at {self.server_path}...")
        
        # Configure server parameters for stdio communication
        server_params = StdioServerParameters(
            command=self.server_path,
            args=[],
            env=None,
        )
        
        # Create stdio client context
        self._context = stdio_client(server_params)
        self._read, self._write = await self._context.__aenter__()
        
        # Create session
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        
        # Initialize the session
        await self._session.initialize()

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
                if self._context:
                    await self._context.__aexit__(None, None, None)
                logger.info("Disconnected from Box MCP server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._session = None
                self._context = None
                self._connected = False

    def _ensure_connected(self) -> None:
        """Ensure client is connected to MCP server.
        
        Raises:
            BoxMCPConnectionError: If not connected
        """
        if not self._connected or not self._session:
            raise BoxMCPConnectionError("Not connected to MCP server. Call connect_to_mcp() first.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(BoxMCPToolError),
    )
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Call an MCP tool with retry logic.
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            MCPToolResult with success status and data
            
        Raises:
            BoxMCPToolError: If tool execution fails after retries
        """
        self._ensure_connected()
        
        try:
            logger.debug(f"Calling MCP tool: {tool_name} with args: {arguments}")
            
            result = await self._session.call_tool(tool_name, arguments)
            
            # Extract content from result
            content = result.content if hasattr(result, 'content') else result
            
            # Check if result indicates an error
            # MCP results have isError attribute when there's an error
            if hasattr(result, 'isError') and result.isError:
                error_msg = str(content)
                logger.error(f"MCP tool {tool_name} returned error: {error_msg}")
                return MCPToolResult(success=False, data=None, error=error_msg)
            
            logger.debug(f"MCP tool {tool_name} succeeded")
            return MCPToolResult(success=True, data=content, error=None)
            
        except Exception as e:
            logger.error(f"MCP tool {tool_name} failed: {e}")
            raise BoxMCPToolError(f"Tool {tool_name} execution failed: {e}") from e

    async def search_files(
        self, query: str, folder_id: Optional[str] = None
    ) -> MCPToolResult:
        """Search for files in Box.
        
        Args:
            query: Search query string
            folder_id: Optional folder ID to limit search scope
            
        Returns:
            MCPToolResult containing search results
        """
        arguments = {"query": query}
        if folder_id:
            arguments["ancestor_folder_ids"] = folder_id
        
        return await self._call_tool("box_search", arguments)

    async def get_file_info(self, file_id: str) -> MCPToolResult:
        """Get metadata about a specific file.
        
        Args:
            file_id: Box file ID
            
        Returns:
            MCPToolResult containing file metadata
        """
        arguments = {"file_id": file_id}
        return await self._call_tool("box_get_file_info", arguments)

    async def read_file(self, file_id: str) -> bytes:
        """Download and read file contents.
        
        Args:
            file_id: Box file ID
            
        Returns:
            File contents as bytes
            
        Raises:
            BoxMCPToolError: If file read fails
        """
        arguments = {"file_id": file_id}
        result = await self._call_tool("box_read_file", arguments)
        
        if not result.success:
            raise BoxMCPToolError(f"Failed to read file {file_id}: {result.error}")
        
        # Convert result data to bytes if needed
        if isinstance(result.data, bytes):
            return result.data
        elif isinstance(result.data, str):
            return result.data.encode('utf-8')
        elif isinstance(result.data, list):
            # MCP might return content as list of text content blocks
            content = ""
            for item in result.data:
                if hasattr(item, 'text'):
                    content += item.text
                elif isinstance(item, dict) and 'text' in item:
                    content += item['text']
            return content.encode('utf-8')
        else:
            return str(result.data).encode('utf-8')

    async def upload_file(
        self, folder_id: str, file_name: str, content: bytes
    ) -> MCPToolResult:
        """Upload a new file to Box.
        
        Args:
            folder_id: Box folder ID where file will be uploaded
            file_name: Name for the uploaded file
            content: File content as bytes
            
        Returns:
            MCPToolResult containing uploaded file information
        """
        # Convert bytes to base64 or string as needed by MCP tool
        import base64
        content_str = base64.b64encode(content).decode('utf-8')
        
        arguments = {
            "folder_id": folder_id,
            "file_name": file_name,
            "content": content_str,
        }
        
        return await self._call_tool("box_upload_file", arguments)

    async def create_folder(
        self, parent_folder_id: str, folder_name: str
    ) -> MCPToolResult:
        """Create a new folder in Box.
        
        Args:
            parent_folder_id: Parent folder ID
            folder_name: Name for the new folder
            
        Returns:
            MCPToolResult containing created folder information
        """
        arguments = {
            "parent_folder_id": parent_folder_id,
            "name": folder_name,
        }
        
        return await self._call_tool("box_create_folder", arguments)

    async def update_file_metadata(
        self, file_id: str, metadata: Dict[str, Any]
    ) -> MCPToolResult:
        """Update custom metadata on a file.
        
        Args:
            file_id: Box file ID
            metadata: Metadata key-value pairs to set
            
        Returns:
            MCPToolResult containing updated file information
        """
        arguments = {
            "file_id": file_id,
            "metadata": metadata,
        }
        
        return await self._call_tool("box_update_file_metadata", arguments)

    async def box_ai_ask(
        self,
        file_ids: List[str],
        prompt: str,
        mode: str = "multiple_item_qa"
    ) -> MCPToolResult:
        """Ask Box AI a question about one or more documents.
        
        Args:
            file_ids: List of Box file IDs to query
            prompt: Question or instruction for Box AI
            mode: Query mode - "single_item_qa" or "multiple_item_qa"
            
        Returns:
            MCPToolResult containing Box AI response
        """
        arguments = {
            "items": [{"type": "file", "id": file_id} for file_id in file_ids],
            "prompt": prompt,
            "mode": mode,
        }
        
        return await self._call_tool("box_ai_ask", arguments)

    async def box_ai_extract(
        self,
        file_id: str,
        fields: List[Dict[str, Any]]
    ) -> MCPToolResult:
        """Extract structured data from a document using Box AI.
        
        Args:
            file_id: Box file ID
            fields: List of field definitions to extract
                   Each field should have: key, type, prompt, options (optional)
            
        Returns:
            MCPToolResult containing extracted structured data
        """
        arguments = {
            "file_id": file_id,
            "fields": fields,
        }
        
        return await self._call_tool("box_ai_extract", arguments)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_to_mcp()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
