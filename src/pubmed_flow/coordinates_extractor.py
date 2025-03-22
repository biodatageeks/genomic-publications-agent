"""
Moduł implementujący ekstrakcję koordynatów genomowych z tekstów publikacji
przy użyciu różnych metod: wyrażeń regularnych i/lub modeli LLM.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms.base import BaseLLM


class CoordinatesRegexExtractor:
    """
    Klasa do ekstrakcji koordynatów genomowych z tekstów przy użyciu wyrażeń regularnych.
    """
    
    def __init__(self):
        """
        Inicjalizacja ekstraktora opartego na wyrażeniach regularnych.
        """
        # Regex do dopasowywania typowych formatów koordynatów genomowych
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
        Ekstrahuje koordynaty genomowe z tekstu przy użyciu wyrażeń regularnych.
        
        Args:
            text: Tekst publikacji do przeszukania
            
        Returns:
            Lista znalezionych koordynatów genomowych
        """
        if not text:
            return []
        
        coordinates = []
        
        # Zastosuj każdy wzorzec regex do tekstu
        for pattern in self.patterns:
            matches = re.findall(pattern, text)
            coordinates.extend(matches)
        
        # Usuń duplikaty zachowując kolejność
        unique_coordinates = []
        seen = set()
        for coord in coordinates:
            if coord not in seen:
                seen.add(coord)
                unique_coordinates.append(coord)
        
        return unique_coordinates


class CoordinatesLlmExtractor:
    """
    Klasa do ekstrakcji koordynatów genomowych z tekstów przy użyciu modeli LLM.
    """
    
    def __init__(self, llm: BaseLLM):
        """
        Inicjalizacja ekstraktora opartego na LLM.
        
        Args:
            llm: Obiekt modelu językowego (LLM)
        """
        self.llm = llm
        self.prompt_template = """
        Jesteś ekspertem w dziedzinie genetyki i genomiki. Twoim zadaniem jest znalezienie wszystkich koordynatów genomowych w tekście poniżej.
        
        Szukaj koordynatów w następujących formatach:
        1. HGVS format: np. c.123A>G, c.76_78delACT, m.8993T>G
        2. Pozycje chromosomowe: np. chr7:140453136-140453136
        3. Format białkowy: np. p.Val600Glu, p.V600E
        
        Zwróć listę wszystkich znalezionych koordynatów w formacie: KOORDYNAT1, KOORDYNAT2, ...
        Jeśli nie znajdziesz żadnych koordynatów, zwróć "Nie znaleziono koordynatów."
        
        Tekst do przeanalizowania:
        {text}
        
        Znalezione koordynaty:
        """
    
    def extract(self, text: str) -> List[str]:
        """
        Ekstrahuje koordynaty genomowe z tekstu przy użyciu modelu LLM.
        
        Args:
            text: Tekst publikacji do przeszukania
            
        Returns:
            Lista znalezionych koordynatów genomowych
        """
        try:
            # Przygotuj prompt dla LLM
            prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["text"]
            )
            
            # Utwórz i uruchom łańcuch LLM
            llm_chain = LLMChain(llm=self.llm, prompt=prompt)
            result = llm_chain.run({
                "text": text
            })
            
            # Przetwórz wynik
            if "Nie znaleziono koordynatów" in result:
                return []
            
            # Podziel wynik na listę koordynatów
            coordinates = [coord.strip() for coord in result.split(',')]
            
            # Odfiltruj puste wartości
            coordinates = [coord for coord in coordinates if coord]
            
            return coordinates
            
        except Exception as e:
            logging.error(f"Błąd podczas ekstrakcji koordynatów przy użyciu LLM: {str(e)}")
            return []


class CoordinatesExtractor:
    """
    Klasa łącząca różne metody ekstrakcji koordynatów genomowych.
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None):
        """
        Inicjalizacja ekstraktora koordynatów.
        
        Args:
            llm: Opcjonalny obiekt modelu językowego (LLM)
        """
        self.regex_extractor = CoordinatesRegexExtractor()
        self.llm_extractor = CoordinatesLlmExtractor(llm) if llm else None
    
    def extract_coordinates(self, text: str, 
                           use_regex: bool = True, 
                           use_llm: bool = True) -> Dict[str, List[str]]:
        """
        Ekstrahuje koordynaty genomowe z tekstu przy użyciu określonych metod.
        
        Args:
            text: Tekst publikacji do przeszukania
            use_regex: Czy używać metody opartej na wyrażeniach regularnych
            use_llm: Czy używać metody opartej na LLM
            
        Returns:
            Słownik z wynikami ekstrakcji dla różnych metod
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
        Łączy wyniki ekstrakcji z różnych metod w jedną listę.
        
        Args:
            results: Słownik z wynikami ekstrakcji dla różnych metod
            
        Returns:
            Połączona lista unikatowych koordynatów
        """
        all_coords = []
        
        for method, coords in results.items():
            all_coords.extend(coords)
            
        # Usuń duplikaty zachowując kolejność
        unique_coords = []
        seen = set()
        
        for coord in all_coords:
            if coord not in seen:
                seen.add(coord)
                unique_coords.append(coord)
                
        return unique_coords 