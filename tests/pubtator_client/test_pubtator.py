from src.pubtator_client.pubtator_client import PubTatorClient
import logging
import pytest
from unittest.mock import patch, Mock
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@pytest.fixture
def client():
    """Fixture returning PubTatorClient instance."""
    # Use mocked client for unit tests
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = json.dumps(SAMPLE_BIOC_JSON)
        mock_response.json.return_value = SAMPLE_BIOC_JSON
        mock_response.raise_for_status = Mock()  # Add mock for raise_for_status method
        mock_post.return_value = mock_response
        mock_get.return_value = mock_response
        yield PubTatorClient()

def test_relations(client):
    """Test get_relations method"""
    print("\n=== Test get_relations method ===")
    try:
        relations = client.get_relations(
            entity1="@GENE_JAK1",
            relation_type="negative_correlate",
            entity2="Chemical"
        )
        print(f"Number of relations found: {len(relations)}")
        print("Sample relations:")
        for relation in relations[:3]:  # Show only first 3 relations
            print(f"- {relation['source']} -> {relation['target']} ({relation['publications']} publications)")
    except Exception as e:
        print(f"Error: {e}")

def test_publications(client):
    """Test get_publications method"""
    pmid = "30429607"
    
    # Test biocjson format
    print("\n=== Test get_publications method (biocjson format) ===")
    try:
        biocjson_result = client.get_publications(pmid, format="biocjson")
        print("Response in biocjson format:")
        print(str(biocjson_result)[:300] + "...")  # Show only beginning of the response
    except Exception as e:
        print(f"Error: {e}")

def test_get_publications_by_pmids(client):
    """Test get_publications_by_pmids method"""
    pmids = ["30429607"]
    
    print("\n=== Test get_publications_by_pmids method (biocjson format) ===")
    try:
        publications = client.get_publications_by_pmids(pmids, format_type="biocjson")
        print(f"Number of publications: {len(publications)}")
        if publications:
            publication = publications[0]
            print(f"Publication ID: {publication.id}")
            if hasattr(publication, 'passages') and publication.passages:
                print(f"Number of passages: {len(publication.passages)}")
                if publication.passages[0].annotations:
                    print(f"Number of annotations in first passage: {len(publication.passages[0].annotations)}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    client = PubTatorClient()
    test_relations(client)
    test_publications(client)
    test_get_publications_by_pmids(client)

if __name__ == "__main__":
    main() 