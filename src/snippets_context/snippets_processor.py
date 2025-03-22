"""
Klasa SnippetsProcessor służy do przetwarzania fragmentów tekstu z publikacji naukowych,
które zawierają odniesienia do koordynatów genomowych.
"""

import os
import json
from typing import List, Dict, Any


class SnippetsProcessor:
    """
    Klasa do przetwarzania fragmentów tekstu zawierających koordynaty genomowe.
    
    Funkcjonalność:
    1. Wczytywanie różnych koordynatów genomowych z pliku
    2. Generowanie listy pubmed ids dla danych koordynatów
    3. Pobieranie publikacji z PubMed
    4. Wyodrębnianie fragmentów tekstu zawierających koordynaty (snippety)
    5. Zapisywanie snippetów do pliku
    """
    
    def __init__(self, variants_file_path: str = None):
        """
        Inicjalizacja procesora snippetów.
        
        Args:
            variants_file_path: Ścieżka do pliku z wariantami genomowymi
        """
        self.variants = []
        self.pubmed_ids = []
        self.snippets = []
        
        if variants_file_path and os.path.exists(variants_file_path):
            self.load_variants(variants_file_path)
    
    def load_variants(self, file_path: str) -> List[str]:
        """
        Wczytuje warianty genomowe z pliku.
        
        Args:
            file_path: Ścieżka do pliku z wariantami
            
        Returns:
            Lista wczytanych wariantów
        """
        with open(file_path, 'r') as file:
            self.variants = [line.strip() for line in file.readlines() if line.strip()]
        return self.variants
    
    def generate_pubmed_ids(self, coordinates: List[str] = None) -> List[str]:
        """
        Generuje listę identyfikatorów PubMed dla podanych koordynatów.
        
        Args:
            coordinates: Lista koordynatów genomowych
            
        Returns:
            Lista identyfikatorów PubMed
        """
        if coordinates is None:
            coordinates = self.variants
            
        # Tutaj należy zaimplementować logikę pobierania pubmed_ids
        # na podstawie koordynatów, np. poprzez API LitVar lub inne
        
        # Przykładowa implementacja:
        self.pubmed_ids = []  # Tutaj będą pubmed_ids z API
        
        return self.pubmed_ids
    
    def fetch_publications(self, pubmed_ids: List[str] = None) -> Dict[str, str]:
        """
        Pobiera publikacje z PubMed na podstawie identyfikatorów.
        
        Args:
            pubmed_ids: Lista identyfikatorów PubMed
            
        Returns:
            Słownik mapujący identyfikatory PubMed na treść publikacji
        """
        if pubmed_ids is None:
            pubmed_ids = self.pubmed_ids
            
        publications = {}
        
        # Tutaj należy zaimplementować logikę pobierania publikacji
        # z PubMed przy użyciu np. PubTatorClient lub innego API
        
        return publications
    
    def extract_snippets(self, publications: Dict[str, str], coordinates: List[str] = None, 
                         context_size: int = 2) -> List[Dict[str, Any]]:
        """
        Wyodrębnia snippety tekstu zawierające odniesienia do koordynatów genomowych.
        
        Args:
            publications: Słownik mapujący identyfikatory PubMed na treść publikacji
            coordinates: Lista koordynatów genomowych do wyszukania
            context_size: Liczba zdań kontekstu przed i po zdaniu z koordynatami
            
        Returns:
            Lista słowników zawierających snippety i metadane
        """
        if coordinates is None:
            coordinates = self.variants
            
        snippets = []
        
        # Tutaj należy zaimplementować logikę wyodrębniania snippetów
        # z publikacji, znajdując zdania zawierające koordynaty i dodając kontekst
        
        self.snippets = snippets
        return snippets
    
    def save_snippets(self, file_path: str, snippets: List[Dict[str, Any]] = None) -> None:
        """
        Zapisuje snippety do pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku wyjściowego
            snippets: Lista snippetów do zapisania
        """
        if snippets is None:
            snippets = self.snippets
            
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(snippets, file, indent=2, ensure_ascii=False)
            
    def process_pipeline(self, variants_file_path: str, output_file_path: str, 
                         context_size: int = 2) -> List[Dict[str, Any]]:
        """
        Przeprowadza cały proces przetwarzania w jednym wywołaniu.
        
        Args:
            variants_file_path: Ścieżka do pliku z wariantami
            output_file_path: Ścieżka do pliku wyjściowego ze snippetami
            context_size: Liczba zdań kontekstu
            
        Returns:
            Lista wygenerowanych snippetów
        """
        self.load_variants(variants_file_path)
        pubmed_ids = self.generate_pubmed_ids()
        publications = self.fetch_publications(pubmed_ids)
        snippets = self.extract_snippets(publications, context_size=context_size)
        self.save_snippets(output_file_path, snippets)
        
        return snippets 