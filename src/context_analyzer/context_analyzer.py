"""
Abstrakcyjna klasa dla analizatorów kontekstu biomedycznego.

Ten moduł definiuje wspólny interfejs dla wszystkich analizatorów kontekstu
używanych do analizy relacji między bytami biomedycznymi w literaturze naukowej.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from src.pubtator_client.pubtator_client import PubTatorClient


class ContextAnalyzer(ABC):
    """
    Abstrakcyjny interfejs dla analizatorów kontekstu biomedycznego.
    
    Ta klasa definiuje wspólny interfejs dla wszystkich analizatorów,
    które wydobywają relacje między bytami biomedycznymi z publikacji naukowych.
    
    Implementacje tego interfejsu powinny dostarczać konkretne metody analizy
    do wykrywania relacji między różnymi typami bytów (geny, warianty, choroby, itd.)
    w kontekście publikacji i pasaży biomedycznych.
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None):
        """
        Inicjalizuje analizator kontekstu.
        
        Args:
            pubtator_client: Opcjonalny klient PubTator do pobierania danych
        """
        self.pubtator_client = pubtator_client if pubtator_client else PubTatorClient()
    
    @abstractmethod
    def analyze_publications(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Analizuje listę publikacji, aby wydobyć relacje kontekstowe.
        
        Args:
            pmids: Lista identyfikatorów PubMed do analizy
            
        Returns:
            Lista słowników zawierających dane relacji
        """
        pass
    
    @abstractmethod
    def analyze_publication(self, pmid: str) -> List[Dict[str, Any]]:
        """
        Analizuje pojedynczą publikację, aby wydobyć relacje kontekstowe.
        
        Args:
            pmid: Identyfikator PubMed do analizy
            
        Returns:
            Lista słowników zawierających dane relacji
        """
        pass
    
    @abstractmethod
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Zapisuje dane relacji do pliku CSV.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            output_file: Ścieżka do pliku wyjściowego CSV
        """
        pass
    
    @abstractmethod
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Zapisuje dane relacji do pliku JSON.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            output_file: Ścieżka do pliku wyjściowego JSON
        """
        pass 