"""
Tests for the ContextAnalyzer class from context_analyzer module.
"""
import os
import pytest
import json
from unittest.mock import patch, MagicMock, mock_open

from src.context_analyzer.context_analyzer import ContextAnalyzer


class TestContextAnalyzer:
    """
    Test suite for the ContextAnalyzer class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        analyzer = ContextAnalyzer()
        assert analyzer.snippets == []
        assert analyzer.snippets_file_path is None
    
    def test_init_with_snippets_file(self):
        """Test initialization with snippets file path."""
        with patch('builtins.open', new_callable=mock_open, read_data='[{"variant": "c.123A>G", "text": "Sample text"}]'):
            analyzer = ContextAnalyzer(snippets_file_path="test_snippets.json")
            assert analyzer.snippets_file_path == "test_snippets.json"
            assert len(analyzer.snippets) == 1
            assert analyzer.snippets[0]["variant"] == "c.123A>G"
    
    def test_init_with_snippets_list(self):
        """Test initialization with snippets list."""
        snippets = [{"variant": "c.123A>G", "text": "Sample text"}]
        analyzer = ContextAnalyzer(snippets=snippets)
        assert analyzer.snippets == snippets
        assert analyzer.snippets_file_path is None
    
    @patch('builtins.open', new_callable=mock_open, read_data='[{"variant": "c.123A>G", "text": "Sample text"}]')
    def test_load_snippets(self, mock_file):
        """Test loading snippets from a file."""
        analyzer = ContextAnalyzer()
        snippets = analyzer.load_snippets("test_snippets.json")
        
        mock_file.assert_called_once_with("test_snippets.json", "r", encoding="utf-8")
        assert len(snippets) == 1
        assert snippets[0]["variant"] == "c.123A>G"
        assert analyzer.snippets == snippets
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_load_snippets_file_error(self, mock_file):
        """Test handling file error when loading snippets."""
        analyzer = ContextAnalyzer()
        with pytest.raises(IOError):
            analyzer.load_snippets("nonexistent.json")
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_load_snippets_json_error(self, mock_file):
        """Test handling JSON error when loading snippets."""
        analyzer = ContextAnalyzer()
        with pytest.raises(json.JSONDecodeError):
            analyzer.load_snippets("invalid.json")
    
    def test_find_snippets_for_variant(self):
        """Test finding snippets for a specific variant."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text with c.123A>G"},
            {"variant": "p.V600E", "text": "Text with p.V600E"},
            {"variant": "c.123A>G", "text": "Another text with c.123A>G"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        # Test exact match
        result = analyzer.find_snippets_for_variant("c.123A>G")
        assert len(result) == 2
        assert result[0]["text"] == "Text with c.123A>G"
        assert result[1]["text"] == "Another text with c.123A>G"
        
        # Test no match
        result = analyzer.find_snippets_for_variant("nonexistent")
        assert len(result) == 0
    
    def test_find_snippets_for_gene(self):
        """Test finding snippets for a specific gene."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text for BRCA1"},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Text for BRAF"},
            {"variant": "c.456G>T", "gene": "BRCA1", "text": "Another text for BRCA1"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        # Test exact match
        result = analyzer.find_snippets_for_gene("BRCA1")
        assert len(result) == 2
        assert result[0]["text"] == "Text for BRCA1"
        assert result[1]["text"] == "Another text for BRCA1"
        
        # Test no match
        result = analyzer.find_snippets_for_gene("TP53")
        assert len(result) == 0
    
    def test_find_snippets_with_term(self):
        """Test finding snippets containing a specific term."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text about cancer mutation"},
            {"variant": "p.V600E", "text": "Text about melanoma"},
            {"variant": "c.456G>T", "text": "Another text about cancer"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        # Test term match
        result = analyzer.find_snippets_with_term("cancer")
        assert len(result) == 2
        assert "cancer" in result[0]["text"]
        assert "cancer" in result[1]["text"]
        
        # Test case insensitive match
        result = analyzer.find_snippets_with_term("CANCER")
        assert len(result) == 2
        
        # Test no match
        result = analyzer.find_snippets_with_term("nonexistent")
        assert len(result) == 0
    
    def test_combine_filters(self):
        """Test combining multiple filters for finding snippets."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text about breast cancer"},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Text about melanoma"},
            {"variant": "c.456G>T", "gene": "BRCA1", "text": "Another text about ovarian cancer"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        # Test combining variant and term
        result = analyzer.find_snippets(variant="c.123A>G", term="breast")
        assert len(result) == 1
        assert result[0]["variant"] == "c.123A>G"
        assert "breast" in result[0]["text"]
        
        # Test combining gene and term
        result = analyzer.find_snippets(gene="BRCA1", term="ovarian")
        assert len(result) == 1
        assert result[0]["gene"] == "BRCA1"
        assert "ovarian" in result[0]["text"]
        
        # Test no matches with combination
        result = analyzer.find_snippets(gene="BRAF", term="breast")
        assert len(result) == 0
    
    def test_find_snippets_no_filters(self):
        """Test finding snippets with no filters (should return all snippets)."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text 1"},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Text 2"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        result = analyzer.find_snippets()
        assert len(result) == 2
        assert result == snippets
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_snippets(self, mock_file):
        """Test saving snippets to a file."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text 1"},
            {"variant": "p.V600E", "text": "Text 2"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        analyzer.save_snippets("output.json")
        
        mock_file.assert_called_once_with("output.json", "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Verify JSON was written correctly
        json_str = mock_handle.write.call_args[0][0]
        saved_snippets = json.loads(json_str)
        assert len(saved_snippets) == 2
        assert saved_snippets[0]["variant"] == "c.123A>G"
        assert saved_snippets[1]["variant"] == "p.V600E"
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_snippets_file_error(self, mock_file):
        """Test handling file error when saving snippets."""
        analyzer = ContextAnalyzer(snippets=[{"variant": "c.123A>G", "text": "Text"}])
        
        with pytest.raises(IOError):
            analyzer.save_snippets("invalid/path/output.json")
    
    def test_extract_variant_context(self):
        """Test extracting context for a specific variant."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text about c.123A>G mutation", "pmid": "12345678"},
            {"variant": "p.V600E", "text": "Text about p.V600E variant", "pmid": "23456789"},
            {"variant": "c.123A>G", "text": "Another text about c.123A>G", "pmid": "34567890"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        context = analyzer.extract_variant_context("c.123A>G")
        
        assert isinstance(context, dict)
        assert context["variant"] == "c.123A>G"
        assert len(context["snippets"]) == 2
        assert context["pmids"] == ["12345678", "34567890"]
        assert "Text about c.123A>G mutation" in context["snippets"]
        assert "Another text about c.123A>G" in context["snippets"]
    
    def test_extract_variant_context_no_match(self):
        """Test extracting context for a variant with no matches."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text about c.123A>G mutation"},
            {"variant": "p.V600E", "text": "Text about p.V600E variant"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        context = analyzer.extract_variant_context("nonexistent")
        
        assert isinstance(context, dict)
        assert context["variant"] == "nonexistent"
        assert len(context["snippets"]) == 0
        assert context["pmids"] == []
    
    def test_extract_gene_context(self):
        """Test extracting context for a specific gene."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text about BRCA1 gene", "pmid": "12345678"},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Text about BRAF gene", "pmid": "23456789"},
            {"variant": "c.456G>T", "gene": "BRCA1", "text": "Another text about BRCA1", "pmid": "34567890"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        context = analyzer.extract_gene_context("BRCA1")
        
        assert isinstance(context, dict)
        assert context["gene"] == "BRCA1"
        assert len(context["snippets"]) == 2
        assert context["pmids"] == ["12345678", "34567890"]
        assert context["variants"] == ["c.123A>G", "c.456G>T"]
    
    def test_generate_disease_summary(self):
        """Test generating a disease summary for a variant."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Associated with breast cancer risk."},
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Also linked to ovarian cancer."},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Common in melanoma patients."}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        # Mock the summarization method
        with patch.object(analyzer, '_summarize_disease_associations', return_value="Associated with breast and ovarian cancer."):
            summary = analyzer.generate_disease_summary("c.123A>G")
            
            assert summary == "Associated with breast and ovarian cancer."
    
    def test_generate_disease_summary_no_snippets(self):
        """Test generating a disease summary for a variant with no snippets."""
        analyzer = ContextAnalyzer(snippets=[])
        
        summary = analyzer.generate_disease_summary("c.123A>G")
        
        assert summary == "No disease associations found."
    
    def test_analyze_variant_frequency(self):
        """Test analyzing variant frequency across snippets."""
        snippets = [
            {"variant": "c.123A>G", "text": "Text 1"},
            {"variant": "p.V600E", "text": "Text 2"},
            {"variant": "c.123A>G", "text": "Text 3"},
            {"variant": "c.123A>G", "text": "Text 4"},
            {"variant": "p.G12D", "text": "Text 5"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        frequency = analyzer.analyze_variant_frequency()
        
        assert isinstance(frequency, dict)
        assert len(frequency) == 3
        assert frequency["c.123A>G"] == 3
        assert frequency["p.V600E"] == 1
        assert frequency["p.G12D"] == 1
    
    def test_analyze_gene_frequency(self):
        """Test analyzing gene frequency across snippets."""
        snippets = [
            {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text 1"},
            {"variant": "p.V600E", "gene": "BRAF", "text": "Text 2"},
            {"variant": "c.456G>T", "gene": "BRCA1", "text": "Text 3"},
            {"variant": "p.G12D", "gene": "KRAS", "text": "Text 4"},
            {"variant": "c.789C>A", "gene": "BRCA1", "text": "Text 5"}
        ]
        analyzer = ContextAnalyzer(snippets=snippets)
        
        frequency = analyzer.analyze_gene_frequency()
        
        assert isinstance(frequency, dict)
        assert len(frequency) == 3
        assert frequency["BRCA1"] == 3
        assert frequency["BRAF"] == 1
        assert frequency["KRAS"] == 1
    
    # Integration tests
    
    def test_integration_load_and_filter(self, snippets_data, temp_json_file):
        """Integration test for loading and filtering snippets."""
        # Write test data to temp file
        with open(temp_json_file, 'w', encoding='utf-8') as f:
            json.dump(snippets_data, f)
        
        # Initialize analyzer and load data
        analyzer = ContextAnalyzer(snippets_file_path=temp_json_file)
        
        # Test filtering
        brca1_snippets = analyzer.find_snippets_for_gene("BRCA1")
        assert len(brca1_snippets) == 1
        assert brca1_snippets[0]["variant"] == "c.123A>G"
        
        variant_snippets = analyzer.find_snippets_for_variant("p.V600E")
        assert len(variant_snippets) == 1
        assert variant_snippets[0]["gene"] == "BRAF"
        
        melanoma_snippets = analyzer.find_snippets_with_term("melanoma")
        assert len(melanoma_snippets) == 1
        assert melanoma_snippets[0]["variant"] == "p.V600E"
    
    def test_integration_extract_and_save(self, snippets_data, temp_json_file):
        """Integration test for extracting context and saving results."""
        analyzer = ContextAnalyzer(snippets=snippets_data)
        
        # Extract context for a variant
        context = analyzer.extract_variant_context("c.123A>G")
        assert context["variant"] == "c.123A>G"
        assert len(context["snippets"]) == 1
        
        # Extract context for a gene
        context = analyzer.extract_gene_context("BRAF")
        assert context["gene"] == "BRAF"
        assert context["variants"] == ["p.V600E"]
        
        # Save filtered results
        melanoma_snippets = analyzer.find_snippets_with_term("melanoma")
        analyzer.save_snippets(temp_json_file, melanoma_snippets)
        
        # Verify saved content
        with open(temp_json_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert len(saved_data) == 1
            assert saved_data[0]["variant"] == "p.V600E" 