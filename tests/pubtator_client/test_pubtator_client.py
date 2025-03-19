"""
Unit tests for PubTatorClient.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from io import StringIO
import requests
import bioc
from bioc import pubtator, BioCDocument, BioCPassage, BioCAnnotation, BioCLocation, biocjson
from typing import List

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
            mock_response = Mock()
            mock_response.text = json.dumps(SAMPLE_BIOC_JSON)
            mock_response.json.return_value = SAMPLE_BIOC_JSON
            mock_post.return_value = mock_response
            mock_get.return_value = mock_response
            yield PubTatorClient()

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

# Initialization tests
def test_client_initialization():
    """Test client initialization with default parameters."""
    client = PubTatorClient()
    assert client.base_url == "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
    assert client.timeout == 30

def test_client_initialization_custom_url():
    """Test client initialization with custom URL."""
    custom_url = "https://custom.api.url/"
    client = PubTatorClient(base_url=custom_url)
    assert client.base_url == custom_url

def test_client_initialization_custom_timeout():
    """Test client initialization with custom timeout."""
    client = PubTatorClient(timeout=60)
    assert client.timeout == 60

# Concept type mapping tests
def test_concept_type_mapping():
    """Test concept type mapping."""
    client = PubTatorClient()
    assert client.CONCEPT_TYPE_MAPPING["gene"] == "Gene"
    assert client.CONCEPT_TYPE_MAPPING["disease"] == "Disease"
    assert client.CONCEPT_TYPE_MAPPING["chemical"] == "Chemical"

# Response handling tests
def test_process_biocjson_response(mock_response):
    """Test processing BioC JSON format response."""
    client = PubTatorClient()
    docs = client._process_response(mock_response, "biocjson")
    assert len(docs) == 1
    assert docs[0].id == "12345"
    assert len(docs[0].passages) == 1
    assert len(docs[0].passages[0].annotations) == 2

def test_process_pubtator_response(mock_pubtator_response):
    """Test processing PubTator format response."""
    client = PubTatorClient()
    docs = client._process_response(mock_pubtator_response, "pubtator")
    assert len(docs) == 1
    assert docs[0].pmid == "12345"  # PubTator uses pmid instead of id
    assert len(docs[0].annotations) == 2  # title + abstract

def test_process_unsupported_format():
    """Test handling unsupported format."""
    client = PubTatorClient()
    mock_response = Mock()
    with pytest.raises(FormatNotSupportedException):
        client._process_response(mock_response, "unsupported")

# Publication retrieval tests
@pytest.mark.parametrize("use_mock", [True, False])
def test_get_publications_by_pmids(client, use_mock):
    """Test retrieving publications by PMID."""
    pmids = ["12345"]
    docs = client.get_publications_by_pmids(pmids)
    assert len(docs) == 1
    assert docs[0].id == "12345"

@pytest.mark.parametrize("use_mock", [True, False])
def test_get_publications_by_pmids_with_concepts(client, use_mock):
    """Test retrieving publications by PMID with specified concepts."""
    pmids = ["12345"]
    concepts = ["gene", "disease"]
    docs = client.get_publications_by_pmids(pmids, concepts)
    assert len(docs) == 1

@pytest.mark.parametrize("use_mock", [True, False])
def test_get_publication_by_pmid(client, use_mock):
    """Test retrieving a single publication by PMID."""
    doc = client.get_publication_by_pmid("12345")
    assert doc.id == "12345"

@pytest.mark.parametrize("use_mock", [True, False])
def test_get_publication_by_pmid_not_found(client, use_mock):
    """Test retrieving non-existent publication."""
    with patch('requests.get') as mock_get:
        # Mock a 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {}
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        # Should return None instead of raising exception
        result = client.get_publication_by_pmid("99999")
        assert result is None

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
            client.get_publications_by_pmids(["12345"])
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
    assert doc.id == "12345"
    assert len(doc.passages) == 1
    assert len(doc.passages[0].annotations) == 1

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

def test_fetch_publications_by_pmids(client: PubTatorClient) -> None:
    """Test fetching publications by PMIDs."""
    pmids = ["12345"]
    publications: List[BioCDocument] = client.get_publications_by_pmids(pmids)  # type: ignore
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
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_response.text = "Not Found"
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        # Should return None for non-existent document
        result = client.get_publication_by_pmid("99999")
        assert result is None
        
    # Test handling of other HTTP errors
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_response.text = "Server Error"
        mock_get.return_value = mock_response
        
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
            client.get_publication_by_pmid("12345")
        assert "Connection timed out" in str(exc_info.value)
    
    # Test with custom timeout
    client = PubTatorClient(timeout=60)
    assert client.timeout == 60
    
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_BIOC_JSON
        mock_get.return_value = mock_response
        client.get_publication_by_pmid("12345")
