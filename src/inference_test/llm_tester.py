"""
Klasa LlmTester umożliwia testowanie i porównywanie różnych modeli LLM
na zadaniach związanych z rozpoznawaniem i analizą wariantów genomowych.
"""

import json
import os
from typing import List, Dict, Any, Optional, Union


class LlmTester:
    """
    Klasa do testowania i porównywania modeli LLM na zadaniach związanych
    z wariantami genomowymi.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicjalizacja testera modeli LLM.
        
        Args:
            api_key: Opcjonalny klucz API do modelu LLM
        """
        if api_key:
            os.environ["TOGETHER_API_KEY"] = api_key
        elif "TOGETHER_API_KEY" in os.environ:
            api_key = os.environ["TOGETHER_API_KEY"]
        else:
            raise ValueError("Nie podano klucza API ani nie znaleziono go w zmiennych środowiskowych.")
        
        self.api_key = api_key
        self.client = self._init_client()
        self.data = []
        self.results = {}
    
    def _init_client(self):
        """
        Inicjalizuje klienta API dla modelu LLM.
        
        Returns:
            Obiekt klienta API
        """
        try:
            from together import Together
            return Together()
        except ImportError:
            raise ImportError("Nie znaleziono pakietu 'together'. Zainstaluj go: pip install together")
    
    def load_data(self, file_path: str, filter_found: bool = False) -> List[Dict[str, Any]]:
        """
        Wczytuje dane z pliku JSONL.
        
        Args:
            file_path: Ścieżka do pliku JSONL z danymi
            filter_found: Czy filtrować tylko rekordy z found=True
            
        Returns:
            Lista wczytanych danych
        """
        with open(file_path, "r") as f:
            data = [json.loads(line) for line in f.readlines()]
        
        if filter_found:
            data = [d for d in data if d.get("metadata", {}).get("found")]
        
        self.data = data
        return data
    
    def get_response(self, model_name: str, messages: List[Dict[str, str]]) -> str:
        """
        Uzyskuje odpowiedź od modelu LLM.
        
        Args:
            model_name: Nazwa modelu LLM
            messages: Lista wiadomości w formacie Chat
            
        Returns:
            Tekst odpowiedzi od modelu
        """
        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        
        return response.choices[0].message.content
    
    def test_model(self, model_name: str, data: Optional[List[Dict[str, Any]]] = None,
                  max_samples: Optional[int] = None) -> Dict[str, Any]:
        """
        Testuje model LLM na podanych danych.
        
        Args:
            model_name: Nazwa modelu LLM
            data: Opcjonalna lista danych testowych
            max_samples: Maksymalna liczba próbek do przetestowania
            
        Returns:
            Słownik z wynikami testu
        """
        if data is None:
            data = self.data
        
        if max_samples is not None:
            data = data[:max_samples]
        
        results = []
        
        for i, sample in enumerate(data):
            messages = sample.get("messages", [])
            
            try:
                response = self.get_response(model_name, messages)
                
                results.append({
                    "sample_id": i,
                    "metadata": sample.get("metadata", {}),
                    "response": response,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "sample_id": i,
                    "metadata": sample.get("metadata", {}),
                    "error": str(e),
                    "success": False
                })
        
        self.results[model_name] = results
        return {"model": model_name, "results": results}
    
    def save_results(self, results: Dict[str, Any], file_path: str) -> None:
        """
        Zapisuje wyniki testów do pliku JSON.
        
        Args:
            results: Słownik z wynikami testów
            file_path: Ścieżka do pliku wyjściowego
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
    
    def compare_models(self, model_results: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        """
        Porównuje wyniki modeli LLM.
        
        Args:
            model_results: Opcjonalny słownik z wynikami modeli
            
        Returns:
            Słownik z porównaniem modeli
        """
        if model_results is None:
            model_results = self.results
        
        if not model_results:
            raise ValueError("Brak wyników do porównania.")
        
        comparison = {
            "models": list(model_results.keys()),
            "total_samples": len(next(iter(model_results.values()))),
            "success_rates": {},
            "details": []
        }
        
        for model_name, results in model_results.items():
            successful = [r for r in results if r.get("success", False)]
            comparison["success_rates"][model_name] = len(successful) / len(results) if results else 0
        
        # Porównaj odpowiedzi dla tych samych próbek
        sample_ids = set(r.get("sample_id") for r in next(iter(model_results.values())))
        
        for sample_id in sample_ids:
            sample_comparison = {"sample_id": sample_id}
            
            for model_name, results in model_results.items():
                sample_result = next((r for r in results if r.get("sample_id") == sample_id), None)
                if sample_result:
                    sample_comparison[model_name] = {
                        "success": sample_result.get("success", False),
                        "response": sample_result.get("response", ""),
                        "metadata": sample_result.get("metadata", {})
                    }
            
            comparison["details"].append(sample_comparison)
        
        return comparison
    
    def test_and_compare(self, model_names: List[str], data_file_path: str,
                        output_file_path: Optional[str] = None,
                        max_samples: Optional[int] = None,
                        filter_found: bool = False) -> Dict[str, Any]:
        """
        Przeprowadza pełny proces testowania i porównywania modeli.
        
        Args:
            model_names: Lista nazw modeli LLM do przetestowania
            data_file_path: Ścieżka do pliku z danymi testowymi
            output_file_path: Opcjonalna ścieżka do pliku wyjściowego
            max_samples: Maksymalna liczba próbek do przetestowania
            filter_found: Czy filtrować tylko rekordy z found=True
            
        Returns:
            Słownik z porównaniem modeli
        """
        # Wczytaj dane
        self.load_data(data_file_path, filter_found)
        
        # Testuj modele
        for model_name in model_names:
            self.test_model(model_name, max_samples=max_samples)
        
        # Porównaj modele
        comparison = self.compare_models()
        
        # Zapisz wyniki
        if output_file_path:
            self.save_results(comparison, output_file_path)
        
        return comparison 