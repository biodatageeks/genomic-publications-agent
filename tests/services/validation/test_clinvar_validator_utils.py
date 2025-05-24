"""
Testy dla funkcji narzędziowych modułu clinvar_relationship_validator.

Ten moduł zawiera testy jednostkowe dla funkcji pomocniczych
używanych przez walidator relacji.
"""

import pytest
from src.services.validation.utils import (
    normalize_gene_symbol,
    normalize_disease_name,
    normalize_variant_notation,
    calculate_text_similarity,
    is_text_similar,
    extract_variant_type
)


class TestNormalizeGeneSymbol:
    """Testy dla funkcji normalize_gene_symbol."""
    
    @pytest.mark.parametrize("input_symbol, expected", [
        ("TP53", "TP53"),
        ("tp53", "TP53"),
        (" BRCA1 ", "BRCA1"),
        ("GEN TP53", "TP53"),
        ("PROTEIN BRCA1", "BRCA1"),
        ("BIAŁKO TP53", "TP53"),
        ("", ""),
        (None, "")
    ])
    def test_normalize_gene_symbol(self, input_symbol, expected):
        """Test normalizacji symboli genów."""
        result = normalize_gene_symbol(input_symbol)
        assert result == expected


class TestNormalizeDiseaseName:
    """Testy dla funkcji normalize_disease_name."""
    
    @pytest.mark.parametrize("input_name, expected", [
        ("Breast Cancer", "breast cancer"),
        ("BREAST CANCER", "breast cancer"),
        ("Breast Cancer Disease", "breast cancer"),
        ("Lynch Syndrome", "lynch"),
        ("  Multiple   Spaces  ", "multiple spaces"),
        ("", ""),
        (None, "")
    ])
    def test_normalize_disease_name(self, input_name, expected):
        """Test normalizacji nazw chorób."""
        result = normalize_disease_name(input_name)
        assert result == expected


class TestNormalizeVariantNotation:
    """Testy dla funkcji normalize_variant_notation."""
    
    @pytest.mark.parametrize("input_variant, expected", [
        ("c.123A>G", "c.123a>g"),
        ("c. 123A>G", "c.123a>g"),
        ("p.Arg123Cys", "p.Arg123Cys"),
        ("p.arg123cys", "p.Arg123cys"),
        ("p. arg123cys", "p.Arg123cys"),
        ("NM_000546.5:c.215C>G", "NM_000546.5:c.215c>g"),
        ("TP53 p.Pro72Arg", "TP53 p.Pro72Arg"),
        ("", ""),
        (None, "")
    ])
    def test_normalize_variant_notation(self, input_variant, expected):
        """Test normalizacji notacji wariantów."""
        result = normalize_variant_notation(input_variant)
        assert result == expected


class TestCalculateTextSimilarity:
    """Testy dla funkcji calculate_text_similarity."""
    
    @pytest.mark.parametrize("text1, text2, expected_min", [
        ("Breast Cancer", "Breast Cancer", 1.0),
        ("Breast Cancer", "BREAST CANCER", 1.0),
        ("Breast Cancer", "Breast Cancers", 0.9),
        ("Breast Cancer", "Colorectal Cancer", 0.3),
        ("TP53", "tp53", 1.0),
        ("TP53", "TP63", 0.5),
        ("", "Cancer", 0.0),
        (None, "Cancer", 0.0),
        ("Cancer", None, 0.0),
        (None, None, 0.0)
    ])
    def test_calculate_text_similarity(self, text1, text2, expected_min):
        """Test obliczania podobieństwa tekstów."""
        similarity = calculate_text_similarity(text1, text2)
        assert similarity >= expected_min


class TestIsTextSimilar:
    """Testy dla funkcji is_text_similar."""
    
    @pytest.mark.parametrize("text1, text2, threshold, expected", [
        ("Breast Cancer", "Breast Cancer", 0.7, True),
        ("Breast Cancer", "Cancer of the Breast", 0.7, True),  # zawieranie się
        ("Breast Cancer", "Ovarian Cancer", 0.7, False),
        ("TP53", "TP53 Gene", 0.7, True),  # zawieranie się
        ("TP53 Gene", "TP53", 0.7, True),  # zawieranie się
        ("TP53", "TP63", 0.7, False),
        ("Cancer", "Cancar", 0.7, True),  # literówka, ale podobne
        ("", "Cancer", 0.7, False),
        (None, "Cancer", 0.7, False),
        ("Cancer", None, 0.7, False),
        (None, None, 0.7, False)
    ])
    def test_is_text_similar(self, text1, text2, threshold, expected):
        """Test sprawdzania podobieństwa tekstów."""
        result = is_text_similar(text1, text2, threshold)
        assert result == expected


class TestExtractVariantType:
    """Testy dla funkcji extract_variant_type."""
    
    @pytest.mark.parametrize("variant_notation, expected", [
        ("c.123A>G", "SNV"),
        ("c.123_124delAG", "Deletion"),
        ("c.123_124del", "Deletion"),
        ("c.123_124insAGT", "Insertion"),
        ("c.123_124dupAG", "Duplication"),
        ("c.123_124delAGinsTC", "Indel"),
        ("c.123_126inv", "Inversion"),
        ("p.Arg123Cys", "Substitution"),
        ("rs1042522", "SNP"),
        ("unknown variant", "Unknown"),
        ("", "Unknown"),
        (None, "Unknown")
    ])
    def test_extract_variant_type(self, variant_notation, expected):
        """Test wykrywania typu wariantu."""
        result = extract_variant_type(variant_notation)
        assert result == expected 