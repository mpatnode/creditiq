"""Methodology Loader for loading and caching credit rating methodology from Box."""

import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from io import BytesIO

from PyPDF2 import PdfReader

from services.box_mcp_client import BoxMCPClient, BoxMCPClientError


logger = logging.getLogger(__name__)


class MethodologyLoaderError(Exception):
    """Base exception for Methodology Loader errors."""
    pass


class MethodologyLoader:
    """Load and cache methodology from Box.
    
    This class handles loading the credit rating methodology PDF from Box,
    extracting text content, and caching it for performance.
    """

    def __init__(self, box_client: BoxMCPClient, methodology_file_id: Optional[str] = None):
        """Initialize Methodology Loader.
        
        Args:
            box_client: BoxMCPClient instance for Box operations
            methodology_file_id: Optional Box file ID for the methodology PDF
        """
        self.box_client = box_client
        self.methodology_file_id = methodology_file_id
        self._cached_content: Optional[str] = None
        self._cached_version: Optional[str] = None
        
        logger.info("Initialized MethodologyLoader")

    async def load_pdf_from_box(self, file_id: Optional[str] = None) -> str:
        """Load methodology PDF from Box and extract text.
        
        Args:
            file_id: Box file ID for the methodology PDF. If not provided,
                    uses the file_id from initialization.
        
        Returns:
            Extracted text content from the PDF
            
        Raises:
            MethodologyLoaderError: If PDF loading or extraction fails
        """
        # Use provided file_id or fall back to instance variable
        target_file_id = file_id or self.methodology_file_id
        
        if not target_file_id:
            raise MethodologyLoaderError(
                "No methodology file ID provided. "
                "Specify file_id parameter or set methodology_file_id during initialization."
            )
        
        try:
            logger.info(f"Loading methodology PDF from Box (file_id: {target_file_id})")
            
            # Download PDF content from Box
            pdf_bytes = await self.box_client.read_file(target_file_id)
            
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(pdf_bytes)
            
            # Cache the content
            self._cached_content = text_content
            self._cached_version = target_file_id
            
            logger.info(
                f"Successfully loaded methodology PDF "
                f"({len(text_content)} characters extracted)"
            )
            
            return text_content
            
        except BoxMCPClientError as e:
            logger.error(f"Failed to load methodology from Box: {e}")
            raise MethodologyLoaderError(f"Box operation failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to extract text from methodology PDF: {e}")
            raise MethodologyLoaderError(f"PDF extraction failed: {e}") from e

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text content from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            MethodologyLoaderError: If PDF extraction fails
        """
        try:
            # Create a BytesIO object from bytes
            pdf_file = BytesIO(pdf_bytes)
            
            # Create PDF reader
            pdf_reader = PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                    logger.debug(f"Extracted text from page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    # Continue with other pages
            
            if not text_content:
                raise MethodologyLoaderError("No text content extracted from PDF")
            
            # Join all pages with newlines
            full_text = "\n\n".join(text_content)
            
            return full_text
            
        except MethodologyLoaderError:
            raise
        except Exception as e:
            raise MethodologyLoaderError(f"PDF parsing failed: {e}") from e

    def get_methodology_content(self) -> str:
        """Get cached methodology content.
        
        Returns:
            Cached methodology text content
            
        Raises:
            MethodologyLoaderError: If no content is cached
        """
        if self._cached_content is None:
            raise MethodologyLoaderError(
                "No methodology content cached. Call load_pdf_from_box() first."
            )
        
        return self._cached_content

    async def get_latest_methodology_version(self) -> Dict[str, Any]:
        """Get latest methodology file version from Box.
        
        Returns:
            Dictionary containing file metadata including version information
            
        Raises:
            MethodologyLoaderError: If version retrieval fails
        """
        if not self.methodology_file_id:
            raise MethodologyLoaderError(
                "No methodology file ID configured. "
                "Set methodology_file_id during initialization."
            )
        
        try:
            logger.info(f"Retrieving methodology file info from Box")
            
            result = await self.box_client.get_file_info(self.methodology_file_id)
            
            if not result.success:
                raise MethodologyLoaderError(
                    f"Failed to get file info: {result.error}"
                )
            
            # Extract version information from result
            file_info = result.data
            
            # Parse file info based on MCP response format
            version_info = {
                "file_id": self.methodology_file_id,
                "data": file_info,
            }
            
            logger.info(f"Retrieved methodology version info")
            
            return version_info
            
        except BoxMCPClientError as e:
            logger.error(f"Failed to get methodology version from Box: {e}")
            raise MethodologyLoaderError(f"Box operation failed: {e}") from e

    def clear_cache(self) -> None:
        """Clear cached methodology content.
        
        This can be used to force a reload of the methodology from Box.
        """
        self._cached_content = None
        self._cached_version = None
        logger.info("Cleared methodology cache")

    @property
    def is_cached(self) -> bool:
        """Check if methodology content is currently cached.
        
        Returns:
            True if content is cached, False otherwise
        """
        return self._cached_content is not None
