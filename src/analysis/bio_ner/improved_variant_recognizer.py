"""
Improved Variant Recognizer without mock data contamination.

This module provides a clean implementation of variant recognition
without generating fake variants.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class VariantMatch:
    """Represents a variant match with confidence and context."""
    variant: str
    confidence: float
    pattern_type: str
    context_before: str
    context_after: str
    start_pos: int
    end_pos: int


class ImprovedVariantRecognizer:
    """
    Improved variant recognizer with better pattern matching and validation.
    
    Key improvements:
    1. No mock data generation
    2. Context-aware pattern matching  
    3. False positive filtering
    4. Confidence scoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Valid variant patterns with confidence scores
        self.variant_patterns = {
            # HGVS DNA notation
            'hgvs_dna': {
                'pattern': r'\bc\.[0-9]+[ATCG]>[ATCG]\b',
                'confidence': 0.9,
                'examples': ['c.123A>G', 'c.456T>C']
            },
            'hgvs_dna_del': {
                'pattern': r'\bc\.[0-9]+(_[0-9]+)?del[ATCG]*\b',
                'confidence': 0.9,
                'examples': ['c.123del', 'c.123_125delATC']
            },
            'hgvs_dna_ins': {
                'pattern': r'\bc\.[0-9]+(_[0-9]+)?ins[ATCG]+\b',
                'confidence': 0.9,
                'examples': ['c.123insA', 'c.123_124insATC']
            },
            'hgvs_dna_utr': {
                'pattern': r'\bc\.\*[0-9]+[ATCG]>[ATCG]\b',
                'confidence': 0.8,
                'examples': ['c.*734A>T']
            },
            
            # HGVS protein notation
            'hgvs_protein_3letter': {
                'pattern': r'\bp\.[A-Z][a-z]{2}[0-9]+[A-Z][a-z]{2}\b',
                'confidence': 0.9,
                'examples': ['p.Val600Glu', 'p.Ala85Pro']
            },
            'hgvs_protein_1letter': {
                'pattern': r'\bp\.[A-Z][0-9]+[A-Z]\b',
                'confidence': 0.9,
                'examples': ['p.V600E', 'p.A85P']
            },
            'hgvs_protein_prefix': {
                'pattern': r'\bp\.[A-Z][0-9]+\*\b',
                'confidence': 0.8,
                'examples': ['p.Q120*']
            },
            'hgvs_protein_ter': {
                'pattern': r'\bp\.Ter[0-9]+[A-Z][a-z]{2}\b',
                'confidence': 0.8,
                'examples': ['p.Ter494Glu']
            },
            'hgvs_protein_fs': {
                'pattern': r'\bp\.[A-Z][0-9]+fs\b',
                'confidence': 0.8,
                'examples': ['p.K100fs']
            },
            
            # dbSNP identifiers
            'dbsnp': {
                'pattern': r'\brs[0-9]+\b',
                'confidence': 0.95,
                'examples': ['rs1234567', 'rs13447455']
            },
            
            # Chromosomal positions
            'chr_position': {
                'pattern': r'\bchr[0-9XY]+:[0-9]+[ATCG]>[ATCG]\b',
                'confidence': 0.8,
                'examples': ['chr7:140453136A>T']
            },
            
            # Simple amino acid changes (only in genetic context)
            'simple_aa_change': {
                'pattern': r'\b[A-Z][0-9]+[A-Z]\b',
                'confidence': 0.6,  # Lower confidence, needs context validation
                'examples': ['V600E', 'A85P']
            }
        }
        
        # Blacklist patterns that are NOT variants
        self.blacklist_patterns = [
            r'\b[A-Z][0-9]*[A-Z]?\b',  # Generic lab codes like H3K, U5F
            r'\b[A-Za-z][0-9]+[a-z]\b',  # Mixed case lab codes
            r'\b[0-9]+[A-Za-z]\b',  # Number-letter combos
            r'\b[A-Z]{1,3}[0-9]{1,2}[A-Z]?\b'  # Short lab codes
        ]
        
        # Context keywords that suggest genetic/variant content
        self.positive_context_keywords = [
            'mutation', 'variant', 'polymorphism', 'substitution', 'deletion', 'insertion',
            'missense', 'nonsense', 'frameshift', 'splice', 'pathogenic', 'benign',
            'hgvs', 'coding', 'exon', 'intron', 'genomic', 'genetic', 'allele',
            'genotype', 'phenotype', 'snp', 'indel', 'cnv'
        ]
        
        # Context keywords that suggest NON-variant content
        self.negative_context_keywords = [
            'protocol', 'buffer', 'reagent', 'plate', 'well', 'tube', 'sample',
            'antibody', 'primer', 'probe', 'kit', 'enzyme', 'medium', 'culture',
            'histone', 'lysine', 'acetyl', 'methyl', 'phospho', 'ubiquitin'
        ]
    
    def get_context(self, text: str, start: int, end: int, window: int = 50) -> Tuple[str, str]:
        """Extract context around a match."""
        context_before = text[max(0, start - window):start].strip()
        context_after = text[end:min(len(text), end + window)].strip()
        return context_before, context_after
    
    def calculate_confidence(self, variant: str, pattern_type: str, 
                           context_before: str, context_after: str) -> float:
        """Calculate confidence score for a variant match."""
        base_confidence = self.variant_patterns[pattern_type]['confidence']
        
        # Context analysis
        context_text = (context_before + " " + context_after).lower()
        
        # Boost for positive genetic context
        positive_boost = 0.0
        for keyword in self.positive_context_keywords:
            if keyword in context_text:
                positive_boost += 0.1
        
        # Penalty for negative context
        negative_penalty = 0.0
        for keyword in self.negative_context_keywords:
            if keyword in context_text:
                negative_penalty += 0.2
        
        # Specific penalties for obvious false positives
        if pattern_type == 'simple_aa_change':
            # Extra validation for simple AA changes
            if re.match(r'^[A-Z][0-9]*[KMH]$', variant):  # Common histone marks
                negative_penalty += 0.5
            if len(variant) <= 3 and not any(kw in context_text for kw in self.positive_context_keywords):
                negative_penalty += 0.3
        
        final_confidence = base_confidence + positive_boost - negative_penalty
        return max(0.0, min(1.0, final_confidence))
    
    def is_blacklisted(self, variant: str, context: str) -> bool:
        """Check if variant matches blacklist patterns."""
        context_lower = context.lower()
        
        # Known false positive patterns
        false_positives = [
            'h3k', 'h2a', 'h2b', 'h4k',  # Histone modifications
            'u5f', 'r5b', 'e3k', 'c5a',  # Lab codes
            'f4a', 'h1b', 'n9d', 'b1a',  # More lab codes
            's22l', 'f1a', 'f2d', 'h2f',  # Lab codes
            'o1a', 'o3a', 'd4l', 'g1b',  # Lab codes
            'a1l', 'a3c', 'l1c', 'p1b',  # Lab codes
            'e2f', 'k1n', 'f2c', 'g2m',  # Lab codes
            'p3r', 'q11d', 'c4a', 'n2b',  # Lab codes
            'l10a', 'r494g'  # More lab codes
        ]
        
        if variant.lower() in false_positives:
            return True
        
        # Check for experimental/protocol context
        experimental_keywords = [
            'protocol', 'buffer', 'reagent', 'kit', 'medium',
            'antibody', 'primer', 'probe', 'plate', 'well'
        ]
        
        if any(keyword in context_lower for keyword in experimental_keywords):
            return True
        
        return False
    
    def recognize_variants_text(self, text: str, min_confidence: float = 0.7) -> List[str]:
        """
        Recognize genomic variants in text using improved pattern matching.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold for accepting variants
            
        Returns:
            List of recognized variants with confidence above threshold
        """
        if not text or not text.strip():
            return []
        
        all_matches = []
        
        # Apply all patterns
        for pattern_name, pattern_info in self.variant_patterns.items():
            pattern = pattern_info['pattern']
            
            for match in re.finditer(pattern, text, re.IGNORECASE):
                variant = match.group().strip()
                start_pos = match.start()
                end_pos = match.end()
                
                # Get context
                context_before, context_after = self.get_context(text, start_pos, end_pos)
                full_context = context_before + " " + context_after
                
                # Skip blacklisted variants
                if self.is_blacklisted(variant, full_context):
                    self.logger.debug(f"Blacklisted variant: {variant}")
                    continue
                
                # Calculate confidence
                confidence = self.calculate_confidence(
                    variant, pattern_name, context_before, context_after
                )
                
                if confidence >= min_confidence:
                    all_matches.append(VariantMatch(
                        variant=variant,
                        confidence=confidence,
                        pattern_type=pattern_name,
                        context_before=context_before,
                        context_after=context_after,
                        start_pos=start_pos,
                        end_pos=end_pos
                    ))
        
        # Remove duplicates and sort by confidence
        unique_variants = {}
        for match in all_matches:
            variant_key = match.variant.lower()
            if variant_key not in unique_variants or match.confidence > unique_variants[variant_key].confidence:
                unique_variants[variant_key] = match
        
        # Sort by confidence (descending) and return variant strings
        sorted_matches = sorted(unique_variants.values(), key=lambda x: x.confidence, reverse=True)
        
        # Log details for debugging
        self.logger.info(f"Found {len(sorted_matches)} high-confidence variants")
        for match in sorted_matches:
            self.logger.debug(f"Variant: {match.variant}, Confidence: {match.confidence:.2f}, Type: {match.pattern_type}")
        
        return [match.variant for match in sorted_matches]
    
    def recognize_variants_with_details(self, text: str, min_confidence: float = 0.7) -> List[VariantMatch]:
        """
        Recognize variants and return detailed match information.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of VariantMatch objects with detailed information
        """
        # This is similar to recognize_variants_text but returns full details
        if not text or not text.strip():
            return []
        
        all_matches = []
        
        for pattern_name, pattern_info in self.variant_patterns.items():
            pattern = pattern_info['pattern']
            
            for match in re.finditer(pattern, text, re.IGNORECASE):
                variant = match.group().strip()
                start_pos = match.start()
                end_pos = match.end()
                
                context_before, context_after = self.get_context(text, start_pos, end_pos)
                full_context = context_before + " " + context_after
                
                if self.is_blacklisted(variant, full_context):
                    continue
                
                confidence = self.calculate_confidence(
                    variant, pattern_name, context_before, context_after
                )
                
                if confidence >= min_confidence:
                    all_matches.append(VariantMatch(
                        variant=variant,
                        confidence=confidence,
                        pattern_type=pattern_name,
                        context_before=context_before,
                        context_after=context_after,
                        start_pos=start_pos,
                        end_pos=end_pos
                    ))
        
        # Remove duplicates and sort by confidence
        unique_variants = {}
        for match in all_matches:
            variant_key = match.variant.lower()
            if variant_key not in unique_variants or match.confidence > unique_variants[variant_key].confidence:
                unique_variants[variant_key] = match
        
        return sorted(unique_variants.values(), key=lambda x: x.confidence, reverse=True)
    
    def evaluate_patterns(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate pattern performance on test cases.
        
        Args:
            test_cases: List of test cases with 'text' and 'expected_variants'
            
        Returns:
            Evaluation metrics
        """
        total_cases = len(test_cases)
        correct_predictions = 0
        total_predicted = 0
        total_expected = 0
        
        results = []
        
        for i, case in enumerate(test_cases):
            text = case.get('text', '')
            expected = set(v.lower() for v in case.get('expected_variants', []))
            
            predicted = set(v.lower() for v in self.recognize_variants_text(text))
            
            true_positives = len(predicted & expected)
            false_positives = len(predicted - expected)
            false_negatives = len(expected - predicted)
            
            precision = true_positives / len(predicted) if predicted else 0.0
            recall = true_positives / len(expected) if expected else 1.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            results.append({
                'case_id': i,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'true_positives': true_positives,
                'false_positives': false_positives,
                'false_negatives': false_negatives,
                'predicted_variants': list(predicted),
                'expected_variants': list(expected)
            })
            
            total_predicted += len(predicted)
            total_expected += len(expected)
            
            if predicted == expected:
                correct_predictions += 1
        
        # Overall metrics
        overall_precision = sum(r['true_positives'] for r in results) / total_predicted if total_predicted > 0 else 0.0
        overall_recall = sum(r['true_positives'] for r in results) / total_expected if total_expected > 0 else 0.0
        overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
        
        return {
            'overall_metrics': {
                'accuracy': correct_predictions / total_cases,
                'precision': overall_precision,
                'recall': overall_recall,
                'f1_score': overall_f1,
                'total_cases': total_cases,
                'correct_predictions': correct_predictions
            },
            'detailed_results': results
        }