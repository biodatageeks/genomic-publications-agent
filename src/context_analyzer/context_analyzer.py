"""
Abstract class for biomedical context analyzers.

This module defines a common interface for all context analyzers
used to analyze relationships between biomedical entities in scientific literature.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from src.pubtator_client.pubtator_client import PubTatorClient
from src.core.config.config import Config


class ContextAnalyzer(ABC):
    """
    Abstract interface for biomedical context analyzers.
    
    This class defines a common interface for all analyzers
    that extract relationships between biomedical entities from scientific publications.
    
    Implementations of this interface should provide specific analysis methods
    for detecting relationships between different types of entities (genes, variants, diseases, etc.)
    in the context of publications and biomedical passages.
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None):
        """
        Initializes the context analyzer.
        
        Args:
            pubtator_client: Optional PubTator client for data retrieval
        """
        if pubtator_client is None:
            config = Config()
            email = config.get_contact_email()
            self.pubtator_client = PubTatorClient(email=email)
        else:
            self.pubtator_client = pubtator_client
    
    @abstractmethod
    def analyze_publications(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Analyzes a list of publications to extract contextual relationships.
        
        Args:
            pmids: List of PubMed identifiers to analyze
            
        Returns:
            List of dictionaries containing relationship data
        """
        pass
    
    @abstractmethod
    def analyze_publication(self, pmid: str) -> List[Dict[str, Any]]:
        """
        Analyzes a single publication to extract contextual relationships.
        
        Args:
            pmid: PubMed identifier to analyze
            
        Returns:
            List of dictionaries containing relationship data
        """
        pass
    
    @abstractmethod
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Saves relationship data to a CSV file.
        
        Args:
            relationships: List of dictionaries containing relationship data
            output_file: Path to the output CSV file
        """
        pass
    
    @abstractmethod
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Saves relationship data to a JSON file.
        
        Args:
            relationships: List of dictionaries containing relationship data
            output_file: Path to the output JSON file
        """
        pass 