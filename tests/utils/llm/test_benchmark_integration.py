"""
Tests for integration between LlmManager and BenchmarkTestService.

This module provides tests that verify the correct interaction
between LlmManager and the BenchmarkTestService class.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, List, Union

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.llm import LlmManager
from src.analysis.BenchmarkTestService import BenchmarkTestService
from src.Config import Config


@pytest.fixture
def mock_llm_manager():
    """Creates a mock LlmManager"""
    mock = MagicMock(spec=LlmManager)
    mock.llm = MagicMock()
    mock.get_llm.return_value = mock.llm
    mock.get_llm_model_name.return_value = "mock-model"
    return mock


@pytest.fixture
def mock_coordinates_inference():
    """Creates a mock CoordinatesInference"""
    with patch('src.analysis.BenchmarkTestService.CoordinatesInference') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def sample_benchmark_test():
    """Creates a sample benchmark test dictionary"""
    return {
        "pmids": ["12345"],
        "user_query_dict": {
            "gene": "TP53",
            "disease": "Li-Fraumeni syndrome"
        },
        "hgvs_coordinate": "NM_000546.5:c.215C>G"
    }


class TestBenchmarkIntegration:
    """Tests for BenchmarkTestService integration with LlmManager"""

    def test_benchmark_service_init(self, mock_llm_manager, mock_coordinates_inference):
        """Test initialization of BenchmarkTestService"""
        # Patch the LlmManager to return our mock
        with patch('src.analysis.BenchmarkTestService.LlmManager', return_value=mock_llm_manager):
            # Create BenchmarkTestService
            service = BenchmarkTestService(
                endpoint_type="mock_endpoint",
                model_name="mock_model",
                max_num_tokens=1000
            )
            
            # Check that LlmManager was created correctly
            assert service.llm_manager is mock_llm_manager
            assert service.max_num_tokens == 1000

    def test_manual_test_coordinate_search(self, mock_llm_manager, mock_coordinates_inference):
        """Test manual_test_coordinate_search method"""
        # Set up mock CoordinatesInference to return some coordinates
        mock_coords_instance = mock_coordinates_inference.return_value
        mock_coords_instance.extract_coordinates_from_text.return_value = [
            "NM_000546.5:c.215C>G", 
            "NM_000546.5:g.7577120C>G"
        ]
        
        # Patch LlmManager and PubmedEndpoint
        with patch('src.analysis.BenchmarkTestService.LlmManager', return_value=mock_llm_manager), \
             patch('src.analysis.BenchmarkTestService.PubmedEndpoint') as mock_pubmed:
            
            # Mock PubmedEndpoint to return test text
            mock_pubmed.fetch_full_text_from_pubmed_id.return_value = "Test publication text"
            
            # Create BenchmarkTestService
            service = BenchmarkTestService(
                endpoint_type="mock_endpoint",
                model_name="mock_model",
                max_num_tokens=1000
            )
            
            # Set up mock text splitter to return single chunk
            with patch('src.analysis.BenchmarkTestService.RecursiveCharacterTextSplitter') as mock_splitter_class:
                mock_splitter = MagicMock()
                mock_splitter_class.return_value = mock_splitter
                
                # Mock document chunks
                mock_doc = MagicMock()
                mock_doc.page_content = "Test publication text"
                mock_splitter.create_documents.return_value = [mock_doc]
                
                # Call manual_test_coordinate_search
                pmids = ["12345"]
                result = service.manual_test_coordinate_search(pmids)
                
                # Verify PubmedEndpoint was called
                mock_pubmed.fetch_full_text_from_pubmed_id.assert_called_once_with("12345")
                
                # Verify CoordinatesInference.extract_coordinates_from_text was called
                mock_coords_instance.extract_coordinates_from_text.assert_called_once_with("Test publication text")
                
                # Verify result contains expected coordinates
                assert len(result) == 2
                assert "NM_000546.5:c.215C>G" in result
                assert "NM_000546.5:g.7577120C>G" in result

    def test_perform_simple_benchmark_test(self, mock_llm_manager, mock_coordinates_inference, sample_benchmark_test):
        """Test perform_simple_benchmark_test method"""
        # Set up mock CoordinatesInference
        mock_coords_instance = mock_coordinates_inference.return_value
        mock_coords_instance.extract_coordinates_from_text.return_value = [
            "NM_000546.5:c.215C>G"  # This should match the test coordinate
        ]
        mock_coords_instance.process_coordinate.return_value = (
            "Context text",  # context
            "missense_variant",  # so_term
            {"ncbi": True, "ensembl": True}  # links
        )
        
        # Patch LlmManager and PubmedEndpoint
        with patch('src.analysis.BenchmarkTestService.LlmManager', return_value=mock_llm_manager), \
             patch('src.analysis.BenchmarkTestService.PubmedEndpoint') as mock_pubmed:
            
            # Mock PubmedEndpoint to return test text
            mock_pubmed.fetch_full_text_from_pubmed_id.return_value = "Test publication text"
            
            # Create BenchmarkTestService
            service = BenchmarkTestService(
                endpoint_type="mock_endpoint",
                model_name="mock_model",
                max_num_tokens=1000
            )
            
            # Set up mock text splitter to return single chunk
            with patch('src.analysis.BenchmarkTestService.RecursiveCharacterTextSplitter') as mock_splitter_class:
                mock_splitter = MagicMock()
                mock_splitter_class.return_value = mock_splitter
                
                # Mock document chunks
                mock_doc = MagicMock()
                mock_doc.page_content = "Test publication text"
                mock_splitter.create_documents.return_value = [mock_doc]
                
                # Call perform_simple_benchmark_test
                found, links_valid = service.perform_simple_benchmark_test(sample_benchmark_test)
                
                # Verify method calls
                mock_pubmed.fetch_full_text_from_pubmed_id.assert_called_once_with("12345")
                mock_coords_instance.extract_coordinates_from_text.assert_called_once_with("Test publication text")
                mock_coords_instance.process_coordinate.assert_called_once_with(
                    "NM_000546.5:c.215C>G", 
                    "Test publication text",
                    sample_benchmark_test["user_query_dict"]
                )
                
                # Verify results
                assert found is True
                assert links_valid is True

    def test_prepare_texts_from_pmids(self, mock_llm_manager, mock_coordinates_inference):
        """Test prepare_texts_from_pmids method"""
        # Patch LlmManager and PubmedEndpoint
        with patch('src.analysis.BenchmarkTestService.LlmManager', return_value=mock_llm_manager), \
             patch('src.analysis.BenchmarkTestService.PubmedEndpoint') as mock_pubmed:
            
            # Mock PubmedEndpoint to return test text
            mock_pubmed.fetch_full_text_from_pubmed_id.return_value = "Test publication text with multiple paragraphs.\n\nSecond paragraph."
            
            # Create BenchmarkTestService
            service = BenchmarkTestService(
                endpoint_type="mock_endpoint",
                model_name="mock_model",
                max_num_tokens=1000
            )
            
            # Set up mock text splitter to return chunks
            with patch('src.analysis.BenchmarkTestService.RecursiveCharacterTextSplitter') as mock_splitter_class:
                mock_splitter = MagicMock()
                mock_splitter_class.return_value = mock_splitter
                
                # Mock document chunks
                mock_doc1 = MagicMock()
                mock_doc1.page_content = "Test publication text with multiple paragraphs."
                mock_doc2 = MagicMock()
                mock_doc2.page_content = "Second paragraph."
                mock_splitter.create_documents.return_value = [mock_doc1, mock_doc2]
                
                # Call prepare_texts_from_pmids
                pmids = ["12345"]
                texts = service.prepare_texts_from_pmids(pmids)
                
                # Verify PubmedEndpoint and splitter were called correctly
                mock_pubmed.fetch_full_text_from_pubmed_id.assert_called_once_with("12345")
                mock_splitter_class.assert_called_once()
                mock_splitter.create_documents.assert_called_once_with(["Test publication text with multiple paragraphs.\n\nSecond paragraph."])
                
                # Verify texts contains expected content
                assert len(texts) == 2
                assert texts[0] == "Test publication text with multiple paragraphs."
                assert texts[1] == "Second paragraph."


class TestRealBenchmarkIntegration:
    """Integration tests with real LlmManager (marked to be skipped by default)"""
    
    @pytest.mark.skip(reason="This test makes real API calls")
    def test_real_benchmark_inference(self):
        """Test manual_test_coordinate_search with real LlmManager and API calls"""
        # Create real LlmManager and BenchmarkTestService
        llm_manager = LlmManager('together')
        
        # Create BenchmarkTestService directly
        service = BenchmarkTestService(
            endpoint_type="together",
            model_name=llm_manager.get_llm_model_name(),
            max_num_tokens=1000
        )
        
        # Set up test data
        pmids = ["31157530"]  # PMID with TP53 mutations
        
        # Patch PubmedEndpoint to return a simple test text to avoid actual API calls
        with patch('src.analysis.BenchmarkTestService.PubmedEndpoint') as mock_pubmed:
            mock_pubmed.fetch_full_text_from_pubmed_id.return_value = (
                "The TP53 gene with mutation c.215C>G (p.Pro72Arg) is associated with Li-Fraumeni syndrome."
            )
            
            # Perform coordinate search
            result = service.manual_test_coordinate_search(pmids)
            
            # Basic validation of result
            assert isinstance(result, list)
            
            # Note: can't assert exact contents as real API response may vary
            print(f"Real API inference returned: {result}") 