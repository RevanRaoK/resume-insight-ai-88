# Requirements Document

## Introduction

SmartResume AI Resume Analyzer is an intelligent backend system that transforms raw resume documents into structured data and provides personalized career guidance through AI-powered analysis. The system serves as a career co-pilot, offering actionable insights to help job seekers optimize their resumes for specific job opportunities and improve their chances of passing through Applicant Tracking Systems (ATS).

## Glossary

- **Document_Ingestion_System**: The backend component responsible for extracting text from various document formats (PDF, DOCX, TXT)
- **NLU_System**: Natural Language Understanding system that performs Named Entity Recognition on resume text
- **Semantic_Analysis_System**: Component that calculates compatibility scores between resumes and job descriptions using semantic embeddings
- **AI_Feedback_System**: Generative AI component that provides personalized career coaching recommendations
- **Resume_Entity**: Structured data extracted from resume text including skills, experience, education, and contact information
- **Match_Score**: Numerical compatibility rating between a resume and job description (0-100%)
- **Supabase_Database**: PostgreSQL database managed by Supabase containing users, resumes, and analyses tables
- **JWT_Token**: JSON Web Token issued by Supabase Auth for user authentication
- **OCR_Pipeline**: Optical Character Recognition system for processing scanned/image-based documents

## Requirements

### Requirement 1

**User Story:** As a job seeker, I want to upload my resume in various formats, so that I can get it analyzed regardless of how I created it

#### Acceptance Criteria

1. WHEN a user uploads a PDF file, THE Document_Ingestion_System SHALL extract text using pdfplumber library
2. IF the extracted text is less than 200 characters, THEN THE Document_Ingestion_System SHALL process the PDF using OCR pipeline with pdf2image and pytesseract
3. WHEN a user uploads a DOCX file, THE Document_Ingestion_System SHALL extract text using python-docx library
4. WHEN a user uploads a TXT file, THE Document_Ingestion_System SHALL detect character encoding using chardet library before processing
5. IF a user uploads an unsupported file format, THEN THE Document_Ingestion_System SHALL reject the file with a clear error message

### Requirement 2

**User Story:** As a job seeker, I want my resume text to be converted into structured data, so that the system can understand my qualifications and experience

#### Acceptance Criteria

1. WHEN resume text is processed, THE NLU_System SHALL use the yashpwr/resume-ner-bert-v2 model for Named Entity Recognition
2. THE NLU_System SHALL extract entities including skills, job titles, company names, education, and contact information
3. THE NLU_System SHALL group adjacent tokens of the same entity type into single coherent entities
4. THE NLU_System SHALL filter out entities with confidence scores below 0.80
5. IF the NER model fails, THEN THE NLU_System SHALL use fallback regex patterns and skill dictionaries for basic extraction

### Requirement 3

**User Story:** As a job seeker, I want to see how well my resume matches a specific job description, so that I can understand my compatibility for the role

#### Acceptance Criteria

1. WHEN a job description is provided, THE Semantic_Analysis_System SHALL generate semantic embeddings using sentence-transformers/all-MiniLM-L6-v2 model
2. THE Semantic_Analysis_System SHALL calculate cosine similarity between resume and job description vectors
3. THE Semantic_Analysis_System SHALL normalize the similarity score to a percentage from 0 to 100
4. THE Semantic_Analysis_System SHALL identify matching keywords between resume and job description
5. THE Semantic_Analysis_System SHALL identify missing keywords from the job description that are not in the resume

### Requirement 4

**User Story:** As a job seeker, I want to receive personalized feedback on how to improve my resume, so that I can make targeted improvements for better job prospects

#### Acceptance Criteria

1. WHEN analysis is complete, THE AI_Feedback_System SHALL generate recommendations using Google Gemini API
2. THE AI_Feedback_System SHALL provide feedback in structured JSON format with categories, priorities, and specific recommendations
3. THE AI_Feedback_System SHALL base recommendations on extracted entities, match score, and keyword analysis
4. THE AI_Feedback_System SHALL implement retry mechanism with exponential backoff for API reliability
5. IF the Gemini API response is malformed, THEN THE AI_Feedback_System SHALL parse and extract valid JSON content

### Requirement 5

**User Story:** As a system administrator, I want the backend to handle multiple concurrent users securely, so that the service remains stable and user data is protected

#### Acceptance Criteria

1. THE Document_Ingestion_System SHALL validate file size limits of 10MB maximum
2. THE Document_Ingestion_System SHALL verify MIME types using python-magic library
3. WHEN a user makes an API request, THE system SHALL verify JWT tokens with Supabase before processing
4. THE system SHALL implement rate limiting of 10 analysis requests per user per hour
5. THE system SHALL handle at least 50 concurrent users without performance degradation

### Requirement 6

**User Story:** As a developer, I want comprehensive logging and error handling, so that I can monitor system performance and troubleshoot issues effectively

#### Acceptance Criteria

1. THE system SHALL implement structured JSON logging with timestamps, log levels, and contextual data
2. THE system SHALL sanitize all user-provided inputs to prevent security vulnerabilities
3. THE system SHALL store all secrets in environment variables
4. THE system SHALL complete end-to-end analysis in under 30 seconds for 95% of requests
5. THE system SHALL cache ML models in memory at startup to minimize latency

### Requirement 7

**User Story:** As a job seeker, I want my analysis results to be stored and retrievable, so that I can review past analyses and track my progress

#### Acceptance Criteria

1. WHEN analysis is complete, THE system SHALL store results in the Supabase_Database analyses table
2. THE system SHALL store match scores, AI feedback, and keyword analysis as structured data
3. WHEN a user requests past analyses, THE system SHALL retrieve results filtered by user authentication
4. THE system SHALL maintain referential integrity between users, resumes, and analyses tables
5. THE system SHALL perform all database operations asynchronously for optimal performance