"""
Context analysis module implementation.
"""
from typing import Dict, List, Optional, Union
from ...core.utils.logging import get_logger
from ...clients.pubtator.client import PubTatorClient

logger = get_logger(__name__)

class ContextAnalyzer:
    """
    Analyzer for extracting and analyzing context from publications.
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None):
        """
        Initialize the context analyzer.
        
        Args:
            pubtator_client: Optional PubTator client instance
        """
        self.pubtator_client = pubtator_client or PubTatorClient()
    
    def extract_context(self, publication: Dict) -> Dict:
        """
        Extract context from a publication.
        
        Args:
            publication: Publication data from PubTator
            
        Returns:
            Dict: Extracted context information
        """
        context = {
            "title": "",
            "abstract": "",
            "genes": [],
            "diseases": [],
            "chemicals": [],
            "species": [],
            "tissues": []
        }
        
        if not publication:
            return context
            
        # Extract title and abstract
        for passage in publication.get("passages", []):
            if passage.get("infons", {}).get("type") == "title":
                context["title"] = passage.get("text", "")
            elif passage.get("infons", {}).get("type") == "abstract":
                context["abstract"] = passage.get("text", "")
        
        # Extract annotations
        for passage in publication.get("passages", []):
            for annotation in passage.get("annotations", []):
                anno_type = annotation.get("infons", {}).get("type", "").lower()
                if anno_type in context:
                    context[anno_type].append({
                        "text": annotation.get("text", ""),
                        "id": annotation.get("infons", {}).get("identifier", ""),
                        "offset": annotation.get("locations", [{}])[0].get("offset", 0),
                        "length": annotation.get("locations", [{}])[0].get("length", 0)
                    })
        
        return context
    
    def analyze_publication(self, pmid: str) -> Optional[Dict]:
        """
        Analyze a publication by its PMID.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Optional[Dict]: Analysis results or None if not found
        """
        publication = self.pubtator_client.get_publication(pmid)
        if not publication:
            return None
            
        context = self.extract_context(publication)
        return {
            "pmid": pmid,
            "context": context,
            "statistics": {
                "gene_count": len(context["genes"]),
                "disease_count": len(context["diseases"]),
                "chemical_count": len(context["chemicals"]),
                "species_count": len(context["species"]),
                "tissue_count": len(context["tissues"])
            }
        } 