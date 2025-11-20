# Implementation Plan

- [x] 1. Set up project structure and development environment
  - Initialize Python project with pyproject.toml or requirements.txt
  - Set up Flask application with Flask-RESTX for API documentation
  - Configure PostgreSQL database connection with SQLAlchemy
  - Set up environment variable management using python-dotenv
  - Install and configure Box MCP server following https://developer.box.com/guides/box-mcp/self-hosted/
  - Configure testing framework (pytest) and property-based testing library (Hypothesis)
  - Create project structure: app/, models/, services/, tests/
  - _Requirements: 8.1_

- [x] 2. Implement Box MCP Client integration
  - Create BoxMCPClient class in services/box_mcp_client.py with MCP connection management
  - Implement MCP tool wrappers for box_search, box_read_file, box_upload_file, box_create_folder
  - Add error handling and retry logic for MCP tool calls using tenacity library
  - _Requirements: 8.1, 8.2_

- [ ]* 2.1 Write property test for Box MCP file operations
  - **Property 14: Methodology loaded from Box**
  - **Validates: Requirements 8.2**

- [-] 3. Implement Methodology Loader component
  - Create MethodologyLoader class in services/methodology_loader.py that uses BoxMCPClient
  - Implement load_pdf_from_box method to retrieve methodology from Box
  - Add PDF text extraction using PyPDF2 or pdfplumber library
  - Implement in-memory caching for methodology content using functools.lru_cache
  - _Requirements: 3.1, 8.2_

- [ ]* 3.1 Write unit tests for methodology loading and caching
  - Test PDF retrieval from Box via MCP
  - Test text extraction from PDF
  - Test caching behavior
  - _Requirements: 3.1, 8.2_

- [ ] 4. Implement Financial Data Retriever component
  - Create FinancialDataRetriever class in services/financial_data_retriever.py with provider integration (e.g., Alpha Vantage or Financial Modeling Prep)
  - Implement get_company_data method to fetch financial statements using requests library
  - Implement search_companies method for company lookup
  - Add data normalization logic to standardize provider responses
  - Implement data quality validation (completeness, age checks)
  - _Requirements: 1.1, 4.1, 4.2_

- [ ]* 4.1 Write property test for data retrieval
  - **Property 1: Valid company data retrieval**
  - **Validates: Requirements 1.1**

- [ ]* 4.2 Write property test for data validation
  - **Property 8: Financial data validation**
  - **Validates: Requirements 4.2, 4.3**

- [ ]* 4.3 Write unit tests for financial data retrieval
  - Test API integration with mock responses
  - Test data normalization
  - Test error handling for API failures
  - _Requirements: 1.1, 4.1, 4.2_

- [ ] 5. Implement LLM Service component
  - Create LLMService class in services/llm_service.py with OpenAI or Anthropic SDK integration
  - Implement apply_methodology method that constructs prompts with methodology and financial data
  - Add structured output parsing to extract rating, score, metrics, and breakdown using Pydantic
  - Implement retry logic with exponential backoff for rate limits using tenacity
  - Add response validation to ensure LLM output matches expected schema
  - _Requirements: 3.2, 3.3_

- [ ]* 5.1 Write property test for LLM context completeness
  - **Property 5: LLM receives complete context**
  - **Validates: Requirements 3.3**

- [ ]* 5.2 Write unit tests for LLM service
  - Test prompt construction
  - Test response parsing
  - Test error handling and retries
  - _Requirements: 3.2, 3.3_

- [ ] 6. Implement Rating Engine component
  - Create RatingEngine class in services/rating_engine.py that orchestrates the rating workflow
  - Implement calculate_rating method that coordinates data retrieval, methodology loading, and LLM invocation
  - Add logic to prepare source documents (financial data snapshot, methodology snapshot) as JSON and text files
  - Implement rating result validation using Pydantic models
  - _Requirements: 1.2, 3.2_

- [ ]* 6.1 Write property test for rating generation
  - **Property 2: Rating generation from financial data**
  - **Validates: Requirements 1.2**

- [ ]* 6.2 Write property test for rating idempotence
  - **Property 6: Rating calculation idempotence**
  - **Validates: Requirements 3.4**

- [ ]* 6.3 Write property test for rating output completeness
  - **Property 3: Rating output completeness**
  - **Validates: Requirements 2.1, 2.2, 2.3**

- [ ] 7. Implement Rating Storage component with Box integration
  - Create RatingStorage class in services/rating_storage.py with SQLAlchemy and Box MCP integration
  - Create SQLAlchemy models in models/rating.py for rating metadata
  - Implement save_rating method to persist rating metadata to PostgreSQL
  - Implement save_rating_package_to_box method to upload rating report and source documents
  - Create folder structure management (ensure_company_folder, ensure_rating_folder)
  - Add metadata tagging for Box files using MCP tools
  - Implement historical ratings retrieval from database with SQLAlchemy queries
  - _Requirements: 6.1, 8.3, 8.4, 8.5_

- [ ]* 7.1 Write property test for rating persistence
  - **Property 10: Rating persistence with metadata**
  - **Validates: Requirements 6.1**

- [ ]* 7.2 Write property test for Box upload with source documents
  - **Property 15: Rating report and source documents uploaded to Box with metadata**
  - **Validates: Requirements 8.3, 8.4, 8.5**

- [ ]* 7.3 Write property test for historical ratings retrieval
  - **Property 11: Historical ratings retrieval completeness**
  - **Validates: Requirements 6.2**

- [ ]* 7.4 Write property test for historical ratings ordering
  - **Property 12: Historical ratings ordering and completeness**
  - **Validates: Requirements 6.3, 6.4**

- [ ]* 7.5 Write unit tests for rating storage
  - Test database operations
  - Test Box folder creation
  - Test file uploads with metadata
  - _Requirements: 6.1, 8.3, 8.4, 8.5_

- [ ] 8. Implement API endpoints
  - Create Flask blueprints in app/routes/ for API organization
  - Create POST /api/companies/search endpoint for company search
  - Create POST /api/ratings/generate endpoint for rating generation
  - Create GET /api/ratings/history/<company_id> endpoint for historical ratings
  - Create GET /api/methodology endpoint for methodology information
  - Add request validation using Flask-RESTX models or marshmallow
  - Add error handling middleware with custom error handlers
  - _Requirements: 1.1, 1.2, 2.4, 6.2_

- [ ]* 8.1 Write property test for company search
  - **Property 9: Company search returns matches**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [ ]* 8.2 Write property test for invalid company handling
  - **Property 4: Invalid company error handling**
  - **Validates: Requirements 1.4**

- [ ]* 8.3 Write unit tests for API endpoints
  - Test request validation using Flask test client
  - Test response formatting
  - Test error handling
  - _Requirements: 1.1, 1.2, 2.4, 6.2_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement error handling and logging
  - Add comprehensive error handling for Financial Data Provider failures
  - Add error handling for Box MCP connection and tool failures
  - Add error handling for LLM API failures
  - Implement retry logic with exponential backoff for network errors using tenacity
  - Set up Python logging with appropriate log levels and handlers
  - Implement error message sanitization for user-facing errors
  - Create custom exception classes in app/exceptions.py
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 10.1 Write property test for error message sanitization
  - **Property 16: Error messages sanitized**
  - **Validates: Requirements 9.5**

- [ ]* 10.2 Write unit tests for error handling
  - Test retry logic
  - Test error message sanitization
  - Test logging behavior
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 11. Implement frontend interface
  - Create Flask templates in templates/ using Jinja2 with Bootstrap or Tailwind CSS
  - Create company search page with autocomplete using JavaScript
  - Create rating display page with visual indicators (letter grade, color coding)
  - Create methodology breakdown visualization using Chart.js
  - Create historical ratings timeline page
  - Add loading states and error message displays
  - Integrate with backend API endpoints using fetch or axios
  - _Requirements: 1.3, 1.5, 2.1, 2.2, 2.3, 6.3_

- [ ]* 11.1 Write unit tests for Flask routes
  - Test template rendering
  - Test context data passed to templates
  - Test error handling in routes
  - _Requirements: 1.3, 2.1, 6.3_

- [ ] 12. Implement optional structured methodology conversion tool
  - Create convert_methodology_to_structured method in LLMService
  - Implement CLI tool using Click or argparse to convert PDF to structured JSON format
  - Add validation for structured methodology format using Pydantic
  - Implement fallback logic to use PDF if structured format is invalid
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]* 12.1 Write property test for structured methodology validation
  - **Property 13: Structured methodology validation**
  - **Validates: Requirements 7.4**

- [ ]* 12.2 Write unit tests for methodology conversion
  - Test PDF to structured conversion
  - Test validation logic
  - Test fallback behavior
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 13. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Create deployment configuration
  - Create Dockerfile for Flask application
  - Create docker-compose.yml for local development with PostgreSQL and Box MCP server
  - Document Box MCP server setup and configuration in README.md
  - Create environment variable template (.env.example)
  - Create requirements.txt or pyproject.toml with all dependencies
  - Write deployment documentation
  - _Requirements: 8.1_
