"""SQLAlchemy models for rating storage."""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Rating(Base):
    """Rating metadata stored in database.
    
    This model stores the core rating information and metadata.
    Full rating reports and source documents are stored in Box.
    """
    __tablename__ = 'ratings'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company information
    company_id = Column(String(50), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    ticker = Column(String(20), nullable=False, index=True)
    
    # Rating information
    rating = Column(String(10), nullable=False)
    score = Column(Float, nullable=False)
    confidence = Column(Float, default=1.0)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Methodology version
    methodology_version = Column(String(100), nullable=False)
    
    # Financial metrics (stored as JSON)
    metrics = Column(JSONB, nullable=True)
    
    # Breakdown by category (stored as JSON)
    breakdown = Column(JSONB, nullable=True)
    
    # Reasoning
    reasoning = Column(Text, nullable=True)
    
    # Box storage references
    box_folder_id = Column(String(50), nullable=True)
    box_report_file_id = Column(String(50), nullable=True)
    box_source_document_ids = Column(JSONB, nullable=True)  # List of file IDs
    
    def __repr__(self):
        return (
            f"<Rating(id={self.id}, company={self.company_name}, "
            f"ticker={self.ticker}, rating={self.rating}, "
            f"timestamp={self.timestamp})>"
        )
    
    def to_dict(self):
        """Convert rating to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'ticker': self.ticker,
            'rating': self.rating,
            'score': self.score,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'methodology_version': self.methodology_version,
            'metrics': self.metrics,
            'breakdown': self.breakdown,
            'reasoning': self.reasoning,
            'box_folder_id': self.box_folder_id,
            'box_report_file_id': self.box_report_file_id,
            'box_source_document_ids': self.box_source_document_ids,
        }
