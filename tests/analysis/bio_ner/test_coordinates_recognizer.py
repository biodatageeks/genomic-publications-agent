"""
Test module for CoordinatesRecognizer class.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch
from src.analysis.bio_ner.coordinates_recognizer import CoordinatesRecognizer


class TestCoordinatesRecognizer:
    """Test suite for CoordinatesRecognizer."""
    
    @pytest.fixture
    def recognizer(self):
        """Create a CoordinatesRecognizer instance for testing."""
        return CoordinatesRecognizer()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager."""
        mock_manager = Mock()
        mock_llm = Mock()
        mock_llm.invoke.return_value = "rs123456, c.123A>G"
        mock_manager.get_llm.return_value = mock_llm
        return mock_manager
    
    def test_01_initialization_without_llm(self, recognizer):
        """Test initialization without LLM manager."""
        assert recognizer.llm_manager is None
        assert recognizer.model_name == "gpt-3.5-turbo"
        assert hasattr(recognizer, 'hgvs_dna_c')
    
    def test_02_initialization_with_llm(self, mock_llm_manager):
        """Test initialization with LLM manager."""
        recognizer = CoordinatesRecognizer(llm_manager=mock_llm_manager)
        assert recognizer.llm_manager == mock_llm_manager
    
    def test_03_hgvs_dna_c_recognition(self, recognizer):
        """Test recognition of HGVS DNA c. notation."""
        text = "The variant MTHFR:c.677C>T is associated with disease."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "MTHFR:c.677C>T"
        assert coords[0]['type'] == "hgvs_dna_c"
    
    def test_04_hgvs_dna_g_recognition(self, recognizer):
        """Test recognition of HGVS DNA g. notation."""
        text = "The genomic variant is NM_000546:g.7578A>G."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "NM_000546:g.7578A>G"
        assert coords[0]['type'] == "hgvs_dna_g"
    
    def test_05_hgvs_protein_recognition(self, recognizer):
        """Test recognition of HGVS protein notation."""
        text = "The protein variant is TP53:p.Val143Ala."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "TP53:p.Val143Ala"
        assert coords[0]['type'] == "hgvs_protein"
    
    def test_06_dbsnp_recognition(self, recognizer):
        """Test recognition of dbSNP identifiers."""
        text = "The SNP rs1234567 is located on chromosome 1."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "rs1234567"
        assert coords[0]['type'] == "dbsnp"
    
    def test_07_chromosomal_position_recognition(self, recognizer):
        """Test recognition of chromosomal positions."""
        text = "The variant is at chr7:140453136A>T."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "chr7:140453136A>T"
        assert coords[0]['type'] == "chr_position"
    
    def test_08_chromosomal_aberration_recognition(self, recognizer):
        """Test recognition of chromosomal aberrations."""
        text = "The deletion del(15)(q11.2q13.1) is pathogenic."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "del(15)(q11.2q13.1)"
        assert coords[0]['type'] == "chr_aberration"
    
    def test_09_translocation_recognition(self, recognizer):
        """Test recognition of chromosomal translocations."""
        text = "The translocation t(9;22)(q34;q11.2) causes CML."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "t(9;22)(q34;q11.2)"
        assert coords[0]['type'] == "chr_aberration"
    
    def test_10_repeat_expansion_recognition(self, recognizer):
        """Test recognition of repeat expansions."""
        text = "HTT:c.52CAG[>36] expansion causes Huntington's disease."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "HTT:c.52CAG[>36]"
        assert coords[0]['type'] == "repeat_expansion"
    
    def test_11_multiple_coordinates_in_text(self, recognizer):
        """Test recognition of multiple coordinates in one text."""
        text = "The variants rs123456 and BRCA1:c.185delAG are linked."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 2
        coord_values = [c['coordinate'] for c in coords]
        assert "rs123456" in coord_values
        assert "BRCA1:c.185delAG" in coord_values
    
    def test_12_case_insensitive_recognition(self, recognizer):
        """Test case insensitive recognition."""
        text = "The variant MTHFR:C.677C>T is important."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "MTHFR:C.677C>T"
    
    def test_13_deletion_variants(self, recognizer):
        """Test recognition of deletion variants."""
        text = "The deletion CFTR:c.1521_1523delCTT is common."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "CFTR:c.1521_1523delCTT"
    
    def test_14_duplication_variants(self, recognizer):
        """Test recognition of duplication variants."""
        text = "The duplication BRCA1:c.5266dupC is pathogenic."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "BRCA1:c.5266dupC"
    
    def test_15_insertion_variants(self, recognizer):
        """Test recognition of insertion variants."""
        text = "The insertion FBN1:c.7754_7755insA affects splicing."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "FBN1:c.7754_7755insA"
    
    def test_16_delins_variants(self, recognizer):
        """Test recognition of deletion-insertion variants."""
        text = "The variant DMD:c.183_186delinsCTG is complex."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "DMD:c.183_186delinsCTG"
    
    def test_17_rna_coordinates(self, recognizer):
        """Test recognition of RNA coordinates."""
        text = "The RNA variant NM_000546:r.123a>g affects splicing."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "NM_000546:r.123a>g"
        assert coords[0]['type'] == "hgvs_rna"
    
    def test_18_protein_deletion(self, recognizer):
        """Test recognition of protein deletions."""
        text = "The protein deletion p.Val143del is pathogenic."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "p.Val143del"
        assert coords[0]['type'] == "hgvs_protein"
    
    def test_19_empty_text_handling(self, recognizer):
        """Test handling of empty text."""
        coords = recognizer.extract_coordinates_regex("")
        assert len(coords) == 0
    
    def test_20_no_coordinates_in_text(self, recognizer):
        """Test text with no coordinates."""
        text = "This is a normal text without any genomic coordinates."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 0
    
    def test_21_coordinate_with_intronic_positions(self, recognizer):
        """Test recognition of coordinates with intronic positions."""
        text = "The variant PAH:c.1066-11_1066-10delTT affects splicing."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "PAH:c.1066-11_1066-10delTT"
    
    def test_22_coordinate_with_utr_positions(self, recognizer):
        """Test recognition of coordinates with UTR positions."""
        text = "The variant c.*123A>G is in the 3' UTR."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "c.*123A>G"
    
    def test_23_chromosomal_coordinates_different_chromosomes(self, recognizer):
        """Test recognition of different chromosome formats."""
        text = "Variants on chrX:123456 and chrMT:7890 were found."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 2
        coord_values = [c['coordinate'] for c in coords]
        assert "chrX:123456" in coord_values
        assert "chrMT:7890" in coord_values
    
    def test_24_inversion_chromosomal_aberration(self, recognizer):
        """Test recognition of chromosomal inversions."""
        text = "The inversion inv(16)(p13q22) is found in AML."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "inv(16)(p13q22)"
        assert coords[0]['type'] == "chr_aberration"
    
    def test_25_protein_stop_codon(self, recognizer):
        """Test recognition of protein stop codons."""
        text = "The nonsense variant p.Arg123Ter truncates the protein."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "p.Arg123Ter"
        assert coords[0]['type'] == "hgvs_protein"
    
    def test_26_recognize_coordinates_text_regex_method(self, recognizer):
        """Test recognize_coordinates_text with regex method."""
        text = "The variant MTHFR:c.677C>T and rs1234567 are important."
        coords = recognizer.recognize_coordinates_text(text, method="regex")
        assert len(coords) == 2
        assert "MTHFR:c.677C>T" in coords
        assert "rs1234567" in coords
    
    def test_27_recognize_coordinates_text_llm_method(self, mock_llm_manager):
        """Test recognize_coordinates_text with LLM method."""
        recognizer = CoordinatesRecognizer(llm_manager=mock_llm_manager)
        text = "Some text with coordinates."
        coords = recognizer.recognize_coordinates_text(text, method="llm")
        assert len(coords) == 2
        assert "rs123456" in coords
        assert "c.123A>G" in coords
    
    def test_28_recognize_coordinates_text_hybrid_method(self, mock_llm_manager):
        """Test recognize_coordinates_text with hybrid method."""
        recognizer = CoordinatesRecognizer(llm_manager=mock_llm_manager)
        text = "The variant MTHFR:c.677C>T is important."
        coords = recognizer.recognize_coordinates_text(text, method="hybrid")
        # Should combine regex and LLM results
        assert len(coords) >= 1
        assert "MTHFR:c.677C>T" in coords
    
    def test_29_recognize_coordinates_text_invalid_method(self, recognizer):
        """Test recognize_coordinates_text with invalid method."""
        with pytest.raises(ValueError, match="Unknown method: invalid"):
            recognizer.recognize_coordinates_text("test", method="invalid")
    
    def test_30_generate_llm_prompt(self, recognizer):
        """Test LLM prompt generation."""
        text = "Sample text for testing."
        prompt = recognizer._generate_llm_prompt(text)
        assert "Extract all genomic coordinates" in prompt
        assert text in prompt
        assert "HGVS DNA" in prompt
    
    def test_31_parse_llm_response_comma_separated(self, recognizer):
        """Test parsing comma-separated LLM response."""
        response = "rs123456, c.677C>T, p.Val600Glu"
        coords = recognizer._parse_llm_response(response)
        assert len(coords) == 3
        assert "rs123456" in coords
        assert "c.677C>T" in coords
        assert "p.Val600Glu" in coords
    
    def test_32_parse_llm_response_numbered_list(self, recognizer):
        """Test parsing numbered list LLM response."""
        response = "1. rs123456\n2. c.677C>T\n3. p.Val600Glu"
        coords = recognizer._parse_llm_response(response)
        assert len(coords) == 3
        assert "rs123456" in coords
        assert "c.677C>T" in coords
        assert "p.Val600Glu" in coords
    
    def test_33_parse_llm_response_bulleted_list(self, recognizer):
        """Test parsing bulleted list LLM response."""
        response = "- rs123456\n- c.677C>T\n* p.Val600Glu"
        coords = recognizer._parse_llm_response(response)
        assert len(coords) == 3
        assert "rs123456" in coords
        assert "c.677C>T" in coords
        assert "p.Val600Glu" in coords
    
    def test_34_parse_llm_response_no_coordinates(self, recognizer):
        """Test parsing LLM response with no coordinates."""
        response = "No coordinates found."
        coords = recognizer._parse_llm_response(response)
        assert len(coords) == 0
    
    def test_35_parse_llm_response_empty(self, recognizer):
        """Test parsing empty LLM response."""
        coords = recognizer._parse_llm_response("")
        assert len(coords) == 0
    
    def test_36_recognize_coordinates_file(self, recognizer):
        """Test recognition of coordinates from a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("The variant MTHFR:c.677C>T is important.")
            temp_file = f.name
        
        try:
            coords = recognizer.recognize_coordinates_file(temp_file)
            assert len(coords) == 1
            assert "MTHFR:c.677C>T" in coords
        finally:
            os.unlink(temp_file)
    
    def test_37_recognize_coordinates_dir(self, recognizer):
        """Test recognition of coordinates from directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1_path = os.path.join(temp_dir, "test1.txt")
            file2_path = os.path.join(temp_dir, "test2.txt")
            
            with open(file1_path, 'w') as f:
                f.write("The variant MTHFR:c.677C>T is important.")
            
            with open(file2_path, 'w') as f:
                f.write("Another variant rs1234567.")
            
            results = recognizer.recognize_coordinates_dir(temp_dir)
            assert "test1.txt" in results
            assert "test2.txt" in results
            assert "MTHFR:c.677C>T" in results["test1.txt"]
            assert "rs1234567" in results["test2.txt"]
    
    def test_38_save_coordinates_to_file(self, recognizer):
        """Test saving coordinates to file."""
        coords = ["MTHFR:c.677C>T", "rs1234567"]
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
        
        try:
            recognizer.save_coordinates_to_file(coords, temp_file)
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "MTHFR:c.677C>T" in content
                assert "rs1234567" in content
        finally:
            os.unlink(temp_file)
    
    def test_39_find_coordinate_in_text_found(self, recognizer):
        """Test finding expected coordinate in text."""
        text = "The variant MTHFR:c.677C>T is important."
        expected = "mthfr:c.677c>t"  # case insensitive
        found, coords = recognizer.find_coordinate_in_text(text, expected)
        assert found == True
        assert len(coords) == 1
    
    def test_40_find_coordinate_in_text_not_found(self, recognizer):
        """Test not finding coordinate in text."""
        text = "This text has no coordinates."
        expected = "c.677C>T"
        found, coords = recognizer.find_coordinate_in_text(text, expected)
        assert found == False
        assert len(coords) == 0
    
    def test_41_evaluate_on_snippets(self, recognizer):
        """Test evaluation on snippets."""
        snippets = [
            {"text": "The variant MTHFR:c.677C>T is important.", "coordinate": "MTHFR:c.677C>T"},
            {"text": "Another variant rs1234567.", "coordinate": "rs1234567"},
            {"text": "No coordinates here.", "coordinate": "c.123A>G"}
        ]
        
        results = recognizer.evaluate_on_snippets(snippets)
        assert results["total_snippets"] == 3
        assert results["found_coordinates"] == 2
        assert results["accuracy"] == 2/3
    
    def test_42_load_snippets_from_file(self, recognizer):
        """Test loading snippets from JSON file."""
        snippets_data = [
            {"text": "Sample text", "coordinate": "c.123A>G"},
            {"text": "Another text", "coordinate": "rs123456"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(snippets_data, f)
            temp_file = f.name
        
        try:
            loaded_snippets = recognizer.load_snippets_from_file(temp_file)
            assert len(loaded_snippets) == 2
            assert loaded_snippets[0]["coordinate"] == "c.123A>G"
        finally:
            os.unlink(temp_file)
    
    def test_43_save_results(self, recognizer):
        """Test saving evaluation results."""
        results = {"total_snippets": 10, "accuracy": 0.8}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            recognizer.save_results(results, temp_file)
            
            with open(temp_file, 'r') as f:
                saved_results = json.load(f)
                assert saved_results["total_snippets"] == 10
                assert saved_results["accuracy"] == 0.8
        finally:
            os.unlink(temp_file)
    
    def test_44_process_and_evaluate_integration(self, recognizer):
        """Test full process and evaluation pipeline."""
        snippets_data = [
            {"text": "The variant MTHFR:c.677C>T is important.", "coordinate": "MTHFR:c.677C>T"},
            {"text": "Another variant rs1234567.", "coordinate": "rs1234567"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(snippets_data, f)
            snippets_file = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            results_file = f.name
        
        try:
            results = recognizer.process_and_evaluate(snippets_file, results_file)
            assert results["total_snippets"] == 2
            assert results["found_coordinates"] == 2
            assert results["accuracy"] == 1.0
            
            # Check if results file was created
            assert os.path.exists(results_file)
        finally:
            os.unlink(snippets_file)
            os.unlink(results_file)
    
    def test_45_get_coordinate_types(self, recognizer):
        """Test coordinate type analysis."""
        coordinates = ["MTHFR:c.677C>T", "rs1234567", "p.Val600Glu"]
        type_counts = recognizer.get_coordinate_types(coordinates)
        
        assert "hgvs_dna_c" in type_counts
        assert "dbsnp" in type_counts
        assert "hgvs_protein" in type_counts
    
    def test_46_coordinates_sorting_by_position(self, recognizer):
        """Test that coordinates are sorted by their position in text."""
        text = "First rs1234567 then MTHFR:c.677C>T finally chr1:12345."
        coords = recognizer.extract_coordinates_regex(text)
        
        # Check order based on position in text
        assert coords[0]['coordinate'] == "rs1234567"
        assert coords[1]['coordinate'] == "MTHFR:c.677C>T"
        assert coords[2]['coordinate'] == "chr1:12345"
    
    def test_47_overlapping_coordinate_patterns(self, recognizer):
        """Test handling of overlapping coordinate patterns."""
        text = "The position chr7:140453136A>T is important."
        coords = recognizer.extract_coordinates_regex(text)
        
        # Should prefer more specific pattern (chr_position over chr_position_basic)
        assert len(coords) == 1
        assert coords[0]['type'] == "chr_position"
    
    def test_48_special_characters_in_coordinates(self, recognizer):
        """Test coordinates with special characters."""
        text = "The variant NM_000546.5:c.123A>G contains underscores and dots."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "NM_000546.5:c.123A>G"
    
    def test_49_complex_repeat_expansion(self, recognizer):
        """Test complex repeat expansion patterns."""
        text = "The expansion FMR1:c.-128CGG[>200] causes fragile X syndrome."
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) == 1
        assert coords[0]['coordinate'] == "FMR1:c.-128CGG[>200]"
        assert coords[0]['type'] == "repeat_expansion"
    
    def test_50_comprehensive_mixed_coordinate_types(self, recognizer):
        """Test comprehensive recognition of mixed coordinate types in one text."""
        text = """
        The study analyzed multiple variants including:
        - HGVS DNA: MTHFR:c.677C>T and BRCA1:g.41234567A>G
        - Protein: p.Val600Glu and p.Arg123Ter
        - dbSNP: rs1234567, rs9876543
        - Chromosomal: chr7:140453136A>T, chr1:12345-67890
        - Aberrations: del(15)(q11.2q13.1), t(9;22)(q34;q11.2)
        - Repeats: HTT:c.52CAG[>36]
        """
        
        coords = recognizer.extract_coordinates_regex(text)
        assert len(coords) >= 8  # Should find multiple coordinates
        
        # Check for presence of different types
        types_found = {coord['type'] for coord in coords}
        expected_types = {'hgvs_dna_c', 'hgvs_dna_g', 'hgvs_protein', 'dbsnp', 'chr_position', 'chr_aberration', 'repeat_expansion'}
        
        # Should find most of the expected types
        assert len(types_found.intersection(expected_types)) >= 5