"""
PubTator client for fetching annotated biomedical publications.

This module provides a client for the PubTator API, which allows fetching
publications with annotations of biomedical entities such as genes,
diseases, mutations, chemicals, and more.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union
import json
import requests
import bioc

from src.data.clients.exceptions import PubTatorError
from src.core.config.config import Config


class PubTatorClient:
    """
    Client for the PubTator API to fetch annotated biomedical publications.
    
    PubTator is a web-based system for assisting biocuration by providing
    automatic annotations of biomedical entities such as genes, diseases,
    variants, and more.
    
    This client provides methods to fetch annotated publications by their
    PubMed IDs (PMIDs) and convert them to BioC format for further processing.
    
    Example usage:
        client = PubTatorClient()
        publications = client.get_publications_by_pmids(["32735606", "32719766"])
        for publication in publications:
            print(f"Title: {publication.passages[0].text}")
    """
    
    # Base URL for the PubTator API
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
    
    # Maximum number of PMIDs per request
    MAX_PMIDS_PER_REQUEST = 100
    
    def __init__(self, email: Optional[str] = None, 
                 max_retries: int = 3, 
                 retry_delay: int = 1,
                 timeout: int = 30):
        """
        Initializes the PubTator client.
        
        Args:
            email: Email address for API usage tracking (recommended by NCBI)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retry attempts in seconds (default: 1)
            timeout: Timeout for API requests in seconds (default: 30)
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        config = Config()
        
        # If email is not provided, try to get it from config
        if email is None:
            email = config.get_contact_email()
        
        self.email = email
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.logger.info(f"Initialized PubTator client (email: {email}, max_retries: {max_retries})")
    
    def get_publication_by_pmid(self, pmid: str) -> bioc.BioCDocument:
        """
        Fetches a single publication by its PubMed ID.
        
        Args:
            pmid: PubMed identifier
            
        Returns:
            BioCDocument representing the publication
            
        Raises:
            PubTatorError: If the publication cannot be fetched
        """
        publications = self.get_publications_by_pmids([pmid])
        
        if not publications:
            raise PubTatorError(f"Failed to fetch publication for PMID: {pmid}")
        
        return publications[0]
    
    def get_publications_by_pmids(self, pmids: List[str]) -> List[bioc.BioCDocument]:
        """
        Fetches multiple publications by their PubMed IDs.
        
        For large numbers of PMIDs, the requests are automatically batched
        according to the API limitations.
        
        Args:
            pmids: List of PubMed identifiers
            
        Returns:
            List of BioCDocuments representing the publications
            
        Raises:
            PubTatorError: If the publications cannot be fetched
        """
        if not pmids:
            self.logger.warning("Empty list of PMIDs provided")
            return []
        
        # Ensure PMIDs are strings
        pmids = [str(pmid) for pmid in pmids]
        
        # Process PMIDs in batches to respect API limits
        all_publications = []
        batch_size = self.MAX_PMIDS_PER_REQUEST
        
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            self.logger.info(f"Fetching batch of {len(batch_pmids)} PMIDs (batch {i//batch_size + 1})")
            
            try:
                batch_publications = self._get_publications_batch(batch_pmids)
                all_publications.extend(batch_publications)
                
                # Add a small delay to be nice to the API
                if i + batch_size < len(pmids):
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"Error fetching batch of PMIDs: {str(e)}")
                raise PubTatorError(f"Failed to fetch publications: {str(e)}") from e
        
        self.logger.info(f"Successfully fetched {len(all_publications)} publications")
        return all_publications
    
    def _get_publications_batch(self, batch_pmids: List[str]) -> List[bioc.BioCDocument]:
        """
        Fetches a batch of publications from PubTator.
        
        Args:
            batch_pmids: List of PubMed identifiers to fetch in one request
            
        Returns:
            List of BioCDocuments representing the publications
            
        Raises:
            PubTatorError: If the publications cannot be fetched
        """
        url = f"{self.BASE_URL}/publications/export/biocjson"
        
        # Prepare request parameters
        params = {
            "pmids": ",".join(batch_pmids),
            "concepts": "gene,disease,mutation,chemical,species,cellline"
        }
        
        # Add email if provided
        headers = {}
        if self.email:
            headers["User-Agent"] = f"PubTatorClient/1.0 ({self.email})"
        
        # Make request with retries
        retries = 0
        while retries <= self.max_retries:
            try:
                response = requests.get(
                    url, 
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Check for successful response
                response.raise_for_status()
                
                # Parse BioC JSON
                bioc_json = response.json()
                return self._parse_bioc_json(bioc_json)
                
            except requests.exceptions.RequestException as e:
                retries += 1
                self.logger.warning(f"Request failed (attempt {retries}/{self.max_retries}): {str(e)}")
                
                if retries > self.max_retries:
                    raise PubTatorError(f"Failed to fetch publications after {self.max_retries} attempts: {str(e)}") from e
                
                # Wait before retrying
                time.sleep(self.retry_delay)
    
    def _parse_bioc_json(self, bioc_json: Dict[str, Any]) -> List[bioc.BioCDocument]:
        """
        Parses BioC JSON format to BioCDocument objects.
        
        Args:
            bioc_json: BioC JSON response from PubTator
            
        Returns:
            List of BioCDocuments
        """
        try:
            # Create BioC collection from JSON
            collection = bioc.BioCCollection()
            collection.encoding = bioc_json.get("encoding", "utf-8")
            collection.version = bioc_json.get("version", "1.0")
            
            documents = []
            for doc_json in bioc_json.get("documents", []):
                # Create document
                document = bioc.BioCDocument()
                document.id = doc_json.get("id", "")
                
                # Add infons
                for key, value in doc_json.get("infons", {}).items():
                    document.infons[key] = value
                
                # Add passages
                for passage_json in doc_json.get("passages", []):
                    passage = bioc.BioCPassage()
                    passage.offset = passage_json.get("offset", 0)
                    passage.text = passage_json.get("text", "")
                    
                    # Add infons to passage
                    for key, value in passage_json.get("infons", {}).items():
                        passage.infons[key] = value
                    
                    # Add annotations
                    for annotation_json in passage_json.get("annotations", []):
                        annotation = bioc.BioCAnnotation()
                        annotation.id = annotation_json.get("id", "")
                        annotation.text = annotation_json.get("text", "")
                        
                        # Add locations
                        for location_json in annotation_json.get("locations", []):
                            location = bioc.BioCLocation()
                            location.offset = location_json.get("offset", 0)
                            location.length = location_json.get("length", 0)
                            annotation.locations.append(location)
                        
                        # Add infons to annotation
                        for key, value in annotation_json.get("infons", {}).items():
                            annotation.infons[key] = value
                        
                        passage.annotations.append(annotation)
                    
                    document.passages.append(passage)
                
                documents.append(document)
            
            return documents
        except Exception as e:
            self.logger.error(f"Error parsing BioC JSON: {str(e)}")
            raise PubTatorError(f"Failed to parse BioC JSON: {str(e)}") from e 