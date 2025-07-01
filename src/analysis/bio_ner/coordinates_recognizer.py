"""
The CoordinatesRecognizer class is used for recognizing genomic coordinates in biomedical texts
using regular expressions and optional LLM models.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple, Union

try:
    import torch
    import numpy as np
    from transformers import AutoTokenizer, AutoModelForTokenClassification, BatchEncoding
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch = None
    np = None
    AutoTokenizer = None
    AutoModelForTokenClassification = None
    BatchEncoding = None

from src.utils.llm.manager import LlmManager


class CoordinatesRecognizer:
    """
    Class implementing the recognition of genomic coordinates in biomedical texts
    using regular expressions and optional LLM models for advanced coordinate recognition.
    
    Supports multiple coordinate formats including HGVS, chromosomal positions, 
    dbSNP identifiers, and chromosomal aberrations.
    """
    
    def __init__(self, llm_manager: Optional[LlmManager] = None, model_name: str = "gpt-3.5-turbo"):
        """
        Initializes the coordinates recognizer.
        
        Args:
            llm_manager: Optional LlmManager instance for LLM-based coordinate recognition
            model_name: Name of the model for coordinate recognition
        """
        self.llm_manager = llm_manager
        self.model_name = model_name
        
        # Initialize regex patterns for different coordinate formats
        self._initialize_regex_patterns()
        
        # Only initialize HuggingFace models if needed for NER and torch is available
        if self._is_huggingface_model():
            if not HAS_TORCH:
                raise ImportError("torch and transformers are required for HuggingFace models. "
                                "Install them with: pip install torch transformers")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.id2label = self.model.config.id2label
    
    def _initialize_regex_patterns(self):
        """Initialize regular expression patterns for different coordinate formats."""
        
        # HGVS DNA patterns
        self.hgvs_dna_c = re.compile(
            r'[A-Z0-9_-]+:?c\.(?:[*-]?[1-9][0-9]*(?:[+-][1-9][0-9]*)?)'
            r'(?:[ACGT]>[ACGT]|del[ACGT]*|dup[ACGT]*|ins[ACGT]+|delins[ACGT]+|_[*-]?[1-9][0-9]*(?:[+-][1-9][0-9]*)?(?:del[ACGT]*|dup[ACGT]*|ins[ACGT]+|delins[ACGT]+))',
            re.IGNORECASE
        )
        
        self.hgvs_dna_g = re.compile(
            r'[A-Z0-9_-]+:?[gmo]\.(?:[1-9][0-9]*)'
            r'(?:[ACGT]>[ACGT]|del|dup|ins[ACGT]+|delins[ACGT]+|_[1-9][0-9]*(?:del|dup|ins[ACGT]+|delins[ACGT]+))',
            re.IGNORECASE
        )
        
        self.hgvs_dna_n = re.compile(
            r'[A-Z0-9_-]+:?n\.(?:[1-9][0-9]*(?:[+-][1-9][0-9]*)?)'
            r'(?:[ACGT]>[ACGT]|del|dup|ins[ACGT]+|delins[ACGT]+|_[1-9][0-9]*(?:[+-][1-9][0-9]*)?(?:del|dup|ins[ACGT]+|delins[ACGT]+))',
            re.IGNORECASE
        )
        
        # HGVS RNA patterns
        self.hgvs_rna = re.compile(
            r'[A-Z0-9_-]+:?r\.(?:[1-9][0-9]*(?:[+-][1-9][0-9]*)?)'
            r'(?:[acgu]>[acgu]|del|dup|ins[acgu]+|delins[acgu]+|_[1-9][0-9]*(?:[+-][1-9][0-9]*)?(?:del|dup|ins[acgu]+|delins[acgu]+))',
            re.IGNORECASE
        )
        
        # HGVS Protein patterns
        self.hgvs_protein = re.compile(
            r'[A-Z0-9_-]+:?p\.(?:(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter)[1-9][0-9]*)'
            r'(?:(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter)|=|del|dup|ins(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter)+|delins(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter)+)',
            re.IGNORECASE
        )
        
        # Chromosomal coordinate patterns
        self.chr_position = re.compile(
            r'chr(?:[1-9][0-9]?|X|Y|M|MT):(?:[1-9][0-9]*)',
            re.IGNORECASE
        )
        
        self.chr_position_full = re.compile(
            r'chr(?:[1-9][0-9]?|X|Y|M|MT):(?:[1-9][0-9]*)[ACGT]>[ACGT]',
            re.IGNORECASE
        )
        
        # dbSNP patterns
        self.dbsnp = re.compile(r'rs[0-9]+', re.IGNORECASE)
        
        # Chromosomal aberration patterns
        self.chr_aberration = re.compile(
            r'(?:del|dup|inv|t)\([0-9]{1,2}(?:;[0-9]{1,2})?\)\([pq][0-9.q]+\)',
            re.IGNORECASE
        )
        
        # Repeat expansion patterns
        self.repeat_expansion = re.compile(
            r'[A-Z0-9_-]+:?c\.(?:[*-]?[1-9][0-9]*)[ACGT]+\[>[0-9]+\]',
            re.IGNORECASE
        )
        
        # Generic genomic coordinates
        self.genomic_coordinate = re.compile(
            r'(?:[1-9][0-9]*):(?:[1-9][0-9]*)-(?:[1-9][0-9]*)',
            re.IGNORECASE
        )
    
    def _is_huggingface_model(self) -> bool:
        """Check if the model is a HuggingFace model."""
        return not self.model_name.startswith("gpt")
    
    def get_llm(self):
        """
        Get the LLM instance. Create a new LlmManager if not provided during initialization.
        
        Returns:
            LLM instance for text generation
        """
        if self.llm_manager is None:
            self.llm_manager = LlmManager('together', self.model_name)
        return self.llm_manager.get_llm()
    
    def extract_coordinates_regex(self, text: str) -> List[Dict[str, str]]:
        """
        Extract genomic coordinates from text using regular expressions.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of dictionaries with coordinate information
        """
        coordinates = []
        
        # Extract HGVS DNA coordinates (c. notation)
        for match in self.hgvs_dna_c.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'hgvs_dna_c',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract HGVS DNA coordinates (g./m./o. notation)
        for match in self.hgvs_dna_g.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'hgvs_dna_g',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract HGVS DNA coordinates (n. notation)
        for match in self.hgvs_dna_n.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'hgvs_dna_n',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract HGVS RNA coordinates
        for match in self.hgvs_rna.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'hgvs_rna',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract HGVS protein coordinates
        for match in self.hgvs_protein.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'hgvs_protein',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract chromosomal positions
        for match in self.chr_position_full.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'chr_position',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract basic chromosomal positions
        for match in self.chr_position.finditer(text):
            # Avoid duplicates with chr_position_full
            if not any(coord['start'] <= match.start() < coord['end'] for coord in coordinates):
                coordinates.append({
                    'coordinate': match.group(),
                    'type': 'chr_position_basic',
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Extract dbSNP identifiers
        for match in self.dbsnp.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'dbsnp',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract chromosomal aberrations
        for match in self.chr_aberration.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'chr_aberration',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract repeat expansions
        for match in self.repeat_expansion.finditer(text):
            coordinates.append({
                'coordinate': match.group(),
                'type': 'repeat_expansion',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract generic genomic coordinates
        for match in self.genomic_coordinate.finditer(text):
            # Avoid duplicates with more specific patterns
            if not any(coord['start'] <= match.start() < coord['end'] for coord in coordinates):
                coordinates.append({
                    'coordinate': match.group(),
                    'type': 'genomic_coordinate',
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Sort by position in text
        coordinates.sort(key=lambda x: x['start'])
        
        return coordinates
    
    def recognize_coordinates_text(self, text: str, method: str = "regex") -> List[str]:
        """
        Recognize genomic coordinates in text using specified method.
        
        Args:
            text: Text to analyze
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            List of recognized coordinates
        """
        if method == "regex":
            coords_data = self.extract_coordinates_regex(text)
            return [coord['coordinate'] for coord in coords_data]
        elif method == "llm":
            return self._recognize_coordinates_llm(text)
        elif method == "hybrid":
            regex_coords = self.extract_coordinates_regex(text)
            llm_coords = self._recognize_coordinates_llm(text)
            
            # Combine and deduplicate
            all_coords = [coord['coordinate'] for coord in regex_coords] + llm_coords
            return list(set(all_coords))
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _recognize_coordinates_llm(self, text: str) -> List[str]:
        """
        Recognize genomic coordinates using LLM.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of recognized coordinates
        """
        llm = self.get_llm()
        prompt = self._generate_llm_prompt(text)
        response = llm.invoke(prompt)
        
        if isinstance(response, str):
            return self._parse_llm_response(response)
        else:
            response_text = str(response)
            return self._parse_llm_response(response_text)
    
    def _generate_llm_prompt(self, text: str) -> str:
        """
        Generate a prompt for LLM-based coordinate recognition.
        
        Args:
            text: Text to analyze
            
        Returns:
            Prompt for LLM
        """
        return f"""
Extract all genomic coordinates from the following text. Return only the coordinates, separated by commas.
If no coordinates are found, reply with "No coordinates found."

Example coordinate formats:
- HGVS DNA: c.123A>G, g.12345A>G, n.456C>T
- HGVS RNA: r.123a>g
- HGVS Protein: p.Val600Glu, p.Arg123*
- Chromosomal: chr7:140453136A>T, chr1:12345-67890
- dbSNP: rs1234567
- Chromosomal aberrations: del(15)(q11.2q13.1), t(9;22)(q34;q11.2)
- Repeat expansions: HTT:c.52CAG[>36]

Text:
{text}

Coordinates:
"""
    
    def _parse_llm_response(self, response: str) -> List[str]:
        """
        Parse the response from the LLM into a list of coordinates.
        
        Args:
            response: Response from the LLM
            
        Returns:
            List of coordinates
        """
        if not response or "no coordinate" in response.lower():
            return []
        
        # Split by commas, then by new lines with numbers, then by new lines with dashes
        coordinates = []
        
        # Try comma separated values first
        if "," in response:
            coordinates = [coord.strip() for coord in response.split(",")]
        else:
            # Try numbered list (1. coordinate)
            numbered_matches = re.findall(r'\d+\.\s*([^,\n]+)', response)
            if numbered_matches:
                coordinates = [coord.strip() for coord in numbered_matches]
            else:
                # Try bulleted list (- coordinate)
                bulleted_matches = re.findall(r'[-*]\s*([^,\n]+)', response)
                if bulleted_matches:
                    coordinates = [coord.strip() for coord in bulleted_matches]
                else:
                    # Just split by new lines and hope for the best
                    coordinates = [coord.strip() for coord in response.split("\n") if coord.strip()]
        
        # Filter out non-coordinates
        return [coord for coord in coordinates if coord and not re.match(r'^\d+\.?$', coord) and "no coordinate" not in coord.lower()]
    
    def recognize_coordinates_file(self, file_path: str, method: str = "regex") -> List[str]:
        """
        Recognize genomic coordinates in a file.
        
        Args:
            file_path: Path to the file
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            List of recognized coordinates
        """
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        
        return self.recognize_coordinates_text(text, method)
    
    def recognize_coordinates_dir(self, dir_path: str, extensions: Optional[List[str]] = None, 
                                 method: str = "regex") -> Dict[str, List[str]]:
        """
        Recognize genomic coordinates in files in a directory.
        
        Args:
            dir_path: Path to the directory
            extensions: List of file extensions to process (default: [".txt"])
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            Dictionary with file paths and lists of recognized coordinates
        """
        if extensions is None:
            extensions = [".txt"]
        
        results = {}
        
        try:
            files = os.listdir(dir_path)
            
            for file_name in files:
                # Check if the file has one of the specified extensions
                if any(file_name.endswith(ext) for ext in extensions):
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        try:
                            coordinates = self.recognize_coordinates_file(file_path, method)
                            results[file_name] = coordinates
                        except Exception as e:
                            print(f"Error processing file {file_path}: {str(e)}")
        except OSError as e:
            raise e
        
        return results
    
    def save_coordinates_to_file(self, coordinates: List[str], output_file: str) -> None:
        """
        Save a list of coordinates to a file.
        
        Args:
            coordinates: List of coordinates to save
            output_file: Path to the output file
        """
        with open(output_file, "w", encoding="utf-8") as file:
            for coordinate in coordinates:
                file.write(f"{coordinate}\n")
    
    def evaluate_on_snippets(self, snippets: List[Dict[str, Any]], 
                           expected_coordinate_key: str = "coordinate",
                           method: str = "regex") -> Dict[str, Any]:
        """
        Evaluates the model's effectiveness on a set of snippets.
        
        Args:
            snippets: List of dictionaries containing snippets and metadata
            expected_coordinate_key: Key in the snippet dictionary that contains the expected coordinate
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            Dictionary with evaluation results
        """
        found_coordinates_count: int = 0
        details_list: List[Dict[str, Any]] = []
        total_snippets: int = len(snippets)
        
        for i, snippet in enumerate(snippets):
            text = snippet.get("text", "")
            expected_coordinate = snippet.get(expected_coordinate_key, "").lower()
            
            if not expected_coordinate or not text:
                continue
                
            found, predicted_coordinates = self.find_coordinate_in_text(text, expected_coordinate, method)
            
            if found:
                found_coordinates_count += 1
                
            details_list.append({
                "snippet_index": i,
                "expected_coordinate": expected_coordinate,
                "predicted_coordinates": predicted_coordinates,
                "found": found
            })
        
        accuracy: float = 0.0
        if total_snippets > 0:
            accuracy = found_coordinates_count / total_snippets
        
        return {
            "total_snippets": total_snippets,
            "found_coordinates": found_coordinates_count,
            "accuracy": accuracy,
            "details": details_list
        }
    
    def find_coordinate_in_text(self, text: str, expected_coordinate: str, method: str = "regex") -> Tuple[bool, List[str]]:
        """
        Checks if the expected coordinate was found in the text.
        
        Args:
            text: Text to analyze
            expected_coordinate: Expected coordinate to find
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            Tuple (found, list_of_coordinates)
        """
        predicted_coordinates = self.recognize_coordinates_text(text, method)
        found = expected_coordinate.lower() in [coord.lower() for coord in predicted_coordinates]
        
        return found, predicted_coordinates
    
    def save_results(self, results: Dict[str, Any], file_path: str) -> None:
        """
        Saves evaluation results to a JSON file.
        
        Args:
            results: Dictionary with evaluation results
            file_path: Path to the output file
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
    
    def load_snippets_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Loads snippets from a JSON file.
        
        Args:
            file_path: Path to the file with snippets
            
        Returns:
            List of snippets
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    def process_and_evaluate(self, snippets_file_path: str, results_file_path: str,
                           expected_coordinate_key: str = "coordinate", 
                           method: str = "regex") -> Dict[str, Any]:
        """
        Conducts the full processing and evaluation process.
        
        Args:
            snippets_file_path: Path to the file with snippets
            results_file_path: Path to the output file with results
            expected_coordinate_key: Key in the snippet dictionary that contains the expected coordinate
            method: Method to use ('regex', 'llm', 'hybrid')
            
        Returns:
            Dictionary with evaluation results
        """
        snippets = self.load_snippets_from_file(snippets_file_path)
        results = self.evaluate_on_snippets(snippets, expected_coordinate_key, method)
        self.save_results(results, results_file_path)
        
        return results
    
    def get_coordinate_types(self, coordinates: List[str]) -> Dict[str, int]:
        """
        Analyze the types of coordinates found.
        
        Args:
            coordinates: List of coordinates to analyze
            
        Returns:
            Dictionary with coordinate types and their counts
        """
        type_counts = {}
        
        for coord in coordinates:
            coord_info = self.extract_coordinates_regex(coord)
            if coord_info:
                coord_type = coord_info[0]['type']
                type_counts[coord_type] = type_counts.get(coord_type, 0) + 1
            else:
                type_counts['unknown'] = type_counts.get('unknown', 0) + 1
        
        return type_counts