"""Rating Storage component for persisting ratings to database and Box."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.rating import Rating
from services.box_mcp_client import BoxMCPClient, BoxMCPToolError, MCPToolResult
from services.rating_engine import RatingResult, SourceDocument


logger = logging.getLogger(__name__)


class RatingStorageError(Exception):
    """Base exception for Rating Storage errors."""
    pass


class RatingPackageInfo:
    """Information about a rating package stored in Box."""
    
    def __init__(
        self,
        rating_report_file_id: str,
        source_document_file_ids: List[str],
        folder_path: str,
        folder_id: str
    ):
        """Initialize rating package info.
        
        Args:
            rating_report_file_id: Box file ID of the rating report
            source_document_file_ids: List of Box file IDs for source documents
            folder_path: Path to the folder in Box
            folder_id: Box folder ID
        """
        self.rating_report_file_id = rating_report_file_id
        self.source_document_file_ids = source_document_file_ids
        self.folder_path = folder_path
        self.folder_id = folder_id


class RatingStorage:
    """Persist ratings to database and Box.
    
    This component handles:
    - Saving rating metadata to PostgreSQL
    - Uploading rating reports and source documents to Box
    - Managing Box folder structure
    - Retrieving historical ratings
    """

    def __init__(
        self,
        db_session: Session,
        box_client: BoxMCPClient,
        ratings_root_folder_id: str
    ):
        """Initialize Rating Storage.
        
        Args:
            db_session: SQLAlchemy database session
            box_client: BoxMCPClient for Box operations
            ratings_root_folder_id: Root folder ID in Box for all ratings
        """
        self.db_session = db_session
        self.box_client = box_client
        self.ratings_root_folder_id = ratings_root_folder_id
        
        logger.info("Initialized RatingStorage")

    def save_rating(self, rating: RatingResult) -> Rating:
        """Save rating metadata to database.
        
        Args:
            rating: RatingResult to save
            
        Returns:
            Rating: Saved Rating model instance
            
        Raises:
            RatingStorageError: If save fails
        """
        try:
            logger.info(
                f"Saving rating for {rating.company_name} ({rating.ticker}): "
                f"{rating.rating}"
            )
            
            # Convert metrics to dict
            metrics_dict = rating.metrics.dict() if rating.metrics else {}
            
            # Convert breakdown to list of dicts
            breakdown_list = [
                {
                    'category': b.category,
                    'weight': b.weight,
                    'score': b.score,
                    'metrics': b.metrics,
                    'reasoning': b.reasoning
                }
                for b in rating.breakdown
            ]
            
            # Create Rating model instance
            db_rating = Rating(
                company_id=rating.company_id,
                company_name=rating.company_name,
                ticker=rating.ticker,
                rating=rating.rating,
                score=rating.score,
                confidence=rating.confidence,
                timestamp=rating.timestamp,
                methodology_version=rating.methodology_version,
                metrics=metrics_dict,
                breakdown=breakdown_list,
                reasoning=rating.reasoning,
            )
            
            # Add to session and commit
            self.db_session.add(db_rating)
            self.db_session.commit()
            self.db_session.refresh(db_rating)
            
            logger.info(f"Rating saved to database with ID: {db_rating.id}")
            
            return db_rating
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to save rating to database: {e}")
            raise RatingStorageError(f"Database save failed: {e}") from e

    async def save_rating_package_to_box(
        self,
        rating: RatingResult,
        company_id: str,
        source_documents: List[SourceDocument]
    ) -> RatingPackageInfo:
        """Upload rating report and source documents to Box.
        
        This method:
        1. Creates company folder if needed
        2. Creates rating-specific subfolder
        3. Uploads rating report PDF
        4. Uploads all source documents
        5. Adds metadata to all files
        
        Args:
            rating: RatingResult to upload
            company_id: Company identifier
            source_documents: List of source documents to upload
            
        Returns:
            RatingPackageInfo with file IDs and folder path
            
        Raises:
            RatingStorageError: If upload fails
        """
        try:
            logger.info(
                f"Uploading rating package to Box for {rating.company_name} "
                f"({rating.ticker})"
            )
            
            # Step 1: Ensure company folder exists
            company_folder_id = await self.ensure_company_folder(
                company_id=company_id,
                company_name=rating.company_name,
                ticker=rating.ticker
            )
            
            # Step 2: Create rating-specific folder
            rating_folder_id = await self.ensure_rating_folder(
                company_folder_id=company_folder_id,
                rating_date=rating.timestamp
            )
            
            # Step 3: Generate and upload rating report
            rating_report_content = self._generate_rating_report(rating)
            report_file_name = f"rating_report_{rating.ticker}_{rating.timestamp.strftime('%Y%m%d')}.json"
            
            report_upload_result = await self.box_client.upload_file(
                folder_id=rating_folder_id,
                file_name=report_file_name,
                content=rating_report_content
            )
            
            if not report_upload_result.success:
                raise RatingStorageError(
                    f"Failed to upload rating report: {report_upload_result.error}"
                )
            
            report_file_id = self._extract_file_id(report_upload_result.data)
            logger.info(f"Rating report uploaded (file_id: {report_file_id})")
            
            # Step 4: Upload source documents
            source_file_ids = []
            for source_doc in source_documents:
                upload_result = await self.box_client.upload_file(
                    folder_id=rating_folder_id,
                    file_name=source_doc.file_name,
                    content=source_doc.content
                )
                
                if not upload_result.success:
                    logger.warning(
                        f"Failed to upload source document {source_doc.file_name}: "
                        f"{upload_result.error}"
                    )
                    continue
                
                file_id = self._extract_file_id(upload_result.data)
                source_file_ids.append(file_id)
                logger.info(
                    f"Source document uploaded: {source_doc.file_name} "
                    f"(file_id: {file_id})"
                )
                
                # Add metadata to source document
                await self._add_file_metadata(
                    file_id=file_id,
                    metadata={
                        **source_doc.metadata,
                        'document_type': source_doc.type,
                        'rating': rating.rating,
                        'company_id': company_id,
                    }
                )
            
            # Step 5: Add metadata to rating report
            await self._add_file_metadata(
                file_id=report_file_id,
                metadata={
                    'company_id': company_id,
                    'company_name': rating.company_name,
                    'ticker': rating.ticker,
                    'rating': rating.rating,
                    'score': str(rating.score),
                    'timestamp': rating.timestamp.isoformat(),
                    'methodology_version': rating.methodology_version,
                }
            )
            
            # Construct folder path
            folder_path = (
                f"/Credit Ratings/Companies/"
                f"{rating.ticker} - {rating.company_name}/"
                f"{rating.timestamp.strftime('%Y-%m-%d')}_Rating_{rating.rating}"
            )
            
            logger.info(
                f"Rating package uploaded successfully to {folder_path}"
            )
            
            return RatingPackageInfo(
                rating_report_file_id=report_file_id,
                source_document_file_ids=source_file_ids,
                folder_path=folder_path,
                folder_id=rating_folder_id
            )
            
        except BoxMCPToolError as e:
            logger.error(f"Box operation failed: {e}")
            raise RatingStorageError(f"Failed to upload to Box: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error uploading rating package: {e}")
            raise RatingStorageError(f"Upload failed: {e}") from e

    async def ensure_company_folder(
        self,
        company_id: str,
        company_name: str,
        ticker: str
    ) -> str:
        """Create company folder in Box if it doesn't exist.
        
        Args:
            company_id: Company identifier
            company_name: Company name
            ticker: Company ticker symbol
            
        Returns:
            Box folder ID for the company
            
        Raises:
            RatingStorageError: If folder creation fails
        """
        folder_name = f"{ticker} - {company_name}"
        
        try:
            # Search for existing folder
            logger.debug(f"Searching for company folder: {folder_name}")
            search_result = await self.box_client.search_files(
                query=folder_name,
                folder_id=self.ratings_root_folder_id
            )
            
            if search_result.success and search_result.data:
                # Parse search results to find matching folder
                folder_id = self._find_folder_in_search_results(
                    search_result.data,
                    folder_name
                )
                if folder_id:
                    logger.info(f"Found existing company folder: {folder_id}")
                    return folder_id
            
            # Folder doesn't exist, create it
            logger.info(f"Creating company folder: {folder_name}")
            create_result = await self.box_client.create_folder(
                parent_folder_id=self.ratings_root_folder_id,
                folder_name=folder_name
            )
            
            if not create_result.success:
                raise RatingStorageError(
                    f"Failed to create company folder: {create_result.error}"
                )
            
            folder_id = self._extract_folder_id(create_result.data)
            logger.info(f"Created company folder: {folder_id}")
            
            return folder_id
            
        except BoxMCPToolError as e:
            logger.error(f"Box operation failed: {e}")
            raise RatingStorageError(f"Failed to ensure company folder: {e}") from e

    async def ensure_rating_folder(
        self,
        company_folder_id: str,
        rating_date: datetime
    ) -> str:
        """Create rating-specific folder in Box.
        
        Args:
            company_folder_id: Parent company folder ID
            rating_date: Date of the rating
            
        Returns:
            Box folder ID for the rating
            
        Raises:
            RatingStorageError: If folder creation fails
        """
        # Note: We don't have the rating yet, so we'll create a folder with date
        # and update it later if needed
        folder_name = rating_date.strftime('%Y-%m-%d')
        
        try:
            logger.info(f"Creating rating folder: {folder_name}")
            create_result = await self.box_client.create_folder(
                parent_folder_id=company_folder_id,
                folder_name=folder_name
            )
            
            if not create_result.success:
                # Folder might already exist, try to find it
                search_result = await self.box_client.search_files(
                    query=folder_name,
                    folder_id=company_folder_id
                )
                
                if search_result.success and search_result.data:
                    folder_id = self._find_folder_in_search_results(
                        search_result.data,
                        folder_name
                    )
                    if folder_id:
                        logger.info(f"Found existing rating folder: {folder_id}")
                        return folder_id
                
                raise RatingStorageError(
                    f"Failed to create rating folder: {create_result.error}"
                )
            
            folder_id = self._extract_folder_id(create_result.data)
            logger.info(f"Created rating folder: {folder_id}")
            
            return folder_id
            
        except BoxMCPToolError as e:
            logger.error(f"Box operation failed: {e}")
            raise RatingStorageError(f"Failed to ensure rating folder: {e}") from e

    def get_historical_ratings(
        self,
        company_id: str,
        limit: Optional[int] = None
    ) -> List[Rating]:
        """Retrieve historical ratings from database.
        
        Args:
            company_id: Company identifier
            limit: Optional limit on number of results
            
        Returns:
            List of Rating instances in reverse chronological order
            
        Raises:
            RatingStorageError: If retrieval fails
        """
        try:
            logger.info(f"Retrieving historical ratings for company: {company_id}")
            
            query = (
                self.db_session.query(Rating)
                .filter(Rating.company_id == company_id)
                .order_by(desc(Rating.timestamp))
            )
            
            if limit:
                query = query.limit(limit)
            
            ratings = query.all()
            
            logger.info(f"Retrieved {len(ratings)} historical ratings")
            
            return ratings
            
        except Exception as e:
            logger.error(f"Failed to retrieve historical ratings: {e}")
            raise RatingStorageError(f"Database query failed: {e}") from e

    def get_latest_rating(self, company_id: str) -> Optional[Rating]:
        """Get most recent rating for a company.
        
        Args:
            company_id: Company identifier
            
        Returns:
            Latest Rating instance or None if no ratings exist
            
        Raises:
            RatingStorageError: If retrieval fails
        """
        try:
            logger.info(f"Retrieving latest rating for company: {company_id}")
            
            rating = (
                self.db_session.query(Rating)
                .filter(Rating.company_id == company_id)
                .order_by(desc(Rating.timestamp))
                .first()
            )
            
            if rating:
                logger.info(f"Found latest rating: {rating.rating} from {rating.timestamp}")
            else:
                logger.info("No ratings found for company")
            
            return rating
            
        except Exception as e:
            logger.error(f"Failed to retrieve latest rating: {e}")
            raise RatingStorageError(f"Database query failed: {e}") from e

    async def get_rating_report_from_box(self, box_file_id: str) -> bytes:
        """Download rating report from Box.
        
        Args:
            box_file_id: Box file ID of the rating report
            
        Returns:
            File contents as bytes
            
        Raises:
            RatingStorageError: If download fails
        """
        try:
            logger.info(f"Downloading rating report from Box: {box_file_id}")
            
            content = await self.box_client.read_file(box_file_id)
            
            logger.info(f"Downloaded rating report ({len(content)} bytes)")
            
            return content
            
        except BoxMCPToolError as e:
            logger.error(f"Failed to download rating report: {e}")
            raise RatingStorageError(f"Box download failed: {e}") from e

    async def get_source_document_from_box(self, box_file_id: str) -> bytes:
        """Download source document from Box.
        
        Args:
            box_file_id: Box file ID of the source document
            
        Returns:
            File contents as bytes
            
        Raises:
            RatingStorageError: If download fails
        """
        try:
            logger.info(f"Downloading source document from Box: {box_file_id}")
            
            content = await self.box_client.read_file(box_file_id)
            
            logger.info(f"Downloaded source document ({len(content)} bytes)")
            
            return content
            
        except BoxMCPToolError as e:
            logger.error(f"Failed to download source document: {e}")
            raise RatingStorageError(f"Box download failed: {e}") from e

    def update_rating_with_box_info(
        self,
        rating_id: int,
        package_info: RatingPackageInfo
    ) -> Rating:
        """Update rating record with Box storage information.
        
        Args:
            rating_id: Database rating ID
            package_info: RatingPackageInfo with Box file IDs
            
        Returns:
            Updated Rating instance
            
        Raises:
            RatingStorageError: If update fails
        """
        try:
            logger.info(f"Updating rating {rating_id} with Box information")
            
            rating = self.db_session.query(Rating).filter(Rating.id == rating_id).first()
            
            if not rating:
                raise RatingStorageError(f"Rating {rating_id} not found")
            
            rating.box_folder_id = package_info.folder_id
            rating.box_report_file_id = package_info.rating_report_file_id
            rating.box_source_document_ids = package_info.source_document_file_ids
            
            self.db_session.commit()
            self.db_session.refresh(rating)
            
            logger.info(f"Updated rating {rating_id} with Box information")
            
            return rating
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update rating with Box info: {e}")
            raise RatingStorageError(f"Database update failed: {e}") from e

    def _generate_rating_report(self, rating: RatingResult) -> bytes:
        """Generate rating report document.
        
        Args:
            rating: RatingResult to generate report for
            
        Returns:
            Report content as bytes (JSON format)
        """
        # Convert rating to dictionary
        report = {
            'company_id': rating.company_id,
            'company_name': rating.company_name,
            'ticker': rating.ticker,
            'rating': rating.rating,
            'score': rating.score,
            'confidence': rating.confidence,
            'timestamp': rating.timestamp.isoformat(),
            'methodology_version': rating.methodology_version,
            'reasoning': rating.reasoning,
            'metrics': rating.metrics.dict() if rating.metrics else {},
            'breakdown': [
                {
                    'category': b.category,
                    'weight': b.weight,
                    'score': b.score,
                    'metrics': b.metrics,
                    'reasoning': b.reasoning
                }
                for b in rating.breakdown
            ],
        }
        
        # Convert to JSON with pretty formatting
        json_str = json.dumps(report, indent=2, default=str)
        
        return json_str.encode('utf-8')

    async def _add_file_metadata(
        self,
        file_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Add metadata to a Box file.
        
        Args:
            file_id: Box file ID
            metadata: Metadata key-value pairs
        """
        try:
            logger.debug(f"Adding metadata to file {file_id}")
            
            result = await self.box_client.update_file_metadata(
                file_id=file_id,
                metadata=metadata
            )
            
            if not result.success:
                logger.warning(
                    f"Failed to add metadata to file {file_id}: {result.error}"
                )
            else:
                logger.debug(f"Metadata added to file {file_id}")
                
        except Exception as e:
            logger.warning(f"Error adding metadata to file {file_id}: {e}")
            # Don't raise - metadata failure shouldn't fail the upload

    def _extract_file_id(self, data: Any) -> str:
        """Extract file ID from Box API response.
        
        Args:
            data: Response data from Box MCP
            
        Returns:
            File ID string
            
        Raises:
            RatingStorageError: If file ID cannot be extracted
        """
        # Handle different response formats from MCP
        if isinstance(data, list):
            for item in data:
                if hasattr(item, 'text'):
                    text = item.text
                elif isinstance(item, dict) and 'text' in item:
                    text = item['text']
                elif isinstance(item, str):
                    text = item
                else:
                    continue
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and 'id' in parsed:
                        return parsed['id']
                except json.JSONDecodeError:
                    # Try to extract file ID from text
                    import re
                    match = re.search(r'file[_\s]id[:\s]+([0-9]+)', text, re.IGNORECASE)
                    if match:
                        return match.group(1)
        
        elif isinstance(data, dict):
            if 'id' in data:
                return data['id']
            if 'file_id' in data:
                return data['file_id']
        
        elif isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and 'id' in parsed:
                    return parsed['id']
            except json.JSONDecodeError:
                pass
        
        raise RatingStorageError(f"Could not extract file ID from: {data}")

    def _extract_folder_id(self, data: Any) -> str:
        """Extract folder ID from Box API response.
        
        Args:
            data: Response data from Box MCP
            
        Returns:
            Folder ID string
            
        Raises:
            RatingStorageError: If folder ID cannot be extracted
        """
        # Same logic as file ID extraction
        return self._extract_file_id(data)

    def _find_folder_in_search_results(
        self,
        search_data: Any,
        folder_name: str
    ) -> Optional[str]:
        """Find folder ID in search results.
        
        Args:
            search_data: Search results from Box MCP
            folder_name: Name of folder to find
            
        Returns:
            Folder ID if found, None otherwise
        """
        try:
            # Parse search results
            if isinstance(search_data, list):
                for item in search_data:
                    if hasattr(item, 'text'):
                        text = item.text
                    elif isinstance(item, dict) and 'text' in item:
                        text = item['text']
                    elif isinstance(item, str):
                        text = item
                    else:
                        continue
                    
                    # Try to parse as JSON
                    try:
                        results = json.loads(text)
                        if isinstance(results, dict) and 'entries' in results:
                            for entry in results['entries']:
                                if (entry.get('type') == 'folder' and 
                                    entry.get('name') == folder_name):
                                    return entry.get('id')
                        elif isinstance(results, list):
                            for entry in results:
                                if (isinstance(entry, dict) and
                                    entry.get('type') == 'folder' and 
                                    entry.get('name') == folder_name):
                                    return entry.get('id')
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing search results: {e}")
            return None
