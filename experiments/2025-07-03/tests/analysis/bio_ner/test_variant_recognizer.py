"""
Comprehensive tests for VariantRecognizer.

This module tests the variant recognition system with
comprehensive coverage of edge cases and false positive detection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.analysis.bio_ner.variant_recognizer import VariantRecognizer, VariantMatch


class TestVariantRecognizer:
    """Test suite for VariantRecognizer."""
    
    @pytest.fixture
    def recognizer(self):
        """Create recognizer instance for testing."""
        return VariantRecognizer()
    
    def test_initialization(self, recognizer):
        """Test proper initialization of the recognizer."""
        assert recognizer is not None
        assert hasattr(recognizer, 'variant_patterns')
        assert hasattr(recognizer, 'false_positive_blacklist')
        assert hasattr(recognizer, 'positive_context_keywords')
        assert hasattr(recognizer, 'negative_context_keywords')
    
    def test_pattern_compilation(self, recognizer):
        """Test that all patterns are properly compiled."""
        patterns = recognizer.variant_patterns
        
        # Check all expected pattern types exist
        expected_types = [
            'hgvs_dna', 'hgvs_dna_del', 'hgvs_dna_ins', 'hgvs_dna_utr',
            'hgvs_protein_3letter', 'hgvs_protein_1letter', 'hgvs_protein_prefix',
            'hgvs_protein_ter', 'hgvs_protein_fs', 'dbsnp', 'chr_position',
            'simple_aa_change'
        ]
        
        for pattern_type in expected_types:
            assert pattern_type in patterns
            assert 'pattern' in patterns[pattern_type]
            assert 'confidence' in patterns[pattern_type]
            assert isinstance(patterns[pattern_type]['confidence'], float)
    
    def test_context_extraction(self, recognizer):
        """Test context extraction around matches."""
        text = "The BRCA1 gene has a mutation c.123A>G that is pathogenic."
        start = text.find("c.123A>G")
        end = start + len("c.123A>G")
        
        context_before, context_after = recognizer.get_context(text, start, end, window=20)
        
        assert "has a mutation" in context_before
        assert "that is pathogenic" in context_after
    
    def test_confidence_calculation(self, recognizer):
        """Test confidence calculation with different contexts."""
        # Test high confidence with genetic context
        variant = "c.123A>G"
        pattern_type = "hgvs_dna"
        context_before = "BRCA1 mutation"
        context_after = "causes breast cancer"
        
        confidence = recognizer.calculate_confidence(variant, pattern_type, context_before, context_after)
        assert confidence > 0.9  # Should be high confidence
        
        # Test lower confidence with lab context
        context_before = "buffer containing"
        context_after = "and Tris-HCl"
        
        confidence = recognizer.calculate_confidence(variant, pattern_type, context_before, context_after)
        assert confidence < 0.7  # Should be lower confidence
    
    def test_false_positive_detection(self, recognizer):
        """Test detection of known false positives."""
        # Test histone modifications
        assert recognizer.is_blacklisted("H3K4", "histone H3K4 methylation")
        assert recognizer.is_blacklisted("H2A", "histone H2A modification")
        
        # Test lab codes
        assert recognizer.is_blacklisted("U5F", "experimental condition")
        assert recognizer.is_blacklisted("R5B", "laboratory protocol")
        
        # Test experimental context
        assert recognizer.is_blacklisted("A1B", "buffer containing A1B and other reagents")
        
        # Test valid variants should not be blacklisted
        assert not recognizer.is_blacklisted("rs123456", "genetic variant rs123456")
        assert not recognizer.is_blacklisted("c.123A>G", "mutation c.123A>G in BRCA1")
    
    def test_hgvs_dna_variants(self, recognizer):
        """Test recognition of HGVS DNA variants."""
        test_cases = [
            ("The mutation c.123A>G is pathogenic.", ["c.123A>G"]),
            ("Found c.456T>C and c.789G>A variants.", ["c.456T>C", "c.789G>A"]),
            ("Deletion c.123_125del was identified.", ["c.123_125del"]),
            ("Insertion c.456insATG found.", ["c.456insATG"]),
            ("UTR variant c.*123A>G detected.", ["c.*123A>G"]),
        ]
        
        for text, expected in test_cases:
            variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
            assert len(variants) == len(expected), f"Expected {expected}, got {variants} for text: {text}"
            for variant in expected:
                assert variant in variants, f"Missing {variant} in {variants}"
    
    def test_hgvs_protein_variants(self, recognizer):
        """Test recognition of HGVS protein variants."""
        test_cases = [
            ("The p.Val600Glu mutation is oncogenic.", ["p.Val600Glu"]),
            ("Found p.V600E variant in BRAF.", ["p.V600E"]),
            ("Nonsense mutation p.Gln120*.", ["p.Gln120*"]),
            ("Frameshift p.Lys100fs detected.", ["p.Lys100fs"]),
            ("The p.Ter494Glu variant.", ["p.Ter494Glu"]),
        ]
        
        for text, expected in test_cases:
            variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
            assert len(variants) == len(expected), f"Expected {expected}, got {variants} for text: {text}"
            for variant in expected:
                assert variant in variants, f"Missing {variant} in {variants}"
    
    def test_dbsnp_variants(self, recognizer):
        """Test recognition of dbSNP identifiers."""
        test_cases = [
            ("SNP rs1234567 was associated with disease.", ["rs1234567"]),
            ("Found rs987654321 and rs555666777.", ["rs987654321", "rs555666777"]),
            ("The rs13447455 variant is common.", ["rs13447455"]),
        ]
        
        for text, expected in test_cases:
            variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
            assert len(variants) == len(expected), f"Expected {expected}, got {variants} for text: {text}"
            for variant in expected:
                assert variant in variants, f"Missing {variant} in {variants}"
    
    def test_chromosomal_variants(self, recognizer):
        """Test recognition of chromosomal position variants."""
        test_cases = [
            ("Variant chr7:140453136A>T found.", ["chr7:140453136A>T"]),
            ("Position chr1:12345G>C identified.", ["chr1:12345G>C"]),
            ("Found chr22:98765T>A mutation.", ["chr22:98765T>A"]),
        ]
        
        for text, expected in test_cases:
            variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
            assert len(variants) == len(expected), f"Expected {expected}, got {variants} for text: {text}"
            for variant in expected:
                assert variant in variants, f"Missing {variant} in {variants}"
    
    def test_false_positive_filtering(self, recognizer):
        """Test filtering of false positives."""
        test_cases = [
            # Should NOT find variants (false positives)
            ("We used H3K4me3 antibody in this experiment.", []),
            ("Buffer contains U5F and R5B reagents.", []),
            ("Laboratory code E3K was used.", []),
            ("Histone H2A modification was analyzed.", []),
            ("Cell culture medium F4A was prepared.", []),
            
            # Should find variants (true positives)
            ("The BRCA1 mutation c.185delAG is pathogenic.", ["c.185delAG"]),
            ("SNP rs13447455 was significant.", ["rs13447455"]),
        ]
        
        for text, expected in test_cases:
            variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
            assert len(variants) == len(expected), f"Expected {expected}, got {variants} for text: {text}"
            if expected:
                for variant in expected:
                    assert variant in variants, f"Missing {variant} in {variants}"
    
    def test_confidence_thresholding(self, recognizer):
        """Test confidence-based filtering."""
        # Text with mixed confidence variants
        text = "Gene mutation c.123A>G in genetic context and lab code H3K in protocol."
        
        # High confidence threshold should only return high-confidence variants
        high_conf_variants = recognizer.recognize_variants_text(text, min_confidence=0.9)
        assert "c.123A>G" in high_conf_variants
        assert "H3K" not in high_conf_variants
        
        # Lower confidence threshold might include more
        low_conf_variants = recognizer.recognize_variants_text(text, min_confidence=0.1)
        assert "c.123A>G" in low_conf_variants
        # H3K should still be filtered as false positive
        assert "H3K" not in low_conf_variants
    
    def test_detailed_recognition(self, recognizer):
        """Test detailed recognition with metadata."""
        text = "The BRCA1 mutation c.185delAG causes frameshift."
        
        detailed_variants = recognizer.recognize_variants_with_details(text, min_confidence=0.7)
        
        assert len(detailed_variants) == 1
        variant = detailed_variants[0]
        
        assert variant.variant == "c.185delAG"
        assert variant.confidence > 0.8
        assert "hgvs_dna" in variant.pattern_type
        assert "BRCA1 mutation" in variant.context_before
        assert "causes frameshift" in variant.context_after
    
    def test_empty_input(self, recognizer):
        """Test handling of empty or invalid input."""
        assert recognizer.recognize_variants_text("") == []
        assert recognizer.recognize_variants_text(None) == []
        assert recognizer.recognize_variants_text("   ") == []
        
        assert recognizer.recognize_variants_with_details("") == []
        assert recognizer.recognize_variants_with_details(None) == []
    
    def test_complex_text_parsing(self, recognizer):
        """Test parsing of complex scientific text."""
        complex_text = """
        In this study, we analyzed mutations in the BRCA1 gene. 
        The c.185delAG variant leads to a frameshift, while the 
        c.123A>G substitution affects splicing. Additionally, 
        the dbSNP variant rs13447455 was found to be associated 
        with increased risk. We also used H3K4me3 antibody for 
        chromatin analysis and buffer U5F for cell culture.
        """
        
        variants = recognizer.recognize_variants_text(complex_text, min_confidence=0.7)
        
        # Should find genetic variants but not lab codes
        expected_variants = ["c.185delAG", "c.123A>G", "rs13447455"]
        unexpected_variants = ["H3K4me3", "U5F"]
        
        for expected in expected_variants:
            assert expected in variants, f"Missing expected variant: {expected}"
        
        for unexpected in unexpected_variants:
            assert unexpected not in variants, f"Found unexpected variant: {unexpected}"
    
    def test_performance_edge_cases(self, recognizer):
        """Test performance with edge cases."""
        # Very long text
        long_text = "Normal text. " * 1000 + "mutation c.123A>G found." + "More text. " * 1000
        variants = recognizer.recognize_variants_text(long_text)
        assert "c.123A>G" in variants
        
        # Text with many false positives
        false_positive_text = "H3K H2A U5F R5B E3K C5A F4A H1B N9D B1A " * 10
        variants = recognizer.recognize_variants_text(false_positive_text)
        assert len(variants) == 0  # Should filter all false positives
        
        # Mixed content
        mixed_text = "mutation c.123A>G and c.456T>C and H3K4 and U5F and rs789"
        variants = recognizer.recognize_variants_text(mixed_text)
        assert "c.123A>G" in variants
        assert "c.456T>C" in variants
        assert "rs789" in variants
        assert "H3K4" not in variants
        assert "U5F" not in variants


class TestVariantMatchDataclass:
    """Test the VariantMatch dataclass."""
    
    def test_variant_match_creation(self):
        """Test creating VariantMatch instances."""
        match = VariantMatch(
            variant="c.123A>G",
            confidence=0.95,
            pattern_type="hgvs_dna",
            context_before="BRCA1 mutation",
            context_after="is pathogenic",
            start_pos=20,
            end_pos=28
        )
        
        assert match.variant == "c.123A>G"
        assert match.confidence == 0.95
        assert match.pattern_type == "hgvs_dna"
        assert match.context_before == "BRCA1 mutation"
        assert match.context_after == "is pathogenic"
        assert match.start_pos == 20
        assert match.end_pos == 28


class TestVariantRecognizerIntegration:
    """Integration tests for VariantRecognizer."""
    
    @pytest.fixture
    def recognizer(self):
        """Create recognizer instance for integration testing."""
        return VariantRecognizer()
    
    def test_real_biomedical_abstracts(self, recognizer):
        """Test with real biomedical abstract examples."""
        abstracts = [
            {
                "text": """The BRCA1 c.68_69delAG mutation is a founder mutation in 
                        Ashkenazi Jewish populations and accounts for approximately 
                        1% of hereditary breast cancer cases.""",
                "expected": ["c.68_69delAG"]
            },
            {
                "text": """In melanoma, the BRAF V600E mutation occurs in approximately 
                        50% of cases and represents a major therapeutic target.""",
                "expected": ["V600E"]
            },
            {
                "text": """Genome-wide association studies identified rs13447455 as 
                        significantly associated with breast cancer risk.""",
                "expected": ["rs13447455"]
            },
            {
                "text": """We performed chromatin immunoprecipitation using H3K4me3 
                        and H3K27ac antibodies to identify active enhancers.""",
                "expected": []  # Should not extract histone modifications
            }
        ]
        
        for abstract in abstracts:
            variants = recognizer.recognize_variants_text(abstract["text"], min_confidence=0.7)
            
            # Check expected variants are found
            for expected in abstract["expected"]:
                assert expected in variants, f"Missing {expected} in {abstract['text'][:100]}..."
            
            # Check no unexpected variants
            non_genetic = ["H3K4me3", "H3K27ac", "H2A", "H4K"]
            for non_var in non_genetic:
                assert non_var not in variants, f"Found false positive {non_var} in {abstract['text'][:100]}..."
    
    def test_batch_processing_simulation(self, recognizer):
        """Test processing multiple texts as in real experiments."""
        texts = [
            "BRCA1 mutation c.185delAG identified.",
            "Found rs123456 SNP association.",
            "Used H3K4me3 antibody in protocol.",
            "BRAF V600E mutation detected.",
            "Buffer U5F was prepared for experiment."
        ]
        
        all_variants = []
        for text in texts:
            variants = recognizer.recognize_variants_text(text)
            all_variants.extend(variants)
        
        # Should find genetic variants
        assert "c.185delAG" in all_variants
        assert "rs123456" in all_variants
        assert "V600E" in all_variants
        
        # Should not find lab codes
        assert "H3K4me3" not in all_variants
        assert "U5F" not in all_variants
    
    def test_comparison_with_old_pattern_matching(self, recognizer):
        """Test comparison with simple pattern matching approach."""
        # Text that would fool simple pattern matching
        tricky_text = """
        The study used several reagents including H3K4me3 antibody,
        buffer F2D, and plate A1B. However, we also identified the
        genuine BRCA1 mutation c.185delAG and the BRAF V600E variant.
        Laboratory codes like U5F and R5B were used throughout.
        """
        
        variants = recognizer.recognize_variants_text(tricky_text, min_confidence=0.7)
        
        # Should find real variants
        real_variants = ["c.185delAG", "V600E"]
        for real_var in real_variants:
            assert real_var in variants, f"Failed to find real variant: {real_var}"
        
        # Should not find lab codes (that simple regex might catch)
        lab_codes = ["H3K4me3", "F2D", "A1B", "U5F", "R5B"]
        for lab_code in lab_codes:
            assert lab_code not in variants, f"Incorrectly found lab code: {lab_code}"
        
        print(f"Improved recognizer correctly filtered {len(lab_codes)} false positives "
              f"while finding {len(real_variants)} real variants.")


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize("variant_text,expected_type,should_find", [
    # HGVS DNA variants
    ("c.123A>G", "hgvs_dna", True),
    ("c.456_789del", "hgvs_dna_del", True),
    ("c.123insATG", "hgvs_dna_ins", True),
    ("c.*734A>T", "hgvs_dna_utr", True),
    
    # HGVS protein variants  
    ("p.Val600Glu", "hgvs_protein_3letter", True),
    ("p.V600E", "hgvs_protein_1letter", True),
    ("p.Ter494Glu", "hgvs_protein_ter", True),
    ("p.Lys100fs", "hgvs_protein_fs", True),
    
    # dbSNP variants
    ("rs1234567", "dbsnp", True),
    ("rs13447455", "dbsnp", True),
    
    # Chromosomal variants
    ("chr7:140453136A>T", "chr_position", True),
    
    # False positives (should not find)
    ("H3K4", "false_positive", False),
    ("U5F", "false_positive", False),
    ("R5B", "false_positive", False),
])
def test_variant_recognition_parametrized(variant_text, expected_type, should_find):
    """Parametrized test for variant recognition."""
    recognizer = VariantRecognizer()
    
    # Create realistic context
    if should_find:
        text = f"Gene mutation {variant_text} was identified in the study."
    else:
        text = f"Laboratory protocol used {variant_text} reagent."
    
    variants = recognizer.recognize_variants_text(text, min_confidence=0.7)
    
    if should_find:
        assert variant_text in variants, f"Failed to find {variant_text} of type {expected_type}"
    else:
        assert variant_text not in variants, f"Incorrectly found false positive {variant_text}"


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])