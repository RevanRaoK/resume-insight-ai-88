"""
Unit tests for semantic analysis service
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from app.services.semantic_service import (
    EmbeddingGenerator, 
    SimilarityCalculator, 
    KeywordAnalyzer,
    SemanticService
)
from app.models.entities import CompatibilityAnalysis


class TestEmbeddingGenerator:
    """Test embedding generation functionality"""
    
    @pytest.fixture
    def embedding_generator(self):
        return EmbeddingGenerator()
    
    def test_preprocess_text(self, embedding_generator):
        """Test text preprocessing"""
        text = "  This is a TEST   with   extra spaces!  "
        processed = embedding_generator._preprocess_text(text)
        assert processed == "this is a test with extra spaces!"
    
    def test_chunk_text_short(self, embedding_generator):
        """Test chunking with short text"""
        text = "Short text"
        chunks = embedding_generator._chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_long(self, embedding_generator):
        """Test chunking with long text"""
        # Create text longer than max_chunk_length (512 words)
        words = ["word"] * 520  # Slightly more than 512 default max
        text = " ".join(words)
        chunks = embedding_generator._chunk_text(text)
        assert len(chunks) > 1
        assert len(chunks) == 2  # Should create exactly 2 chunks
        
        # Verify chunk overlap logic
        first_chunk_words = chunks[0].split()
        second_chunk_words = chunks[1].split()
        assert len(first_chunk_words) == 512  # Max chunk length
        assert len(second_chunk_words) > 0  # Has remaining words
    
    def test_get_cache_key(self, embedding_generator):
        """Test cache key generation"""
        text = "test text"
        key1 = embedding_generator._get_cache_key(text)
        key2 = embedding_generator._get_cache_key(text)
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_generate_embedding_mock(self, embedding_generator):
        """Test embedding generation with mocked model"""
        with patch.object(embedding_generator, '_get_model') as mock_model:
            # Mock the sentence transformer model
            mock_transformer = Mock()
            mock_transformer.encode.return_value = np.array([0.1, 0.2, 0.3])
            mock_model.return_value = mock_transformer
            
            text = "test text"
            embedding = await embedding_generator.generate_embedding(text)
            
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (3,)
            mock_transformer.encode.assert_called_once()


class TestSimilarityCalculator:
    """Test similarity calculation functionality"""
    
    @pytest.fixture
    def similarity_calculator(self):
        return SimilarityCalculator()
    
    def test_calculate_cosine_similarity(self, similarity_calculator):
        """Test cosine similarity calculation"""
        # Create test embeddings
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([1.0, 0.0, 0.0])  # Identical
        
        similarity = similarity_calculator.calculate_cosine_similarity(embedding1, embedding2)
        assert abs(similarity - 1.0) < 0.001  # Should be very close to 1.0
        
        # Test orthogonal vectors
        embedding3 = np.array([0.0, 1.0, 0.0])
        similarity2 = similarity_calculator.calculate_cosine_similarity(embedding1, embedding3)
        assert abs(similarity2 - 0.0) < 0.001  # Should be close to 0.0
    
    def test_normalize_to_percentage(self, similarity_calculator):
        """Test similarity normalization"""
        # Test boundary values
        assert similarity_calculator.normalize_to_percentage(1.0) == 100.0
        assert similarity_calculator.normalize_to_percentage(-1.0) == 0.0
        assert similarity_calculator.normalize_to_percentage(0.0) == 50.0
    
    def test_get_confidence_level(self, similarity_calculator):
        """Test confidence level determination"""
        assert similarity_calculator.get_confidence_level(0.8) == "high"
        assert similarity_calculator.get_confidence_level(0.5) == "medium"
        assert similarity_calculator.get_confidence_level(0.05) == "low"
    
    def test_interpret_similarity(self, similarity_calculator):
        """Test similarity interpretation"""
        result = similarity_calculator.interpret_similarity(0.8)
        
        assert "percentage" in result
        assert "confidence" in result
        assert "match_quality" in result
        assert "description" in result
        assert result["percentage"] == 90.0  # (0.8 + 1) / 2 * 100
        assert result["confidence"] == "high"
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_with_metrics(self, similarity_calculator):
        """Test comprehensive similarity calculation"""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.8, 0.6, 0.0])  # Normalized: cos(θ) ≈ 0.8
        
        result = await similarity_calculator.calculate_similarity_with_metrics(embedding1, embedding2)
        
        assert "percentage" in result
        assert "confidence" in result
        assert "match_quality" in result
        assert "embedding_dimensions" in result
        assert result["embedding_dimensions"] == 3


class TestKeywordAnalyzer:
    """Test keyword analysis functionality"""
    
    @pytest.fixture
    def keyword_analyzer(self):
        return KeywordAnalyzer()
    
    def test_normalize_keyword(self, keyword_analyzer):
        """Test keyword normalization"""
        keyword = "  Python Programming!  "
        normalized = keyword_analyzer._normalize_keyword(keyword)
        assert normalized == "python programming"
    
    def test_expand_with_synonyms(self, keyword_analyzer):
        """Test synonym expansion"""
        keywords = ["javascript", "python"]
        expanded = keyword_analyzer._expand_with_synonyms(keywords)
        
        assert "javascript" in expanded
        assert "js" in expanded  # Should include synonym
        assert "python" in expanded
    
    def test_match_keywords(self, keyword_analyzer):
        """Test keyword matching"""
        resume_keywords = ["python", "javascript", "react", "sql"]
        job_keywords = ["python", "js", "database", "api"]
        
        matched, missing = keyword_analyzer.match_keywords(resume_keywords, job_keywords)
        
        assert "python" in matched
        assert "js" in matched  # Should match with javascript
        assert "database" in missing
        assert "api" in missing
    
    def test_calculate_keyword_coverage(self, keyword_analyzer):
        """Test keyword coverage calculation"""
        matched = ["python", "javascript"]
        total_job = ["python", "javascript", "react", "sql"]
        
        coverage = keyword_analyzer.calculate_keyword_coverage(matched, total_job)
        assert coverage == 50.0  # 2/4 * 100
    
    def test_prioritize_missing_keywords(self, keyword_analyzer):
        """Test missing keyword prioritization"""
        missing = ["python", "react", "sql"]
        job_text = "We need Python experience. Python is essential. React is nice to have."
        
        prioritized = keyword_analyzer.prioritize_missing_keywords(missing, job_text)
        
        # Python should be first due to higher frequency
        assert prioritized[0] == "python"


class TestSemanticService:
    """Test integrated semantic service functionality"""
    
    @pytest.fixture
    def semantic_service(self):
        return SemanticService()
    
    @pytest.mark.asyncio
    async def test_analyze_compatibility_mock(self, semantic_service):
        """Test compatibility analysis with mocked components"""
        # Mock the embedding generator
        with patch.object(semantic_service.embedding_generator, 'generate_embedding') as mock_embed:
            mock_embed.return_value = np.array([0.5, 0.5, 0.0])
            
            # Mock the keyword analyzer
            with patch.object(semantic_service.keyword_analyzer, 'extract_keywords') as mock_extract:
                mock_extract.side_effect = [
                    ["python", "javascript"],  # Resume keywords
                    ["python", "react", "sql"]  # Job keywords
                ]
                
                with patch.object(semantic_service.keyword_analyzer, 'match_keywords') as mock_match:
                    mock_match.return_value = (["python"], ["react", "sql"])
                    
                    with patch.object(semantic_service.keyword_analyzer, 'calculate_keyword_coverage') as mock_coverage:
                        mock_coverage.return_value = 33.3
                        
                        resume_text = "Python developer with JavaScript experience"
                        job_text = "Looking for Python, React, and SQL skills"
                        
                        result = await semantic_service.analyze_compatibility(resume_text, job_text)
                        
                        assert isinstance(result, CompatibilityAnalysis)
                        assert result.matched_keywords == ["python"]
                        assert result.missing_keywords == ["react", "sql"]
                        assert result.keyword_coverage == 33.3
    
    def test_get_service_stats(self, semantic_service):
        """Test service statistics"""
        stats = semantic_service.get_service_stats()
        
        assert "embedding_cache_stats" in stats
        assert "similarity_thresholds" in stats
        assert "keyword_analyzer_config" in stats
    
    def test_clear_caches(self, semantic_service):
        """Test cache clearing"""
        # This should not raise an exception
        semantic_service.clear_caches()