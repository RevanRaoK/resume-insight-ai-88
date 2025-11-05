"""
Natural Language Understanding service for resume entity extraction
"""
import re
import json
import os
from typing import List, Dict, Optional, Any, Tuple, Set
from collections import defaultdict
from app.utils.logger import get_logger
from app.utils.ml_utils import model_cache
from app.models.entities import ResumeEntities
from app.core.exceptions import NLUProcessingError

logger = get_logger(__name__)


class NERProcessor:
    """
    Named Entity Recognition processor using Hugging Face transformers.
    Runs inference on resume text to extract structured entities.
    """
    
    def __init__(self):
        self.confidence_threshold = 0.80
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using the NER model.
        
        Args:
            text: Resume text to process
            
        Returns:
            List of entity dictionaries with labels, text, and confidence scores
            
        Raises:
            NLUProcessingError: If NER processing fails
        """
        try:
            # Get NER pipeline from model cache
            ner_pipeline = model_cache.get_ner_pipeline()
            
            if ner_pipeline is None:
                raise NLUProcessingError(
                    "NER model not available",
                    model_name="yashpwr/resume-ner-bert-v2",
                    processing_stage="entity_extraction"
                )
            
            # Clean and preprocess text
            cleaned_text = self._preprocess_text(text)
            
            # Run NER inference
            logger.info("Running NER inference", text_length=len(cleaned_text))
            raw_entities = ner_pipeline(cleaned_text)
            
            # Filter by confidence threshold
            filtered_entities = [
                entity for entity in raw_entities 
                if entity.get('score', 0) >= self.confidence_threshold
            ]
            
            logger.info(
                "NER extraction completed",
                total_entities=len(raw_entities),
                filtered_entities=len(filtered_entities),
                confidence_threshold=self.confidence_threshold
            )
            
            return filtered_entities
            
        except Exception as e:
            logger.error("NER processing failed", error=str(e))
            raise NLUProcessingError(
                f"Entity extraction failed: {str(e)}",
                model_name="yashpwr/resume-ner-bert-v2",
                processing_stage="entity_extraction"
            )
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for NER processing"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might confuse the model
        text = re.sub(r'[^\w\s\-\.\@\(\)\+]', ' ', text)
        
        # Limit text length to prevent memory issues (max 5000 chars)
        if len(text) > 5000:
            text = text[:5000]
            logger.warning("Text truncated for NER processing", original_length=len(text))
        
        return text.strip()


class EntityPostProcessor:
    """
    Post-processes raw NER entities to group adjacent tokens,
    filter low-confidence results, and deduplicate entities.
    """
    
    def __init__(self):
        self.entity_mapping = {
            'PERSON': 'contact_info',
            'EMAIL': 'contact_info', 
            'PHONE': 'contact_info',
            'LINKEDIN': 'contact_info',
            'SKILLS': 'skills',
            'JOB_TITLE': 'job_titles',
            'COMPANY': 'companies',
            'EDUCATION': 'education',
            'DEGREE': 'education',
            'UNIVERSITY': 'education',
            'EXPERIENCE': 'experience'
        }
    
    def process_entities(self, raw_entities: List[Dict[str, Any]]) -> ResumeEntities:
        """
        Process raw NER entities into structured ResumeEntities.
        
        Args:
            raw_entities: Raw entities from NER model
            
        Returns:
            ResumeEntities with grouped and deduplicated entities
        """
        try:
            # Group adjacent tokens
            grouped_entities = self._group_adjacent_tokens(raw_entities)
            
            # Categorize entities
            categorized = self._categorize_entities(grouped_entities)
            
            # Deduplicate entities
            deduplicated = self._deduplicate_entities(categorized)
            
            # Extract contact information
            contact_info = self._extract_contact_info(deduplicated.get('contact_info', []))
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(deduplicated)
            
            # Extract experience years (if available)
            experience_years = self._extract_experience_years(raw_entities)
            
            return ResumeEntities(
                skills=deduplicated.get('skills', []),
                job_titles=deduplicated.get('job_titles', []),
                companies=deduplicated.get('companies', []),
                education=deduplicated.get('education', []),
                contact_info=contact_info,
                experience_years=experience_years,
                confidence_scores=confidence_scores
            )
            
        except Exception as e:
            logger.error("Entity post-processing failed", error=str(e))
            raise NLUProcessingError(
                f"Entity post-processing failed: {str(e)}",
                processing_stage="post_processing"
            )
    
    def _group_adjacent_tokens(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group adjacent tokens of the same entity type into single entities"""
        if not entities:
            return []
        
        grouped = []
        current_group = None
        
        for entity in sorted(entities, key=lambda x: x.get('start', 0)):
            entity_label = entity.get('entity_group', entity.get('label', ''))
            
            if (current_group and 
                current_group['entity_group'] == entity_label and
                abs(entity.get('start', 0) - current_group.get('end', 0)) <= 2):
                # Extend current group
                current_group['word'] += ' ' + entity.get('word', '').replace('##', '')
                current_group['end'] = entity.get('end', current_group['end'])
                current_group['score'] = max(current_group['score'], entity.get('score', 0))
            else:
                # Start new group
                if current_group:
                    grouped.append(current_group)
                
                current_group = {
                    'entity_group': entity_label,
                    'word': entity.get('word', '').replace('##', ''),
                    'start': entity.get('start', 0),
                    'end': entity.get('end', 0),
                    'score': entity.get('score', 0)
                }
        
        if current_group:
            grouped.append(current_group)
        
        return grouped
    
    def _categorize_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize entities by type"""
        categorized = defaultdict(list)
        
        for entity in entities:
            entity_type = entity.get('entity_group', '').upper()
            entity_text = entity.get('word', '').strip()
            
            if entity_text and entity_type in self.entity_mapping:
                category = self.entity_mapping[entity_type]
                categorized[category].append(entity_text)
        
        return dict(categorized)
    
    def _deduplicate_entities(self, categorized: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Remove duplicate entities (case-insensitive)"""
        deduplicated = {}
        
        for category, entities in categorized.items():
            # Use set for deduplication (case-insensitive)
            seen = set()
            unique_entities = []
            
            for entity in entities:
                entity_lower = entity.lower().strip()
                if entity_lower not in seen and len(entity_lower) > 1:
                    seen.add(entity_lower)
                    unique_entities.append(entity.strip())
            
            deduplicated[category] = unique_entities
        
        return deduplicated
    
    def _extract_contact_info(self, contact_entities: List[str]) -> Dict[str, str]:
        """Extract structured contact information"""
        contact_info = {}
        
        for entity in contact_entities:
            entity = entity.strip()
            
            # Email detection
            if '@' in entity and re.match(r'^[^@]+@[^@]+\.[^@]+$', entity):
                contact_info['email'] = entity
            
            # Phone detection
            elif re.match(r'^[\+\-\(\)\s\d]{10,}$', entity):
                contact_info['phone'] = entity
            
            # LinkedIn URL detection
            elif 'linkedin.com' in entity.lower():
                contact_info['linkedin'] = entity
            
            # Name detection (if no other contact info found)
            elif 'name' not in contact_info and len(entity.split()) >= 2:
                contact_info['name'] = entity
        
        return contact_info
    
    def _calculate_confidence_scores(self, categorized: Dict[str, List[str]]) -> Dict[str, float]:
        """Calculate average confidence scores by category"""
        # For now, return default confidence scores
        # In a real implementation, we'd track scores through the pipeline
        return {
            category: 0.85 for category in categorized.keys()
        }
    
    def _extract_experience_years(self, raw_entities: List[Dict[str, Any]]) -> Optional[int]:
        """Extract years of experience from entities (basic implementation)"""
        # This is a simplified implementation
        # In practice, this would require more sophisticated parsing
        for entity in raw_entities:
            text = entity.get('word', '').lower()
            if 'year' in text and any(char.isdigit() for char in text):
                # Extract first number found
                numbers = re.findall(r'\d+', text)
                if numbers:
                    try:
                        return int(numbers[0])
                    except ValueError:
                        continue
        
        return None


class FallbackExtractor:
    """
    Fallback extraction system using regex patterns and skill dictionaries.
    Activates when NER model confidence is too low or model fails.
    """
    
    def __init__(self):
        self.skills_dict = self._load_skills_dictionary()
        self.min_confidence_threshold = 0.70  # Threshold below which fallback activates
        
        # Regex patterns for contact information
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        self.linkedin_pattern = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9-]+/?', re.IGNORECASE)
        
        # Common job title patterns
        self.job_title_keywords = {
            'engineer', 'developer', 'programmer', 'analyst', 'manager', 'director', 
            'lead', 'senior', 'junior', 'principal', 'architect', 'consultant',
            'specialist', 'coordinator', 'administrator', 'technician', 'designer',
            'scientist', 'researcher', 'intern', 'associate', 'executive', 'officer'
        }
        
        # Education keywords
        self.education_keywords = {
            'university', 'college', 'school', 'institute', 'academy', 'bachelor',
            'master', 'phd', 'doctorate', 'degree', 'diploma', 'certificate',
            'bs', 'ba', 'ms', 'ma', 'mba', 'bsc', 'msc', 'beng', 'meng'
        }
    
    def _load_skills_dictionary(self) -> Dict[str, Set[str]]:
        """Load technical skills dictionary from JSON file"""
        try:
            skills_file_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'data', 
                'technical_skills.json'
            )
            
            with open(skills_file_path, 'r', encoding='utf-8') as f:
                skills_data = json.load(f)
            
            # Convert lists to sets for faster lookup and normalize to lowercase
            normalized_skills = {}
            for category, skills_list in skills_data.items():
                normalized_skills[category] = {skill.lower() for skill in skills_list}
            
            logger.info("Skills dictionary loaded successfully", 
                       categories=len(normalized_skills),
                       total_skills=sum(len(skills) for skills in normalized_skills.values()))
            
            return normalized_skills
            
        except Exception as e:
            logger.error("Failed to load skills dictionary", error=str(e))
            # Return empty dict if loading fails
            return {}
    
    def should_use_fallback(self, ner_entities: List[Dict[str, Any]]) -> bool:
        """
        Determine if fallback extraction should be used based on NER confidence.
        
        Args:
            ner_entities: Entities extracted by NER model
            
        Returns:
            True if fallback should be used, False otherwise
        """
        if not ner_entities:
            return True
        
        # Calculate average confidence
        total_confidence = sum(entity.get('score', 0) for entity in ner_entities)
        avg_confidence = total_confidence / len(ner_entities)
        
        use_fallback = avg_confidence < self.min_confidence_threshold
        
        logger.info("Fallback decision made",
                   avg_confidence=avg_confidence,
                   threshold=self.min_confidence_threshold,
                   use_fallback=use_fallback)
        
        return use_fallback
    
    def extract_fallback_entities(self, text: str) -> ResumeEntities:
        """
        Extract entities using rule-based fallback methods.
        
        Args:
            text: Resume text to process
            
        Returns:
            ResumeEntities extracted using fallback methods
        """
        try:
            logger.info("Using fallback extraction", text_length=len(text))
            
            # Extract contact information
            contact_info = self._extract_contact_info_fallback(text)
            
            # Extract skills using dictionary matching
            skills = self._extract_skills_fallback(text)
            
            # Extract job titles using keyword matching
            job_titles = self._extract_job_titles_fallback(text)
            
            # Extract education using keyword matching
            education = self._extract_education_fallback(text)
            
            # Extract companies (basic implementation)
            companies = self._extract_companies_fallback(text)
            
            # Set default confidence scores for fallback extraction
            confidence_scores = {
                'skills': 0.75,
                'job_titles': 0.70,
                'companies': 0.65,
                'education': 0.70,
                'contact_info': 0.80
            }
            
            return ResumeEntities(
                skills=skills,
                job_titles=job_titles,
                companies=companies,
                education=education,
                contact_info=contact_info,
                experience_years=None,  # Not implemented in fallback
                confidence_scores=confidence_scores
            )
            
        except Exception as e:
            logger.error("Fallback extraction failed", error=str(e))
            raise NLUProcessingError(
                f"Fallback extraction failed: {str(e)}",
                processing_stage="fallback_extraction"
            )
    
    def _extract_contact_info_fallback(self, text: str) -> Dict[str, str]:
        """Extract contact information using regex patterns"""
        contact_info = {}
        
        # Extract email
        email_matches = self.email_pattern.findall(text)
        if email_matches:
            contact_info['email'] = email_matches[0]
        
        # Extract phone
        phone_matches = self.phone_pattern.findall(text)
        if phone_matches:
            # Clean up phone number
            phone = re.sub(r'[^\d+]', '', phone_matches[0])
            if len(phone) >= 10:
                contact_info['phone'] = phone_matches[0]
        
        # Extract LinkedIn
        linkedin_matches = self.linkedin_pattern.findall(text)
        if linkedin_matches:
            contact_info['linkedin'] = linkedin_matches[0]
        
        return contact_info
    
    def _extract_skills_fallback(self, text: str) -> List[str]:
        """Extract skills using dictionary matching"""
        found_skills = set()
        text_lower = text.lower()
        
        # Search for skills from all categories
        for category, skills_set in self.skills_dict.items():
            for skill in skills_set:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, text_lower):
                    # Add the original case skill name
                    found_skills.add(skill.title())
        
        # Normalize and deduplicate
        normalized_skills = self._normalize_skills(list(found_skills))
        
        logger.info("Fallback skills extraction completed", 
                   skills_found=len(normalized_skills))
        
        return normalized_skills
    
    def _normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize and standardize skill names"""
        normalized = []
        seen = set()
        
        # Common normalizations
        normalizations = {
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'nodejs': 'Node.js',
            'reactjs': 'React',
            'vuejs': 'Vue.js',
            'angularjs': 'Angular',
            'css3': 'CSS',
            'html5': 'HTML',
            'postgresql': 'PostgreSQL',
            'mysql': 'MySQL',
            'mongodb': 'MongoDB',
            'aws': 'AWS',
            'gcp': 'Google Cloud',
            'azure': 'Azure'
        }
        
        for skill in skills:
            skill_lower = skill.lower().strip()
            
            # Apply normalizations
            normalized_skill = normalizations.get(skill_lower, skill)
            
            if normalized_skill.lower() not in seen:
                seen.add(normalized_skill.lower())
                normalized.append(normalized_skill)
        
        return sorted(normalized)
    
    def _extract_job_titles_fallback(self, text: str) -> List[str]:
        """Extract job titles using keyword matching"""
        job_titles = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Look for lines that contain job title keywords
            if any(keyword in line_lower for keyword in self.job_title_keywords):
                # Clean up the line
                cleaned_title = re.sub(r'[^\w\s]', ' ', line).strip()
                if len(cleaned_title) > 5 and len(cleaned_title) < 100:
                    job_titles.append(cleaned_title)
        
        # Remove duplicates and return first 5
        unique_titles = list(dict.fromkeys(job_titles))[:5]
        
        logger.info("Fallback job titles extraction completed", 
                   titles_found=len(unique_titles))
        
        return unique_titles
    
    def _extract_education_fallback(self, text: str) -> List[str]:
        """Extract education information using keyword matching"""
        education = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Look for lines that contain education keywords
            if any(keyword in line_lower for keyword in self.education_keywords):
                # Clean up the line
                cleaned_education = re.sub(r'[^\w\s\-\.]', ' ', line).strip()
                if len(cleaned_education) > 5 and len(cleaned_education) < 150:
                    education.append(cleaned_education)
        
        # Remove duplicates and return first 5
        unique_education = list(dict.fromkeys(education))[:5]
        
        logger.info("Fallback education extraction completed", 
                   education_found=len(unique_education))
        
        return unique_education
    
    def _extract_companies_fallback(self, text: str) -> List[str]:
        """Extract company names using basic heuristics"""
        companies = []
        
        # Look for common company indicators
        company_indicators = ['inc', 'corp', 'ltd', 'llc', 'company', 'technologies', 'systems', 'solutions']
        
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            
            # Look for lines with company indicators
            if any(indicator in line_lower for indicator in company_indicators):
                # Extract potential company name
                cleaned_company = re.sub(r'[^\w\s\-\.]', ' ', line).strip()
                if len(cleaned_company) > 3 and len(cleaned_company) < 100:
                    companies.append(cleaned_company)
        
        # Remove duplicates and return first 5
        unique_companies = list(dict.fromkeys(companies))[:5]
        
        logger.info("Fallback companies extraction completed", 
                   companies_found=len(unique_companies))
        
        return unique_companies


class NLUService:
    """
    Main NLU service that orchestrates entity extraction pipeline.
    Combines NER processing with post-processing and fallback mechanisms.
    """
    
    def __init__(self):
        self.ner_processor = NERProcessor()
        self.post_processor = EntityPostProcessor()
        self.fallback_extractor = FallbackExtractor()
    
    async def extract_entities(self, text: str) -> ResumeEntities:
        """
        Extract structured entities from resume text.
        Uses NER model with fallback to rule-based extraction when confidence is low.
        
        Args:
            text: Resume text to process
            
        Returns:
            ResumeEntities with extracted and processed entities
            
        Raises:
            NLUProcessingError: If entity extraction fails
        """
        try:
            logger.info("Starting entity extraction", text_length=len(text))
            
            # Attempt NER processing first
            try:
                raw_entities = await self.ner_processor.extract_entities(text)
                
                # Check if we should use fallback based on confidence
                if self.fallback_extractor.should_use_fallback(raw_entities):
                    logger.info("NER confidence too low, using fallback extraction")
                    fallback_entities = self.fallback_extractor.extract_fallback_entities(text)
                    
                    # Merge NER and fallback results
                    processed_entities = self._merge_entities(
                        self.post_processor.process_entities(raw_entities),
                        fallback_entities
                    )
                else:
                    # Use NER results with high confidence
                    processed_entities = self.post_processor.process_entities(raw_entities)
                    
            except Exception as ner_error:
                logger.warning("NER processing failed, falling back to rule-based extraction", 
                             error=str(ner_error))
                
                # Use fallback extraction when NER fails completely
                processed_entities = self.fallback_extractor.extract_fallback_entities(text)
            
            logger.info(
                "Entity extraction completed successfully",
                skills_count=len(processed_entities.skills),
                job_titles_count=len(processed_entities.job_titles),
                companies_count=len(processed_entities.companies),
                education_count=len(processed_entities.education),
                extraction_method="hybrid" if hasattr(processed_entities, '_merged') else "single"
            )
            
            return processed_entities
            
        except Exception as e:
            logger.error("NLU service entity extraction failed", error=str(e))
            raise NLUProcessingError(
                f"Entity extraction pipeline failed: {str(e)}",
                processing_stage="nlu_service"
            )
    
    def _merge_entities(self, ner_entities: ResumeEntities, fallback_entities: ResumeEntities) -> ResumeEntities:
        """
        Merge NER and fallback extraction results, prioritizing higher confidence results.
        
        Args:
            ner_entities: Entities from NER model
            fallback_entities: Entities from fallback extraction
            
        Returns:
            Merged ResumeEntities
        """
        try:
            # Merge skills (combine and deduplicate)
            merged_skills = list(set(ner_entities.skills + fallback_entities.skills))
            
            # Merge job titles (prioritize NER if available, otherwise fallback)
            merged_job_titles = ner_entities.job_titles if ner_entities.job_titles else fallback_entities.job_titles
            
            # Merge companies (prioritize NER if available, otherwise fallback)
            merged_companies = ner_entities.companies if ner_entities.companies else fallback_entities.companies
            
            # Merge education (prioritize NER if available, otherwise fallback)
            merged_education = ner_entities.education if ner_entities.education else fallback_entities.education
            
            # Merge contact info (combine both sources)
            merged_contact_info = {**fallback_entities.contact_info, **ner_entities.contact_info}
            
            # Use NER experience years if available
            merged_experience_years = ner_entities.experience_years
            
            # Merge confidence scores (average where both exist)
            merged_confidence_scores = {}
            for key in set(ner_entities.confidence_scores.keys()) | set(fallback_entities.confidence_scores.keys()):
                ner_score = ner_entities.confidence_scores.get(key, 0)
                fallback_score = fallback_entities.confidence_scores.get(key, 0)
                
                if ner_score > 0 and fallback_score > 0:
                    merged_confidence_scores[key] = (ner_score + fallback_score) / 2
                else:
                    merged_confidence_scores[key] = max(ner_score, fallback_score)
            
            merged_entities = ResumeEntities(
                skills=merged_skills,
                job_titles=merged_job_titles,
                companies=merged_companies,
                education=merged_education,
                contact_info=merged_contact_info,
                experience_years=merged_experience_years,
                confidence_scores=merged_confidence_scores
            )
            
            # Mark as merged for logging
            merged_entities._merged = True
            
            logger.info("Entity merging completed",
                       ner_skills=len(ner_entities.skills),
                       fallback_skills=len(fallback_entities.skills),
                       merged_skills=len(merged_skills))
            
            return merged_entities
            
        except Exception as e:
            logger.error("Entity merging failed", error=str(e))
            # Return fallback entities if merging fails
            return fallback_entities


# Global service instance
nlu_service = NLUService()