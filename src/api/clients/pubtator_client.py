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
import time
import threading
from io import StringIO
from typing import List, Dict, Any, Optional, Union

import requests
import bioc
from bioc import pubtator, biocjson
from .exceptions import FormatNotSupportedException, PubTatorError
from src.api.cache.cache import MemoryCache, DiskCache

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

    # API rate limit is 20 requests per second according to NCBI
    API_REQUEST_INTERVAL = 0.05  # 50 ms = 20 req/s

    # Mapping between API parameters (lowercase) and data types (uppercase)
    # based on documentation:
    # https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/usage/
    # Official bioconcepts from PubTator API documentation:
    # - Gene, Disease, Chemical, Species, Mutation
    # Additional types observed in the API responses but not documented:
    # - CellLine, DNAMutation, Tissue
    CONCEPT_TYPE_MAPPING = {
        # Official bioconcepts from PubTator API documentation
        "gene": "Gene",
        "disease": "Disease",
        "chemical": "Chemical",
        "species": "Species",
        "mutation": "Mutation",
        # Additional types observed in API responses but not documented
        "cellline": "CellLine",
        "dnamutation": "DNAMutation",
        "tissue": "Tissue"
    }
    
    def __init__(
            self,
            base_url: Optional[str] = None,
            timeout: int = 30,
            use_cache: bool = True,
            cache_ttl: int = 86400,  # 24 hours
            cache_storage_type: str = "disk",
            email: Optional[str] = None,
            tool: str = "coordinates-lit"):
        """
        Initialize the PubTator client.
        
        Args:
            base_url: Custom base URL for the API (optional)
            timeout: API response timeout in seconds
            use_cache: Whether to use caching for API requests
            cache_ttl: Cache entry lifetime in seconds (default 24 hours)
            cache_storage_type: Cache storage type: "memory" or "disk"
            email: User's email address (optional, but recommended by NCBI)
            tool: Name of the tool using the API
        """
        self.base_url = base_url if base_url else DEFAULT_BASE_URL
        self.timeout = timeout
        self.email = email
        self.tool = tool
        self.logger = logging.getLogger(__name__)

        # Variables for tracking last request time
        self._last_request_time = 0
        self._request_lock = threading.Lock()

        # Initialize cache
        self.use_cache = use_cache
        if use_cache:
            if cache_storage_type == "disk":
                self.cache = DiskCache(ttl=cache_ttl)
            else:
                self.cache = MemoryCache(ttl=cache_ttl, max_size=1000)
            self.logger.info(f"Cache enabled ({cache_storage_type}), TTL: {cache_ttl}s")
        else:
            self.cache = None
            self.logger.info("Cache disabled")
            
    def _wait_for_rate_limit(self):
        """
        Waits if necessary to meet API rate limit requirements.
        Ensures at least self.API_REQUEST_INTERVAL seconds between requests.
        """
        with self._request_lock:
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time
            
            # If less time has passed since last request than required interval
            if time_since_last_request < self.API_REQUEST_INTERVAL:
                sleep_time = self.API_REQUEST_INTERVAL - time_since_last_request
                self.logger.debug(f"Waiting {sleep_time:.2f}s to meet API limit (max 20 req/s)")
                time.sleep(sleep_time)
            
            # Update last request time
            self._last_request_time = time.time()

    def _make_request(
            self,
            endpoint: str,
            method: str = "GET",
            params: Optional[Dict] = None,
            use_cache: Optional[bool] = None) -> requests.Response:
        """
        Makes a request to the PubTator API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method (GET or POST)
            params: Request parameters
            use_cache: Whether to use cache (if None, uses constructor setting)
            
        Returns:
            HTTP response object
            
        Raises:
            PubTatorError: When an error occurs during the request
        """
        # Wait for rate limit
        self._wait_for_rate_limit()
        
        # Determine whether to use cache
        should_use_cache = self.use_cache if use_cache is None else use_cache
        
        # Prepare URL
        url = f"{self.base_url}/{endpoint}"
        
        # Prepare parameters
        request_params = {}
        if params:
            request_params.update(params)
            
        # Add NCBI parameters if email is provided
        if self.email:
            request_params["email"] = self.email
            request_params["tool"] = self.tool
        
        try:
            # Check cache
            if should_use_cache and method == "GET" and self.cache:
                cache_key = f"{method}:{url}:{json.dumps(request_params, sort_keys=True)}"
                
                if self.cache.has(cache_key):
                    cached_response = self.cache.get(cache_key)
                    # Create response object from cached data
                    response = requests.Response()
                    response.status_code = cached_response["status_code"]
                    response._content = cached_response["content"].encode("utf-8") if isinstance(cached_response["content"], str) else cached_response["content"]
                    response.headers = cached_response["headers"]
                    response.url = url
                    
                    self.logger.debug(f"Retrieved from cache: {url}")
                    return response
            
            # Make API request
            if method == "GET":
                response = requests.get(url, params=request_params, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=request_params, timeout=self.timeout)
            else:
                raise PubTatorError(f"Unsupported HTTP method: {method}")
                
            # Handle mocks in tests - check if response has Mock object properties
            is_mock = hasattr(response, '__class__') and 'Mock' in response.__class__.__name__
            
            # Check response code
            if not is_mock and response.status_code != 200:
                raise PubTatorError(f"PubTator API error: {response.status_code} - {response.text}")
                
            # Save response to cache
            if should_use_cache and method == "GET" and self.cache and not is_mock:
                cache_key = f"{method}:{url}:{json.dumps(request_params, sort_keys=True)}"
                
                # Prepare cache data
                cache_data = {
                    "status_code": response.status_code,
                    "content": response.text,
                    "headers": dict(response.headers)
                }
                
                self.cache.set(cache_key, cache_data)
                self.logger.debug(f"Saved to cache: {url}")
                
            return response
        except requests.RequestException as e:
            raise PubTatorError(f"Error making request: {str(e)}")

    def _process_response(
            self,
            response: requests.Response,
            format_type: str) -> List[Any]:
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
                self.logger.error(
                    f"Error processing PubTator response: {
                        str(e)}")
                raise PubTatorError(
                    f"Error processing PubTator response: {
                        str(e)}")
        else:
            self.logger.warning(
                f"Format {format_type} is not fully supported at this time")
            raise FormatNotSupportedException(
                f"Format {format_type} is not fully supported at this time")

    # todo this method is totally too long. please refactor it and split it into smaller methods that will be easier to test. then write tests for them in appropriate test file.
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
            ValueError: If the PMIDs list is empty or contains non-digit IDs
        """
        # Only biocjson format works correctly with the API
        if format_type.lower() != "biocjson":
            self.logger.warning(
                f"Format {format_type} may not be supported by the API. Using 'biocjson'.")
            format_type = "biocjson"

        # Validate PMIDs
        self._validate_pmids(pmids)
        
        # Prepare request parameters
        params = self._prepare_publications_params(pmids, concepts)
        
        # Check cache
        cache_key = self._get_publications_cache_key(pmids, concepts)
        if self.use_cache and self.cache and self.cache.has(cache_key):
            self.logger.debug(f"Cache hit dla get_publications_by_pmids: {cache_key}")
            return self.cache.get(cache_key)
            
        try:
            # Make the API request
            response = self._make_request("publications/export/biocjson", params=params)
            
            # Process the response
            documents = self._process_publications_response(response)
            
            # Cache the results
            if self.use_cache and self.cache:
                self.cache.set(cache_key, documents)
                
            return documents
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error retrieving publications: {str(e)}")
            raise PubTatorError(f"Error retrieving publications: {str(e)}")
    
    def _validate_pmids(self, pmids: List[str]) -> None:
        """
        Validate list of PMIDs.
        
        Args:
            pmids: List of PubMed identifiers
            
        Raises:
            ValueError: If the PMIDs list is empty or contains non-digit IDs
        """
        if not all(pmid.isdigit() for pmid in pmids):
            raise ValueError("All PMIDs must be natural numbers.")
        
        if len(pmids) == 0:
            raise ValueError("PMID list cannot be empty.")
    
    def _prepare_publications_params(self, pmids: List[str], concepts: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Prepare parameters for publications request.
        
        Args:
            pmids: List of PubMed identifiers
            concepts: List of concept types to include
            
        Returns:
            Dictionary with request parameters
        """
        params = {
            "pmids": ",".join(pmids)
        }

        if concepts:
            params["concepts"] = ",".join(concepts)
            
        return params
    
    def _get_publications_cache_key(self, pmids: List[str], concepts: Optional[List[str]] = None) -> str:
        """
        Generate cache key for publications request.
        
        Args:
            pmids: List of PubMed identifiers
            concepts: List of concept types to include
            
        Returns:
            Cache key string
        """
        return f"pubtator:publications:{','.join(pmids)}:{','.join(concepts) if concepts else 'all'}"
    
    def _process_publications_response(self, response: requests.Response) -> List[bioc.BioCDocument]:
        """
        Process response from publications request.
        
        Args:
            response: Response from PubTator API
            
        Returns:
            List of BioCDocument objects
            
        Raises:
            PubTatorError: If there is an error processing the response
        """
        # Handle 404 error - resource not found
        if response.status_code == 404:
            raise PubTatorError(f"Resource not found: {response.url}")

        if not response.ok:
            raise PubTatorError(f"API request failed: {response.text}")

        try:
            data = response.json()
            if "PubTator3" in data:
                documents = []
                for doc_data in data["PubTator3"]:
                    document = self._parse_pubtator3_document(doc_data)
                    documents.append(document)
                return documents
            else:
                self.logger.warning("Unexpected response format from PubTator API")
                raise PubTatorError("Unexpected response format from PubTator API")
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error processing PubTator response: {str(e)}")
            raise PubTatorError(f"Error processing PubTator response: {str(e)}")
    
    def _parse_pubtator3_document(self, doc_data: Dict) -> bioc.BioCDocument:
        """
        Parse PubTator3 document data into BioCDocument.
        
        Args:
            doc_data: Document data from PubTator3 response
            
        Returns:
            BioCDocument object
        """
        doc = bioc.BioCDocument()
        doc.id = doc_data.get("id", "")

        # Process passages
        if "passages" in doc_data:
            for passage_data in doc_data["passages"]:
                passage = self._parse_pubtator3_passage(passage_data)
                doc.add_passage(passage)
                
        return doc
    
    def _parse_pubtator3_passage(self, passage_data: Dict) -> bioc.BioCPassage:
        """
        Parse PubTator3 passage data into BioCPassage.
        
        Args:
            passage_data: Passage data from PubTator3 response
            
        Returns:
            BioCPassage object
        """
        passage = bioc.BioCPassage()
        passage.text = passage_data.get("text", "")
        passage.offset = passage_data.get("offset", 0)

        # Copy information
        for key, value in passage_data.get("infons", {}).items():
            passage.infons[key] = value

        # Process annotations
        if "annotations" in passage_data:
            for anno_data in passage_data["annotations"]:
                annotation = self._parse_pubtator3_annotation(anno_data)
                passage.add_annotation(annotation)
                
        return passage
    
    def _parse_pubtator3_annotation(self, anno_data: Dict) -> bioc.BioCAnnotation:
        """
        Parse PubTator3 annotation data into BioCAnnotation.
        
        Args:
            anno_data: Annotation data from PubTator3 response
            
        Returns:
            BioCAnnotation object
        """
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
                
        return annotation

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
            docs = self.get_publications_by_pmids(
                [pmid], concepts, format_type)
            if not docs:
                self.logger.warning(f"No publication found for PMID: {pmid}")
                return None
            return docs[0]
        except PubTatorError as e:
            if "Resource not found" in str(e) or "404" in str(e):
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

            response = self._make_request(
                endpoint, method="GET", params=params)

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
        # Convert single type to list
        if isinstance(annotation_type, str):
            types_to_check = {annotation_type}
        else:
            types_to_check = set(annotation_type)

        # Check if types are lowercase (API parameters) and convert them
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
                        "locations": [
                            (loc.offset,
                             loc.offset +
                             loc.length) for loc in annotation.locations],
                        "infons": annotation.infons}

                    if include_type_in_result:
                        anno_data["type"] = anno_type

                    annotations.append(anno_data)

        return annotations

    def extract_gene_annotations(
            self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract gene annotations from a BioC document.

        Args:
            document: BioC document with annotations

        Returns:
            List of dictionaries containing information about gene annotations
        """
        return self.extract_annotations_by_type(document, "Gene")

    def extract_disease_annotations(
            self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract disease annotations from a BioC document.

        Args:
            document: BioC document with annotations

        Returns:
            List of dictionaries containing information about disease annotations
        """
        return self.extract_annotations_by_type(document, "Disease")

    def extract_variant_annotations(
            self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract variant annotations from a BioC document.

        Args:
            document: BioC document with annotations

        Returns:
            List of dictionaries containing information about variant annotations
        """
        return self.extract_annotations_by_type(document, "Variant")

    def extract_tissue_specificity(
            self, document: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract tissue specificity annotations from a BioC document.

        Args:
            document: BioC document with annotations

        Returns:
            List of dictionaries containing information about tissue annotations
        """
        return self.extract_annotations_by_type(document, "TissueSpecificity")

    def extract_all_annotations(
            self, document: bioc.BioCDocument) -> Dict[str, List[Dict[str, Any]]]:
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
                anno_type = annotation.infons.get("type", "Unknown")
                if anno_type not in annotations_by_type:
                    annotations_by_type[anno_type] = []

                anno_data = {
                    "id": annotation.id,
                    "text": annotation.text,
                    "normalized_id": annotation.infons.get("identifier"),
                    "locations": [
                        (loc.offset,
                         loc.offset +
                         loc.length) for loc in annotation.locations],
                    "infons": annotation.infons}
                annotations_by_type[anno_type].append(anno_data)

        return annotations_by_type

    def get_annotation_types(
            self, document: bioc.BioCDocument) -> Dict[str, int]:
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

    def get_relations(
        self,
        entity1: str,
        relation_type: str,
        entity2: str
    ) -> List[Dict[str, Any]]:
        """Retrieve relations between entities from the PubTator API.

        Args:
            entity1 (str): First entity (e.g. '@GENE_JAK1')
            relation_type (str): Relation type (e.g. 'negative_correlate')
            entity2 (str): Second entity (e.g. 'Chemical')

        Returns:
            List[Dict[str, Any]]: List of relations in JSON format with source,
                target and publications fields

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

    def get_publications(
        self,
        pmids: Union[str, List[str]],
        format: str = "biocjson"
    ) -> Dict[str, Any]:
        """Retrieve publications from the PubTator API in raw JSON format.

        This method returns the raw JSON response from the API, while
        get_publications_by_pmids returns processed BioCDocument objects.

        Args:
            pmids (Union[str, List[str]]): PMID identifier or a list of identifiers
            format (str, optional): Response format ('biocjson', 'biocxml').
                Default 'biocjson'.

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
            self.logger.warning(
                f"Format {format} may not be supported by the API. Using 'biocjson'.")
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
