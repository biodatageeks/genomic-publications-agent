"""
Tests for the UnifiedLlmContextAnalyzer class.

This module contains unit tests for the UnifiedLlmContextAnalyzer class,
which is used to analyze relationships between variants and other biomedical
entities in scientific publications.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
import bioc
from typing import List, Dict, Any

from src.analysis.llm.context_analyzer import UnifiedLlmContextAnalyzer
from src.models.data.clients.pubtator import PubTatorClient
from src.models.data.clients.exceptions import PubTatorError
from src.utils.llm.manager import LlmManager


@pytest.fixture
def mock_llm_manager():
    """Fixture providing a mocked LlmManager instance."""
    with patch('src.analysis.llm.context_analyzer.LlmManager') as mock:
        mock_instance = MagicMock()
        mock_llm = MagicMock()
        mock_instance.get_llm.return_value = mock_llm
        mock.return_value = mock_instance
        yield mock_instance
        

@pytest.fixture
def mock_pubtator_client():
    """Fixture providing a mocked PubTatorClient instance."""
    mock_client = MagicMock(spec=PubTatorClient)
    return mock_client


@pytest.fixture
def mock_cache():
    """Fixture providing a mocked cache instance."""
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    return mock_cache


@pytest.fixture
def mock_document() -> bioc.BioCDocument:
    """Fixture providing a mock BioCDocument for testing."""
    document = bioc.BioCDocument()
    document.id = "12345678"
    
    # Add a passage with annotations
    passage = bioc.BioCPassage()
    passage.offset = 0
    passage.text = "BRAF V600E mutation was found in melanoma patients."
    
    # Add variant annotation
    variant_annotation = bioc.BioCAnnotation()
    variant_annotation.id = "1"
    variant_annotation.text = "BRAF V600E"
    variant_annotation.infons["type"] = "Mutation"
    location = bioc.BioCLocation()
    location.offset = 0
    location.length = 9
    variant_annotation.locations.append(location)
    passage.annotations.append(variant_annotation)
    
    # Add disease annotation
    disease_annotation = bioc.BioCAnnotation()
    disease_annotation.id = "2"
    disease_annotation.text = "melanoma"
    disease_annotation.infons["type"] = "Disease"
    location = bioc.BioCLocation()
    location.offset = 23
    location.length = 8
    disease_annotation.locations.append(location)
    passage.annotations.append(disease_annotation)
    
    document.passages.append(passage)
    return document


@pytest.fixture
def sample_relationship_response() -> Dict[str, Any]:
    """Fixture providing a sample LLM response for relationship analysis."""
    return {
        "relationships": [
            {
                "entity_type": "Disease",
                "entity_text": "melanoma",
                "entity_id": "2",
                "has_relationship": True,
                "relationship_score": 9,
                "explanation": "BRAF V600E mutation is strongly associated with melanoma in the text."
            }
        ]
    }


@pytest.fixture
def analyzer(mock_pubtator_client, mock_llm_manager, mock_cache):
    """Fixture providing an instance of UnifiedLlmContextAnalyzer for testing."""
    with patch('src.analysis.llm.context_analyzer.CacheManager') as mock_cache_manager:
        mock_cache_manager.create.return_value = mock_cache
        analyzer = UnifiedLlmContextAnalyzer(
            pubtator_client=mock_pubtator_client,
            llm_model_name="test-model",
            use_cache=True,
            cache_storage_type="memory",
            debug_mode=True
        )
        return analyzer


def test_init(mock_pubtator_client, mock_llm_manager):
    """Test the initialization of UnifiedLlmContextAnalyzer."""
    with patch('src.analysis.llm.context_analyzer.CacheManager') as mock_cache_manager:
        mock_cache = MagicMock()
        mock_cache_manager.create.return_value = mock_cache
        
        analyzer = UnifiedLlmContextAnalyzer(
            pubtator_client=mock_pubtator_client,
            llm_model_name="test-model",
            use_cache=True
        )
        
        assert analyzer.llm_model_name == "test-model"
        assert analyzer.pubtator_client == mock_pubtator_client
        assert analyzer.use_cache is True
        assert analyzer.cache == mock_cache
        mock_cache_manager.create.assert_called_once()


def test_analyze_publication(analyzer, mock_document):
    """Test the analyze_publication method."""
    # Configure the analyzer's mocked LLM to return a specific response
    llm_response = MagicMock()
    llm_response.content = json.dumps({
        "relationships": [
            {
                "entity_type": "Disease",
                "entity_text": "melanoma",
                "entity_id": "2",
                "has_relationship": True,
                "relationship_score": 9,
                "explanation": "BRAF V600E mutation is strongly associated with melanoma in the text."
            }
        ]
    })
    analyzer.llm.invoke.return_value = llm_response
    
    # Configure PubTator client to return the mock document
    analyzer.pubtator_client.get_publication_by_pmid.return_value = mock_document
    
    # Call the method
    result = analyzer.analyze_publication("12345678")
    
    # Verify results
    assert len(result) == 1
    relationship = result[0]
    assert relationship["entity_type"] == "Disease"
    assert relationship["entity_text"] == "melanoma"
    assert relationship["variant_text"] == "BRAF V600E"
    assert relationship["pmid"] == "12345678"
    assert relationship["has_relationship"] is True
    assert relationship["relationship_score"] == 9


def test_analyze_publications(analyzer, mock_document):
    """Test the analyze_publications method."""
    # Configure the analyzer's mocked LLM to return a specific response
    llm_response = MagicMock()
    llm_response.content = json.dumps({
        "relationships": [
            {
                "entity_type": "Disease",
                "entity_text": "melanoma",
                "entity_id": "2",
                "has_relationship": True,
                "relationship_score": 9,
                "explanation": "BRAF V600E mutation is strongly associated with melanoma in the text."
            }
        ]
    })
    analyzer.llm.invoke.return_value = llm_response
    
    # Configure PubTator client to return a list of documents
    analyzer.pubtator_client.get_publications_by_pmids.return_value = [mock_document]
    
    # Call the method
    result = analyzer.analyze_publications(["12345678"])
    
    # Verify results
    assert len(result) == 1
    relationship = result[0]
    assert relationship["entity_type"] == "Disease"
    assert relationship["entity_text"] == "melanoma"
    assert relationship["variant_text"] == "BRAF V600E"
    assert relationship["pmid"] == "12345678"
    assert relationship["has_relationship"] is True
    assert relationship["relationship_score"] == 9


def test_analyze_publications_with_pubtator_error(analyzer):
    """Test the analyze_publications method with PubTator error."""
    # Configure PubTator client to raise an error
    analyzer.pubtator_client.get_publications_by_pmids.side_effect = PubTatorError("API error")
    
    # Call the method and expect an exception
    with pytest.raises(PubTatorError, match="Error analyzing publications"):
        analyzer.analyze_publications(["12345678"])


def test_analyze_relationships_with_llm(analyzer, sample_relationship_response):
    """Test the _analyze_relationships_with_llm method."""
    # Configure the LLM to return a specific response
    llm_response = MagicMock()
    llm_response.content = json.dumps(sample_relationship_response)
    analyzer.llm.invoke.return_value = llm_response
    
    # Prepare test data
    variant_text = "BRAF V600E"
    entities = [
        {
            "entity_category": "disease",
            "entity_type": "Disease",
            "entity_text": "melanoma",
            "entity_id": "2"
        }
    ]
    passage_text = "BRAF V600E mutation was found in melanoma patients."
    
    # Call the method
    result = analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
    
    # Verify results
    assert len(result) == 1
    relationship = result[0]
    assert relationship["entity_type"] == "Disease"
    assert relationship["entity_text"] == "melanoma"
    assert relationship["has_relationship"] is True
    assert relationship["relationship_score"] == 9


def test_analyze_relationships_with_llm_cache_hit(analyzer, sample_relationship_response):
    """Test the _analyze_relationships_with_llm method with cache hit."""
    # Configure cache to return a cached result
    analyzer.cache.get.return_value = sample_relationship_response["relationships"]
    
    # Prepare test data
    variant_text = "BRAF V600E"
    entities = [
        {
            "entity_category": "disease",
            "entity_type": "Disease",
            "entity_text": "melanoma",
            "entity_id": "2"
        }
    ]
    passage_text = "BRAF V600E mutation was found in melanoma patients."
    
    # Call the method
    result = analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
    
    # Verify results
    assert len(result) == 1
    assert result == sample_relationship_response["relationships"]
    
    # Verify that LLM was not called
    analyzer.llm.invoke.assert_not_called()


def test_clean_json_response():
    """Test the _clean_json_response method."""
    analyzer = UnifiedLlmContextAnalyzer(llm_model_name="test-model")
    
    # Test with JSON in markdown code block
    markdown_response = '```json\n{"key": "value"}\n```'
    result = analyzer._clean_json_response(markdown_response)
    assert result == '{"key": "value"}'
    
    # Test with plain JSON
    plain_json = '{"key": "value"}'
    result = analyzer._clean_json_response(plain_json)
    assert result == '{"key": "value"}'
    
    # Test with JSON embedded in text
    text_with_json = 'Here is the result: {"key": "value"} and more text'
    result = analyzer._clean_json_response(text_with_json)
    assert result == '{"key": "value"}'


def test_fix_trailing_commas():
    """Test the _fix_trailing_commas method."""
    analyzer = UnifiedLlmContextAnalyzer(llm_model_name="test-model")
    
    # Test with trailing comma in object
    json_with_trailing_comma_obj = '{"key1": "value1", "key2": "value2",}'
    result = analyzer._fix_trailing_commas(json_with_trailing_comma_obj)
    assert result == '{"key1": "value1", "key2": "value2"}'
    
    # Test with trailing comma in array
    json_with_trailing_comma_arr = '["value1", "value2",]'
    result = analyzer._fix_trailing_commas(json_with_trailing_comma_arr)
    assert result == '["value1", "value2"]'


def test_save_relationships_to_csv(analyzer, tmp_path):
    """Test the save_relationships_to_csv method."""
    # Prepare test data
    relationships = [
        {
            "pmid": "12345678",
            "variant_id": "1",
            "variant_text": "BRAF V600E",
            "entity_id": "2",
            "entity_text": "melanoma",
            "entity_type": "Disease",
            "entity_category": "disease",
            "has_relationship": True,
            "relationship_score": 9,
            "explanation": "BRAF V600E mutation is strongly associated with melanoma."
        }
    ]
    
    # Create a temporary output file
    output_file = os.path.join(tmp_path, "relationships.csv")
    
    # Call the method
    analyzer.save_relationships_to_csv(relationships, output_file)
    
    # Verify that the file was created
    assert os.path.exists(output_file)
    
    # Read the file content and verify
    with open(output_file, "r") as f:
        lines = f.readlines()
        assert len(lines) > 1  # Header + at least one data row
        assert "pmid,variant_id,variant_text" in lines[0]  # Header
        assert "12345678,1,BRAF V600E" in lines[1]  # Data


def test_save_relationships_to_json(analyzer, tmp_path):
    """Test the save_relationships_to_json method."""
    # Prepare test data
    relationships = [
        {
            "pmid": "12345678",
            "variant_id": "1",
            "variant_text": "BRAF V600E",
            "entity_id": "2",
            "entity_text": "melanoma",
            "entity_type": "Disease",
            "entity_category": "disease",
            "has_relationship": True,
            "relationship_score": 9,
            "explanation": "BRAF V600E mutation is strongly associated with melanoma."
        }
    ]
    
    # Create a temporary output file
    output_file = os.path.join(tmp_path, "relationships.json")
    
    # Call the method
    analyzer.save_relationships_to_json(relationships, output_file)
    
    # Verify that the file was created
    assert os.path.exists(output_file)
    
    # Read the file content and verify
    with open(output_file, "r") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["pmid"] == "12345678"
        assert data[0]["variant_text"] == "BRAF V600E"
        assert data[0]["entity_text"] == "melanoma"
        assert data[0]["relationship_score"] == 9


def test_filter_relationships_by_entity(analyzer):
    """Test the filter_relationships_by_entity method."""
    # Prepare test data
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "BRAF V600E",
            "entity_text": "melanoma",
            "entity_category": "disease",
            "relationship_score": 9
        },
        {
            "pmid": "12345678",
            "variant_text": "BRAF V600E",
            "entity_text": "BRAF",
            "entity_category": "gene",
            "relationship_score": 8
        },
        {
            "pmid": "87654321",
            "variant_text": "BRCA1 185delAG",
            "entity_text": "breast cancer",
            "entity_category": "disease",
            "relationship_score": 7
        }
    ]
    
    # Filter by disease
    disease_results = analyzer.filter_relationships_by_entity(relationships, "disease", "melanoma")
    assert len(disease_results) == 1
    assert disease_results[0]["entity_text"] == "melanoma"
    
    # Filter by gene
    gene_results = analyzer.filter_relationships_by_entity(relationships, "gene", "BRAF")
    assert len(gene_results) == 1
    assert gene_results[0]["entity_text"] == "BRAF"
    
    # Filter with no matches
    no_results = analyzer.filter_relationships_by_entity(relationships, "tissue", "skin")
    assert len(no_results) == 0 