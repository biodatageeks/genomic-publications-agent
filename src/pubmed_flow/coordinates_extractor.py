"""
Module implementing genomic coordinates extraction from publication texts
using various methods: regular expressions and/or LLM models.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms.base import BaseLLM


class CoordinatesRegexExtractor:
    """
    Class for extracting genomic coordinates from texts using regular expressions.
    """
    
    def __init__(self):
        """
        Initialize the regex-based extractor.
        """
        # Regex patterns for matching common genomic coordinate formats
        self.patterns = [
            # HGVS format
            r'[cm]\.[0-9]+[ACGT]+>[ACGT]+',
            r'[cm]\.(?:-)?[0-9]+(?:_(?:-)?[0-9]+)?(?:del|ins|dup|inv|con)[ACGT]*',
            r'[cm]\.[0-9]+(?:_[0-9]+)?[ACGT]+>[ACGT]+',
            
            # Chr:position format
            r'chr[0-9XYM]+:[0-9]+-[0-9]+',
            
            # Various other formats
            r'[gm]\.[0-9]+[ACGT]>[ACGT]',
            r'p\.[A-Z][a-z]{2}[0-9]+(?:[A-Z][a-z]{2})?[^\s\.,]*'
        ]
    
    def extract_coordinates(self, text: str) -> List[str]:
        """
        Extracts genomic coordinates from text using regular expressions.
        
        Args:
            text: Publication text to search
            
        Returns:
            List of found genomic coordinates
        """
        if not text:
            return []
        
        coordinates = []
        
        # Apply each regex pattern to the text
        for pattern in self.patterns:
            matches = re.findall(pattern, text)
            coordinates.extend(matches)
        
        # Remove duplicates while preserving order
        unique_coordinates = []
        seen = set()
        for coord in coordinates:
            if coord not in seen:
                seen.add(coord)
                unique_coordinates.append(coord)
        
        return unique_coordinates


class CoordinatesLlmExtractor:
    """
    Class for extracting genomic coordinates from texts using LLM models.
    """
    
    def __init__(self, llm: BaseLLM):
        """
        Initialize the LLM-based extractor.
        
        Args:
            llm: Language model (LLM) object
        """
        self.llm = llm
        self.prompt_template = """
        You are an expert in genetics and genomics. Your task is to find all genomic coordinates in the text below.
        
        Look for coordinates in the following formats:
        1. HGVS format: e.g., c.123A>G, c.76_78delACT, m.8993T>G
        2. Chromosomal positions: e.g., chr7:140453136-140453136
        3. Protein format: e.g., p.Val600Glu, p.V600E
        
        Return a list of all found coordinates in the format: COORDINATE1, COORDINATE2, ...
        If no coordinates are found, return "No coordinates found."
        
        Text to analyze:
        {text}
        
        Found coordinates:
        """
    
    def extract(self, text: str) -> List[str]:
        """
        Extracts genomic coordinates from text using the LLM model.
        
        Args:
            text: Publication text to search
            
        Returns:
            List of found genomic coordinates
        """
        try:
            # Prepare prompt for LLM
            prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["text"]
            )
            
            # Create and run LLM chain
            llm_chain = LLMChain(llm=self.llm, prompt=prompt)
            result = llm_chain.run({
                "text": text
            })
            
            # Process result
            if "No coordinates found" in result:
                return []
            
            # Split result into list of coordinates
            coordinates = [coord.strip() for coord in result.split(',')]
            
            # Filter out empty values
            coordinates = [coord for coord in coordinates if coord]
            
            return coordinates
            
        except Exception as e:
            logging.error(f"Error during coordinate extraction using LLM: {str(e)}")
            return []


class CoordinatesExtractor:
    """
    Class combining various methods for extracting genomic coordinates.
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None):
        """
        Initialize the coordinates extractor.
        
        Args:
            llm: Optional language model (LLM) object
        """
        self.regex_extractor = CoordinatesRegexExtractor()
        self.llm_extractor = CoordinatesLlmExtractor(llm) if llm else None
    
    def extract_coordinates(self, text: str, 
                           use_regex: bool = True, 
                           use_llm: bool = True) -> Dict[str, List[str]]:
        """
        Extracts genomic coordinates from text using specified methods.
        
        Args:
            text: Publication text to search
            use_regex: Whether to use regex-based method
            use_llm: Whether to use LLM-based method
            
        Returns:
            Dictionary with extraction results for different methods
        """
        results = {}
        
        if use_regex:
            regex_coords = self.regex_extractor.extract_coordinates(text)
            results["regex"] = regex_coords
            
        if use_llm and self.llm_extractor:
            llm_coords = self.llm_extractor.extract(text)
            results["llm"] = llm_coords
            
        return results
    
    def get_combined_coordinates(self, results: Dict[str, List[str]]) -> List[str]:
        """
        Combines extraction results from different methods into a single list.
        
        Args:
            results: Dictionary with extraction results for different methods
            
        Returns:
            Combined list of unique coordinates
        """
        all_coords = []
        
        for method, coords in results.items():
            all_coords.extend(coords)
            
        # Remove duplicates while preserving order
        unique_coords = []
        seen = set()
        
        for coord in all_coords:
            if coord not in seen:
                seen.add(coord)
                unique_coords.append(coord)
                
        return unique_coords 