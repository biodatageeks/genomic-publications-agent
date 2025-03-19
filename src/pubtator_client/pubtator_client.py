"""
PubTator3 API client for retrieving scientific publications data with annotations.

PubTator3 API provides access to a database of biomedical publications with predefined
annotations for genes, diseases, chemical compounds, mutations, species, variants,
and other biological concepts.

This module offers an interface for communicating with the PubTator3 API and processing
the returned data using the bioc library.
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union, Set
from urllib.parse import urljoin

import bioc
from bioc import pubtator
from exceptions import FormatNotSupportedException


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
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3/api/"
    
    # Mapowanie między parametrami API (małe litery) a typami w danych (wielkie litery)
    # na podstawie dokumentacji: https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/PubTatorCentral/api.html
    CONCEPT_TYPE_MAPPING = {
        "gene": "Gene",
        "disease": "Disease",
        "chemical": "Chemical",
        "species": "Species",
        "mutation": "Mutation",
        "cellline": "CellLine",
        # Dodatkowe typy obserwowane w danych
        "dnamutation": "DNAMutation",
        "tissue": "Tissue"
    }
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the PubTator client.
        
        Args:
            base_url: Optional custom API URL (defaults to the standard PubTator3 address)
            timeout: API response timeout limit in seconds
        """
        self.base_url = base_url if base_url is not None else self.BASE_URL
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, method: str = "GET", 
                     params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Any] = None) -> requests.Response:
        """
        Make a request to the PubTator API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method (GET, POST)
            params: URL query parameters
            data: Data to send in the request body (for POST)
            
        Returns:
            Response object from requests
            
        Raises:
            requests.RequestException: For errors in API communication
        """
        url = urljoin(self.base_url, endpoint)
        self.logger.debug(f"Making {method} request to {url}")
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params or {}, timeout=self.timeout)
            elif method.upper() == "POST":
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, params=params or {}, json=data, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response
        
        except requests.RequestException as e:
            self.logger.error(f"Error in communication with PubTator API: {e}")
            raise
    
    def _process_response(self, response: requests.Response, format_type: str) -> List[Any]:
        """
        Process the API response based on the requested format.
        
        Args:
            response: Response object from the API request
            format_type: Format of the data (biocjson, pubtator, biocxml)
            
        Returns:
            List of BioCDocument objects or a list containing the raw response
            
        Raises:
            FormatNotSupportedException: If the requested format is not fully supported
        """
        if format_type == "biocjson":
            data = response.json()
            collection = bioc.BioCCollection()
            collection.from_dict(data)
            return collection.documents
        elif format_type == "pubtator":
            # Process PubTator format using the bioc.pubtator module
            docs = pubtator.load(response.text.splitlines())
            return docs
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
            format_type: Format of returned data (biocjson, pubtator, biocxml)
            
        Returns:
            List of BioCDocument objects containing publication texts with annotations
        """
        endpoint = "v1/publications"
        payload = {
            "pmids": pmids,
            "format": format_type
        }
        
        if concepts:
            payload["concepts"] = concepts
            
        response = self._make_request(endpoint, method="POST", data=payload)
        return self._process_response(response, format_type)
    
    def get_publication_by_pmid(self, pmid: str, 
                               concepts: Optional[List[str]] = None, 
                               format_type: str = "biocjson") -> Any:
        """
        Retrieve a single publication by PubMed ID.
        
        Args:
            pmid: PubMed identifier
            concepts: List of concept types to include
            format_type: Format of returned data
            
        Returns:
            A BioCDocument object containing the publication text with annotations
        """
        docs = self.get_publications_by_pmids([pmid], concepts, format_type)
        return docs[0] if docs else None
    
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
        """
        endpoint = "v1/search"
        params: Dict[str, Any] = {
            "q": query,
            "format": format_type
        }
        
        if concepts:
            params["concepts"] = ",".join(concepts)
            
        response = self._make_request(endpoint, method="GET", params=params)
        return self._process_response(response, format_type)
    
    def extract_annotations_by_type(self, document: bioc.BioCDocument, 
                                  annotation_type: Union[str, List[str], Set[str]],
                                  include_type_in_result: bool = False) -> List[Dict[str, Any]]:
        """
        Extract annotations of specified type(s) from a BioC document.
        
        Args:
            document: BioC document with annotations
            annotation_type: Type or types of annotations to extract (e.g., "Gene", "Disease")
                           Can be a single string or a list/set of strings
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
                        "locations": [(loc.offset, loc.offset + loc.length) for loc in annotation.locations]
                    }
                    
                    if include_type_in_result:
                        anno_data["type"] = anno_type
                        
                    annotations.append(anno_data)
        
        return annotations
    
    # Kompatybilne metody dla zachowania wstecznej zgodności
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
        Extract genetic variant annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about variant annotations
        """
        return self.extract_annotations_by_type(document, ["Mutation", "DNAMutation"])
    
    def extract_tissue_specificity(self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract tissue specificity annotations from a BioC document.
        
        Args:
            document: BioC document with annotations
            
        Returns:
            List of dictionaries containing information about tissue annotations
        """
        tissues = self.extract_annotations_by_type(document, ["CellLine", "Tissue"], include_type_in_result=True)
        return tissues
    
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


if __name__ == "__main__":
    # Example usage of the PubTator client
    logging.basicConfig(level=logging.INFO)
    
    client = PubTatorClient()
    
    # Example of searching for publications
    try:
        results = client.search_publications("BRCA1 cancer")
        print(f"Found {len(results)} publications")
        
        if results:
            # Get details of the first publication
            doc = results[0]
            print(f"Title: {doc.passages[0].text if doc.passages else 'No data'}")
            
            # Sprawdź, jakie typy adnotacji są dostępne
            types = client.get_annotation_types(doc)
            print("Dostępne typy adnotacji:")
            for anno_type, count in types.items():
                print(f"  {anno_type}: {count} adnotacji")
            
            # Użyj generycznej metody
            genes = client.extract_annotations_by_type(doc, "Gene")
            diseases = client.extract_annotations_by_type(doc, "Disease")
            chemicals = client.extract_annotations_by_type(doc, "Chemical")
            
            print(f"Znaleziono: {len(genes)} genów, {len(diseases)} chorób, {len(chemicals)} związków chemicznych")
    
    except Exception as e:
        print(f"An error occurred: {e}") 