"""
Klasa VariantRecognizer służy do rozpoznawania wariantów genomowych w tekstach biomedycznych
przy użyciu modelu NER.
"""

import torch
import numpy as np
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from transformers import AutoTokenizer, AutoModelForTokenClassification


class VariantRecognizer:
    """
    Klasa implementująca rozpoznawanie wariantów genomowych w tekstach biomedycznych
    przy użyciu modelu NER (Named Entity Recognition).
    
    Wykorzystuje modele HuggingFace do tokenizacji i klasyfikacji tokenów.
    """
    
    def __init__(self, model_name: str = "drAbreu/bioBERT-NER-HGVS"):
        """
        Inicjalizacja rozpoznawacza wariantów.
        
        Args:
            model_name: Nazwa modelu HuggingFace do rozpoznawania wariantów
        """
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.id2label = self.model.config.id2label
    
    def tokenize_text(self, text: str) -> Dict[str, torch.Tensor]:
        """
        Tokenizuje tekst przy użyciu tokenizera.
        
        Args:
            text: Tekst do tokenizacji
            
        Returns:
            Słownik z tokenami i maskami uwagi
        """
        return self.tokenizer(text, return_tensors="pt").to(self.device)
    
    def predict(self, text: str) -> List[str]:
        """
        Wykonuje predykcję wariantów w tekście.
        
        Args:
            text: Tekst do analizy
            
        Returns:
            Lista rozpoznanych wariantów
        """
        tokenized_text = self.tokenize_text(text)
        
        with torch.no_grad():
            outputs = self.model(**tokenized_text)
            predictions = torch.argmax(outputs.logits, dim=2)
        
        token_predictions = [self.id2label[prediction.item()] for prediction in predictions[0]]
        tokens = self.tokenizer.convert_ids_to_tokens(tokenized_text["input_ids"][0])
        
        # Wyodrębnij tylko tokeny z etykietami wariantów
        variant_tokens = []
        for token, prediction in zip(tokens, token_predictions):
            if prediction in ["B-Sequence_Variant", "I-Sequence_Variant", "variant", "sequence"]:
                # Usuń znaki specjalne i odfiltruj puste
                cleaned_token = token.replace("#", "").replace("▁", "").strip()
                if cleaned_token:
                    variant_tokens.append(cleaned_token)
        
        return variant_tokens
    
    def predict_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Wykonuje predykcję wariantów dla listy tekstów.
        
        Args:
            texts: Lista tekstów do analizy
            
        Returns:
            Lista list rozpoznanych wariantów dla każdego tekstu
        """
        results = []
        for text in texts:
            results.append(self.predict(text))
        return results
    
    def find_variant_in_text(self, text: str, expected_variant: str) -> Tuple[bool, List[str]]:
        """
        Sprawdza, czy oczekiwany wariant został znaleziony w tekście.
        
        Args:
            text: Tekst do analizy
            expected_variant: Oczekiwany wariant do znalezienia
            
        Returns:
            Krotka (znaleziono, lista_wariantów)
        """
        predicted_variants = self.predict(text)
        found = expected_variant.lower() in [v.lower() for v in predicted_variants]
        
        return found, predicted_variants
    
    def evaluate_on_snippets(self, snippets: List[Dict[str, Any]], 
                            expected_variant_key: str = "variant") -> Dict[str, Any]:
        """
        Ocenia skuteczność modelu na zbiorze snippetów.
        
        Args:
            snippets: Lista słowników zawierających snippety i metadane
            expected_variant_key: Klucz w słowniku snippetu, który zawiera oczekiwany wariant
            
        Returns:
            Słownik z wynikami ewaluacji
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
        Zapisuje wyniki ewaluacji do pliku JSON.
        
        Args:
            results: Słownik z wynikami ewaluacji
            file_path: Ścieżka do pliku wyjściowego
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
    
    def load_snippets_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Wczytuje snippety z pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku ze snippetami
            
        Returns:
            Lista snippetów
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    
    def process_and_evaluate(self, snippets_file_path: str, results_file_path: str,
                           expected_variant_key: str = "variant") -> Dict[str, Any]:
        """
        Przeprowadza pełny proces przetwarzania i ewaluacji.
        
        Args:
            snippets_file_path: Ścieżka do pliku ze snippetami
            results_file_path: Ścieżka do pliku wyjściowego z wynikami
            expected_variant_key: Klucz w słowniku snippetu, który zawiera oczekiwany wariant
            
        Returns:
            Słownik z wynikami ewaluacji
        """
        snippets = self.load_snippets_from_file(snippets_file_path)
        results = self.evaluate_on_snippets(snippets, expected_variant_key)
        self.save_results(results, results_file_path)
        
        return results 