#!/usr/bin/env python3
"""
Tests for the UnifiedLlmContextAnalyzer class.
"""

import unittest
import json
import pytest
from unittest.mock import patch, MagicMock, Mock

import bioc
from bioc import BioCDocument, BioCPassage, BioCAnnotation, BioCLocation
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from src.analysis.llm.unified_llm_context_analyzer import UnifiedLlmContextAnalyzer
from src.api.clients.pubtator_client import PubTatorClient
from src.api.clients.exceptions import PubTatorError


# Helper functions for creating mock objects
def create_mock_annotation(text, anno_type, identifier="", offset=0, length=0):
    """Creates mock BioCAnnotation objects."""
    anno = Mock(spec=BioCAnnotation)
    anno.text = text
    anno.infons = {"type": anno_type, "identifier": identifier}
    
    location = Mock(spec=BioCLocation)
    location.offset = offset
    location.length = length
    anno.locations = [location]
    
    return anno


def create_mock_passage(text, annotations):
    """Creates mock BioCPassage objects."""
    passage = Mock(spec=BioCPassage)
    passage.text = text
    passage.annotations = annotations
    return passage


def create_mock_document(pmid, passages):
    """Creates mock BioCDocument objects."""
    document = Mock(spec=BioCDocument)
    document.id = pmid
    document.passages = passages
    return document


# Mock LLM response with relationship scores
MOCK_LLM_RESPONSE = {
    "relationships": [
        {
            "entity_type": "gene",
            "entity_text": "BRAF",
            "entity_id": "673",
            "has_relationship": True,
            "relationship_score": 9,
            "explanation": "BRAF V600E mutation directly affects the BRAF gene function."
        },
        {
            "entity_type": "disease",
            "entity_text": "melanoma",
            "entity_id": "D008545",
            "has_relationship": True,
            "relationship_score": 8,
            "explanation": "The V600E mutation in BRAF is strongly associated with melanoma."
        },
        {
            "entity_type": "species",
            "entity_text": "human",
            "entity_id": "9606",
            "has_relationship": True,
            "relationship_score": 3,
            "explanation": "The variant is mentioned in the context of human studies."
        }
    ]
}


class TestUnifiedLlmContextAnalyzer(unittest.TestCase):
    """
    Test cases for the UnifiedLlmContextAnalyzer class.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock PubTator client
        self.pubtator_mock = MagicMock(spec=PubTatorClient)
        
        # Patch LlmManager class to isolate tests
        with patch("src.llm_context_analyzer.unified_llm_context_analyzer.LlmManager") as self.mock_llm_manager:
            self.mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps(MOCK_LLM_RESPONSE)
            self.mock_llm.invoke.return_value = mock_response
            
            self.mock_llm_manager_instance = MagicMock()
            self.mock_llm_manager_instance.get_llm.return_value = self.mock_llm
            self.mock_llm_manager.return_value = self.mock_llm_manager_instance
            
            # Create the analyzer with the mock
            self.analyzer = UnifiedLlmContextAnalyzer(
                pubtator_client=self.pubtator_mock,
                llm_model_name="test-model",
                use_cache=True,
                debug_mode=True
            )
    
    def test_initialization(self):
        """Test proper initialization of the analyzer."""
        self.assertEqual(self.analyzer.llm_model_name, "test-model")
        self.assertTrue(self.analyzer.use_cache)
        self.assertTrue(self.analyzer.debug_mode)
        self.mock_llm_manager.assert_called_once_with('together', 'test-model')
    
    def test_cache_usage_with_model_name(self):
        """Test that the cache key includes the model name."""
        # Create a mock cache
        self.analyzer.cache = MagicMock()
        self.analyzer.cache.has.return_value = False
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps(MOCK_LLM_RESPONSE)
        self.mock_llm.invoke.return_value = mock_response
        
        # Test data
        variant_text = "V600E"
        entities = [{"entity_type": "gene", "text": "BRAF", "id": "673", "offset": 0}]
        passage_text = "BRAF V600E mutation is common in melanoma."
        
        # Call the method
        self.analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        
        # Check if the cache key includes the model name
        cache_key_pattern = f"llm_analysis:{self.analyzer.llm_model_name}:{variant_text}:"
        
        # Verify cache.has was called with a key containing the model name
        self.analyzer.cache.has.assert_called_once()
        actual_key = self.analyzer.cache.has.call_args[0][0]
        self.assertTrue(actual_key.startswith(cache_key_pattern))
        
        # Verify cache.set was called with the same key pattern
        self.analyzer.cache.set.assert_called_once()
        actual_set_key = self.analyzer.cache.set.call_args[0][0]
        self.assertTrue(actual_set_key.startswith(cache_key_pattern))
    
    def test_cache_hit(self):
        """Test handling of a cache hit."""
        # Create a mock cache with a hit
        self.analyzer.cache = MagicMock()
        self.analyzer.cache.has.return_value = True
        self.analyzer.cache.get.return_value = MOCK_LLM_RESPONSE["relationships"]
        
        # Test data
        variant_text = "V600E"
        entities = [{"entity_type": "gene", "text": "BRAF", "id": "673", "offset": 0}]
        passage_text = "BRAF V600E mutation is common in melanoma."
        
        # Call the method
        result = self.analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        
        # Verify cache was used and LLM was not called
        self.analyzer.cache.has.assert_called_once()
        self.analyzer.cache.get.assert_called_once()
        self.mock_llm.invoke.assert_not_called()
        
        # Check the result
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["entity_text"], "BRAF")
        self.assertEqual(result[0]["relationship_score"], 9)
    
    def test_analyze_passage_with_scores(self):
        """Test analyzing a passage with relationship scores."""
        pmid = "12345678"
        
        # Create mock passage with annotations
        gene_anno = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
        variant_anno = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
        disease_anno = create_mock_annotation("melanoma", "Disease", "D008545", 24, 8)
        
        passage = create_mock_passage(
            "BRAF with V600E mutation in melanoma.", 
            [gene_anno, variant_anno, disease_anno]
        )
        
        # Call the method
        result = self.analyzer._analyze_passage(pmid, passage)
        
        # Verify the result contains relationship scores
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pmid"], pmid)
        self.assertEqual(result[0]["variant_text"], "V600E")
        
        # Check gene relationship
        self.assertEqual(len(result[0]["genes"]), 1)
        self.assertEqual(result[0]["genes"][0]["text"], "BRAF")
        self.assertEqual(result[0]["genes"][0]["relationship_score"], 9)
        
        # Check disease relationship
        self.assertEqual(len(result[0]["diseases"]), 1)
        self.assertEqual(result[0]["diseases"][0]["text"], "melanoma")
        self.assertEqual(result[0]["diseases"][0]["relationship_score"], 8)
    
    def test_analyze_publication(self):
        """Test analyzing a complete publication."""
        pmid = "12345678"
        
        # Create mock passages
        gene_anno = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
        variant_anno = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
        disease_anno = create_mock_annotation("melanoma", "Disease", "D008545", 24, 8)
        
        passage = create_mock_passage(
            "BRAF with V600E mutation in melanoma.", 
            [gene_anno, variant_anno, disease_anno]
        )
        
        document = create_mock_document(pmid, [passage])
        
        # Call the method
        result = self.analyzer._analyze_publication(document)
        
        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pmid"], pmid)
        self.assertEqual(result[0]["variant_text"], "V600E")
        self.assertEqual(len(result[0]["genes"]), 1)
        self.assertEqual(result[0]["genes"][0]["text"], "BRAF")
        self.assertEqual(result[0]["genes"][0]["relationship_score"], 9)
    
    def test_json_repair_functions(self):
        """Test JSON repair functions."""
        # Test fixing trailing commas
        invalid_json = '{"key1": "value1", "key2": "value2", }'
        fixed = self.analyzer._fix_trailing_commas(invalid_json)
        self.assertEqual(fixed, '{"key1": "value1", "key2": "value2" }')
        
        # Test fixing missing quotes
        invalid_json = '{key1: "value1", key2: "value2"}'
        fixed = self.analyzer._fix_missing_quotes(invalid_json)
        self.assertEqual(fixed, '{ "key1": "value1", "key2": "value2"}')
        
        # Test fixing inconsistent quotes
        invalid_json = "{'key1': \"value1\", 'key2': 'value2'}"
        fixed = self.analyzer._fix_inconsistent_quotes(invalid_json)
        self.assertEqual(fixed, "{\"key1\": \"value1\", \"key2\": \"value2\"}")
        
        # Test fixing missing commas
        invalid_json = '{"key1": "value1" "key2": "value2"}'
        fixed = self.analyzer._fix_missing_commas(invalid_json)
        self.assertEqual(fixed, '{"key1": "value1", "key2": "value2"}')
    
    def test_save_relationships_to_csv_with_scores(self):
        """Test saving relationships to CSV with relationship scores."""
        import tempfile
        import csv
        import os
        
        # Create test relationships with scores
        relationships = [
            {
                "pmid": "12345678",
                "variant_text": "V600E",
                "variant_id": "p.Val600Glu",
                "variant_offset": 10,
                "genes": [
                    {
                        "text": "BRAF",
                        "id": "673",
                        "explanation": "Direct association",
                        "relationship_score": 9
                    }
                ],
                "diseases": [
                    {
                        "text": "melanoma",
                        "id": "D008545",
                        "explanation": "Strong association",
                        "relationship_score": 8
                    }
                ],
                "tissues": [],
                "species": [],
                "chemicals": [],
                "passage_text": "BRAF with V600E mutation in melanoma."
            }
        ]
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name
        
        try:
            # Save relationships to the temporary file
            self.analyzer.save_relationships_to_csv(relationships, tmp_path)
            
            # Read the CSV file and verify the content
            with open(tmp_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # Should have 2 rows (one for gene, one for disease)
                self.assertEqual(len(rows), 2)
                
                # Check gene row
                gene_row = next(row for row in rows if row["gene"] == "BRAF")
                self.assertEqual(gene_row["gene_score"], "9")
                self.assertEqual(gene_row["gene_explanation"], "Direct association")
                
                # Check disease row
                disease_row = next(row for row in rows if row["disease"] == "melanoma")
                self.assertEqual(disease_row["disease_score"], "8")
                self.assertEqual(disease_row["disease_explanation"], "Strong association")
        
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main() 