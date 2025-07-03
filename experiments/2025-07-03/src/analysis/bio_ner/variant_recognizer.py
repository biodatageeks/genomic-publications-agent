"""
Variant Recognizer with enhanced context validation and false positive filtering.

This module provides a robust variant recognition system that:
- Filters out mock data contamination
- Validates biological context around matches
- Implements confidence scoring
- Blacklists known false positives (lab codes, histone modifications)
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class VariantMatch:
    """Represents a variant match with metadata."""
    variant: str
    confidence: float
    pattern_type: str
    context_before: str
    context_after: str
    start_pos: int
    end_pos: int


class VariantRecognizer:
    """
    Enhanced variant recognizer with context validation and false positive filtering.
    
    This replaces the problematic SimpleVariantRecognizer that was injecting mock data.
    Key improvements:
    - No mock data injection
    - Context-aware confidence scoring
    - Comprehensive false positive blacklist
    - Multiple variant format support
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Compile variant patterns with confidence scores
        self.variant_patterns = self._compile_variant_patterns()
        
        # Known false positive patterns (lab codes, histone modifications, etc.)
        self.false_positive_blacklist = {
            # Histone modifications
            'h3k4', 'h3k4me3', 'h3k27', 'h3k27me3', 'h3k9', 'h3k9me3',
            'h2a', 'h2b', 'h4k', 'h4k20', 'h3k36', 'h3k79',
            
            # Common lab codes
            'u5f', 'r5b', 'e3k', 'c5a', 'f4a', 'h1b', 'n9d', 'b1a',
            's22l', 'f1a', 'f2d', 'h2f', 'o1a', 'o3a', 'd4l', 'g1b',
            'a1l', 'a3c', 'l1c', 'p1b', 'e2f', 'k1n', 'f2c', 'g2m',
            'p3r', 'q11d', 'c4a', 'n2b', 'l10a', 'r494g',
            
            # Buffer components and reagents
            'tris', 'edta', 'dmso', 'pbs', 'bsa', 'sds',
            
            # Cell line codes
            'hela', 'hek293', 'cos7', 'cho', 'nih3t3'
        }
        
        # Context keywords for confidence scoring
        self.positive_context_keywords = {
            'mutation', 'variant', 'polymorphism', 'substitution', 'deletion', 
            'insertion', 'frameshift', 'nonsense', 'missense', 'splice',
            'genetic', 'genomic', 'allele', 'genotype', 'phenotype',
            'pathogenic', 'benign', 'oncogenic', 'tumor', 'cancer',
            'disease', 'syndrome', 'disorder', 'defect', 'deficiency'
        }
        
        self.negative_context_keywords = {
            'buffer', 'protocol', 'experiment', 'antibody', 'reagent',
            'solution', 'medium', 'culture', 'plate', 'dish', 'tube',
            'incubation', 'washing', 'staining', 'fixation', 'lysis',
            'centrifugation', 'precipitation', 'chromatography'
        }
    
    def _compile_variant_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Compile regex patterns for different variant types with confidence scores."""
        patterns = {
            # HGVS DNA notation
            'hgvs_dna': {
                'pattern': re.compile(r'\b[cgmn]\.[\*\-]?\d+[\+\-]?\d*[ATCG]>[ATCG]\b', re.IGNORECASE),
                'confidence': 0.95
            },
            'hgvs_dna_del': {
                'pattern': re.compile(r'\b[cgmn]\.\d+(_\d+)?del[ATCG]*\b', re.IGNORECASE),
                'confidence': 0.95
            },
            'hgvs_dna_ins': {
                'pattern': re.compile(r'\b[cgmn]\.\d+(_\d+)?ins[ATCG]+\b', re.IGNORECASE),
                'confidence': 0.95
            },
            'hgvs_dna_utr': {
                'pattern': re.compile(r'\b[cgmn]\.\*[\-]?\d+[ATCG]>[ATCG]\b', re.IGNORECASE),
                'confidence': 0.90
            },
            
            # HGVS protein notation
            'hgvs_protein_3letter': {
                'pattern': re.compile(r'\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\b'),
                'confidence': 0.92
            },
            'hgvs_protein_1letter': {
                'pattern': re.compile(r'\bp\.[A-Z]\d+[A-Z]\b'),
                'confidence': 0.90
            },
            'hgvs_protein_prefix': {
                'pattern': re.compile(r'\bp\.[A-Z][a-z]{2}\d+[A-Z]\b'),
                'confidence': 0.88
            },
            'hgvs_protein_ter': {
                'pattern': re.compile(r'\bp\.[A-Z][a-z]{2}\d+(Ter|\*)\b'),
                'confidence': 0.92
            },
            'hgvs_protein_fs': {
                'pattern': re.compile(r'\bp\.[A-Z][a-z]{2}\d+fs\b'),
                'confidence': 0.92
            },
            
            # dbSNP identifiers
            'dbsnp': {
                'pattern': re.compile(r'\brs\d+\b', re.IGNORECASE),
                'confidence': 0.95
            },
            
            # Chromosomal positions
            'chr_position': {
                'pattern': re.compile(r'\bchr[0-9XYxy]+:\d+[ATCG]>[ATCG]\b', re.IGNORECASE),
                'confidence': 0.90
            },
            
            # Simple amino acid changes (only in strong genetic context)
            'simple_aa_change': {
                'pattern': re.compile(r'\b[A-Z]\d+[A-Z]\b'),
                'confidence': 0.70  # Lower confidence, needs strong context
            }
        }
        
        return patterns
    
    def get_context(self, text: str, start: int, end: int, window: int = 50) -> Tuple[str, str]:
        """Extract context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        context_before = text[context_start:start].lower()
        context_after = text[end:context_end].lower()
        
        return context_before, context_after
    
    def calculate_confidence(self, variant: str, pattern_type: str, 
                           context_before: str, context_after: str) -> float:
        """Calculate confidence score based on pattern type and context."""
        base_confidence = self.variant_patterns[pattern_type]['confidence']
        
        # Check for positive context keywords
        positive_score = 0
        for keyword in self.positive_context_keywords:
            if keyword in context_before or keyword in context_after:
                positive_score += 0.1
        
        # Check for negative context keywords  
        negative_score = 0
        for keyword in self.negative_context_keywords:
            if keyword in context_before or keyword in context_after:
                negative_score += 0.15
        
        # Adjust confidence
        adjusted_confidence = base_confidence + positive_score - negative_score
        
        # Apply special rules for simple patterns
        if pattern_type == 'simple_aa_change':
            # Require strong positive context for simple patterns
            if positive_score < 0.2:
                adjusted_confidence *= 0.5
        
        return max(0.0, min(1.0, adjusted_confidence))
    
    def is_blacklisted(self, variant: str, context: str = "") -> bool:
        """Check if variant is in the false positive blacklist."""
        variant_lower = variant.lower().strip()
        context_lower = context.lower()
        
        # Direct blacklist match
        if variant_lower in self.false_positive_blacklist:
            return True
        
        # Pattern-based blacklisting
        # Very short variants that look like lab codes
        if len(variant_lower) <= 3 and not re.match(r'^rs\d+$', variant_lower):
            return True
        
        # Histone-like patterns in experimental context
        if re.match(r'^h[0-9]+[a-z]', variant_lower) and ('histone' in context_lower or 'chromatin' in context_lower):
            return True
        
        # Lab code patterns in protocol context
        if re.match(r'^[a-z][0-9]+[a-z]?$', variant_lower) and len(variant_lower) <= 4:
            if any(keyword in context_lower for keyword in ['buffer', 'protocol', 'reagent', 'antibody']):
                return True
        
        return False
    
    def recognize_variants_text(self, text: str, min_confidence: float = 0.7) -> List[str]:
        """
        Recognize variants in text with confidence filtering.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of high-confidence variant strings
        """
        if not text:
            return []
        
        variants = []
        found_variants = set()  # To avoid duplicates
        
        for pattern_type, pattern_info in self.variant_patterns.items():
            pattern = pattern_info['pattern']
            
            for match in pattern.finditer(text):
                variant = match.group().strip()
                start, end = match.span()
                
                # Skip if already found
                if variant in found_variants:
                    continue
                
                # Get context
                context_before, context_after = self.get_context(text, start, end)
                full_context = context_before + " " + context_after
                
                # Check blacklist
                if self.is_blacklisted(variant, full_context):
                    self.logger.debug(f"Filtered blacklisted variant: {variant}")
                    continue
                
                # Calculate confidence
                confidence = self.calculate_confidence(variant, pattern_type, context_before, context_after)
                
                # Filter by confidence
                if confidence >= min_confidence:
                    variants.append(variant)
                    found_variants.add(variant)
                    self.logger.debug(f"Found variant: {variant} (confidence: {confidence:.2f})")
        
        self.logger.info(f"Found {len(variants)} high-confidence variants")
        return variants
    
    def recognize_variants_with_details(self, text: str, min_confidence: float = 0.7) -> List[VariantMatch]:
        """
        Recognize variants with detailed information.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of VariantMatch objects with detailed information
        """
        if not text:
            return []
        
        detailed_variants = []
        found_variants = set()
        
        for pattern_type, pattern_info in self.variant_patterns.items():
            pattern = pattern_info['pattern']
            
            for match in pattern.finditer(text):
                variant = match.group().strip()
                start, end = match.span()
                
                # Skip if already found
                if variant in found_variants:
                    continue
                
                # Get context
                context_before, context_after = self.get_context(text, start, end)
                full_context = context_before + " " + context_after
                
                # Check blacklist
                if self.is_blacklisted(variant, full_context):
                    continue
                
                # Calculate confidence
                confidence = self.calculate_confidence(variant, pattern_type, context_before, context_after)
                
                # Filter by confidence
                if confidence >= min_confidence:
                    variant_match = VariantMatch(
                        variant=variant,
                        confidence=confidence,
                        pattern_type=pattern_type,
                        context_before=context_before.strip(),
                        context_after=context_after.strip(),
                        start_pos=start,
                        end_pos=end
                    )
                    detailed_variants.append(variant_match)
                    found_variants.add(variant)
        
        return detailed_variants


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create recognizer
    recognizer = VariantRecognizer()
    
    # Test cases
    test_texts = [
        "The BRCA1 mutation c.185delAG causes a frameshift.",
        "We used H3K4me3 antibody in this experiment.",
        "The V600E mutation in BRAF is oncogenic.",
        "Buffer contains Tris-HCl and EDTA with pH 8.0.",
        "rs13447455 was associated with disease risk.",
        "The p.Val600Glu substitution affects protein function."
    ]
    
    print("=== Variant Recognition Test ===")
    for i, text in enumerate(test_texts):
        print(f"\nText {i+1}: {text}")
        variants = recognizer.recognize_variants_text(text)
        print(f"Variants: {variants}")
        
        # Test detailed recognition
        detailed = recognizer.recognize_variants_with_details(text)
        for detail in detailed:
            print(f"  - {detail.variant} ({detail.pattern_type}, conf: {detail.confidence:.2f})")
            print(f"    Context: ...{detail.context_before[-20:]} | {detail.context_after[:20]}...")