"""
Base analyzer module providing a common interface for all analyzers in the project.

This module contains BaseAnalyzer abstract class that all analyzers should inherit from.
"""

import logging
from typing import Optional, List, Dict, Any

import bioc
from abc import ABC, abstractmethod

from src.data.clients.pubtator import PubTatorClient


class BaseAnalyzer(ABC):
    """
    Base abstract class for all analyzers.
    
    Provides a common interface and shared functionality for analyzing
    biomedical publications and extracting structured information.
    
    Example implementation:
        class MyAnalyzer(BaseAnalyzer):
            def analyze_publications(self, pmids):
                # Implement your analysis logic
                return results
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None):
        """
        Initializes the BaseAnalyzer.
        
        Args:
            pubtator_client: Optional PubTator client for fetching publication data
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize PubTator client if not provided
        if pubtator_client is None:
            self.pubtator_client = PubTatorClient()
        else:
            self.pubtator_client = pubtator_client
            
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def analyze_publications(self, pmids: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Analyzes a list of publications.
        
        Args:
            pmids: List of PubMed identifiers to analyze
            **kwargs: Additional keyword arguments
            
        Returns:
            List of dictionaries containing analysis results
        """
        pass
    
    @abstractmethod
    def analyze_publication(self, pmid: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Analyzes a single publication.
        
        Args:
            pmid: PubMed identifier to analyze
            **kwargs: Additional keyword arguments
            
        Returns:
            List of dictionaries containing analysis results
        """
        pass
    
    @abstractmethod
    def _analyze_publication(self, publication: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Internal method to analyze a publication.
        
        Args:
            publication: BioCDocument to analyze
            
        Returns:
            List of dictionaries containing analysis results
        """
        pass 