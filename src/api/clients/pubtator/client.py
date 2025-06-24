"""
PubTator API client implementation.
"""
import requests
from typing import Dict, List, Optional, Union
from ...core.utils.logging import get_logger
from ...core.config.settings import API_TIMEOUT, API_RETRY_ATTEMPTS, API_RETRY_DELAY

logger = get_logger(__name__)

class PubTatorClient:
    """
    Client for interacting with the PubTator API.
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson"
    
    def __init__(self, timeout: int = API_TIMEOUT):
        """
        Initialize the PubTator client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_publication(self, pmid: str) -> Optional[Dict]:
        """
        Get publication data for a given PMID.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Optional[Dict]: Publication data or None if not found
        """
        try:
            response = self.session.get(
                self.BASE_URL,
                params={"pmids": pmid},
                headers={"Accept": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "PubTator3" in data and data["PubTator3"]:
                return data["PubTator3"][0]
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching publication {pmid}: {str(e)}")
            return None
    
    def get_publications(self, pmids: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Get publication data for multiple PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            Dict[str, Optional[Dict]]: Mapping of PMIDs to their data
        """
        results = {}
        for pmid in pmids:
            results[pmid] = self.get_publication(pmid)
        return results 