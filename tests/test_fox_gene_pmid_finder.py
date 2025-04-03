"""
Unit tests for the FoxGenePMIDFinder class.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from src.fox_pmid_finder.fox_gene_pmid_finder import FoxGenePMIDFinder


@pytest.fixture
def mock_gene_file():
    """Create a temporary file with test gene names."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("FOXA1\nFOXA2\nFOXA3\n")
        temp_file_name = f.name
    
    yield temp_file_name
    
    # Clean up after test
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.fixture
def mock_output_file():
    """Create a temporary output file path."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_file_name = f.name
    
    # Remove the file immediately so it can be recreated by the tested function
    os.remove(temp_file_name)
    
    yield temp_file_name
    
    # Clean up after test
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


def test_load_genes_from_file(mock_gene_file):
    """Test loading genes from a file."""
    finder = FoxGenePMIDFinder()
    genes = finder.load_genes_from_file(mock_gene_file)
    
    assert genes == ["FOXA1", "FOXA2", "FOXA3"]
    assert finder.genes == ["FOXA1", "FOXA2", "FOXA3"]


def test_load_genes_file_not_found():
    """Test handling of non-existent input file."""
    finder = FoxGenePMIDFinder()
    
    with pytest.raises(FileNotFoundError):
        finder.load_genes_from_file("nonexistent_file.txt")


@patch('requests.get')
def test_find_pmids_for_genes(mock_get, mock_gene_file):
    """Test finding PMIDs for genes."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'esearchresult': {
            'idlist': ['123456', '789012', '345678']
        }
    }
    mock_get.return_value = mock_response
    
    finder = FoxGenePMIDFinder()
    finder.load_genes_from_file(mock_gene_file)
    pmids = finder.find_pmids_for_genes()
    
    # We should have called the API 3 times (once for each gene)
    assert mock_get.call_count == 3
    
    # We should have collected 3 unique PMIDs
    assert len(pmids) == 3
    assert '123456' in pmids
    assert '789012' in pmids
    assert '345678' in pmids


@patch('requests.get')
def test_save_pmids_to_file(mock_get, mock_gene_file, mock_output_file):
    """Test saving PMIDs to a file."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'esearchresult': {
            'idlist': ['123456', '789012', '345678']
        }
    }
    mock_get.return_value = mock_response
    
    finder = FoxGenePMIDFinder()
    finder.load_genes_from_file(mock_gene_file)
    finder.find_pmids_for_genes()
    finder.save_pmids_to_file(mock_output_file)
    
    # Check that the output file exists and contains the expected data
    assert os.path.exists(mock_output_file)
    
    with open(mock_output_file, 'r') as f:
        content = f.read().strip().split('\n')
    
    assert sorted(content) == sorted(['123456', '345678', '789012'])


def test_save_pmids_no_pmids(mock_output_file):
    """Test saving PMIDs when no PMIDs have been found."""
    finder = FoxGenePMIDFinder()
    
    with pytest.raises(ValueError, match="No PMIDs found"):
        finder.save_pmids_to_file(mock_output_file)


@patch('requests.get')
def test_process_and_save(mock_get, mock_gene_file, mock_output_file):
    """Test the process_and_save convenience method."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'esearchresult': {
            'idlist': ['123456', '789012', '345678']
        }
    }
    mock_get.return_value = mock_response
    
    finder = FoxGenePMIDFinder()
    finder.process_and_save(mock_gene_file, mock_output_file)
    
    # Check that the output file exists and contains the expected data
    assert os.path.exists(mock_output_file)
    
    with open(mock_output_file, 'r') as f:
        content = f.read().strip().split('\n')
    
    assert sorted(content) == sorted(['123456', '345678', '789012']) 