"""
PubTator client for retrieving and analyzing biomedical publications.

PubTator3 API provides access to a database of biomedical publications with predefined
annotations for genes, diseases, chemical compounds, mutations, species, variants,
and other biological concepts.

This module offers an interface for communicating with the PubTator3 API and processing
the returned data using the bioc library.
"""

import json
import logging
import re
import time
from io import StringIO
from typing import List, Dict, Any, Optional, Union, Set
from urllib.parse import urljoin

import requests
import bioc
from bioc import pubtator, biocjson
from exceptions import FormatNotSupportedException, PubTatorError

DEFAULT_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"

class PubTatorClient:
    """
    Client for communicating with the PubTator3 API.
    
    Allows for retrieving publications with annotations related to genes, diseases, 
    tissue specificity, and other biological concepts.
    
    Example usage:
        client = PubTatorClient()
        pmids = ["32735606", "32719766"]
        publications = client.get_publications_by_pmids(pmids)
        for pub in publications:
            print(f"Title: {pub.title}")
            for passage in pub.passages:
                for annotation in passage.annotations:
                    print(f"  Annotation: {annotation.text} [{annotation.infons.get('type')}]")
    """
    
    # Mapping between API parameters (lowercase) and data types (uppercase)
    # based on documentation: https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTatorCentral/api.html
    CONCEPT_TYPE_MAPPING = {
        "gene": "Gene",
        "disease": "Disease",
        "chemical": "Chemical",
        "species": "Species",
        "mutation": "Mutation",
        "cellline": "CellLine",
        # Additional types observed in the data
        "dnamutation": "DNAMutation",
        "tissue": "Tissue"
    }
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the PubTator client.
        
        Args:
            base_url: Custom base URL for the API (optional)
            timeout: API response timeout limit in seconds
        """
        self.base_url = base_url if base_url else DEFAULT_BASE_URL
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> requests.Response:
        """
        Make a request to the PubTator API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method (GET or POST)
            params: Query parameters
            
        Returns:
            Response from the API
            
        Raises:
            PubTatorError: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error making request to {url}: {str(e)}")
            raise PubTatorError(f"API request failed: {str(e)}")
    
    def _process_response(self, response: requests.Response, format_type: str) -> List[Any]:
        """
        Process response from PubTator API based on format type.
        
        Args:
            response: Response from PubTator API
            format_type: Format of the response data
            
        Returns:
            List of BioCDocument objects or a list containing the raw response
            
        Raises:
            FormatNotSupportedException: If the requested format is not fully supported
            PubTatorError: If there is an error processing the response
        """
        if response.status_code == 404:
            raise PubTatorError(f"Resource not found: {response.text}")
            
        if not response.ok:
            raise PubTatorError(f"API request failed: {response.text}")
            
        if format_type == "biocjson":
            try:
                data = response.json()
                collection = biocjson.load(StringIO(json.dumps(data)))
                return collection.documents
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Error processing response: {str(e)}")
                raise PubTatorError(f"Error processing response: {str(e)}")
        elif format_type == "pubtator":
            # Process PubTator format using the bioc.pubtator module
            try:
                docs = pubtator.load(StringIO(response.text))
                return docs
            except Exception as e:
                self.logger.error(f"Error processing PubTator response: {str(e)}")
                raise PubTatorError(f"Error processing PubTator response: {str(e)}")
        else:
            self.logger.warning(f"Format {format_type} is not fully supported at this time")
            raise FormatNotSupportedException(f"Format {format_type} is not fully supported at this time")
    
    def get_publications_by_pmids(self, pmids: List[str], 
                                 concepts: Optional[List[str]] = None, 
                                 format_type: str = "biocjson") -> List[Any]:
        """
        Retrieve publications by PubMed IDs (PMIDs).
        
        Args:
            pmids: List of PubMed identifiers
            concepts: List of concept types to include (e.g., "gene", "disease", "mutation")
                     If not provided, returns all available annotation types
            format_type: Format of returned data (currently only 'biocjson' is fully supported)
            
        Returns:
            List of BioCDocument objects containing publication texts with annotations
            
        Raises:
            PubTatorError: If the publications cannot be found or an error occurs
        """
        # Only biocjson format works correctly with the API
        if format_type.lower() != "biocjson":
            self.logger.warning(f"Format {format_type} may not be supported by the API. Using 'biocjson'.")
            format_type = "biocjson"
        
        params = {
            "pmids": ",".join(pmids)
        }
        
        if concepts:
            params["concepts"] = ",".join(concepts)
        
        headers = {"Accept": "application/json"}
        try:
            response = requests.get(
                f"{self.base_url}/publications/export/biocjson",
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            # Handle 404 error - resource not found
            if response.status_code == 404:
                raise PubTatorError(f"Resource not found: {','.join(pmids)}")
                
            if not response.ok:
                raise PubTatorError(f"API request failed: {response.text}")
            
            try:
                data = response.json()
                if "PubTator3" in data:
                    documents = []
                    for doc_data in data["PubTator3"]:
                        doc = bioc.BioCDocument()
                        doc.id = doc_data.get("id", "")
                        
                        # Process passages
                        if "passages" in doc_data:
                            for passage_data in doc_data["passages"]:
                                passage = bioc.BioCPassage()
                                passage.text = passage_data.get("text", "")
                                passage.offset = passage_data.get("offset", 0)
                                
                                # Copy information
                                for key, value in passage_data.get("infons", {}).items():
                                    passage.infons[key] = value
                                
                                # Process annotations
                                if "annotations" in passage_data:
                                    for anno_data in passage_data["annotations"]:
                                        annotation = bioc.BioCAnnotation()
                                        annotation.id = anno_data.get("id", "")
                                        annotation.text = anno_data.get("text", "")
                                        
                                        # Copy information
                                        for key, value in anno_data.get("infons", {}).items():
                                            annotation.infons[key] = value
                                        
                                        # Process locations
                                        if "locations" in anno_data:
                                            for loc_data in anno_data["locations"]:
                                                offset = loc_data.get("offset", 0)
                                                length = loc_data.get("length", 0)
                                                location = bioc.BioCLocation(offset=offset, length=length)
                                                annotation.add_location(location)
                                        
                                        passage.add_annotation(annotation)
                                
                                doc.add_passage(passage)
                        
                        documents.append(doc)
                    return documents
                else:
                    # Try to process the response as standard BioC
                    collection = biocjson.load(StringIO(json.dumps(data)))
                    return collection.documents
                    
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                self.logger.error(f"Error processing response: {str(e)}")
                raise PubTatorError(f"Error processing response: {str(e)}")
        except requests.HTTPError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise PubTatorError(f"Resource not found: {','.join(pmids)}")
            raise PubTatorError(f"API request failed: {str(e)}")
        except Exception as e:
            raise PubTatorError(f"Error retrieving publications: {str(e)}")
    
    def get_publication_by_pmid(self, pmid: str, 
                               concepts: Optional[List[str]] = None, 
                               format_type: str = "biocjson") -> Optional[bioc.BioCDocument]:
        """
        Retrieve a single publication by PubMed ID.
        
        Args:
            pmid: PubMed identifier
            concepts: List of concept types to include
            format_type: Format of returned data
            
        Returns:
            A BioCDocument object containing the publication text with annotations,
            or None if the publication was not found
            
        Raises:
            PubTatorError: If an error occurs during retrieval (except for 404 Not Found)
        """
        try:
            docs = self.get_publications_by_pmids([pmid], concepts, format_type)
            if not docs:
                self.logger.warning(f"No publication found for PMID: {pmid}")
                return None
            return docs[0]
        except PubTatorError as e:
            if "Resource not found" in str(e):
                self.logger.warning(f"Resource not found: {pmid}")
                return None
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving publication {pmid}: {str(e)}")
            raise PubTatorError(f"Error retrieving publication: {str(e)}")
    
    def search_publications(self, query: str, 
                           concepts: Optional[List[str]] = None,
                           format_type: str = "biocjson") -> List[Any]:
        """
        Search for publications using a text query.
        
        Args:
            query: Search query (similar to PubMed queries)
            concepts: List of concept types to include
            format_type: Format of returned data
            
        Returns:
            List of BioCDocument objects matching the query
            
        Raises:
            PubTatorError: If the search fails or no results are found
        """
        try:
            endpoint = "v1/search"
            params: Dict[str, Any] = {
                "q": query,
                "format": format_type
            }
            
            if concepts:
                params["concepts"] = ",".join(concepts)
                
            response = self._make_request(endpoint, method="GET", params=params)
            
            # Handle 404 error - resource not found
            if response.status_code == 404:
                raise PubTatorError(f"Resource not found: {query}")
                
            if not response.ok:
                raise PubTatorError(f"API request failed: {response.text}")
                
            return self._process_response(response, format_type)
        except PubTatorError:
            # Re-raise PubTatorError without modification
            raise
        except Exception as e:
            self.logger.error(f"Error searching for publications: {str(e)}")
            raise PubTatorError(f"Error searching for publications: {str(e)}")
    
    def extract_annotations_by_type(self, document: bioc.BioCDocument, 
                                  annotation_type: Union[str, List[str]], 
                                  include_type_in_result: bool = False) -> List[Dict[str, Any]]:
        """
        Extract annotations of specified type(s) from a BioC document.
        
        Args:
            document: BioC document with annotations
            annotation_type: Type or list of types of annotations to extract
            include_type_in_result: Whether to include the annotation type in the result
            
        Returns:
            List of dictionaries containing information about annotations
        """
        # Konwertuj pojedynczy typ do listy
        if isinstance(annotation_type, str):
            types_to_check = {annotation_type}
        else:
            types_to_check = set(annotation_type)
        
        # Sprawdź, czy typy są małymi literami (parametry API) i przekonwertuj je
        normalized_types = set()
        for atype in types_to_check:
            if atype in self.CONCEPT_TYPE_MAPPING:
                normalized_types.add(self.CONCEPT_TYPE_MAPPING[atype])
            else:
                normalized_types.add(atype)
        
        annotations = []
        
        for passage in document.passages:
            for annotation in passage.annotations:
                anno_type = annotation.infons.get("type")
                if anno_type in normalized_types:
                    anno_data = {
                        "id": annotation.id,
                        "text": annotation.text,
                        "normalized_id": annotation.infons.get("identifier"),
                        "locations": [(loc.offset, loc.offset + loc.length) for loc in annotation.locations],
                        "infons": annotation.infons
                    }
                    
                    if include_type_in_result:
                        anno_data["type"] = anno_type
                        
                    annotations.append(anno_data)
        
        return annotations
    
    def extract_gene_annotations(self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract gene annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about gene annotations
        """
        return self.extract_annotations_by_type(document, "Gene")
    
    def extract_disease_annotations(self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract disease annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about disease annotations
        """
        return self.extract_annotations_by_type(document, "Disease")
    
    def extract_variant_annotations(self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract variant annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about variant annotations
        """
        return self.extract_annotations_by_type(document, "Variant")
    
    def extract_tissue_specificity(self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract tissue specificity annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about tissue annotations
        """
        return self.extract_annotations_by_type(document, "TissueSpecificity")
    
    def extract_all_annotations(self, document: bioc.BioCDocument) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all annotations from a BioC document and group them by type.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            Dictionary containing annotations grouped by type
        """
        annotations_by_type = {}
        
        for passage in document.passages:
            for annotation in passage.annotations:
                anno_type = annotation.infons.get("type")
                if anno_type not in annotations_by_type:
                    annotations_by_type[anno_type] = []
                
                anno_data = {
                    "id": annotation.id,
                    "text": annotation.text,
                    "normalized_id": annotation.infons.get("identifier"),
                    "locations": [(loc.offset, loc.offset + loc.length) for loc in annotation.locations],
                    "infons": annotation.infons
                }
                annotations_by_type[anno_type].append(anno_data)
        
        return annotations_by_type
    
    def get_annotation_types(self, document: bioc.BioCDocument) -> Dict[str, int]:
        """
        Get all annotation types present in a document and their counts.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            Dictionary with annotation types as keys and counts as values
        """
        type_counts = {}
        
        for passage in document.passages:
            for annotation in passage.annotations:
                anno_type = annotation.infons.get("type")
                if anno_type not in type_counts:
                    type_counts[anno_type] = 0
                type_counts[anno_type] += 1
        
        return type_counts

    def get_relations(self, entity1: str, relation_type: str, entity2: str) -> List[Dict[str, Any]]:
        """Retrieve relations between entities from the PubTator API.

        Args:
            entity1 (str): First entity (e.g. '@GENE_JAK1')
            relation_type (str): Relation type (e.g. 'negative_correlate')
            entity2 (str): Second entity (e.g. 'Chemical')

        Returns:
            List[Dict[str, Any]]: List of relations in JSON format with source, target and publications fields

        Raises:
            PubTatorError: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/relations",
                params={
                    "e1": entity1,
                    "type": relation_type,
                    "e2": entity2
                },
                headers={"Accept": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error retrieving relations: {str(e)}")
            raise PubTatorError(f"Failed to retrieve relations: {str(e)}")

    def get_publications(self, pmids: Union[str, List[str]], format: str = "biocjson") -> Dict[str, Any]:
        """Retrieve publications from the PubTator API in raw JSON format.

        This method returns the raw JSON response from the API, while get_publications_by_pmids
        returns processed BioCDocument objects.

        Args:
            pmids (Union[str, List[str]]): PMID identifier or a list of identifiers
            format (str, optional): Response format ('biocjson', 'biocxml'). Default 'biocjson'.

        Returns:
            Dict[str, Any]: Response data in JSON format

        Raises:
            PubTatorError: If the request fails or the resource is not found
        """
        # Convert list to comma-separated string if necessary
        if isinstance(pmids, list):
            pmids = ",".join(pmids)
            
        # Only biocjson format works correctly with the API
        if format.lower() != "biocjson":
            self.logger.warning(f"Format {format} may not be supported by the API. Using 'biocjson'.")
            format = "biocjson"
        
        headers = {"Accept": "application/json"}
        try:
            response = requests.get(
                f"{self.base_url}/publications/export/biocjson",
                params={"pmids": pmids},
                headers=headers,
                timeout=self.timeout
            )
            
            # Handle 404 error - resource not found
            if response.status_code == 404:
                raise PubTatorError(f"Resource not found: {pmids}")
                
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error retrieving publications: {str(e)}")
            raise PubTatorError(f"Failed to retrieve publications: {str(e)}") 