"""
Tests for integration between LlmManager and LlmContextAnalyzer.

This module provides tests that verify the correct interaction
between LlmManager and the LlmContextAnalyzer class.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.LlmManager import LlmManager
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer


@pytest.fixture
def mock_llm_manager():
    """Creates a mock LlmManager"""
    mock = MagicMock(spec=LlmManager)
    mock.llm = MagicMock()
    mock.get_llm.return_value = mock.llm
    mock.get_llm_model_name.return_value = "mock-model"
    return mock


@pytest.fixture
def mock_bioc_document():
    """Creates a mock BioCDocument for testing"""
    mock_doc = MagicMock()
    mock_doc.id = "12345"
    
    # Create mock passage
    mock_passage = MagicMock()
    mock_passage.text = (
        "Li-Fraumeni syndrome is associated with germline mutations in the TP53 gene. "
        "The c.215C>G (p.Pro72Arg) variant has been reported in several families."
    )
    
    # Create mock annotations for variant
    mock_variant_annotation = MagicMock()
    mock_variant_annotation.text = "c.215C>G"
    mock_variant_annotation.infons = {"type": "Mutation", "identifier": "dbSNP:rs1042522"}
    mock_variant_location = MagicMock()
    mock_variant_location.offset = 87
    mock_variant_annotation.locations = [mock_variant_location]
    
    # Create mock annotations for gene
    mock_gene_annotation = MagicMock()
    mock_gene_annotation.text = "TP53"
    mock_gene_annotation.infons = {"type": "Gene", "identifier": "NCBI:7157"}
    mock_gene_location = MagicMock()
    mock_gene_location.offset = 54
    mock_gene_annotation.locations = [mock_gene_location]
    
    # Create mock annotations for disease
    mock_disease_annotation = MagicMock()
    mock_disease_annotation.text = "Li-Fraumeni syndrome"
    mock_disease_annotation.infons = {"type": "Disease", "identifier": "MESH:D008288"}
    mock_disease_location = MagicMock()
    mock_disease_location.offset = 0
    mock_disease_annotation.locations = [mock_disease_location]
    
    # Add annotations to passage
    mock_passage.annotations = [mock_variant_annotation, mock_gene_annotation, mock_disease_annotation]
    
    # Add passage to document
    mock_doc.passages = [mock_passage]
    
    return mock_doc


@pytest.fixture
def mock_llm_response():
    """Sample LLM response with relationships"""
    return {
        "relationships": [
            {
                "entity_type": "gene",
                "entity_text": "TP53",
                "entity_id": "NCBI:7157",
                "has_relationship": True,
                "explanation": "The text explicitly states that c.215C>G is a mutation in the TP53 gene."
            },
            {
                "entity_type": "disease",
                "entity_text": "Li-Fraumeni syndrome",
                "entity_id": "MESH:D008288",
                "has_relationship": True,
                "explanation": "The text states that Li-Fraumeni syndrome is associated with TP53 mutations, specifically mentioning c.215C>G."
            }
        ]
    }


class TestLlmContextAnalyzerIntegration:
    """Tests for LlmContextAnalyzer integration with LlmManager"""

    def test_llm_context_analyzer_init(self, mock_llm_manager):
        """Test initialization of LlmContextAnalyzer with LlmManager"""
        # Patch the LlmManager to return our mock
        with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager', return_value=mock_llm_manager):
            # Create LlmContextAnalyzer
            analyzer = LlmContextAnalyzer(llm_model_name="mock-model")
            
            # Verify LlmManager was created correctly
            assert analyzer.llm_manager is mock_llm_manager
            assert analyzer.llm is mock_llm_manager.llm

    def test_analyze_publication_method(self, mock_llm_manager, mock_bioc_document, mock_llm_response):
        """Test _analyze_publication method with mocked LlmManager"""
        # Set up mock LLM response
        mock_llm = mock_llm_manager.llm
        mock_llm.invoke.return_value.content = str(mock_llm_response)
        
        # Patch the LlmManager to return our mock
        with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager', return_value=mock_llm_manager):
            # Create LlmContextAnalyzer
            analyzer = LlmContextAnalyzer(llm_model_name="mock-model")
            
            # Call _analyze_publication
            result = analyzer._analyze_publication(mock_bioc_document)
            
            # Verify result structure
            assert isinstance(result, list)
            assert len(result) == 1  # One relationship from the document
            
            # Check first relationship
            rel = result[0]
            assert rel["pmid"] == "12345"
            assert rel["variant_text"] == "c.215C>G"
            
            # Check that gene and disease relationships were extracted
            assert len(rel["genes"]) > 0
            assert rel["genes"][0]["text"] == "TP53"
            
            assert len(rel["diseases"]) > 0
            assert rel["diseases"][0]["text"] == "Li-Fraumeni syndrome"

    def test_clean_json_response(self, mock_llm_manager):
        """Test _clean_json_response method"""
        # Patch the LlmManager to return our mock
        with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager', return_value=mock_llm_manager):
            # Create LlmContextAnalyzer
            analyzer = LlmContextAnalyzer(llm_model_name="mock-model")
            
            # Test cleaning a messy JSON string
            messy_json = '''```json
            {
                "key": "value",
                "number": 42
            }
            ```'''
            
            clean_json = analyzer._clean_json_response(messy_json)
            
            # Verify cleaning worked
            assert clean_json == '{\n                "key": "value",\n                "number": 42\n            }'
            
            # Test with already clean JSON
            clean_input = '{"key": "value"}'
            result = analyzer._clean_json_response(clean_input)
            assert result == '{"key": "value"}'
            
            # Test with invalid input (no JSON)
            invalid_input = "This is not JSON"
            result = analyzer._clean_json_response(invalid_input)
            assert result == "{}"

    def test_group_annotations_by_type(self, mock_llm_manager, mock_bioc_document):
        """Test _group_annotations_by_type method"""
        # Patch the LlmManager to return our mock
        with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager', return_value=mock_llm_manager):
            # Create LlmContextAnalyzer
            analyzer = LlmContextAnalyzer(llm_model_name="mock-model")
            
            # Get the passage from the mock document
            passage = mock_bioc_document.passages[0]
            
            # Call _group_annotations_by_type
            result = analyzer._group_annotations_by_type(passage)
            
            # Verify result
            assert "Mutation" in result
            assert "Gene" in result
            assert "Disease" in result
            
            assert len(result["Mutation"]) == 1
            assert len(result["Gene"]) == 1
            assert len(result["Disease"]) == 1
            
            assert result["Mutation"][0].text == "c.215C>G"
            assert result["Gene"][0].text == "TP53"
            assert result["Disease"][0].text == "Li-Fraumeni syndrome"

    def test_with_cache(self, mock_llm_manager, mock_bioc_document, mock_llm_response):
        """Test that caching works correctly"""
        # Set up mock LLM response
        mock_llm = mock_llm_manager.llm
        mock_llm.invoke.return_value.content = str(mock_llm_response)
        
        # Create mock cache
        mock_cache = MagicMock()
        mock_cache.has.return_value = False  # First call will be cache miss
        
        # Patch the LlmManager and cache
        with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager', return_value=mock_llm_manager), \
             patch('src.llm_context_analyzer.llm_context_analyzer.APICache', return_value=mock_cache):
            
            # Create LlmContextAnalyzer with caching enabled
            analyzer = LlmContextAnalyzer(llm_model_name="mock-model", use_cache=True)
            analyzer.cache = mock_cache  # Set our mock cache
            
            # Call _analyze_publication twice
            analyzer._analyze_publication(mock_bioc_document)
            
            # Now make cache return a hit for second call
            mock_cache.has.return_value = True
            mock_cache.get.return_value = mock_llm_response["relationships"]
            
            analyzer._analyze_publication(mock_bioc_document)
            
            # Verify cache.set was called on first pass
            mock_cache.set.assert_called_once()
            
            # Verify cache.get was called on second pass
            mock_cache.get.assert_called_once()


class TestRealLlmContextAnalyzerIntegration:
    """Integration tests with real LlmManager (marked to be skipped by default)"""
    
    @pytest.mark.skip(reason="This test makes real API calls")
    def test_real_analyze_publication_method(self):
        """Test _analyze_publication with real LlmManager and API calls"""
        # Create a simple BioCDocument for testing
        from bioc import BioCDocument, BioCPassage, BioCAnnotation, BioCLocation
        
        # Create document
        document = BioCDocument()
        document.id = "test_doc"
        
        # Create passage
        passage = BioCPassage()
        passage.text = (
            "TP53 gene mutations, particularly c.215C>G (p.Pro72Arg), are associated with Li-Fraumeni syndrome. "
            "This mutation alters the function of the p53 protein, which normally acts as a tumor suppressor."
        )
        
        # Create variant annotation
        variant_ann = BioCAnnotation()
        variant_ann.text = "c.215C>G"
        variant_ann.infons = {"type": "Mutation", "identifier": "dbSNP:rs1042522"}
        # Create location with required parameters
        variant_location = BioCLocation(offset=34, length=8)  # Length of "c.215C>G"
        variant_ann.locations.append(variant_location)
        
        # Create gene annotation
        gene_ann = BioCAnnotation()
        gene_ann.text = "TP53"
        gene_ann.infons = {"type": "Gene", "identifier": "NCBI:7157"}
        # Create location with required parameters
        gene_location = BioCLocation(offset=0, length=4)  # Length of "TP53"
        gene_ann.locations.append(gene_location)
        
        # Create disease annotation
        disease_ann = BioCAnnotation()
        disease_ann.text = "Li-Fraumeni syndrome"
        disease_ann.infons = {"type": "Disease", "identifier": "MESH:D008288"}
        # Create location with required parameters
        disease_location = BioCLocation(offset=74, length=20)  # Length of "Li-Fraumeni syndrome"
        disease_ann.locations.append(disease_location)
        
        # Add annotations to passage
        passage.annotations.extend([variant_ann, gene_ann, disease_ann])
        
        # Add passage to document
        document.passages.append(passage)
        
        # Create analyzer with real LLM
        analyzer = LlmContextAnalyzer(llm_model_name="meta-llama/Llama-3.1-8B-Instruct")
        
        # Analyze
        result = analyzer._analyze_publication(document)
        
        # Basic validation
        assert isinstance(result, list)
        
        # Print result for inspection (real response content will vary)
        print(f"Real API analysis returned: {result}") 