"""
HGVS Variant Normalizer

This module provides standardized normalization of genomic variants
to improve comparison accuracy between different data sources.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class VariantType(Enum):
    """Types of genomic variants."""
    DNA_SUBSTITUTION = "dna_substitution"
    DNA_DELETION = "dna_deletion"
    DNA_INSERTION = "dna_insertion"
    DNA_DELINS = "dna_delins"
    PROTEIN_SUBSTITUTION = "protein_substitution"
    PROTEIN_DELETION = "protein_deletion"
    PROTEIN_INSERTION = "protein_insertion"
    DBSNP = "dbsnp"
    CHROMOSOMAL = "chromosomal"
    UNKNOWN = "unknown"


@dataclass
class NormalizedVariant:
    """Normalized variant representation."""
    original: str
    normalized: str
    variant_type: VariantType
    confidence: float
    components: Dict[str, str]  # e.g., {'type': 'c', 'position': '123', 'ref': 'A', 'alt': 'G'}


class HGVSNormalizer:
    """
    HGVS variant normalizer with comprehensive pattern matching.
    
    Handles normalization of:
    - DNA variants (c., g., m., n.)
    - Protein variants (p.)
    - dbSNP identifiers
    - Chromosomal positions
    - Legacy notation conversion
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Amino acid code mappings
        self.aa_3to1 = {
            'ala': 'A', 'arg': 'R', 'asn': 'N', 'asp': 'D', 'cys': 'C',
            'gln': 'Q', 'glu': 'E', 'gly': 'G', 'his': 'H', 'ile': 'I',
            'leu': 'L', 'lys': 'K', 'met': 'M', 'phe': 'F', 'pro': 'P',
            'ser': 'S', 'thr': 'T', 'trp': 'W', 'tyr': 'Y', 'val': 'V',
            'ter': '*', 'stop': '*'
        }
        
        self.aa_1to3 = {v: k.capitalize() for k, v in self.aa_3to1.items()}
        self.aa_1to3['*'] = 'Ter'
        
        # Common variant patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for variant recognition."""
        
        # DNA substitution patterns
        self.dna_sub_patterns = [
            r'([cgmn])\.\*?(\d+)([ATCG])>([ATCG])',  # c.123A>G, c.*123A>G
            r'([cgmn])\.(\d+)([atcg])>([atcg])',     # c.123a>g (lowercase)
            r'(\d+)([ATCG])>([ATCG])',               # 123A>G (missing prefix)
        ]
        
        # DNA deletion patterns  
        self.dna_del_patterns = [
            r'([cgmn])\.(\d+)(_(\d+))?del([ATCG]*)',  # c.123del, c.123_125delATC
            r'([cgmn])\.(\d+)(_(\d+))?del',           # c.123del, c.123_125del
        ]
        
        # DNA insertion patterns
        self.dna_ins_patterns = [
            r'([cgmn])\.(\d+)(_(\d+))?ins([ATCG]+)',  # c.123insA, c.123_124insATC
        ]
        
        # Protein substitution patterns
        self.protein_sub_patterns = [
            r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})',  # p.Val600Glu
            r'p\.([A-Z])(\d+)([A-Z])',                  # p.V600E
            r'p\.([A-Z][a-z]{2})(\d+)\*',               # p.Gln120*
            r'p\.([A-Z])(\d+)\*',                       # p.Q120*
            r'([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})',    # Val600Glu (missing p.)
            r'([A-Z])(\d+)([A-Z])',                     # V600E (missing p.)
        ]
        
        # Special protein patterns
        self.protein_special_patterns = [
            r'p\.Ter(\d+)([A-Z][a-z]{2})',              # p.Ter494Glu
            r'p\.([A-Z][a-z]{2})(\d+)fs',               # p.Lys100fs
            r'p\.([A-Z])(\d+)fs',                       # p.K100fs
        ]
        
        # dbSNP pattern
        self.dbsnp_pattern = r'(rs)(\d+)'
        
        # Chromosomal position pattern
        self.chr_pattern = r'(chr)?([0-9XY]+):(\d+)([ATCG])>([ATCG])'
        
        # Compile all patterns
        self.compiled_patterns = {
            'dna_sub': [re.compile(p, re.IGNORECASE) for p in self.dna_sub_patterns],
            'dna_del': [re.compile(p, re.IGNORECASE) for p in self.dna_del_patterns],
            'dna_ins': [re.compile(p, re.IGNORECASE) for p in self.dna_ins_patterns],
            'protein_sub': [re.compile(p, re.IGNORECASE) for p in self.protein_sub_patterns],
            'protein_special': [re.compile(p, re.IGNORECASE) for p in self.protein_special_patterns],
            'dbsnp': re.compile(self.dbsnp_pattern, re.IGNORECASE),
            'chr': re.compile(self.chr_pattern, re.IGNORECASE)
        }
    
    def normalize_amino_acid(self, aa: str) -> str:
        """Convert amino acid to standard 1-letter code."""
        aa_lower = aa.lower()
        if aa_lower in self.aa_3to1:
            return self.aa_3to1[aa_lower]
        elif aa.upper() in self.aa_1to3:
            return aa.upper()
        else:
            return aa  # Return as-is if not recognized
    
    def normalize_dna_variant(self, variant: str) -> Optional[NormalizedVariant]:
        """Normalize DNA variants to standard HGVS format."""
        
        # Try DNA substitution patterns
        for pattern in self.compiled_patterns['dna_sub']:
            match = pattern.match(variant)
            if match:
                groups = match.groups()
                
                if len(groups) == 4:
                    prefix, pos, ref, alt = groups
                    normalized = f"{prefix.lower()}.{pos}{ref.upper()}>{alt.upper()}"
                elif len(groups) == 3:
                    pos, ref, alt = groups
                    normalized = f"c.{pos}{ref.upper()}>{alt.upper()}"  # Default to c.
                
                return NormalizedVariant(
                    original=variant,
                    normalized=normalized,
                    variant_type=VariantType.DNA_SUBSTITUTION,
                    confidence=0.95,
                    components={
                        'type': prefix.lower() if len(groups) == 4 else 'c',
                        'position': pos,
                        'ref': ref.upper(),
                        'alt': alt.upper()
                    }
                )
        
        # Try DNA deletion patterns
        for pattern in self.compiled_patterns['dna_del']:
            match = pattern.match(variant)
            if match:
                groups = match.groups()
                prefix, start_pos, _, end_pos, deleted_seq = groups
                
                if end_pos:
                    if deleted_seq:
                        normalized = f"{prefix.lower()}.{start_pos}_{end_pos}del{deleted_seq.upper()}"
                    else:
                        normalized = f"{prefix.lower()}.{start_pos}_{end_pos}del"
                else:
                    if deleted_seq:
                        normalized = f"{prefix.lower()}.{start_pos}del{deleted_seq.upper()}"
                    else:
                        normalized = f"{prefix.lower()}.{start_pos}del"
                
                return NormalizedVariant(
                    original=variant,
                    normalized=normalized,
                    variant_type=VariantType.DNA_DELETION,
                    confidence=0.9,
                    components={
                        'type': prefix.lower(),
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'deleted_seq': deleted_seq.upper() if deleted_seq else ''
                    }
                )
        
        # Try DNA insertion patterns
        for pattern in self.compiled_patterns['dna_ins']:
            match = pattern.match(variant)
            if match:
                groups = match.groups()
                prefix, start_pos, _, end_pos, inserted_seq = groups
                
                if end_pos:
                    normalized = f"{prefix.lower()}.{start_pos}_{end_pos}ins{inserted_seq.upper()}"
                else:
                    normalized = f"{prefix.lower()}.{start_pos}ins{inserted_seq.upper()}"
                
                return NormalizedVariant(
                    original=variant,
                    normalized=normalized,
                    variant_type=VariantType.DNA_INSERTION,
                    confidence=0.9,
                    components={
                        'type': prefix.lower(),
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'inserted_seq': inserted_seq.upper()
                    }
                )
        
        return None
    
    def normalize_protein_variant(self, variant: str) -> Optional[NormalizedVariant]:
        """Normalize protein variants to standard HGVS format."""
        
        # Try protein substitution patterns
        for pattern in self.compiled_patterns['protein_sub']:
            match = pattern.match(variant)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    aa1, pos, aa2 = groups
                    
                    # Normalize amino acids
                    norm_aa1 = self.normalize_amino_acid(aa1)
                    norm_aa2 = self.normalize_amino_acid(aa2)
                    
                    # Always use p. prefix
                    normalized = f"p.{norm_aa1}{pos}{norm_aa2}"
                    
                    return NormalizedVariant(
                        original=variant,
                        normalized=normalized,
                        variant_type=VariantType.PROTEIN_SUBSTITUTION,
                        confidence=0.95,
                        components={
                            'type': 'p',
                            'position': pos,
                            'ref_aa': norm_aa1,
                            'alt_aa': norm_aa2
                        }
                    )
        
        # Try special protein patterns
        for pattern in self.compiled_patterns['protein_special']:
            match = pattern.match(variant)
            if match:
                groups = match.groups()
                
                if 'ter' in variant.lower():
                    # Ter variant: p.Ter494Glu
                    pos, aa = groups
                    norm_aa = self.normalize_amino_acid(aa)
                    normalized = f"p.Ter{pos}{norm_aa}"
                    
                    return NormalizedVariant(
                        original=variant,
                        normalized=normalized,
                        variant_type=VariantType.PROTEIN_SUBSTITUTION,
                        confidence=0.9,
                        components={
                            'type': 'p',
                            'position': pos,
                            'ref_aa': '*',
                            'alt_aa': norm_aa
                        }
                    )
                elif 'fs' in variant.lower():
                    # Frameshift: p.Lys100fs
                    aa, pos = groups
                    norm_aa = self.normalize_amino_acid(aa)
                    normalized = f"p.{norm_aa}{pos}fs"
                    
                    return NormalizedVariant(
                        original=variant,
                        normalized=normalized,
                        variant_type=VariantType.PROTEIN_SUBSTITUTION,
                        confidence=0.9,
                        components={
                            'type': 'p',
                            'position': pos,
                            'ref_aa': norm_aa,
                            'alt_aa': 'fs'
                        }
                    )
        
        return None
    
    def normalize_dbsnp(self, variant: str) -> Optional[NormalizedVariant]:
        """Normalize dbSNP identifiers."""
        match = self.compiled_patterns['dbsnp'].match(variant)
        if match:
            prefix, number = match.groups()
            normalized = f"rs{number}"
            
            return NormalizedVariant(
                original=variant,
                normalized=normalized,
                variant_type=VariantType.DBSNP,
                confidence=1.0,
                components={
                    'type': 'dbsnp',
                    'id': number
                }
            )
        
        return None
    
    def normalize_chromosomal(self, variant: str) -> Optional[NormalizedVariant]:
        """Normalize chromosomal position variants."""
        match = self.compiled_patterns['chr'].match(variant)
        if match:
            chr_prefix, chromosome, position, ref, alt = match.groups()
            normalized = f"chr{chromosome}:{position}{ref.upper()}>{alt.upper()}"
            
            return NormalizedVariant(
                original=variant,
                normalized=normalized,
                variant_type=VariantType.CHROMOSOMAL,
                confidence=0.9,
                components={
                    'type': 'chromosomal',
                    'chromosome': chromosome,
                    'position': position,
                    'ref': ref.upper(),
                    'alt': alt.upper()
                }
            )
        
        return None
    
    def normalize_variant(self, variant: str) -> NormalizedVariant:
        """
        Normalize any variant to standard format.
        
        Args:
            variant: Raw variant string
            
        Returns:
            NormalizedVariant object with standardized representation
        """
        if not variant or not variant.strip():
            return NormalizedVariant(
                original=variant,
                normalized="",
                variant_type=VariantType.UNKNOWN,
                confidence=0.0,
                components={}
            )
        
        variant = variant.strip()
        
        # Try different normalization methods in order of specificity
        normalizers = [
            self.normalize_dbsnp,
            self.normalize_dna_variant,
            self.normalize_protein_variant,
            self.normalize_chromosomal,
        ]
        
        for normalizer in normalizers:
            result = normalizer(variant)
            if result:
                self.logger.debug(f"Normalized '{variant}' -> '{result.normalized}' using {normalizer.__name__}")
                return result
        
        # If no pattern matched, return as-is with low confidence
        self.logger.debug(f"Could not normalize variant: {variant}")
        return NormalizedVariant(
            original=variant,
            normalized=variant.lower(),  # At least make it lowercase
            variant_type=VariantType.UNKNOWN,
            confidence=0.1,
            components={'type': 'unknown'}
        )
    
    def normalize_variant_list(self, variants: List[str]) -> List[NormalizedVariant]:
        """Normalize a list of variants."""
        return [self.normalize_variant(v) for v in variants]
    
    def variants_are_equivalent(self, variant1: str, variant2: str, 
                              confidence_threshold: float = 0.7) -> bool:
        """
        Check if two variants are equivalent after normalization.
        
        Args:
            variant1: First variant
            variant2: Second variant
            confidence_threshold: Minimum confidence for comparison
            
        Returns:
            True if variants are equivalent
        """
        norm1 = self.normalize_variant(variant1)
        norm2 = self.normalize_variant(variant2)
        
        # Only compare if both have sufficient confidence
        if norm1.confidence >= confidence_threshold and norm2.confidence >= confidence_threshold:
            return norm1.normalized == norm2.normalized
        
        # Fallback to case-insensitive string comparison
        return variant1.lower().strip() == variant2.lower().strip()
    
    def get_variant_equivalence_groups(self, variants: List[str]) -> List[List[str]]:
        """
        Group equivalent variants together.
        
        Args:
            variants: List of variant strings
            
        Returns:
            List of groups, where each group contains equivalent variants
        """
        groups = []
        processed = set()
        
        for variant in variants:
            if variant in processed:
                continue
                
            # Find all equivalent variants
            equivalent_group = [variant]
            processed.add(variant)
            
            for other_variant in variants:
                if other_variant not in processed:
                    if self.variants_are_equivalent(variant, other_variant):
                        equivalent_group.append(other_variant)
                        processed.add(other_variant)
            
            if len(equivalent_group) > 1:
                self.logger.info(f"Found equivalent variants: {equivalent_group}")
            
            groups.append(equivalent_group)
        
        return groups


def normalize_variants_for_comparison(predicted_variants: List[str], 
                                    reference_variants: List[str]) -> Tuple[List[str], List[str]]:
    """
    Utility function to normalize variant lists for metric comparison.
    
    Args:
        predicted_variants: List of predicted variant strings
        reference_variants: List of reference variant strings
        
    Returns:
        Tuple of (normalized_predicted, normalized_reference)
    """
    normalizer = HGVSNormalizer()
    
    normalized_predicted = []
    normalized_reference = []
    
    for variant in predicted_variants:
        norm = normalizer.normalize_variant(variant)
        normalized_predicted.append(norm.normalized)
    
    for variant in reference_variants:
        norm = normalizer.normalize_variant(variant)
        normalized_reference.append(norm.normalized)
    
    return normalized_predicted, normalized_reference


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_variants = [
        "c.123A>G",
        "c.123a>g",
        "123A>G",
        "p.Val600Glu",
        "p.V600E",
        "Val600Glu",
        "V600E",
        "rs1234567",
        "chr7:140453136A>T",
        "c.*734A>T",
        "734A>T",
        "p.Ter494Glu",
        "Ala85Pro",
        "p.I126S",
        "I126S",
        "c.123_125del",
        "c.123insA"
    ]
    
    normalizer = HGVSNormalizer()
    
    print("=== HGVS Normalization Test ===")
    for variant in test_variants:
        result = normalizer.normalize_variant(variant)
        print(f"{variant:15} -> {result.normalized:20} (conf: {result.confidence:.2f}, type: {result.variant_type.value})")
    
    # Test equivalence
    print("\n=== Equivalence Test ===")
    equiv_pairs = [
        ("c.123A>G", "c.123a>g"),
        ("p.Val600Glu", "p.V600E"),
        ("Val600Glu", "V600E"),
        ("734A>T", "c.*734A>T"),
        ("Ala85Pro", "p.A85P")
    ]
    
    for v1, v2 in equiv_pairs:
        is_equiv = normalizer.variants_are_equivalent(v1, v2)
        print(f"{v1} == {v2}: {is_equiv}")