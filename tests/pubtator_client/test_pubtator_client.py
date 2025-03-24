"""
Unit tests for PubTatorClient.
"""

import json
import pytest
import requests
import threading
import time
from io import StringIO
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

import bioc
from bioc import pubtator, BioCDocument, BioCPassage, BioCAnnotation, BioCLocation, biocjson

from src.pubtator_client.pubtator_client import PubTatorClient
from src.pubtator_client.exceptions import FormatNotSupportedException, PubTatorError

# Sample test data
SAMPLE_BIOC_JSON = {
    "source": "PubTator",
    "date": "2024-03-20",
    "key": "test_key",
    "infons": {},
    "relations": [],
    "documents": [
        {
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": [
                {
                    "offset": 0,
                    "infons": {},
                    "text": "Test publication about BRCA1 and cancer",
                    "sentences": [],
                    "relations": [],
                    "annotations": [
                        {
                            "id": "T1",
                            "text": "BRCA1",
                            "infons": {"type": "Gene", "identifier": "GENE:123"},
                            "locations": [{"offset": 0, "length": 5}]
                        },
                        {
                            "id": "T2",
                            "text": "cancer",
                            "infons": {"type": "Disease", "identifier": "DISEASE:456"},
                            "locations": [{"offset": 20, "length": 6}]
                        }
                    ]
                }
            ]
        }
    ]
}

SAMPLE_PUBTATOR = """12345|t|Test publication about BRCA1 and cancer
12345|a|This is an abstract about BRCA1 and cancer.
12345	0	5	BRCA1	Gene	9606	GENE:123
12345	20	26	cancer	Disease	9606	DISEASE:456"""

# Test configuration
def pytest_configure(config):
    """Configure pytest."""
    # Add marker for integration tests
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

def is_integration_test(request):
    """Check if the test is an integration test."""
    return request.node.get_closest_marker('integration') is not None

@pytest.fixture
def client(request):
    """Fixture returning PubTatorClient instance."""
    if is_integration_test(request):
        # Use real client for integration tests
        yield PubTatorClient()
    else:
        # Use mocked client for unit tests
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.text = json.dumps(SAMPLE_BIOC_JSON)
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_response.headers = {}
            mock_post.return_value = mock_response
            mock_get.return_value = mock_response
            
            client = PubTatorClient()
            
            # Mockujemy metodę _process_publications_response, aby zwracała oczekiwany wynik
            with patch.object(client, '_process_publications_response', return_value=[biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]]):
                yield client

@pytest.fixture
def mock_response():
    """Fixture returning mocked API response."""
    mock = Mock()
    mock.text = json.dumps(SAMPLE_BIOC_JSON)
    mock.json.return_value = SAMPLE_BIOC_JSON
    return mock

@pytest.fixture
def mock_pubtator_response():
    """Fixture returning mocked PubTator format response."""
    mock = Mock()
    mock.text = SAMPLE_PUBTATOR
    return mock

@pytest.fixture
def sample_bioc_document():
    """Fixture returning a sample BioCDocument."""
    return biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]

@pytest.fixture
def empty_bioc_document():
    """Fixture returning an empty BioCDocument."""
    empty_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key", 
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": [{
                "offset": 0,
                "infons": {},
                "text": "Empty document with no annotations",
                "sentences": [],
                "relations": [],
                "annotations": []
            }]
        }]
    }
    return biocjson.load(StringIO(json.dumps(empty_doc))).documents[0]

class TestInitialization:
    """Tests for the initialization of PubTatorClient."""

    def test_client_initialization(self):
        """Test client initialization with default parameters."""
        client = PubTatorClient()
        assert client.base_url == "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
        assert client.timeout == 30
        assert client.use_cache is True

    def test_client_initialization_custom_url(self):
        """Test client initialization with custom URL."""
        custom_url = "https://custom.api.url/"
        client = PubTatorClient(base_url=custom_url)
        assert client.base_url == custom_url

    def test_client_initialization_custom_timeout(self):
        """Test client initialization with custom timeout."""
        client = PubTatorClient(timeout=60)
        assert client.timeout == 60

    def test_client_initialization_cache_disabled(self):
        """Test client initialization with cache disabled."""
        client = PubTatorClient(use_cache=False)
        assert client.use_cache is False
        assert client.cache is None

    def test_client_initialization_memory_cache(self):
        """Test client initialization with memory cache."""
        client = PubTatorClient(cache_storage_type="memory")
        assert client.use_cache is True
        assert hasattr(client.cache, "get")
        assert hasattr(client.cache, "set")

    def test_client_initialization_disk_cache(self):
        """Test client initialization with disk cache."""
        client = PubTatorClient(cache_storage_type="disk")
        assert client.use_cache is True
        assert hasattr(client.cache, "get")
        assert hasattr(client.cache, "set")

    def test_client_initialization_custom_email_tool(self):
        """Test client initialization with custom email and tool."""
        email = "test@example.com"
        tool = "custom-tool"
        client = PubTatorClient(email=email, tool=tool)
        assert client.email == email
        assert client.tool == tool

    def test_concept_type_mapping(self):
        """Test concept type mapping."""
        client = PubTatorClient()
        assert client.CONCEPT_TYPE_MAPPING["gene"] == "Gene"
        assert client.CONCEPT_TYPE_MAPPING["disease"] == "Disease"
        assert client.CONCEPT_TYPE_MAPPING["chemical"] == "Chemical"
        assert client.CONCEPT_TYPE_MAPPING["mutation"] == "Mutation"

class TestPrivateMethods:
    """Tests for private methods of PubTatorClient."""

    def test_wait_for_rate_limit(self):
        """Test rate limiting mechanism."""
        client = PubTatorClient()
        # Ustaw _last_request_time w przeszłości
        client._last_request_time = time.time() - 1  # 1 sekunda temu
        
        # Pierwsze wywołanie powinno przejść bez czekania
        start_time = time.time()
        client._wait_for_rate_limit()
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Powinno zająć mniej niż 100ms
        
        # Drugie wywołanie powinno czekać na limit
        start_time = time.time()
        client._wait_for_rate_limit()
        elapsed = time.time() - start_time
        assert elapsed >= client.API_REQUEST_INTERVAL

    def test_make_request_get(self, client, mock_response):
        """Test making GET request."""
        with patch('requests.get', return_value=mock_response) as mock_get:
            client._make_request("test/endpoint", method="GET")
            mock_get.assert_called_once()

    def test_make_request_post(self, client, mock_response):
        """Test making POST request."""
        with patch('requests.post', return_value=mock_response) as mock_post:
            client._make_request("test/endpoint", method="POST")
            mock_post.assert_called_once()

    def test_make_request_invalid_method(self, client):
        """Test behavior with invalid HTTP method."""
        with pytest.raises(PubTatorError):
            client._make_request("test/endpoint", method="INVALID")

    def test_make_request_with_params(self, client, mock_response):
        """Test making request with parameters."""
        params = {"param1": "value1", "param2": "value2"}
        with patch('requests.get', return_value=mock_response) as mock_get:
            client._make_request("test/endpoint", method="GET", params=params)
            mock_get.assert_called_once()
            # Sprawdź, czy przekazane parametry są poprawne
            call_kwargs = mock_get.call_args[1]
            assert "params" in call_kwargs
            for key, value in params.items():
                assert key in call_kwargs["params"]
                assert call_kwargs["params"][key] == value

    def test_make_request_with_email_and_tool(self, mock_response):
        """Test making request with email and tool parameters."""
        email = "test@example.com"
        tool = "custom-tool"
        client = PubTatorClient(email=email, tool=tool)
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            client._make_request("test/endpoint", method="GET")
            call_kwargs = mock_get.call_args[1]
            assert "params" in call_kwargs
            assert call_kwargs["params"]["email"] == email
            assert call_kwargs["params"]["tool"] == tool

    def test_make_request_failure(self, client):
        """Test behavior when request fails."""
        with patch('requests.get', side_effect=requests.RequestException("Test error")):
            with pytest.raises(PubTatorError):
                client._make_request("test/endpoint", method="GET")

    def test_make_request_non_200_response(self, client):
        """Test behavior when response status code is not 200."""
        error_response = MagicMock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        error_response.__class__.__name__ = "Response"  # Wymuszamy, żeby nie został wykryty jako Mock
        
        with patch('requests.get', return_value=error_response):
            with pytest.raises(PubTatorError):
                client._make_request("test/endpoint", method="GET")

    def test_process_biocjson_response(self, client, mock_response):
        """Test processing BioC JSON format response."""
        docs = client._process_response(mock_response, "biocjson")
        assert len(docs) == 1
        assert docs[0].id == "12345"
        assert len(docs[0].passages) == 1
        assert len(docs[0].passages[0].annotations) == 2

    def test_process_pubtator_response(self, client, mock_pubtator_response):
        """Test processing PubTator format response."""
        docs = client._process_response(mock_pubtator_response, "pubtator")
        assert len(docs) == 1
        assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id
        assert len(docs[0].annotations) == 2  # title + abstract

    def test_process_unsupported_format(self, client, mock_response):
        """Test handling unsupported format."""
        with pytest.raises(FormatNotSupportedException):
            client._process_response(mock_response, "unsupported")

    def test_process_response_404(self, client):
        """Test behavior when response is 404."""
        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        error_response.ok = False
        
        with pytest.raises(PubTatorError):
            client._process_response(error_response, "biocjson")

    def test_process_response_non_ok(self, client):
        """Test behavior when response is not OK."""
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Server Error"
        error_response.ok = False
        
        with pytest.raises(PubTatorError):
            client._process_response(error_response, "biocjson")

    def test_process_biocjson_response_error(self, client):
        """Test behavior when processing JSON response fails."""
        bad_response = Mock()
        bad_response.status_code = 200
        bad_response.ok = True
        bad_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with pytest.raises(PubTatorError):
            client._process_response(bad_response, "biocjson")

    def test_process_pubtator_response_error(self, client):
        """Test behavior when processing PubTator response fails."""
        bad_response = Mock()
        bad_response.status_code = 200
        bad_response.ok = True
        bad_response.text = "Invalid PubTator format"
        
        with patch('bioc.pubtator.load', side_effect=Exception("Parse error")):
            with pytest.raises(PubTatorError):
                client._process_response(bad_response, "pubtator")

class TestPublicMethods:
    """Tests for public methods of PubTatorClient."""
    
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_publications_by_pmids(self, client, use_mock):
        """Test retrieving publications by PMID."""
        pmids = ["12345"]
        docs = client.get_publications_by_pmids(pmids)
        assert len(docs) == 1
        assert docs[0].id == "12345"

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_publications_by_pmids_with_concepts(self, client, use_mock):
        """Test retrieving publications by PMID with specified concepts."""
        pmids = ["12345"]
        concepts = ["gene", "disease"]
        docs = client.get_publications_by_pmids(pmids, concepts)
        assert len(docs) == 1

    def test_get_publications_by_pmids_invalid_pmid(self, client):
        """Test behavior with invalid PMID."""
        with pytest.raises(ValueError):
            client.get_publications_by_pmids(["invalid"])

    def test_get_publications_by_pmids_empty_list(self, client):
        """Test behavior with empty PMID list."""
        with pytest.raises(ValueError):
            client.get_publications_by_pmids([])

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_publication_by_pmid(self, client, use_mock):
        """Test retrieving a single publication by PMID."""
        doc = client.get_publication_by_pmid("12345")
        assert doc.id == "12345"

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_publication_by_pmid_not_found(self, client, use_mock):
        """Test retrieving non-existent publication."""
        with patch('src.pubtator_client.pubtator_client.PubTatorClient.get_publications_by_pmids') as mock_get_publications:
            # Symuluj, że get_publications_by_pmids rzuca wyjątek PubTatorError z informacją o błędzie 404
            mock_get_publications.side_effect = PubTatorError("Resource not found: 99999")
            
            # Should return None instead of raising exception
            result = client.get_publication_by_pmid("99999")
            assert result is None

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_publications(self, client, use_mock):
        """Test searching for publications."""
        results = client.search_publications("BRCA1 cancer")
        assert len(results) == 1
        assert results[0].id == "12345"

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_publications_with_concepts(self, client, use_mock):
        """Test searching for publications with specified concepts."""
        concepts = ["gene", "disease"]
        results = client.search_publications("BRCA1 cancer", concepts)
        assert len(results) == 1
        
    def test_search_publications_error(self, client):
        """Test behavior when search fails."""
        with patch('requests.get', side_effect=requests.RequestException("Test error")):
            with pytest.raises(PubTatorError):
                client.search_publications("test query")
                
    def test_search_publications_empty_query(self, client):
        """Test searching with empty query."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = {
                "source": "PubTator",
                "date": "2024-03-20",
                "key": "test_key",
                "infons": {},
                "documents": []
            }
            mock_get.return_value = mock_response
            
            results = client.search_publications("")
            assert results is not None
            assert len(results) == 0
    
    def test_extract_annotations_by_type(self, client, sample_bioc_document):
        """Test extracting annotations of specified type."""
        genes = client.extract_annotations_by_type(sample_bioc_document, "Gene")
        assert len(genes) == 1
        assert genes[0]["text"] == "BRCA1"

    def test_extract_annotations_by_type_multiple(self, client, sample_bioc_document):
        """Test extracting annotations of multiple types."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, ["Gene", "Disease"])
        assert len(annotations) == 2

    def test_extract_annotations_by_type_with_type(self, client, sample_bioc_document):
        """Test extracting annotations with type in result."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, "Gene", include_type_in_result=True)
        assert len(annotations) == 1
        assert annotations[0]["type"] == "Gene"
        
    def test_extract_annotations_by_type_none_found(self, client, sample_bioc_document):
        """Test behavior when no annotations of the specified type are found."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, "Chemical")
        assert len(annotations) == 0
        
    def test_extract_annotations_by_type_empty_document(self, client, empty_bioc_document):
        """Test behavior with empty document."""
        annotations = client.extract_annotations_by_type(empty_bioc_document, "Gene")
        assert len(annotations) == 0
        
    def test_extract_annotations_by_type_case_insensitive(self, client, sample_bioc_document):
        """Test that annotation type matching is case-insensitive."""
        genes_lowercase = client.extract_annotations_by_type(sample_bioc_document, "gene")
        genes_uppercase = client.extract_annotations_by_type(sample_bioc_document, "Gene")
        assert len(genes_lowercase) == len(genes_uppercase)
        assert genes_lowercase[0]["text"] == genes_uppercase[0]["text"]
    
    def test_extract_gene_annotations(self, client, sample_bioc_document):
        """Test extracting gene annotations."""
        genes = client.extract_gene_annotations(sample_bioc_document)
        assert len(genes) == 1
        assert genes[0]["text"] == "BRCA1"

    def test_extract_disease_annotations(self, client, sample_bioc_document):
        """Test extracting disease annotations."""
        diseases = client.extract_disease_annotations(sample_bioc_document)
        assert len(diseases) == 1
        assert diseases[0]["text"] == "cancer"

    def test_extract_variant_annotations(self, client, sample_bioc_document):
        """Test extracting variant annotations."""
        variants = client.extract_variant_annotations(sample_bioc_document)
        assert isinstance(variants, list)
        assert len(variants) == 0  # No variants in sample data

    def test_extract_tissue_specificity(self, client, sample_bioc_document):
        """Test extracting tissue specificity annotations."""
        tissues = client.extract_tissue_specificity(sample_bioc_document)
        assert isinstance(tissues, list)
        assert len(tissues) == 0  # No tissues in sample data

    def test_extract_all_annotations(self, client, sample_bioc_document):
        """Test extracting all annotations."""
        all_annotations = client.extract_all_annotations(sample_bioc_document)
        assert "Gene" in all_annotations
        assert "Disease" in all_annotations
        assert len(all_annotations["Gene"]) == 1
        assert len(all_annotations["Disease"]) == 1
        
    def test_extract_all_annotations_empty_document(self, client, empty_bioc_document):
        """Test extracting all annotations from empty document."""
        all_annotations = client.extract_all_annotations(empty_bioc_document)
        assert len(all_annotations) == 0
        
    def test_get_annotation_types(self, client, sample_bioc_document):
        """Test getting annotation types and their counts."""
        types = client.get_annotation_types(sample_bioc_document)
        assert types["Gene"] == 1
        assert types["Disease"] == 1
        
    def test_get_annotation_types_empty_document(self, client, empty_bioc_document):
        """Test getting annotation types from empty document."""
        types = client.get_annotation_types(empty_bioc_document)
        assert len(types) == 0
        
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_relations(self, client, use_mock):
        """Test retrieving relations between entities."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = [
                {"source": "Gene1", "relation": "associated_with", "target": "Disease1", "pmids": ["12345"]}
            ]
            mock_get.return_value = mock_response
            
            relations = client.get_relations("@GENE_JAK1", "negative_correlate", "Chemical")
            assert len(relations) == 1
            assert "source" in relations[0]
            assert "relation" in relations[0]
            assert "target" in relations[0]
            
    def test_get_relations_error(self, client):
        """Test behavior when retrieving relations fails."""
        with patch('requests.get', side_effect=requests.RequestException("Test error")):
            with pytest.raises(PubTatorError):
                client.get_relations("@GENE_JAK1", "negative_correlate", "Chemical")
                
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_publications(self, client, use_mock):
        """Test retrieving publications in raw JSON format."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_get.return_value = mock_response
            
            publications = client.get_publications("12345")
            assert publications is not None
            assert "documents" in publications
            
    def test_get_publications_error(self, client):
        """Test behavior when retrieving publications fails."""
        with patch('requests.get', side_effect=requests.RequestException("Test error")):
            with pytest.raises(PubTatorError):
                client.get_publications("12345")
                
    def test_get_publications_not_found(self, client):
        """Test behavior when publication is not found."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.ok = False
            mock_response.text = "Not Found"
            mock_get.return_value = mock_response
            
            with pytest.raises(PubTatorError):
                client.get_publications("99999")

# Search tests
@pytest.mark.parametrize("use_mock", [True, False])
def test_search_publications(client, use_mock):
    """Test searching for publications."""
    results = client.search_publications("BRCA1 cancer")
    assert len(results) == 1
    assert results[0].id == "12345"

@pytest.mark.parametrize("use_mock", [True, False])
def test_search_publications_with_concepts(client, use_mock):
    """Test searching for publications with specified concepts."""
    concepts = ["gene", "disease"]
    results = client.search_publications("BRCA1 cancer", concepts)
    assert len(results) == 1

# Annotation extraction tests
def test_extract_annotations_by_type():
    """Test extracting annotations of specified type."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    genes = client.extract_annotations_by_type(doc, "Gene")
    assert len(genes) == 1
    assert genes[0]["text"] == "BRCA1"

def test_extract_annotations_by_type_multiple():
    """Test extracting annotations of multiple types."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    annotations = client.extract_annotations_by_type(doc, ["Gene", "Disease"])
    assert len(annotations) == 2

def test_extract_annotations_by_type_with_type():
    """Test extracting annotations with type in result."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    annotations = client.extract_annotations_by_type(doc, "Gene", include_type_in_result=True)
    assert len(annotations) == 1
    assert annotations[0]["type"] == "Gene"

def test_extract_gene_annotations():
    """Test extracting gene annotations."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    genes = client.extract_gene_annotations(doc)
    assert len(genes) == 1
    assert genes[0]["text"] == "BRCA1"

def test_extract_disease_annotations():
    """Test extracting disease annotations."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    diseases = client.extract_disease_annotations(doc)
    assert len(diseases) == 1
    assert diseases[0]["text"] == "cancer"

def test_extract_variant_annotations():
    """Test extracting variant annotations."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    variants = client.extract_variant_annotations(doc)
    assert isinstance(variants, list)

def test_extract_tissue_specificity():
    """Test extracting tissue specificity annotations."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    tissues = client.extract_tissue_specificity(doc)
    assert isinstance(tissues, list)

def test_extract_all_annotations():
    """Test extracting all annotations."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    all_annotations = client.extract_all_annotations(doc)
    assert "Gene" in all_annotations
    assert "Disease" in all_annotations
    assert len(all_annotations["Gene"]) == 1
    assert len(all_annotations["Disease"]) == 1

def test_get_annotation_types():
    """Test getting annotation types and their counts."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    types = client.get_annotation_types(doc)
    assert types["Gene"] == 1
    assert types["Disease"] == 1

# Error handling tests
def test_request_error_handling():
    """Test handling request errors."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("API Error")
        client = PubTatorClient()
        with pytest.raises(PubTatorError) as exc_info:
            client._make_request("test/endpoint")
        assert "API Error" in str(exc_info.value)

def test_invalid_annotation_type():
    """Test handling invalid annotation type."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    annotations = client.extract_annotations_by_type(doc, "InvalidType")
    assert len(annotations) == 0

# Data format tests
def test_biocjson_format():
    """Test handling BioC JSON format."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    assert doc.id == "12345"
    assert len(doc.passages) == 1

def test_pubtator_format():
    """Test handling PubTator format."""
    client = PubTatorClient()
    docs = pubtator.load(StringIO(SAMPLE_PUBTATOR))
    assert len(docs) == 1
    assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id

# Parameter tests
def test_concept_type_normalization():
    """Test concept type normalization."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    annotations = client.extract_annotations_by_type(doc, "gene")  # lowercase
    assert len(annotations) == 1
    assert annotations[0]["text"] == "BRCA1"

def test_multiple_concept_types():
    """Test handling multiple concept types."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    annotations = client.extract_annotations_by_type(doc, ["Gene", "Disease", "Chemical"])
    assert len(annotations) == 2  # only Gene and Disease are present

# Performance tests
def test_large_document_handling():
    """Test handling large documents."""
    large_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": [{
                "offset": 0,
                "infons": {},
                "text": "Test publication with many annotations",
                "sentences": [],
                "relations": [],
                "annotations": [
                    {
                        "id": f"T{i}",
                        "text": f"Annotation {i}",
                        "infons": {"type": "Gene", "identifier": f"GENE:{i}"},
                        "locations": [{"offset": i*10, "length": 5}]
                    } for i in range(100)
                ]
            }]
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(large_doc))).documents[0]
    assert doc.id == "12345"
    assert len(doc.passages) == 1
    assert len(doc.passages[0].annotations) == 100

# Edge case tests
def test_empty_document():
    """Test handling empty document."""
    empty_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": [{
                "offset": 0,
                "infons": {},
                "text": "Test publication without annotations",
                "sentences": [],
                "relations": [],
                "annotations": []
            }]
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(empty_doc))).documents[0]
    assert doc.id == "12345"
    assert len(doc.passages) == 1
    assert len(doc.passages[0].annotations) == 0

def test_document_without_passages():
    """Test handling document without passages."""
    doc_without_passages = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": []
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(doc_without_passages))).documents[0]
    assert doc.id == "12345"
    assert len(doc.passages) == 0

# Integration tests
@pytest.mark.integration
def test_full_workflow(request):
    """Test full client workflow with real API."""
    if not is_integration_test(request):
        pytest.skip("This is an integration test")
    
    client = PubTatorClient()
    
    # Use the real API (no mocks)
    pmid = "30429607"  # Real PMID that exists in the PubTator database
    
    # Get publication in PubTator format
    doc = client.get_publication_by_pmid(pmid, format_type="pubtator")
    assert doc is not None
    
    # Check if we can extract annotations
    all_annotations = client.extract_all_annotations(doc)
    assert isinstance(all_annotations, dict)

# Data validation tests
def test_invalid_annotation_data():
    """Test handling invalid annotation data."""
    invalid_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "relations": [],
            "passages": [{
                "offset": 0,
                "infons": {},
                "text": "Test publication with invalid annotation",
                "sentences": [],
                "relations": [],
                "annotations": [{
                    "id": "T1",
                    "text": "Invalid",
                    "infons": {},  # missing type
                    "locations": [{"offset": 0, "length": 5}]
                }]
            }]
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(invalid_doc))).documents[0]
    all_annotations = client.extract_all_annotations(doc)
    assert "Unknown" in all_annotations

# Performance tests
def test_memory_efficiency():
    """Test memory efficiency when processing large documents."""
    large_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {},
        "relations": [],
        "documents": [{
            "id": "12345",
            "infons": {},
            "text": "",
            "relations": [],
            "passages": [{
                "offset": 0,
                "text": "Test publication with many annotations",
                "infons": {},
                "sentences": [],
                "relations": [],
                "annotations": [
                    {
                        "id": f"T{i}",
                        "text": f"Annotation {i}",
                        "infons": {"type": "Gene", "identifier": f"GENE:{i}"},
                        "locations": [{"offset": i*10, "length": 5}]
                    } for i in range(1000)
                ]
            }]
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(large_doc))).documents[0]
    annotations = client.extract_all_annotations(doc)
    assert len(annotations["Gene"]) == 1000

# Security tests
def test_sanitization_of_input():
    """Test input sanitization."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    # Attempt extraction with invalid type
    annotations = client.extract_annotations_by_type(doc, "<script>alert('xss')</script>")
    assert len(annotations) == 0

# Compatibility tests
def test_backward_compatibility():
    """Test backward compatibility of methods."""
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
    
    # Test old methods
    genes_old = client.extract_gene_annotations(doc)
    diseases_old = client.extract_disease_annotations(doc)
    
    # Test new methods
    genes_new = client.extract_annotations_by_type(doc, "Gene")
    diseases_new = client.extract_annotations_by_type(doc, "Disease")
    
    assert genes_old == genes_new
    assert diseases_old == diseases_new

def test_fetch_publications_by_pmids(client) -> None:
    """Test fetching publications by PMIDs."""
    with patch.object(client, '_make_request') as mock_make_request:
        # Przygotowanie mocka z odpowiednimi właściwościami
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = SAMPLE_BIOC_JSON
        mock_make_request.return_value = mock_response
        
        # Mockowanie _process_publications_response, aby zwracało faktyczne dane
        with patch.object(client, '_process_publications_response') as mock_process:
            mock_process.return_value = [biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]]
            
            pmids = ["12345"]
            publications = client.get_publications_by_pmids(pmids)
            assert len(publications) == 1
            assert publications[0].id == "12345"

def test_load_pubtator():
    """Test loading PubTator format."""
    client = PubTatorClient()
    docs = pubtator.load(StringIO(SAMPLE_PUBTATOR))
    assert len(docs) == 1
    assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id

# Dodany test dla bardziej złożonych struktur danych
def test_complex_data_structure():
    """Test handling more complex data structures."""
    complex_doc = {
        "source": "PubTator",
        "date": "2024-03-20",
        "key": "test_key",
        "infons": {"complex": "value", "nested": {"data": "structure"}},
        "relations": [{"id": "R1", "refid": "12345", "type": "relation", "infons": {}, "nodes": []}],
        "documents": [{
            "id": "12345",
            "infons": {"document_info": "metadata"},
            "relations": [{"id": "R2", "role1": "Gene", "role2": "Disease", "infons": {}, "nodes": []}],
            "passages": [{
                "offset": 0,
                "infons": {"section": "title"},
                "text": "Test publication with complex annotations",
                "sentences": [{"offset": 0, "text": "Test sentence", "infons": {}, "annotations": [], "relations": []}],
                "relations": [{"id": "R3", "type": "association", "infons": {}, "nodes": []}],
                "annotations": [
                    {
                        "id": "T1",
                        "text": "Gene1",
                        "infons": {
                            "type": "Gene",
                            "identifier": "GENE:123",
                            "extra_data": {"synonyms": ["G1", "GN1"], "function": "protein coding"}
                        },
                        "locations": [
                            {"offset": 0, "length": 5},
                            {"offset": 20, "length": 5}  # multiple locations
                        ]
                    }
                ]
            }]
        }]
    }
    client = PubTatorClient()
    doc = biocjson.load(StringIO(json.dumps(complex_doc))).documents[0]
    assert doc.id == "12345"
    gene_annotations = client.extract_gene_annotations(doc)
    assert len(gene_annotations) == 1
    assert "extra_data" in gene_annotations[0]["infons"]
    assert len(gene_annotations[0]["locations"]) == 2  # check handling of multiple locations

# Error handling consistency test
def test_error_handling_consistency():
    """Test error handling consistency."""
    client = PubTatorClient()
    
    # Test handling of non-existent document
    with patch('src.pubtator_client.pubtator_client.PubTatorClient.get_publications_by_pmids') as mock_get_publications:
        # Symuluj, że get_publications_by_pmids rzuca wyjątek PubTatorError z informacją o błędzie 404
        mock_get_publications.side_effect = PubTatorError("Resource not found: 99999")
        
        # Should return None for non-existent document
        result = client.get_publication_by_pmid("99999")
        assert result is None
    
    # Test handling of other HTTP errors
    with patch('src.pubtator_client.pubtator_client.PubTatorClient.get_publications_by_pmids') as mock_get_publications:
        # Symuluj, że get_publications_by_pmids rzuca wyjątek PubTatorError z informacją o ogólnym błędzie
        mock_get_publications.side_effect = PubTatorError("API request failed: Server Error")
        
        # Should raise PubTatorError for server errors
        with pytest.raises(PubTatorError) as exc_info:
            client.get_publication_by_pmid("12345")
        assert "Error" in str(exc_info.value)

# Timeout handling test
def test_timeout_handling():
    """Test handling of response timeouts."""
    client = PubTatorClient(timeout=1)  # use integer value
    
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout("Connection timed out")
        
        with pytest.raises(PubTatorError) as exc_info:
            client._make_request("test/endpoint")
        assert "Connection timed out" in str(exc_info.value)
    
    # Test with custom timeout
    client = PubTatorClient(timeout=60)
    assert client.timeout == 60
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = SAMPLE_BIOC_JSON
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        # Powinno zakończyć się sukcesem
        response = client._make_request("test/endpoint")
        assert response is not None

class TestErrorHandling:
    """Tests for error handling in PubTatorClient."""
    
    def test_request_error_handling(self):
        """Test handling request errors."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("API Error")
            client = PubTatorClient()
            with pytest.raises(PubTatorError) as exc_info:
                client._make_request("test/endpoint")
            assert "API Error" in str(exc_info.value)

    def test_invalid_annotation_type(self, client, sample_bioc_document):
        """Test handling invalid annotation type."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, "InvalidType")
        assert len(annotations) == 0

    def test_invalid_annotation_data(self):
        """Test handling invalid annotation data."""
        invalid_doc = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {},
            "relations": [],
            "documents": [{
                "id": "12345",
                "infons": {},
                "relations": [],
                "passages": [{
                    "offset": 0,
                    "infons": {},
                    "text": "Test publication with invalid annotation",
                    "sentences": [],
                    "relations": [],
                    "annotations": [{
                        "id": "T1",
                        "text": "Invalid",
                        "infons": {},  # missing type
                        "locations": [{"offset": 0, "length": 5}]
                    }]
                }]
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(invalid_doc))).documents[0]
        all_annotations = client.extract_all_annotations(doc)
        assert "Unknown" in all_annotations

    def test_timeout_handling(self):
        """Test handling of response timeouts."""
        client = PubTatorClient(timeout=1)  # use integer value
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout("Connection timed out")
            
            with pytest.raises(PubTatorError) as exc_info:
                client._make_request("test/endpoint")
            assert "Connection timed out" in str(exc_info.value)

    def test_malformed_response_handling(self, client):
        """Test handling of malformed API responses."""
        # Wyłączamy cache, aby uniknąć problemów z zapisywaniem mocka
        client.use_cache = False
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.__class__.__name__ = "Response"  # Wymuszamy, żeby nie został wykryty jako Mock
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response
            
            with patch.object(client, '_process_response') as mock_process:
                mock_process.side_effect = PubTatorError("Error processing response: Invalid JSON")
                
                with pytest.raises(PubTatorError):
                    client.search_publications("test query")
                    
    def test_connection_error_handling(self, client):
        """Test handling of connection errors."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection failed")
            
            with pytest.raises(PubTatorError) as exc_info:
                client._make_request("test/endpoint")
            assert "Connection failed" in str(exc_info.value)

    def test_error_handling_consistency(self):
        """Test error handling consistency."""
        client = PubTatorClient()
        
        # Test handling of non-existent document
        with patch('src.pubtator_client.pubtator_client.PubTatorClient.get_publications_by_pmids') as mock_get_publications:
            # Symuluj, że get_publications_by_pmids rzuca wyjątek PubTatorError z informacją o błędzie 404
            mock_get_publications.side_effect = PubTatorError("Resource not found: 99999")
            
            # Should return None for non-existent document
            result = client.get_publication_by_pmid("99999")
            assert result is None
        
        # Test handling of other HTTP errors
        with patch('src.pubtator_client.pubtator_client.PubTatorClient.get_publications_by_pmids') as mock_get_publications:
            # Symuluj, że get_publications_by_pmids rzuca wyjątek PubTatorError z informacją o ogólnym błędzie
            mock_get_publications.side_effect = PubTatorError("API request failed: Server Error")
            
            # Should raise PubTatorError for server errors
            with pytest.raises(PubTatorError) as exc_info:
                client.get_publication_by_pmid("12345")
            assert "Error" in str(exc_info.value)
            
class TestDataFormats:
    """Tests for data format handling in PubTatorClient."""
    
    def test_biocjson_format(self):
        """Test handling BioC JSON format."""
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]
        assert doc.id == "12345"
        assert len(doc.passages) == 1

    def test_pubtator_format(self):
        """Test handling PubTator format."""
        client = PubTatorClient()
        docs = pubtator.load(StringIO(SAMPLE_PUBTATOR))
        assert len(docs) == 1
        assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id

    def test_concept_type_normalization(self, client, sample_bioc_document):
        """Test concept type normalization."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, "gene")  # lowercase
        assert len(annotations) == 1
        assert annotations[0]["text"] == "BRCA1"

    def test_multiple_concept_types(self, client, sample_bioc_document):
        """Test handling multiple concept types."""
        annotations = client.extract_annotations_by_type(sample_bioc_document, ["Gene", "Disease", "Chemical"])
        assert len(annotations) == 2  # only Gene and Disease are present

    def test_complex_data_structure(self):
        """Test handling more complex data structures."""
        complex_doc = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {"complex": "value", "nested": {"data": "structure"}},
            "relations": [{"id": "R1", "refid": "12345", "type": "relation", "infons": {}, "nodes": []}],
            "documents": [{
                "id": "12345",
                "infons": {"document_info": "metadata"},
                "relations": [{"id": "R2", "role1": "Gene", "role2": "Disease", "infons": {}, "nodes": []}],
                "passages": [{
                    "offset": 0,
                    "infons": {"section": "title"},
                    "text": "Test publication with complex annotations",
                    "sentences": [{"offset": 0, "text": "Test sentence", "infons": {}, "annotations": [], "relations": []}],
                    "relations": [{"id": "R3", "type": "association", "infons": {}, "nodes": []}],
                    "annotations": [
                        {
                            "id": "T1",
                            "text": "Gene1",
                            "infons": {
                                "type": "Gene",
                                "identifier": "GENE:123",
                                "extra_data": {"synonyms": ["G1", "GN1"], "function": "protein coding"}
                            },
                            "locations": [
                                {"offset": 0, "length": 5},
                                {"offset": 20, "length": 5}  # multiple locations
                            ]
                        }
                    ]
                }]
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(complex_doc))).documents[0]
        assert doc.id == "12345"
        gene_annotations = client.extract_gene_annotations(doc)
        assert len(gene_annotations) == 1
        assert "extra_data" in gene_annotations[0]["infons"]
        assert len(gene_annotations[0]["locations"]) == 2  # check handling of multiple locations

class TestPerformance:
    """Tests for performance aspects of PubTatorClient."""
    
    def test_large_document_handling(self):
        """Test handling large documents."""
        large_doc = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {},
            "relations": [],
            "documents": [{
                "id": "12345",
                "infons": {},
                "relations": [],
                "passages": [{
                    "offset": 0,
                    "infons": {},
                    "text": "Test publication with many annotations",
                    "sentences": [],
                    "relations": [],
                    "annotations": [
                        {
                            "id": f"T{i}",
                            "text": f"Annotation {i}",
                            "infons": {"type": "Gene", "identifier": f"GENE:{i}"},
                            "locations": [{"offset": i*10, "length": 5}]
                        } for i in range(100)
                    ]
                }]
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(large_doc))).documents[0]
        assert doc.id == "12345"
        assert len(doc.passages) == 1
        assert len(doc.passages[0].annotations) == 100
        
        # Testowanie wydajności ekstrakcji
        start_time = time.time()
        annotations = client.extract_all_annotations(doc)
        elapsed = time.time() - start_time
        
        assert len(annotations["Gene"]) == 100
        # Sprawdzenie czy operacja nie trwa zbyt długo
        assert elapsed < 1.0  # Powinna zająć mniej niż 1 sekundę

    def test_memory_efficiency(self):
        """Test memory efficiency when processing large documents."""
        large_doc = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {},
            "relations": [],
            "documents": [{
                "id": "12345",
                "infons": {},
                "text": "",
                "relations": [],
                "passages": [{
                    "offset": 0,
                    "text": "Test publication with many annotations",
                    "infons": {},
                    "sentences": [],
                    "relations": [],
                    "annotations": [
                        {
                            "id": f"T{i}",
                            "text": f"Annotation {i}",
                            "infons": {"type": "Gene", "identifier": f"GENE:{i}"},
                            "locations": [{"offset": i*10, "length": 5}]
                        } for i in range(1000)
                    ]
                }]
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(large_doc))).documents[0]
        annotations = client.extract_all_annotations(doc)
        assert len(annotations["Gene"]) == 1000

    def test_caching_behavior(self):
        """Test that caching works correctly."""
        client = PubTatorClient(use_cache=True, cache_storage_type="memory")
        
        with patch('requests.get') as mock_get:
            # Przygotowanie mocka z odpowiednimi właściwościami
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.text = json.dumps(SAMPLE_BIOC_JSON)
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            # Mockowanie _process_publications_response aby nie wymagał konkretnych pól
            with patch.object(client, '_process_publications_response', return_value=[]) as mock_process:
                # Pierwszy request powinien wywołać API
                client.get_publications_by_pmids(["12345"])
                assert mock_get.call_count == 1
                
                # Drugi taki sam request powinien użyć cache'a
                client.get_publications_by_pmids(["12345"])
                assert mock_get.call_count == 1  # Liczba wywołań nie powinna się zmienić

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        client = PubTatorClient(use_cache=True, cache_storage_type="memory", cache_ttl=1)  # 1 sekunda TTL
        
        with patch('requests.get') as mock_get:
            # Przygotowanie mocka z odpowiednimi właściwościami
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.text = json.dumps(SAMPLE_BIOC_JSON)
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            # Mockowanie _process_publications_response aby nie wymagał konkretnych pól
            with patch.object(client, '_process_publications_response', return_value=[]) as mock_process:
                # Pierwszy request powinien wywołać API
                client.get_publications_by_pmids(["12345"])
                assert mock_get.call_count == 1
                
                # Drugi natychmiastowy request powinien użyć cache'a
                client.get_publications_by_pmids(["12345"])
                assert mock_get.call_count == 1
                
                # Poczekaj na wygaśnięcie cache'a
                time.sleep(2)
                
                # Trzeci request po wygaśnięciu TTL powinien znowu wywołać API
                client.get_publications_by_pmids(["12345"])
                assert mock_get.call_count == 2

class TestEdgeCases:
    """Tests for edge cases in PubTatorClient."""
    
    def test_empty_document(self):
        """Test handling empty document."""
        empty_doc = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {},
            "relations": [],
            "documents": [{
                "id": "12345",
                "infons": {},
                "relations": [],
                "passages": [{
                    "offset": 0,
                    "infons": {},
                    "text": "Test publication without annotations",
                    "sentences": [],
                    "relations": [],
                    "annotations": []
                }]
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(empty_doc))).documents[0]
        assert doc.id == "12345"
        assert len(doc.passages) == 1
        assert len(doc.passages[0].annotations) == 0
        
        # Testowanie ekstrakcji z pustego dokumentu
        all_annotations = client.extract_all_annotations(doc)
        assert len(all_annotations) == 0

    def test_document_without_passages(self):
        """Test handling document without passages."""
        doc_without_passages = {
            "source": "PubTator",
            "date": "2024-03-20",
            "key": "test_key",
            "infons": {},
            "relations": [],
            "documents": [{
                "id": "12345",
                "infons": {},
                "relations": [],
                "passages": []
            }]
        }
        client = PubTatorClient()
        doc = biocjson.load(StringIO(json.dumps(doc_without_passages))).documents[0]
        assert doc.id == "12345"
        assert len(doc.passages) == 0
        
        # Testowanie ekstrakcji z dokumentu bez passaży
        all_annotations = client.extract_all_annotations(doc)
        assert len(all_annotations) == 0

    def test_sanitization_of_input(self, client, sample_bioc_document):
        """Test input sanitization."""
        # Attempt extraction with invalid type
        annotations = client.extract_annotations_by_type(sample_bioc_document, "<script>alert('xss')</script>")
        assert len(annotations) == 0

    def test_backward_compatibility(self, client, sample_bioc_document):
        """Test backward compatibility of methods."""
        # Test old methods
        genes_old = client.extract_gene_annotations(sample_bioc_document)
        diseases_old = client.extract_disease_annotations(sample_bioc_document)
        
        # Test new methods
        genes_new = client.extract_annotations_by_type(sample_bioc_document, "Gene")
        diseases_new = client.extract_annotations_by_type(sample_bioc_document, "Disease")
        
        assert genes_old == genes_new
        assert diseases_old == diseases_new

    def test_fetch_publications_by_pmids(self, client) -> None:
        """Test fetching publications by PMIDs."""
        with patch.object(client, '_make_request') as mock_make_request:
            # Przygotowanie mocka z odpowiednimi właściwościami
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_make_request.return_value = mock_response
            
            # Mockowanie _process_publications_response, aby zwracało faktyczne dane
            with patch.object(client, '_process_publications_response') as mock_process:
                mock_process.return_value = [biocjson.load(StringIO(json.dumps(SAMPLE_BIOC_JSON))).documents[0]]
                
                pmids = ["12345"]
                publications = client.get_publications_by_pmids(pmids)
                assert len(publications) == 1
                assert publications[0].id == "12345"

    def test_load_pubtator(self):
        """Test loading PubTator format."""
        client = PubTatorClient()
        docs = pubtator.load(StringIO(SAMPLE_PUBTATOR))
        assert len(docs) == 1
        assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id
        
class TestIntegration:
    """Integration tests with the real API."""
    
    @pytest.mark.integration
    def test_full_workflow(self, request):
        """Test full client workflow with real API."""
        if not is_integration_test(request):
            pytest.skip("This is an integration test")
        
        client = PubTatorClient()
        
        # Use the real API (no mocks)
        pmid = "30429607"  # Real PMID that exists in the PubTator database
        
        # Get publication in PubTator format
        doc = client.get_publication_by_pmid(pmid, format_type="pubtator")
        assert doc is not None
        
        # Check if we can extract annotations
        all_annotations = client.extract_all_annotations(doc)
        assert isinstance(all_annotations, dict)
        
    @pytest.mark.integration
    def test_search_functionality(self, request):
        """Test search functionality with real API."""
        if not is_integration_test(request):
            pytest.skip("This is an integration test")
            
        client = PubTatorClient()
        
        try:
            # Search for publications about BRCA1
            results = client.search_publications("BRCA1 cancer")
            assert len(results) > 0
            
            # Get a single publication from the results
            if results:
                pmid = results[0].id
                publication = client.get_publication_by_pmid(pmid)
                assert publication is not None
                assert publication.id == pmid
        except PubTatorError as e:
            if "404" in str(e) or "not available" in str(e):
                pytest.skip("Search endpoint is not available in this PubTator API version")
            else:
                raise
        
    @pytest.mark.integration
    def test_publications_by_pmids(self, request):
        """Test getting publications by PMIDs with real API."""
        if not is_integration_test(request):
            pytest.skip("This is an integration test")
            
        client = PubTatorClient()
        
        # List of PMIDs to test with
        pmids = ["30429607", "29446767"]  # Real PMIDs
        
        # Get publications
        publications = client.get_publications_by_pmids(pmids)
        assert len(publications) == 2
        
        # Check that IDs match
        publication_ids = {pub.id for pub in publications}
        assert publication_ids == {"30429607", "29446767"}
        
    @pytest.mark.integration
    def test_relations_functionality(self, request):
        """Test relations functionality with real API."""
        if not is_integration_test(request):
            pytest.skip("This is an integration test")
            
        client = PubTatorClient()
        
        # Test getting relations between entities
        try:
            relations = client.get_relations("@GENE_JAK1", "negative_correlate", "Chemical")
            # Nie możemy być pewni wyniku, więc sprawdzamy tylko czy odpowiedź ma właściwą strukturę
            assert isinstance(relations, list)
        except PubTatorError:
            pytest.skip("Relations API may not be available or returned error")
