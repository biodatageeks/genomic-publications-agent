"""
The VariantRecognizer class is used for recognizing genomic variants in biomedical texts
using the NER model.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple, Union

from src.utils.models.factory import ModelFactory
from src.utils.models.base import BaseModelWrapper
from src.utils.models.huggingface import HuggingFaceModelWrapper
from src.utils.models.llm import LLMModelWrapper


class VariantRecognizer:
    """
    Class implementing the recognition of genomic variants in biomedical texts
    using the NER (Named Entity Recognition) model.
    
    Utilizes HuggingFace models for tokenization and token classification.
    Can also utilize LLM models for more advanced variant recognition.
    """
    
    def __init__(self, model_wrapper: Optional[BaseModelWrapper] = None, model_name: Optional[str] = None, 
                 provider: Optional[str] = None):
        """
        Initializes the variant recognizer.
        
        Args:
            model_wrapper: Optional model wrapper instance for variant recognition
            model_name: Name of the model for variant recognition. If None, uses default
            provider: Provider for LLM models (e.g., 'together', 'openai')
        """
        if model_wrapper is not None:
            if not isinstance(model_wrapper, BaseModelWrapper):
                raise TypeError("model_wrapper must be an instance of BaseModelWrapper")
            self.model_wrapper = model_wrapper
            self.model_name = model_wrapper.model_name
        elif model_name is not None:
            # Auto-create appropriate wrapper
            self.model_wrapper = ModelFactory.create(model_name, provider=provider)
            self.model_name = model_name
        else:
            # Default to a common LLM model
            self.model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
            self.model_wrapper = ModelFactory.create_llm(self.model_name, provider=provider or 'together')
        
        # For backward compatibility
        self.device = self.model_wrapper.get_device()
        self.id2label = self.model_wrapper.get_id2label()
    
    def get_llm(self):
        """
        Get the LLM instance.
        
        Returns:
            LLM instance for text generation
        """
        if self.model_wrapper.get_model_type() == "llm":
            return self.model_wrapper.llm
        else:
            raise RuntimeError("Current model is not an LLM model")
    
    def tokenize_text(self, text: str):
        """
        Tokenizes the text using the tokenizer.
        
        Args:
            text: Text to be tokenized
            
        Returns:
            BatchEncoding object with tokens and attention masks
        """
        if self.model_wrapper.get_model_type() != "huggingface":
            raise RuntimeError("Tokenization is only available for HuggingFace models")
        
        return self.model_wrapper.tokenize_text(text)
    
    def predict(self, text: str) -> List[str]:
        """
        Makes predictions of variants in the text using NER model.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of recognized variants
        """
        if self.model_wrapper.get_model_type() != "huggingface":
            raise RuntimeError("NER prediction is only available for HuggingFace models")
            
        result = self.model_wrapper.predict(text)
        
        # Extract variant tokens from the result
        variant_tokens = []
        if 'predictions' in result and result['predictions']:
            prediction = result['predictions'][0]
            if 'entities' in prediction:
                # Use entities if available
                for entity in prediction['entities']:
                    if entity['label'].lower() in ['sequence_variant', 'variant', 'mutation']:
                        variant_tokens.append(entity['text'])
            elif 'tokens' in prediction and 'predictions' in prediction:
                # Fallback to token-level processing
                tokens = prediction['tokens']
                token_predictions = prediction['predictions']
                
                for token, pred in zip(tokens, token_predictions):
                    if pred in ["B-Sequence_Variant", "I-Sequence_Variant", "variant", "sequence"]:
                        # Remove special characters and filter out empty tokens
                        cleaned_token = token.replace("#", "").replace("▁", "").strip()
                        if cleaned_token:
                            variant_tokens.append(cleaned_token)
        
        return variant_tokens
    
    def generate_llm_prompt(self, text: str) -> str:
        """
        Generate a prompt for LLM-based variant recognition.
        
        Args:
            text: Text to analyze
            
        Returns:
            Prompt for LLM
        """
        return f"""
Extract all genomic variants from the following text. Return only the variants, separated by commas. 
If no variants are found, reply with "No variants found."

Example genomic variant formats:
- HGVS format (e.g., c.123A>G, p.Val600Glu, g.12345A>G)
- Chromosomal positions (e.g., chr7:140453136A>T)
- dbSNP identifiers (e.g., rs1234567)

Text:
{text}

Variants:
"""
    
    def parse_llm_response(self, response: str) -> List[str]:
        """
        Parse the response from the LLM into a list of variants.
        
        Args:
            response: Response from the LLM
            
        Returns:
            List of variants
        """
        if not response or "no variant" in response.lower():
            return []
        
        # Split by commas, then by new lines with numbers, then by new lines with dashes
        variants = []
        
        # Try comma separated values first
        if "," in response:
            variants = [v.strip() for v in response.split(",")]
        else:
            # Try numbered list (1. variant)
            numbered_matches = re.findall(r'\d+\.\s*([^,\n]+)', response)
            if numbered_matches:
                variants = [v.strip() for v in numbered_matches]
            else:
                # Try bulleted list (- variant)
                bulleted_matches = re.findall(r'[-*]\s*([^,\n]+)', response)
                if bulleted_matches:
                    variants = [v.strip() for v in bulleted_matches]
                else:
                    # Just split by new lines and hope for the best
                    variants = [v.strip() for v in response.split("\n") if v.strip()]
        
        # Filter out non-variants
        return [v for v in variants if v and not re.match(r'^\d+\.?$', v) and "no variant" not in v.lower()]
    
    def recognize_variants_text(self, text: str) -> List[str]:
        """
        Recognize genomic variants in text using LLM.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of recognized variants
        """
        if self.model_wrapper.get_model_type() != "llm":
            raise RuntimeError("LLM variant recognition is only available for LLM models")
            
        prompt = self.generate_llm_prompt(text)
        result = self.model_wrapper.predict(prompt)
        
        if 'predictions' in result and result['predictions']:
            response = result['predictions'][0].get('generated_text', '')
            return self.parse_llm_response(response)
        else:
            return []
    
    def recognize_variants_file(self, file_path: str) -> List[str]:
        """
        Recognize genomic variants in a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of recognized variants
        """
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        
        # Use appropriate method based on model type
        if self.model_wrapper.get_model_type() == "huggingface":
            variants = self.predict(text)
        else:
            variants = self.recognize_variants_text(text)
        
        return variants
    
    def recognize_variants_dir(self, dir_path: str, extensions: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Recognize genomic variants in files in a directory.
        
        Args:
            dir_path: Path to the directory
            extensions: List of file extensions to process (default: [".txt"])
            
        Returns:
            Dictionary with file paths and lists of recognized variants
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
                            variants = self.recognize_variants_file(file_path)
                            results[file_name] = variants
                        except Exception as e:
                            print(f"Error processing file {file_path}: {str(e)}")
        except OSError as e:
            # Re-raise the error for directory access issues
            raise e
        
        return results
    
    def save_variants_to_file(self, variants: List[str], output_file: str) -> None:
        """
        Save a list of variants to a file.
        
        Args:
            variants: List of variants to save
            output_file: Path to the output file
        """
        with open(output_file, "w", encoding="utf-8") as file:
            for variant in variants:
                file.write(f"{variant}\n")
    
    def evaluate_on_snippets(self, snippets: List[Dict[str, Any]], 
                           expected_variant_key: str = "variant") -> Dict[str, Any]:
        """
        Evaluates the model's effectiveness on a set of snippets.
        
        Args:
            snippets: List of dictionaries containing snippets and metadata
            expected_variant_key: Key in the snippet dictionary that contains the expected variant
            
        Returns:
            Dictionary with evaluation results
        """
        # Define initial result with explicit types
        found_variants_count: int = 0
        details_list: List[Dict[str, Any]] = []
        total_snippets: int = len(snippets)
        
        # Process snippets
        for i, snippet in enumerate(snippets):
            text = snippet.get("text", "")
            expected_variant = snippet.get(expected_variant_key, "").lower()
            
            if not expected_variant or not text:
                continue
                
            found, predicted_variants = self.find_variant_in_text(text, expected_variant)
            
            if found:
                found_variants_count += 1
                
            details_list.append({
                "snippet_index": i,
                "expected_variant": expected_variant,
                "predicted_variants": predicted_variants,
                "found": found
            })
        
        # Calculate accuracy
        accuracy: float = 0.0
        if total_snippets > 0:
            accuracy = found_variants_count / total_snippets
        
        # Return results dictionary with explicit types
        return {
            "total_snippets": total_snippets,
            "found_variants": found_variants_count,
            "accuracy": accuracy,
            "details": details_list
        }
    
    def find_variant_in_text(self, text: str, expected_variant: str) -> Tuple[bool, List[str]]:
        """
        Checks if the expected variant was found in the text.
        
        Args:
            text: Text to analyze
            expected_variant: Expected variant to find
            
        Returns:
            Tuple (found, list_of_variants)
        """
        if self.model_wrapper.get_model_type() == "huggingface":
            predicted_variants = self.predict(text)
        else:
            predicted_variants = self.recognize_variants_text(text)
            
        found = expected_variant.lower() in [v.lower() for v in predicted_variants]
        
        return found, predicted_variants
    
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
                           expected_variant_key: str = "variant") -> Dict[str, Any]:
        """
        Conducts the full processing and evaluation process.
        
        Args:
            snippets_file_path: Path to the file with snippets
            results_file_path: Path to the output file with results
            expected_variant_key: Key in the snippet dictionary that contains the expected variant
            
        Returns:
            Dictionary with evaluation results
        """
        snippets = self.load_snippets_from_file(snippets_file_path)
        results = self.evaluate_on_snippets(snippets, expected_variant_key)
        self.save_results(results, results_file_path)
        
        return results 