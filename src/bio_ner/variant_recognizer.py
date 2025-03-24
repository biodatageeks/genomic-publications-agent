"""
The VariantRecognizer class is used for recognizing genomic variants in biomedical texts
using the NER model.
"""

import torch
import numpy as np
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from transformers import AutoTokenizer, AutoModelForTokenClassification


class VariantRecognizer:
    """
    Class implementing the recognition of genomic variants in biomedical texts
    using the NER (Named Entity Recognition) model.
    
    Utilizes HuggingFace models for tokenization and token classification.
    """
    
    def __init__(self, model_name: str = "drAbreu/bioBERT-NER-HGVS"):
        """
        Initializes the variant recognizer.
        
        Args:
            model_name: Name of the HuggingFace model for variant recognition
        """
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.id2label = self.model.config.id2label
    
    def tokenize_text(self, text: str) -> Dict[str, torch.Tensor]:
        """
        Tokenizes the text using the tokenizer.
        
        Args:
            text: Text to be tokenized
            
        Returns:
            Dictionary with tokens and attention masks
        """
        return self.tokenizer(text, return_tensors="pt").to(self.device)
    
    def predict(self, text: str) -> List[str]:
        """
        Makes predictions of variants in the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of recognized variants
        """
        tokenized_text = self.tokenize_text(text)
        
        with torch.no_grad():
            outputs = self.model(**tokenized_text)
            predictions = torch.argmax(outputs.logits, dim=2)
        
        token_predictions = [self.id2label[prediction.item()] for prediction in predictions[0]]
        tokens = self.tokenizer.convert_ids_to_tokens(tokenized_text["input_ids"][0])
        
        # Extract only tokens with variant labels
        variant_tokens = []
        for token, prediction in zip(tokens, token_predictions):
            if prediction in ["B-Sequence_Variant", "I-Sequence_Variant", "variant", "sequence"]:
                # Remove special characters and filter out empty tokens
                cleaned_token = token.replace("#", "").replace("▁", "").strip()
                if cleaned_token:
                    variant_tokens.append(cleaned_token)
        
        return variant_tokens
    
    def predict_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Makes predictions of variants for a list of texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of lists of recognized variants for each text
        """
        results = []
        for text in texts:
            results.append(self.predict(text))
        return results
    
    def find_variant_in_text(self, text: str, expected_variant: str) -> Tuple[bool, List[str]]:
        """
        Checks if the expected variant was found in the text.
        
        Args:
            text: Text to analyze
            expected_variant: Expected variant to find
            
        Returns:
            Tuple (found, list_of_variants)
        """
        predicted_variants = self.predict(text)
        found = expected_variant.lower() in [v.lower() for v in predicted_variants]
        
        return found, predicted_variants
    
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
        results = {
            "total_snippets": len(snippets),
            "found_variants": 0,
            "accuracy": 0.0,
            "details": []
        }
        
        for i, snippet in enumerate(snippets):
            text = snippet.get("text", "")
            expected_variant = snippet.get(expected_variant_key, "").lower()
            
            if not expected_variant or not text:
                continue
                
            found, predicted_variants = self.find_variant_in_text(text, expected_variant)
            
            if found:
                results["found_variants"] += 1
                
            results["details"].append({
                "snippet_index": i,
                "expected_variant": expected_variant,
                "predicted_variants": predicted_variants,
                "found": found
            })
        
        if results["total_snippets"] > 0:
            results["accuracy"] = results["found_variants"] / results["total_snippets"]
            
        return results
    
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