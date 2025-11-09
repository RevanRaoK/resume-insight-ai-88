"""
Semantic analysis service for resume-job description compatibility analysis
"""
import re
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from sentence_transformers import SentenceTransformer
import spacy
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
from functools import lru_cache
import hashlib

from app.utils.logger import get_logger
from app.models.entities import CompatibilityAnalysis
from app.core.exceptions import SemanticAnalysisError

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generates semantic embeddings using sentence-transformers model"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self.max_chunk_length = 512  # Model's max sequence length
        self.chunk_overlap = 50  # Overlap between chunks
    
    def _get_model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model"""
        if self._model is None:
            try:
                logger.info("Loading sentence transformer model", model=self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info("Successfully loaded sentence transformer model")
            except Exception as e:
                logger.error("Failed to load sentence transformer model", error=str(e))
                raise SemanticAnalysisError(f"Failed to load embedding model: {str(e)}")
        return self._model
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding generation with length optimization"""
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters that might interfere with embeddings
        text = re.sub(r'[^\w\s\-\.\,\;\:\!\?]', ' ', text)
        
        # PERFORMANCE OPTIMIZATION: Truncate very long texts to prevent slowdown
        max_length = 2000  # Limit to 2000 characters for performance
        if len(text) > max_length:
            logger.info(f"Truncating text from {len(text)} to {max_length} characters for performance")
            # Try to truncate at sentence boundary
            truncated = text[:max_length]
            last_sentence = truncated.rfind('.')
            if last_sentence > max_length * 0.8:  # If we can find a sentence boundary in the last 20%
                text = truncated[:last_sentence + 1]
            else:
                text = truncated
        
        # Normalize case for consistency
        text = text.lower()
        
        return text
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split long text into overlapping chunks for processing"""
        words = text.split()
        
        if len(words) <= self.max_chunk_length:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = min(start + self.max_chunk_length, len(words))
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(words):
                break
        
        return chunks
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate semantic embedding for text with caching and chunking support
        
        Args:
            text: Input text to embed
            
        Returns:
            numpy array representing the text embedding
            
        Raises:
            SemanticAnalysisError: If embedding generation fails
        """
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            # Check cache first
            cache_key = self._get_cache_key(processed_text)
            if cache_key in self._embedding_cache:
                logger.debug("Using cached embedding", cache_key=cache_key[:8])
                return self._embedding_cache[cache_key]
            
            # Get model
            model = self._get_model()
            
            # Chunk text if necessary
            chunks = self._chunk_text(processed_text)
            
            if len(chunks) == 1:
                # Single chunk - direct embedding
                embedding = await asyncio.get_event_loop().run_in_executor(
                    None, model.encode, processed_text
                )
            else:
                # Multiple chunks - generate embeddings and average
                logger.info("Processing multi-chunk text", num_chunks=len(chunks))
                
                chunk_embeddings = []
                for i, chunk in enumerate(chunks):
                    chunk_embedding = await asyncio.get_event_loop().run_in_executor(
                        None, model.encode, chunk
                    )
                    chunk_embeddings.append(chunk_embedding)
                    logger.debug("Processed chunk", chunk_num=i+1, total_chunks=len(chunks))
                
                # Average the embeddings
                embedding = np.mean(chunk_embeddings, axis=0)
            
            # Normalize the embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            # Cache the result
            self._embedding_cache[cache_key] = embedding
            
            logger.info("Generated embedding", 
                       text_length=len(text), 
                       embedding_dim=embedding.shape[0],
                       num_chunks=len(chunks))
            
            return embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e), text_length=len(text))
            raise SemanticAnalysisError(f"Embedding generation failed: {str(e)}")
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self._embedding_cache.clear()
        logger.info("Cleared embedding cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._embedding_cache),
            "model_loaded": self._model is not None
        }


class SimilarityCalculator:
    """Calculates semantic similarity between text embeddings"""
    
    def __init__(self):
        self.min_confidence_threshold = 0.1  # Minimum similarity for meaningful results
        self.high_confidence_threshold = 0.7  # Threshold for high confidence matches
    
    def calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1 to 1)
            
        Raises:
            SemanticAnalysisError: If calculation fails
        """
        try:
            # Ensure embeddings are 2D for sklearn
            if embedding1.ndim == 1:
                embedding1 = embedding1.reshape(1, -1)
            if embedding2.ndim == 1:
                embedding2 = embedding2.reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(embedding1, embedding2)[0, 0]
            
            # Ensure result is within expected range
            similarity = np.clip(similarity, -1.0, 1.0)
            
            logger.debug("Calculated cosine similarity", similarity=similarity)
            return float(similarity)
            
        except Exception as e:
            logger.error("Failed to calculate cosine similarity", error=str(e))
            raise SemanticAnalysisError(f"Similarity calculation failed: {str(e)}")
    
    def normalize_to_percentage(self, similarity: float) -> float:
        """
        Normalize similarity score from (-1, 1) to (0, 100) percentage
        
        Args:
            similarity: Cosine similarity score (-1 to 1)
            
        Returns:
            Normalized percentage score (0 to 100)
        """
        try:
            # Convert from (-1, 1) to (0, 1) then to (0, 100)
            normalized = (similarity + 1) / 2
            percentage = normalized * 100
            
            # Ensure within bounds
            percentage = np.clip(percentage, 0.0, 100.0)
            
            logger.debug("Normalized similarity to percentage", 
                        original=similarity, 
                        percentage=percentage)
            
            return float(percentage)
            
        except Exception as e:
            logger.error("Failed to normalize similarity", error=str(e))
            raise SemanticAnalysisError(f"Similarity normalization failed: {str(e)}")
    
    def get_confidence_level(self, similarity: float) -> str:
        """
        Determine confidence level based on similarity score
        
        Args:
            similarity: Cosine similarity score (-1 to 1)
            
        Returns:
            Confidence level string
        """
        abs_similarity = abs(similarity)
        
        if abs_similarity >= self.high_confidence_threshold:
            return "high"
        elif abs_similarity >= self.min_confidence_threshold:
            return "medium"
        else:
            return "low"
    
    def interpret_similarity(self, similarity: float) -> Dict[str, Any]:
        """
        Provide interpretation of similarity score
        
        Args:
            similarity: Cosine similarity score (-1 to 1)
            
        Returns:
            Dictionary with interpretation details
        """
        percentage = self.normalize_to_percentage(similarity)
        confidence = self.get_confidence_level(similarity)
        
        # Determine match quality
        if percentage >= 80:
            match_quality = "excellent"
            description = "Very strong semantic match"
        elif percentage >= 60:
            match_quality = "good"
            description = "Good semantic alignment"
        elif percentage >= 40:
            match_quality = "moderate"
            description = "Moderate semantic similarity"
        elif percentage >= 20:
            match_quality = "weak"
            description = "Limited semantic overlap"
        else:
            match_quality = "poor"
            description = "Minimal semantic similarity"
        
        return {
            "percentage": percentage,
            "confidence": confidence,
            "match_quality": match_quality,
            "description": description,
            "raw_similarity": similarity
        }
    
    async def calculate_similarity_with_metrics(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculate similarity with comprehensive metrics
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Dictionary with similarity metrics and interpretation
        """
        try:
            # Calculate raw similarity
            similarity = self.calculate_cosine_similarity(embedding1, embedding2)
            
            # Get interpretation
            interpretation = self.interpret_similarity(similarity)
            
            # Add additional metrics
            result = {
                **interpretation,
                "embedding_dimensions": embedding1.shape[0],
                "calculation_method": "cosine_similarity"
            }
            
            logger.info("Calculated similarity with metrics", 
                       percentage=result["percentage"],
                       confidence=result["confidence"],
                       match_quality=result["match_quality"])
            
            return result
            
        except Exception as e:
            logger.error("Failed to calculate similarity with metrics", error=str(e))
            raise SemanticAnalysisError(f"Similarity calculation with metrics failed: {str(e)}")


class KeywordAnalyzer:
    """Intelligent keyword analysis using spaCy NLP"""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp = None
        self.min_keyword_length = 2
        self.max_keyword_length = 50
        
        # Common stop words to exclude from keywords
        self.additional_stop_words = {
            'experience', 'work', 'working', 'job', 'position', 'role', 'company',
            'team', 'project', 'projects', 'years', 'year', 'month', 'months',
            'day', 'days', 'time', 'good', 'great', 'excellent', 'strong',
            'ability', 'skills', 'skill', 'knowledge', 'understanding'
        }
        
        # Synonym mappings for better keyword matching
        self.synonym_mappings = {
            'javascript': ['js', 'ecmascript'],
            'python': ['py'],
            'artificial intelligence': ['ai', 'machine learning', 'ml'],
            'user interface': ['ui'],
            'user experience': ['ux'],
            'database': ['db', 'databases'],
            'application programming interface': ['api', 'apis'],
            'continuous integration': ['ci'],
            'continuous deployment': ['cd'],
            'software development': ['development', 'dev'],
            'quality assurance': ['qa', 'testing'],
            'project management': ['pm'],
            'customer relationship management': ['crm'],
            'enterprise resource planning': ['erp']
        }
    
    def _get_nlp_model(self):
        """Lazy load the spaCy model"""
        if self._nlp is None:
            try:
                logger.info("Loading spaCy model", model=self.model_name)
                import spacy
                self._nlp = spacy.load(self.model_name)
                
                # Add custom stop words
                for word in self.additional_stop_words:
                    self._nlp.vocab[word].is_stop = True
                
                logger.info("Successfully loaded spaCy model")
            except Exception as e:
                logger.error("Failed to load spaCy model", error=str(e))
                logger.warning("Using fallback keyword extraction without spaCy")
                self._nlp = None  # Will trigger fallback mode
                return None
        return self._nlp
    
    def _fallback_keyword_extraction(self, text: str) -> List[str]:
        """Simple fallback keyword extraction without spaCy"""
        import re
        
        # Simple regex-based keyword extraction
        words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
        
        # Common stop words to filter out
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'
        }
        
        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if (word not in stop_words and 
                len(word) >= self.min_keyword_length and 
                len(word) <= self.max_keyword_length and
                word not in seen):
                keywords.append(word)
                seen.add(word)
        
        return keywords[:20]  # Limit to top 20 keywords
    
    def _normalize_keyword(self, keyword: str) -> str:
        """Normalize keyword for consistent matching"""
        # Convert to lowercase and strip whitespace
        normalized = keyword.lower().strip()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters except hyphens and dots
        normalized = re.sub(r'[^\w\s\-\.]', '', normalized)
        
        return normalized
    
    def _extract_noun_phrases(self, text: str) -> List[str]:
        """Extract noun phrases from text using spaCy"""
        try:
            nlp = self._get_nlp_model()
            if nlp is None:
                # Fallback to simple keyword extraction
                return self._fallback_keyword_extraction(text)
            
            doc = nlp(text)
            
            noun_phrases = []
            
            # Extract noun chunks
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip()
                normalized = self._normalize_keyword(phrase)
                
                # Filter by length and content
                if (self.min_keyword_length <= len(normalized) <= self.max_keyword_length 
                    and not chunk.root.is_stop 
                    and chunk.root.pos_ in ['NOUN', 'PROPN']):
                    noun_phrases.append(normalized)
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'PRODUCT', 'SKILL', 'TECH']:  # Relevant entity types
                    phrase = ent.text.strip()
                    normalized = self._normalize_keyword(phrase)
                    
                    if self.min_keyword_length <= len(normalized) <= self.max_keyword_length:
                        noun_phrases.append(normalized)
            
            # Extract individual important tokens
            for token in doc:
                if (token.pos_ in ['NOUN', 'PROPN', 'ADJ'] 
                    and not token.is_stop 
                    and not token.is_punct 
                    and len(token.text) >= self.min_keyword_length):
                    normalized = self._normalize_keyword(token.text)
                    if len(normalized) >= self.min_keyword_length:
                        noun_phrases.append(normalized)
            
            return list(set(noun_phrases))  # Remove duplicates
            
        except Exception as e:
            logger.error("Failed to extract noun phrases", error=str(e))
            raise SemanticAnalysisError(f"Noun phrase extraction failed: {str(e)}")
    
    def _expand_with_synonyms(self, keywords: List[str]) -> List[str]:
        """Expand keywords with synonyms for better matching"""
        expanded = set(keywords)
        
        for keyword in keywords:
            # Check if keyword has synonyms
            for canonical, synonyms in self.synonym_mappings.items():
                if keyword == canonical:
                    expanded.update(synonyms)
                elif keyword in synonyms:
                    expanded.add(canonical)
                    expanded.update(synonyms)
        
        return list(expanded)
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text using NLP analysis
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of extracted keywords
        """
        try:
            # Extract noun phrases and important terms
            keywords = self._extract_noun_phrases(text)
            
            # Expand with synonyms
            expanded_keywords = self._expand_with_synonyms(keywords)
            
            # Sort by length (longer phrases first) and alphabetically
            sorted_keywords = sorted(expanded_keywords, key=lambda x: (-len(x), x))
            
            logger.info("Extracted keywords", 
                       original_count=len(keywords),
                       expanded_count=len(expanded_keywords),
                       text_length=len(text))
            
            return sorted_keywords
            
        except Exception as e:
            logger.error("Failed to extract keywords", error=str(e))
            raise SemanticAnalysisError(f"Keyword extraction failed: {str(e)}")
    
    def match_keywords(self, resume_keywords: List[str], job_keywords: List[str]) -> Tuple[List[str], List[str]]:
        """
        Match keywords between resume and job description
        
        Args:
            resume_keywords: Keywords from resume
            job_keywords: Keywords from job description
            
        Returns:
            Tuple of (matched_keywords, missing_keywords)
        """
        try:
            # Normalize all keywords
            resume_set = {self._normalize_keyword(kw) for kw in resume_keywords}
            job_set = {self._normalize_keyword(kw) for kw in job_keywords}
            
            # Find exact matches
            matched = resume_set.intersection(job_set)
            
            # Find partial matches (substring matching)
            additional_matches = set()
            for job_kw in job_set:
                if job_kw not in matched:
                    for resume_kw in resume_set:
                        if (job_kw in resume_kw or resume_kw in job_kw) and len(job_kw) > 3:
                            additional_matches.add(job_kw)
                            break
            
            matched.update(additional_matches)
            
            # Find missing keywords
            missing = job_set - matched
            
            # Convert back to lists and sort
            matched_list = sorted(list(matched))
            missing_list = sorted(list(missing))
            
            logger.info("Matched keywords", 
                       matched_count=len(matched_list),
                       missing_count=len(missing_list),
                       match_rate=len(matched_list) / len(job_set) if job_set else 0)
            
            return matched_list, missing_list
            
        except Exception as e:
            logger.error("Failed to match keywords", error=str(e))
            raise SemanticAnalysisError(f"Keyword matching failed: {str(e)}")
    
    def prioritize_missing_keywords(self, missing_keywords: List[str], job_text: str) -> List[str]:
        """
        Prioritize missing keywords by frequency in job description
        
        Args:
            missing_keywords: List of missing keywords
            job_text: Original job description text
            
        Returns:
            List of missing keywords sorted by priority (frequency)
        """
        try:
            job_text_lower = job_text.lower()
            keyword_frequencies = {}
            
            for keyword in missing_keywords:
                # Count occurrences (case-insensitive)
                count = job_text_lower.count(keyword.lower())
                keyword_frequencies[keyword] = count
            
            # Sort by frequency (descending) then alphabetically
            prioritized = sorted(missing_keywords, 
                               key=lambda x: (-keyword_frequencies.get(x, 0), x))
            
            logger.info("Prioritized missing keywords", 
                       total_missing=len(missing_keywords),
                       frequencies=keyword_frequencies)
            
            return prioritized
            
        except Exception as e:
            logger.error("Failed to prioritize missing keywords", error=str(e))
            return missing_keywords  # Return original list on error
    
    def calculate_keyword_coverage(self, matched_keywords: List[str], total_job_keywords: List[str]) -> float:
        """
        Calculate keyword coverage percentage
        
        Args:
            matched_keywords: List of matched keywords
            total_job_keywords: Total keywords from job description
            
        Returns:
            Coverage percentage (0-100)
        """
        if not total_job_keywords:
            return 0.0
        
        coverage = (len(matched_keywords) / len(total_job_keywords)) * 100
        return min(coverage, 100.0)  # Cap at 100%


class SemanticService:
    """
    Main semantic analysis service that orchestrates embedding generation,
    similarity calculation, and keyword analysis
    """
    
    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.similarity_calculator = SimilarityCalculator()
        self.keyword_analyzer = KeywordAnalyzer()
    
    async def analyze_compatibility(
        self, 
        resume_text: str, 
        job_description: str
    ) -> CompatibilityAnalysis:
        """
        Perform comprehensive compatibility analysis between resume and job description
        
        Args:
            resume_text: Text content of the resume
            job_description: Text content of the job description
            
        Returns:
            CompatibilityAnalysis object with all analysis results
            
        Raises:
            SemanticAnalysisError: If analysis fails
        """
        try:
            logger.info("Starting compatibility analysis", 
                       resume_length=len(resume_text),
                       job_desc_length=len(job_description))
            
            # PERFORMANCE OPTIMIZATION: Generate embeddings concurrently
            logger.info("Generating embeddings")
            resume_task = asyncio.create_task(
                self.embedding_generator.generate_embedding(resume_text)
            )
            job_task = asyncio.create_task(
                self.embedding_generator.generate_embedding(job_description)
            )
            
            # Wait for both embeddings to complete
            resume_embedding, job_embedding = await asyncio.gather(resume_task, job_task)
            
            # Calculate semantic similarity
            logger.info("Calculating semantic similarity")
            similarity_metrics = await self.similarity_calculator.calculate_similarity_with_metrics(
                resume_embedding, job_embedding
            )
            
            # Extract and match keywords
            logger.info("Analyzing keywords")
            resume_keywords = self.keyword_analyzer.extract_keywords(resume_text)
            job_keywords = self.keyword_analyzer.extract_keywords(job_description)
            
            matched_keywords, missing_keywords = self.keyword_analyzer.match_keywords(
                resume_keywords, job_keywords
            )
            
            # Prioritize missing keywords
            prioritized_missing = self.keyword_analyzer.prioritize_missing_keywords(
                missing_keywords, job_description
            )
            
            # Calculate keyword coverage
            keyword_coverage = self.keyword_analyzer.calculate_keyword_coverage(
                matched_keywords, job_keywords
            )
            
            # Create compatibility analysis result
            analysis = CompatibilityAnalysis(
                match_score=similarity_metrics["percentage"],
                matched_keywords=matched_keywords,
                missing_keywords=prioritized_missing,
                semantic_similarity=similarity_metrics["raw_similarity"],
                keyword_coverage=keyword_coverage
            )
            
            logger.info("Compatibility analysis completed", 
                       match_score=analysis.match_score,
                       matched_keywords_count=len(matched_keywords),
                       missing_keywords_count=len(prioritized_missing),
                       keyword_coverage=keyword_coverage)
            
            return analysis
            
        except Exception as e:
            logger.error("Compatibility analysis failed", error=str(e))
            raise SemanticAnalysisError(f"Compatibility analysis failed: {str(e)}")
    
    async def generate_embedding_only(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (utility method)
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        return await self.embedding_generator.generate_embedding(text)
    
    def extract_keywords_only(self, text: str) -> List[str]:
        """
        Extract keywords from text (utility method)
        
        Args:
            text: Input text
            
        Returns:
            List of extracted keywords
        """
        return self.keyword_analyzer.extract_keywords(text)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the service components
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "embedding_cache_stats": self.embedding_generator.get_cache_stats(),
            "similarity_thresholds": {
                "min_confidence": self.similarity_calculator.min_confidence_threshold,
                "high_confidence": self.similarity_calculator.high_confidence_threshold
            },
            "keyword_analyzer_config": {
                "min_keyword_length": self.keyword_analyzer.min_keyword_length,
                "max_keyword_length": self.keyword_analyzer.max_keyword_length,
                "synonym_mappings_count": len(self.keyword_analyzer.synonym_mappings)
            }
        }
    
    def clear_caches(self):
        """Clear all internal caches"""
        self.embedding_generator.clear_cache()
        logger.info("Cleared all semantic service caches")


# Global service instance (will be initialized in main.py)
semantic_service: Optional[SemanticService] = None


def get_semantic_service() -> SemanticService:
    """Get the global semantic service instance"""
    global semantic_service
    if semantic_service is None:
        semantic_service = SemanticService()
    return semantic_service