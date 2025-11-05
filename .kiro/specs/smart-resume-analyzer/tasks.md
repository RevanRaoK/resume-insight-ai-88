# Implementation Plan

- [x] 1. Set up project structure and core infrastructure





  - Create FastAPI application directory structure with routers, services, models, and utils folders
  - Set up configuration management with environment variables for API keys and database connections
  - Implement structured JSON logging with contextual data (user_id, request_id, timestamps)
  - Create custom exception hierarchy for different error types (DocumentProcessingError, NLUProcessingError, etc.)
  - _Requirements: 6.1, 6.3_

- [x] 2. Implement authentication and security middleware





  - Create JWT authentication middleware that validates Supabase tokens on protected endpoints
  - Implement input sanitization utilities for text inputs and file uploads
  - Set up rate limiting middleware (10 requests per user per hour for analysis endpoints)
  - Add file upload security validation (MIME type checking, size limits, temporary file cleanup)
  - _Requirements: 5.3, 5.4, 6.2_

- [x] 3. Create database service layer





  - Implement async database connection management with connection pooling
  - Create repository classes for users, resumes, and analyses tables following existing Supabase schema
  - Build database service methods for storing and retrieving analysis results
  - Add database health check functionality for monitoring
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4. Build document ingestion system










- [x] 4.1 Implement core document processors


  - Create PDFProcessor class using pdfplumber for digital PDF text extraction
  - Implement OCRProcessor with pdf2image and pytesseract for scanned PDFs with fallback logic
  - Build DOCXProcessor using python-docx for Microsoft Word document processing
  - Create TextProcessor with chardet for encoding detection and plain text processing
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 4.2 Add file validation and security


  - Implement FileValidator class with python-magic for MIME type verification
  - Add file size validation (10MB limit) and security checks
  - Create temporary file management with automatic cleanup
  - Build error handling for unsupported formats with clear error messages
  - _Requirements: 1.5, 5.1, 5.2_

- [x] 4.3 Write unit tests for document processing






  - Create test cases for each document processor with sample files
  - Test OCR fallback logic with scanned PDF samples
  - Validate error handling for corrupted and unsupported files
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 5. Implement Natural Language Understanding system





- [x] 5.1 Set up ML model loading and caching


  - Create ModelCache singleton for loading Hugging Face models at startup
  - Implement NER model loading (yashpwr/resume-ner-bert-v2) with error handling
  - Add model health checks and fallback mechanisms for model failures
  - Build memory-efficient model caching to minimize latency
  - _Requirements: 2.1, 2.5, 6.6_

- [x] 5.2 Build entity extraction pipeline


  - Implement NERProcessor class for running inference on resume text
  - Create EntityPostProcessor for grouping adjacent tokens and filtering low-confidence results
  - Build entity deduplication logic accounting for case-insensitivity
  - Add confidence score filtering (0.80 threshold) and entity validation
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 5.3 Create fallback extraction system


  - Implement FallbackExtractor with regex patterns for emails, phone numbers, LinkedIn URLs
  - Create curated technical skills dictionary as JSON file for rule-based extraction
  - Build fallback logic that activates when NER model confidence is too low
  - Add skill normalization and standardization functionality
  - _Requirements: 2.5_

- [x] 5.4 Write unit tests for NLU system






  - Test NER model integration with sample resume texts
  - Validate entity post-processing and deduplication logic
  - Test fallback extraction with edge cases and model failures
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [-] 6. Build semantic analysis and scoring system



- [x] 6.1 Implement semantic embedding generation


  - Create EmbeddingGenerator class using sentence-transformers/all-MiniLM-L6-v2 model
  - Implement text preprocessing and chunking for long documents
  - Build vector averaging for multi-chunk documents to create single representative embeddings
  - Add embedding caching and optimization for repeated analyses
  - _Requirements: 3.1, 3.2_

- [x] 6.2 Create similarity calculation engine


  - Implement cosine similarity calculation between resume and job description vectors
  - Build score normalization to convert similarity (-1 to 1) to percentage (0-100)
  - Create SimilarityCalculator class with mathematical operations and validation
  - Add confidence metrics and similarity interpretation logic
  - _Requirements: 3.3_

- [x] 6.3 Build intelligent keyword analysis



  - Implement KeywordAnalyzer using spaCy for part-of-speech tagging and noun phrase extraction
  - Create keyword matching logic between resume and job description
  - Build missing keyword identification with frequency-based prioritization
  - Add keyword normalization and synonym handling for better matching
  - _Requirements: 3.4, 3.5_

- [-] 6.4 Write unit tests for semantic analysis

















  - Test embedding generation with various text inputs
  - Validate similarity calculations with known test cases
  - Test keyword analysis with sample resume and job description pairs
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. Implement AI feedback generation system





- [x] 7.1 Set up Google Gemini API integration


  - Create GeminiClient class with API key management from environment variables
  - Implement retry mechanism with exponential backoff for API reliability
  - Add circuit breaker pattern for handling API failures gracefully
  - Build API response validation and error handling
  - _Requirements: 4.4_

- [x] 7.2 Build advanced prompt engineering system


  - Create PromptEngine class with chain-of-thought prompting approach
  - Implement persona priming for career coach expertise simulation
  - Build context injection system for resume entities, match scores, and keywords
  - Create few-shot learning examples for consistent JSON output formatting
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 7.3 Create response parsing and validation


  - Implement ResponseParser for extracting valid JSON from AI responses
  - Build robust parsing that handles conversational text mixed with JSON
  - Create feedback validation against expected schema structure
  - Add fallback parsing for malformed responses with content recovery
  - _Requirements: 4.5_

- [x] 7.4 Write unit tests for AI feedback system






  - Test Gemini API integration with mock responses
  - Validate prompt engineering with various input combinations
  - Test response parsing with malformed and edge case responses
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. Create API endpoints and request handling





- [x] 8.1 Build document upload endpoints


  - Create POST /upload endpoint for resume file uploads with multipart form handling
  - Implement file validation, processing, and storage in database
  - Add progress tracking and async processing for large files
  - Build response formatting with processed document metadata
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 8.2 Implement analysis endpoints


  - Create POST /analyze endpoint for resume-job description analysis
  - Build request validation using Pydantic models for job descriptions and resume references
  - Implement complete analysis pipeline orchestration (NLU → Semantic → AI Feedback)
  - Add response formatting with structured analysis results and timing information
  - _Requirements: 2.1, 3.1, 4.1, 7.1_

- [x] 8.3 Create history and retrieval endpoints


  - Build GET /analyses endpoint for retrieving user's past analyses with pagination
  - Implement GET /analyses/{analysis_id} for specific analysis retrieval
  - Add filtering and sorting capabilities for analysis history
  - Create user-specific data access with proper authorization checks
  - _Requirements: 7.2, 7.3_

- [x] 8.4 Add health check and monitoring endpoints


  - Create GET /health endpoint with comprehensive system health checks
  - Implement dependency health checks (database, ML models, external APIs)
  - Build metrics endpoints for monitoring system performance
  - Add status reporting for all critical system components
  - _Requirements: 6.1, 6.6_

- [x] 8.5 Write integration tests for API endpoints






  - Test complete end-to-end analysis workflow with real files
  - Validate authentication and authorization on protected endpoints
  - Test error handling and edge cases for all endpoints
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.3, 7.1_

- [x] 9. Implement performance optimization and monitoring





- [x] 9.1 Add async processing optimizations


  - Optimize all I/O operations (database calls, API requests) for async execution
  - Implement connection pooling for database operations with proper resource management
  - Add background task processing for long-running analyses (optional enhancement)
  - Create async generators for streaming document processing pipeline
  - _Requirements: 6.5, 6.6_

- [x] 9.2 Build comprehensive monitoring system


  - Implement metrics collection for request latency, error rates, and model inference times
  - Create performance monitoring for database queries and external API calls
  - Add user session tracking and concurrent user monitoring
  - Build alerting system for performance degradation and system failures
  - _Requirements: 5.5, 6.1, 6.6_

- [x] 9.3 Write performance tests






  - Create load tests simulating 50 concurrent users using locust or similar
  - Test system performance under various load conditions
  - Validate 30-second response time requirement for 95% of requests
  - _Requirements: 5.5, 6.6_

- [x] 10. Final integration and deployment preparation





- [x] 10.1 Complete system integration testing


  - Test complete workflow from file upload through AI feedback generation
  - Validate integration with existing Supabase database and authentication
  - Test error handling and recovery across all system components
  - Verify performance requirements under realistic load conditions
  - _Requirements: 5.5, 6.6, 7.4, 7.5_

- [x] 10.2 Create deployment configuration


  - Set up production environment configuration with proper secret management
  - Create Docker configuration for containerized deployment (optional)
  - Build deployment scripts and environment setup documentation
  - Add production logging and monitoring configuration
  - _Requirements: 6.1, 6.3_

- [x] 10.3 Write comprehensive system documentation






  - Create API documentation with OpenAPI/Swagger integration
  - Document deployment procedures and environment setup
  - Create troubleshooting guides and operational runbooks
  - _Requirements: 6.1_