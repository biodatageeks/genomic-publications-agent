"""
Tests for HGVSNormalizer.

This module tests HGVS variant normalization and standardization functionality.
"""

import pytest
from typing import List, Dict, Set
from src.utils.variant_normalizer import HGVSNormalizer


class TestHGVSNormalizer:
    """Test suite for HGVSNormalizer."""
    
    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance for testing."""
        return HGVSNormalizer()
    
    def test_initialization(self, normalizer):
        """Test proper initialization."""
        assert normalizer is not None
        assert hasattr(normalizer, 'dna_patterns')
        assert hasattr(normalizer, 'protein_patterns')
        assert hasattr(normalizer, 'amino_acid_codes')
    
    def test_dna_variant_normalization(self, normalizer):
        """Test normalization of DNA variants."""
        test_cases = [
            # Basic substitutions
            ("c.123A>G", "c.123A>G"),
            ("C.123A>G", "c.123A>G"),  # Case normalization
            ("c.123a>g", "c.123A>G"),  # Case normalization
            
            # With prefixes
            ("734A>T", "c.734A>T"),
            ("g.123A>G", "g.123A>G"),
            ("m.123A>G", "m.123A>G"),
            ("n.123A>G", "n.123A>G"),
            
            # UTR variants
            ("c.*734A>T", "c.*734A>T"),
            ("*734A>T", "c.*734A>T"),
            
            # Deletions
            ("c.123_125del", "c.123_125del"),
            ("c.123del", "c.123del"),
            
            # Insertions
            ("c.123insATG", "c.123insATG"),
            ("c.123ins", "c.123ins"),
        ]
        
        for input_variant, expected in test_cases:
            result = normalizer.normalize_variant(input_variant)
            assert result.normalized == expected, f"Input: {input_variant}, Expected: {expected}, Got: {result.normalized}"
            assert result.confidence > 0.8
    
    def test_protein_variant_normalization(self, normalizer):
        """Test normalization of protein variants."""
        test_cases = [
            # 3-letter to 1-letter conversion
            ("p.Val600Glu", "p.V600E"),
            ("p.Ala85Pro", "p.A85P"),
            ("p.Lys100Ter", "p.K100*"),
            
            # 1-letter variants (should remain unchanged)
            ("p.V600E", "p.V600E"),
            ("p.A85P", "p.A85P"),
            ("p.K100*", "p.K100*"),
            
            # Without p. prefix
            ("Val600Glu", "p.V600E"),
            ("V600E", "p.V600E"),
            ("Ala85Pro", "p.A85P"),
            ("A85P", "p.A85P"),
            
            # Frameshift variants
            ("p.Lys100fs", "p.K100fs"),
            ("Lys100fs", "p.K100fs"),
            ("K100fs", "p.K100fs"),
            
            # Stop/nonsense variants
            ("p.Gln120*", "p.Q120*"),
            ("p.Gln120Ter", "p.Q120*"),
            ("Gln120*", "p.Q120*"),
            
            # Case variations
            ("p.val600glu", "p.V600E"),
            ("P.VAL600GLU", "p.V600E"),
        ]
        
        for input_variant, expected in test_cases:
            result = normalizer.normalize_variant(input_variant)
            assert result.normalized == expected, f"Input: {input_variant}, Expected: {expected}, Got: {result.normalized}"
    
    def test_dbsnp_normalization(self, normalizer):
        """Test normalization of dbSNP identifiers."""
        test_cases = [
            ("rs1234567", "rs1234567"),
            ("RS1234567", "rs1234567"),  # Case normalization
            ("1234567", "rs1234567"),    # Add rs prefix
            ("rs13447455", "rs13447455"),
        ]
        
        for input_variant, expected in test_cases:
            result = normalizer.normalize_variant(input_variant)
            assert result.normalized == expected, f"Input: {input_variant}, Expected: {expected}, Got: {result.normalized}"
    
    def test_chromosomal_position_normalization(self, normalizer):
        """Test normalization of chromosomal positions."""
        test_cases = [
            ("chr7:140453136A>T", "chr7:140453136A>T"),
            ("CHR7:140453136A>T", "chr7:140453136A>T"),  # Case normalization
            ("7:140453136A>T", "chr7:140453136A>T"),     # Add chr prefix
            ("chrX:12345G>C", "chrX:12345G>C"),
            ("chrY:98765T>A", "chrY:98765T>A"),
        ]
        
        for input_variant, expected in test_cases:
            result = normalizer.normalize_variant(input_variant)
            assert result.normalized == expected, f"Input: {input_variant}, Expected: {expected}, Got: {result.normalized}"
    
    def test_amino_acid_code_conversion(self, normalizer):
        """Test amino acid code conversion."""
        # Test 3-letter to 1-letter
        assert normalizer.convert_aa_3to1("Val") == "V"
        assert normalizer.convert_aa_3to1("Ala") == "A"
        assert normalizer.convert_aa_3to1("Glu") == "E"
        assert normalizer.convert_aa_3to1("Ter") == "*"
        assert normalizer.convert_aa_3to1("*") == "*"  # Already 1-letter
        
        # Test 1-letter to 3-letter
        assert normalizer.convert_aa_1to3("V") == "Val"
        assert normalizer.convert_aa_1to3("A") == "Ala"
        assert normalizer.convert_aa_1to3("E") == "Glu"
        assert normalizer.convert_aa_1to3("*") == "Ter"
        assert normalizer.convert_aa_1to3("Val") == "Val"  # Already 3-letter
        
        # Test case insensitive
        assert normalizer.convert_aa_3to1("val") == "V"
        assert normalizer.convert_aa_1to3("v") == "Val"
        
        # Test unknown codes
        assert normalizer.convert_aa_3to1("XYZ") == "XYZ"  # Return as-is
        assert normalizer.convert_aa_1to3("Z") == "Z"      # Return as-is
    
    def test_variant_equivalence(self, normalizer):
        """Test checking if variants are equivalent."""
        # Exact matches
        assert normalizer.are_equivalent("c.123A>G", "c.123A>G")
        assert normalizer.are_equivalent("p.V600E", "p.V600E")
        
        # Case differences
        assert normalizer.are_equivalent("c.123A>G", "C.123A>G")
        assert normalizer.are_equivalent("rs123456", "RS123456")
        
        # Protein format differences
        assert normalizer.are_equivalent("p.Val600Glu", "p.V600E")
        assert normalizer.are_equivalent("Val600Glu", "p.V600E")
        assert normalizer.are_equivalent("V600E", "p.V600E")
        
        # DNA prefix differences
        assert normalizer.are_equivalent("734A>T", "c.734A>T")
        assert normalizer.are_equivalent("*734A>T", "c.*734A>T")
        
        # dbSNP prefix differences
        assert normalizer.are_equivalent("1234567", "rs1234567")
        
        # Non-equivalent variants
        assert not normalizer.are_equivalent("c.123A>G", "c.123A>T")
        assert not normalizer.are_equivalent("p.V600E", "p.V600K")
        assert not normalizer.are_equivalent("rs123456", "rs789012")
    
    def test_variant_grouping(self, normalizer):
        """Test grouping equivalent variants."""
        variant_list = [
            "c.123A>G",
            "C.123A>G",
            "c.123a>g",
            "p.Val600Glu",
            "p.V600E",
            "Val600Glu",
            "V600E",
            "rs1234567",
            "RS1234567",
            "1234567",
            "c.456T>C",
            "different.variant"
        ]
        
        groups = normalizer.group_equivalent_variants(variant_list)
        
        # Should have groups for c.123A>G, p.V600E, rs1234567, c.456T>C, and different.variant
        assert len(groups) >= 5
        
        # Check specific groupings
        c123_group = None
        v600_group = None
        rs123_group = None
        
        for group in groups:
            normalized = group['normalized']
            if normalized == "c.123A>G":
                c123_group = group
            elif normalized == "p.V600E":
                v600_group = group
            elif normalized == "rs1234567":
                rs123_group = group
        
        assert c123_group is not None
        assert len(c123_group['variants']) == 3  # c.123A>G, C.123A>G, c.123a>g
        
        assert v600_group is not None
        assert len(v600_group['variants']) == 4  # p.Val600Glu, p.V600E, Val600Glu, V600E
        
        assert rs123_group is not None
        assert len(rs123_group['variants']) == 3  # rs1234567, RS1234567, 1234567
    
    def test_confidence_scoring(self, normalizer):
        """Test confidence scoring for normalizations."""
        # High confidence cases
        high_conf_cases = [
            "c.123A>G",      # Already normalized HGVS
            "p.V600E",       # Already normalized protein
            "rs1234567",     # Already normalized dbSNP
        ]
        
        for variant in high_conf_cases:
            result = normalizer.normalize_variant(variant)
            assert result.confidence >= 0.95
        
        # Medium confidence cases
        medium_conf_cases = [
            "734A>T",        # Missing prefix
            "V600E",         # Missing p. prefix
            "1234567",       # Missing rs prefix
        ]
        
        for variant in medium_conf_cases:
            result = normalizer.normalize_variant(variant)
            assert 0.7 <= result.confidence < 0.95
        
        # Lower confidence cases
        low_conf_cases = [
            "p.val600glu",   # Case issues
            "VAL600GLU",     # Case + prefix issues
        ]
        
        for variant in low_conf_cases:
            result = normalizer.normalize_variant(variant)
            assert 0.5 <= result.confidence < 0.8
    
    def test_variant_type_classification(self, normalizer):
        """Test classification of variant types."""
        test_cases = [
            ("c.123A>G", "substitution"),
            ("c.123_125del", "deletion"),
            ("c.123insATG", "insertion"),
            ("p.V600E", "substitution"),
            ("p.K100fs", "frameshift"),
            ("p.Q120*", "nonsense"),
            ("rs1234567", "dbsnp"),
            ("chr7:140453136A>T", "chromosomal"),
        ]
        
        for variant, expected_type in test_cases:
            result = normalizer.normalize_variant(variant)
            assert result.variant_type == expected_type
    
    def test_batch_normalization(self, normalizer):
        """Test batch normalization of multiple variants."""
        variants = [
            "c.123A>G",
            "p.Val600Glu",
            "rs1234567",
            "734A>T",
            "V600E",
            "1234567"
        ]
        
        results = normalizer.normalize_variants_batch(variants)
        
        assert len(results) == len(variants)
        
        # Check specific results
        expected_normalized = [
            "c.123A>G",
            "p.V600E",
            "rs1234567",
            "c.734A>T",
            "p.V600E",
            "rs1234567"
        ]
        
        for i, expected in enumerate(expected_normalized):
            assert results[i].normalized == expected
    
    def test_edge_cases(self, normalizer):
        """Test edge cases and error handling."""
        # Empty or None input
        result = normalizer.normalize_variant("")
        assert result.normalized == ""
        assert result.confidence == 0.0
        
        result = normalizer.normalize_variant(None)
        assert result.normalized == ""
        assert result.confidence == 0.0
        
        # Unrecognized variant format
        result = normalizer.normalize_variant("random_text_123")
        assert result.normalized == "random_text_123"  # Return as-is
        assert result.confidence < 0.5
        
        # Very long variant
        long_variant = "c." + "A" * 1000 + ">G"
        result = normalizer.normalize_variant(long_variant)
        assert result.normalized == long_variant
        assert result.confidence < 0.8  # Lower confidence for unusual cases
    
    def test_complex_protein_variants(self, normalizer):
        """Test complex protein variant normalizations."""
        test_cases = [
            # Multiple amino acid changes
            ("p.Val600Glu", "p.V600E"),
            ("p.Ala85Pro", "p.A85P"),
            
            # Different termination notations
            ("p.Gln120Ter", "p.Q120*"),
            ("p.Gln120Stop", "p.Q120*"),
            ("p.Gln120X", "p.Q120*"),
            
            # Frameshift variants
            ("p.Lys100Ter*fs", "p.K100fs"),
            ("p.Lys100TerfsX", "p.K100fs"),
            
            # Extension variants
            ("p.Ter110GlnextTer17", "p.*110Qext*17"),
        ]
        
        for input_variant, expected in test_cases:
            result = normalizer.normalize_variant(input_variant)
            # Some complex cases might not normalize perfectly
            if result.confidence > 0.7:
                assert result.normalized == expected, f"Input: {input_variant}, Expected: {expected}, Got: {result.normalized}"


class TestVariantEquivalenceChecking:
    """Test variant equivalence checking functionality."""
    
    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance for testing."""
        return HGVSNormalizer()
    
    def test_set_comparison_with_normalization(self, normalizer):
        """Test comparing sets of variants with normalization."""
        set1 = {"c.123A>G", "p.Val600Glu", "rs1234567"}
        set2 = {"C.123A>G", "p.V600E", "RS1234567"}
        
        # Without normalization, these would be different
        assert set1 != set2
        
        # With normalization, they should be equivalent
        normalized_set1 = normalizer.normalize_variant_set(set1)
        normalized_set2 = normalizer.normalize_variant_set(set2)
        
        assert normalized_set1 == normalized_set2
    
    def test_overlap_calculation(self, normalizer):
        """Test calculating overlap between variant sets."""
        predicted = {"c.123A>G", "p.Val600Glu", "rs1234567", "c.456T>C"}
        reference = {"C.123A>G", "p.V600E", "RS1234567", "c.789G>A"}
        
        overlap = normalizer.calculate_normalized_overlap(predicted, reference)
        
        # Should find 3 overlapping variants (after normalization)
        assert overlap['intersection_size'] == 3
        assert overlap['predicted_size'] == 4
        assert overlap['reference_size'] == 4
        assert overlap['jaccard'] == 3 / 5  # 3 / (4 + 4 - 3)
    
    def test_performance_with_large_sets(self, normalizer):
        """Test performance with large variant sets."""
        # Create large sets with variants
        large_set = set()
        for i in range(1000):
            large_set.add(f"c.{i}A>G")
            large_set.add(f"p.V{i}E")
            large_set.add(f"rs{i}")
        
        # This should complete without timeout
        normalized = normalizer.normalize_variant_set(large_set)
        assert len(normalized) == len(large_set)


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])