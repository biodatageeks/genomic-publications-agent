"""
Tests for the FoxGenePMIDFinder class.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.fox_pmid_finder.fox_gene_pmid_finder import FoxGenePMIDFinder


class TestFoxGenePMIDFinder:
    """
    Tests for the FoxGenePMIDFinder class.
    """
    
    def test_init(self):
        """Test initialization of FoxGenePMIDFinder."""
        finder = FoxGenePMIDFinder()
        assert finder.genes == []
        assert finder.pmids == set()
        assert finder.litvar_client is not None
    
    def test_load_genes_from_file(self):
        """Test loading genes from a file."""
        # Create a temporary file with gene symbols
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("FOXA1\nFOXA2\nFOXA3\n")
            temp_file_path = temp_file.name
        
        try:
            finder = FoxGenePMIDFinder()
            genes = finder.load_genes_from_file(temp_file_path)
            
            assert len(genes) == 3
            assert genes == ["FOXA1", "FOXA2", "FOXA3"]
            assert finder.genes == genes
        
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    def test_load_genes_from_file_empty_lines(self):
        """Test loading genes from a file with empty lines."""
        # Create a temporary file with gene symbols and empty lines
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("FOXA1\n\nFOXA2\n\n\nFOXA3\n")
            temp_file_path = temp_file.name
        
        try:
            finder = FoxGenePMIDFinder()
            genes = finder.load_genes_from_file(temp_file_path)
            
            assert len(genes) == 3
            assert genes == ["FOXA1", "FOXA2", "FOXA3"]
        
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    def test_load_genes_from_file_not_found(self):
        """Test loading genes from a non-existent file."""
        finder = FoxGenePMIDFinder()
        with pytest.raises(FileNotFoundError):
            finder.load_genes_from_file("non_existent_file.txt")
    
    @patch('src.litvar_client.litvar_endpoint.LitVarEndpoint.search_by_genes')
    @patch('src.litvar_client.litvar_endpoint.LitVarEndpoint.get_pmids_pmcids')
    def test_find_pmids_for_genes(self, mock_get_pmids, mock_search):
        """Test finding PMIDs for genes."""
        # Mock the search_by_genes response
        mock_search.return_value = [
            {"_id": "id1", "rsid": "rs1", "gene": "FOXA1"},
            {"_id": "id2", "rsid": "rs2", "gene": "FOXA2"},
            {"_id": "id3", "rsid": None, "gene": "FOXA3"}  # Test handling None rsid
        ]
        
        # Mock the get_pmids_pmcids response
        mock_get_pmids.return_value = {
            "rs1": {"pmids": ["12345", "23456"], "pmcids": ["PMC1"]},
            "rs2": {"pmids": ["23456", "34567"], "pmcids": ["PMC2"]}
        }
        
        finder = FoxGenePMIDFinder()
        finder.genes = ["FOXA1", "FOXA2", "FOXA3"]
        
        pmids = finder.find_pmids_for_genes()
        
        # Check that mock functions were called with correct arguments
        mock_search.assert_called_once_with(["FOXA1", "FOXA2", "FOXA3"])
        mock_get_pmids.assert_called_once_with(["rs1", "rs2"])
        
        # Check results
        assert pmids == {"12345", "23456", "34567"}
        assert finder.pmids == pmids
    
    def test_find_pmids_for_genes_no_genes(self):
        """Test finding PMIDs when no genes are loaded."""
        finder = FoxGenePMIDFinder()
        with pytest.raises(ValueError, match="No genes loaded"):
            finder.find_pmids_for_genes()
    
    def test_save_pmids_to_file(self):
        """Test saving PMIDs to a file."""
        # Set up the finder with PMIDs
        finder = FoxGenePMIDFinder()
        finder.pmids = {"12345", "23456", "34567"}
        
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Save PMIDs
            finder.save_pmids_to_file(output_path)
            
            # Read and check the file contents
            with open(output_path, 'r') as file:
                pmids = [line.strip() for line in file]
            
            assert len(pmids) == 3
            assert set(pmids) == {"12345", "23456", "34567"}
            assert pmids == sorted(pmids)  # Verify sorting
        
        finally:
            # Clean up the temporary file
            os.unlink(output_path)
    
    def test_save_pmids_to_file_no_pmids(self):
        """Test saving PMIDs when no PMIDs are found."""
        finder = FoxGenePMIDFinder()
        with pytest.raises(ValueError, match="No PMIDs found"):
            finder.save_pmids_to_file("output.txt")
    
    @patch('src.fox_pmid_finder.fox_gene_pmid_finder.FoxGenePMIDFinder.load_genes_from_file')
    @patch('src.fox_pmid_finder.fox_gene_pmid_finder.FoxGenePMIDFinder.find_pmids_for_genes')
    @patch('src.fox_pmid_finder.fox_gene_pmid_finder.FoxGenePMIDFinder.save_pmids_to_file')
    def test_process_and_save(self, mock_save, mock_find, mock_load):
        """Test the process_and_save method."""
        # Mock the return values
        mock_load.return_value = ["FOXA1", "FOXA2"]
        mock_find.return_value = {"12345", "23456"}
        
        finder = FoxGenePMIDFinder()
        finder.process_and_save("input.txt", "output.txt")
        
        # Verify all methods were called with correct arguments
        mock_load.assert_called_once_with("input.txt")
        mock_find.assert_called_once()
        mock_save.assert_called_once_with("output.txt") 