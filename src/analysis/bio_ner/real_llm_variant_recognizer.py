"""
Real LLM Variant Recognizer with structured prompting.

This module provides a real LLM-based variant recognition system using
advanced prompting techniques instead of simple pattern matching.
"""

import json
import logging
import re
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

# LLM integration imports
try:
    from langchain.llms import Together
    from langchain.chat_models import ChatOpenAI
    from langchain.prompts import PromptTemplate, ChatPromptTemplate
    from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
    from langchain.schema import HumanMessage, SystemMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

try:
    from pydantic import BaseModel, Field
    from typing import List as PydanticList
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class LLMProvider(Enum):
    """Supported LLM providers."""
    TOGETHER = "together"
    OPENAI = "openai"
    MOCK = "mock"


@dataclass
class VariantExtraction:
    """Structured variant extraction result."""
    variant: str
    variant_type: str  # SNP, INDEL, CNV, etc.
    confidence: float
    context: str
    reasoning: str


@dataclass
class VariantExtractionResponse:
    """Response format for variant extraction (simplified without Pydantic)."""
    variants: List[Dict[str, Any]]
    reasoning: str
    confidence: float


class RealLLMVariantRecognizer:
    """
    Real LLM-based variant recognizer with structured prompting.
    
    Features:
    - Chain-of-thought reasoning
    - Structured output parsing
    - Multiple LLM provider support
    - Advanced prompt engineering
    - False positive filtering
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.TOGETHER,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM
        self.llm = self._initialize_llm(model_name, api_key)
        
        # Note: We use simple JSON parsing instead of structured Pydantic parsing
        self.structured_parser = None
            
        # Known false positive patterns (same as improved recognizer)
        self.false_positive_patterns = {
            'h3k', 'h2a', 'h2b', 'h4k',  # Histone modifications
            'u5f', 'r5b', 'e3k', 'c5a',  # Lab codes
            'f4a', 'h1b', 'n9d', 'b1a',  # More lab codes
            's22l', 'f1a', 'f2d', 'h2f',  # Lab codes
            'o1a', 'o3a', 'd4l', 'g1b',  # Lab codes
            'a1l', 'a3c', 'l1c', 'p1b',  # Lab codes
            'e2f', 'k1n', 'f2c', 'g2m',  # Lab codes
            'p3r', 'q11d', 'c4a', 'n2b',  # Lab codes
            'l10a', 'r494g'  # More lab codes
        }
    
    def _initialize_llm(self, model_name: Optional[str], api_key: Optional[str]):
        """Initialize LLM based on provider."""
        if not HAS_LANGCHAIN:
            self.logger.warning("LangChain not available, using mock LLM")
            return MockLLM()
        
        if self.provider == LLMProvider.TOGETHER:
            model_name = model_name or "meta-llama/Llama-2-70b-chat-hf"
            return Together(
                model=model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                together_api_key=api_key
            )
        elif self.provider == LLMProvider.OPENAI:
            model_name = model_name or "gpt-3.5-turbo"
            return ChatOpenAI(
                model_name=model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                openai_api_key=api_key
            )
        else:
            return MockLLM()
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for variant extraction."""
        return """You are an expert bioinformatician specializing in genomic variant identification from scientific literature.

Your task is to extract genomic variants from biomedical text with high precision and recall.

VALID VARIANT FORMATS:
1. HGVS DNA notation: c.123A>G, c.456_789del, c.123insT
2. HGVS protein notation: p.Val600Glu, p.V600E, p.Lys100*
3. dbSNP identifiers: rs1234567
4. Chromosomal positions: chr7:140453136A>T
5. Simple amino acid changes: V600E, K100fs (only in genetic context)

IMPORTANT - DO NOT EXTRACT:
- Histone modifications (H3K4, H2A, etc.)
- Laboratory codes (U5F, R5B, E3K, etc.)
- Experimental conditions or reagent names
- Buffer components or protocol steps
- Cell line names or culture conditions

REASONING PROCESS:
1. Identify potential variant-like patterns
2. Check surrounding context for genetic/genomic keywords
3. Validate format against known variant nomenclature
4. Exclude non-variant laboratory terminology
5. Assign confidence based on context clarity

Respond with structured data including variants found, reasoning, and confidence score."""
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create extraction prompt with examples."""
        format_instructions = """
Return a JSON object with:
{
    "variants": [
        {
            "variant": "variant_string",
            "variant_type": "SNP|INDEL|CNV|other",
            "confidence": 0.0-1.0,
            "context": "surrounding_text",
            "reasoning": "why_this_is_a_variant"
        }
    ],
    "reasoning": "overall_extraction_reasoning",
    "confidence": 0.0-1.0
}
"""
        
        prompt = f"""Extract genomic variants from the following biomedical text.

TEXT TO ANALYZE:
{text}

EXAMPLE EXTRACTIONS:

Text: "The BRCA1 mutation c.185delAG leads to a frameshift."
Result: {{"variants": [{{"variant": "c.185delAG", "variant_type": "INDEL", "confidence": 0.95, "context": "BRCA1 mutation c.185delAG leads", "reasoning": "Clear HGVS deletion notation in genetic context"}}], "reasoning": "Single clear variant in cancer gene context", "confidence": 0.95}}

Text: "We used H3K4me3 antibody and buffer containing Tris-HCl."
Result: {{"variants": [], "reasoning": "H3K4me3 is histone modification, not genomic variant. No actual variants found.", "confidence": 0.9}}

Text: "The V600E mutation in BRAF is pathogenic."
Result: {{"variants": [{{"variant": "V600E", "variant_type": "SNP", "confidence": 0.9, "context": "V600E mutation in BRAF", "reasoning": "Well-known oncogenic variant in clear genetic context"}}], "reasoning": "Single amino acid substitution in known cancer gene", "confidence": 0.9}}

{format_instructions}

Remember:
- Only extract genuine genomic variants
- Exclude laboratory codes and histone marks
- Provide reasoning for each decision
- Use high confidence only for clear genetic contexts
"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> VariantExtractionResponse:
        """Parse LLM response into structured format."""
        # Use manual JSON parsing
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                # Create empty response
                data = {"variants": [], "reasoning": "Failed to parse response", "confidence": 0.0}
            
            # Convert to VariantExtractionResponse format
            variants = []
            for v in data.get("variants", []):
                if isinstance(v, dict):
                    variants.append(v)
                elif isinstance(v, str):
                    variants.append({
                        "variant": v,
                        "variant_type": "unknown",
                        "confidence": 0.5,
                        "context": "",
                        "reasoning": "Parsed from simple string"
                    })
            
            return VariantExtractionResponse(
                variants=variants,
                reasoning=data.get("reasoning", "Manual parsing"),
                confidence=data.get("confidence", 0.5)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            return VariantExtractionResponse(
                variants=[],
                reasoning=f"Parsing failed: {e}",
                confidence=0.0
            )
    
    def _filter_false_positives(self, variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out known false positives."""
        filtered = []
        
        for variant in variants:
            variant_text = variant.get("variant", "").lower()
            
            # Check against known false positives
            if variant_text in self.false_positive_patterns:
                self.logger.debug(f"Filtered false positive: {variant_text}")
                continue
            
            # Additional heuristic filtering
            if len(variant_text) <= 3 and not re.match(r'^rs\d+$', variant_text):
                # Very short variants are likely lab codes unless they're dbSNP
                self.logger.debug(f"Filtered short variant: {variant_text}")
                continue
            
            filtered.append(variant)
        
        return filtered
    
    def recognize_variants_text(self, text: str, min_confidence: float = 0.7) -> List[str]:
        """
        Recognize variants in text using real LLM.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of variant strings
        """
        if not text or not text.strip():
            return []
        
        try:
            # Create prompts
            system_prompt = self._create_system_prompt()
            extraction_prompt = self._create_extraction_prompt(text)
            
            # Get LLM response
            if hasattr(self.llm, 'invoke'):
                # LangChain v0.2+ interface
                if HAS_LANGCHAIN and hasattr(self.llm, '__class__') and 'ChatOpenAI' in str(self.llm.__class__):
                    # For ChatOpenAI, we need to handle messages differently in mock
                    full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                    response = self.llm.invoke(full_prompt)
                    response_text = getattr(response, 'content', response) if hasattr(response, 'content') else str(response)
                else:
                    # Together or other LLMs
                    full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                    response = self.llm.invoke(full_prompt)
                    response_text = str(response)
            else:
                # Fallback for older interfaces
                full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                response_text = str(self.llm(full_prompt))
            
            # Parse response
            parsed_response = self._parse_llm_response(response_text)
            
            # Filter false positives
            filtered_variants = self._filter_false_positives(parsed_response.variants)
            
            # Extract variants meeting confidence threshold
            high_confidence_variants = []
            for variant in filtered_variants:
                variant_confidence = variant.get("confidence", 0.0)
                if variant_confidence >= min_confidence:
                    high_confidence_variants.append(variant.get("variant", ""))
            
            self.logger.info(
                f"Extracted {len(high_confidence_variants)} high-confidence variants "
                f"from {len(parsed_response.variants)} total candidates"
            )
            
            return high_confidence_variants
            
        except Exception as e:
            self.logger.error(f"LLM variant recognition failed: {e}")
            return []
    
    def recognize_variants_with_details(self, text: str, min_confidence: float = 0.7) -> List[VariantExtraction]:
        """
        Recognize variants with detailed information.
        
        Args:
            text: Text to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of VariantExtraction objects
        """
        if not text or not text.strip():
            return []
        
        try:
            # Create prompts
            system_prompt = self._create_system_prompt()
            extraction_prompt = self._create_extraction_prompt(text)
            
            # Get LLM response
            if hasattr(self.llm, 'invoke'):
                if HAS_LANGCHAIN and hasattr(self.llm, '__class__') and 'ChatOpenAI' in str(self.llm.__class__):
                    # For ChatOpenAI, we need to handle messages differently in mock
                    full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                    response = self.llm.invoke(full_prompt)
                    response_text = getattr(response, 'content', response) if hasattr(response, 'content') else str(response)
                else:
                    full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                    response = self.llm.invoke(full_prompt)
                    response_text = str(response)
            else:
                full_prompt = f"{system_prompt}\n\n{extraction_prompt}"
                response_text = str(self.llm(full_prompt))
            
            # Parse response
            parsed_response = self._parse_llm_response(response_text)
            
            # Filter false positives
            filtered_variants = self._filter_false_positives(parsed_response.variants)
            
            # Convert to VariantExtraction objects
            detailed_variants = []
            for variant in filtered_variants:
                variant_confidence = variant.get("confidence", 0.0)
                if variant_confidence >= min_confidence:
                    detailed_variants.append(VariantExtraction(
                        variant=variant.get("variant", ""),
                        variant_type=variant.get("variant_type", "unknown"),
                        confidence=variant_confidence,
                        context=variant.get("context", ""),
                        reasoning=variant.get("reasoning", "")
                    ))
            
            return detailed_variants
            
        except Exception as e:
            self.logger.error(f"Detailed LLM variant recognition failed: {e}")
            return []
    
    def batch_recognize_variants(self, texts: List[str], min_confidence: float = 0.7) -> List[List[str]]:
        """
        Recognize variants in multiple texts efficiently.
        
        Args:
            texts: List of texts to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of variant lists for each text
        """
        results = []
        
        for i, text in enumerate(texts):
            self.logger.debug(f"Processing text {i+1}/{len(texts)}")
            
            try:
                variants = self.recognize_variants_text(text, min_confidence)
                results.append(variants)
                
                # Add small delay to respect rate limits
                if i < len(texts) - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Error processing text {i+1}: {e}")
                results.append([])
        
        return results


class MockLLM:
    """Mock LLM for testing when LangChain is not available."""
    
    def invoke(self, prompt: str) -> str:
        """Mock invoke method."""
        # Simple pattern-based mock for testing
        if "H3K" in prompt or "U5F" in prompt:
            return '{"variants": [], "reasoning": "No genomic variants found", "confidence": 0.9}'
        elif "c.123A>G" in prompt:
            return '{"variants": [{"variant": "c.123A>G", "variant_type": "SNP", "confidence": 0.95, "context": "mutation c.123A>G", "reasoning": "HGVS format"}], "reasoning": "Found HGVS variant", "confidence": 0.95}'
        else:
            return '{"variants": [], "reasoning": "No clear variants identified", "confidence": 0.8}'
    
    def __call__(self, prompt: str) -> str:
        """Callable interface."""
        return self.invoke(prompt)


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create recognizer (will use mock if LangChain not available)
    recognizer = RealLLMVariantRecognizer(provider=LLMProvider.MOCK)
    
    # Test cases
    test_texts = [
        "The BRCA1 mutation c.185delAG causes a frameshift.",
        "We used H3K4me3 antibody in this experiment.",
        "The V600E mutation in BRAF is oncogenic.",
        "Buffer contains Tris-HCl and EDTA with pH 8.0.",
        "rs13447455 was associated with disease risk.",
        "The p.Val600Glu substitution affects protein function."
    ]
    
    print("=== Real LLM Variant Recognition Test ===")
    for i, text in enumerate(test_texts):
        print(f"\nText {i+1}: {text}")
        variants = recognizer.recognize_variants_text(text)
        print(f"Variants: {variants}")
        
        # Test detailed recognition
        detailed = recognizer.recognize_variants_with_details(text)
        for detail in detailed:
            print(f"  - {detail.variant} ({detail.variant_type}, conf: {detail.confidence:.2f})")
            print(f"    Reasoning: {detail.reasoning}")
    
    print("\n=== Batch Processing Test ===")
    batch_results = recognizer.batch_recognize_variants(test_texts)
    for i, variants in enumerate(batch_results):
        print(f"Text {i+1}: {variants}")