from src.pubtator_client.pubtator_client import PubTatorClient
import logging
import pytest
from unittest.mock import patch, Mock
import json

# Konfiguracja logowania
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
        mock_response.raise_for_status = Mock()  # Dodajemy mock metody raise_for_status
        mock_post.return_value = mock_response
        mock_get.return_value = mock_response
        yield PubTatorClient()

def test_relations(client):
    """Test metody get_relations"""
    print("\n=== Test metody get_relations ===")
    try:
        relations = client.get_relations(
            entity1="@GENE_JAK1",
            relation_type="negative_correlate",
            entity2="Chemical"
        )
        print(f"Liczba znalezionych relacji: {len(relations)}")
        print("Przykładowe relacje:")
        for relation in relations[:3]:  # Pokazujemy tylko pierwsze 3 relacje
            print(f"- {relation['source']} -> {relation['target']} ({relation['publications']} publikacji)")
    except Exception as e:
        print(f"Błąd: {e}")

def test_publications(client):
    """Test metody get_publications"""
    pmid = "30429607"
    
    # Test formatu biocjson
    print("\n=== Test metody get_publications (format biocjson) ===")
    try:
        biocjson_result = client.get_publications(pmid, format="biocjson")
        print("Odpowiedź w formacie biocjson:")
        print(str(biocjson_result)[:300] + "...")  # Pokazujemy tylko początek odpowiedzi
    except Exception as e:
        print(f"Błąd: {e}")

def test_get_publications_by_pmids(client):
    """Test metody get_publications_by_pmids"""
    pmids = ["30429607"]
    
    print("\n=== Test metody get_publications_by_pmids (format biocjson) ===")
    try:
        publications = client.get_publications_by_pmids(pmids, format_type="biocjson")
        print(f"Liczba publikacji: {len(publications)}")
        if publications:
            publication = publications[0]
            print(f"ID publikacji: {publication.id}")
            if hasattr(publication, 'passages') and publication.passages:
                print(f"Liczba fragmentów: {len(publication.passages)}")
                if publication.passages[0].annotations:
                    print(f"Liczba adnotacji w pierwszym fragmencie: {len(publication.passages[0].annotations)}")
    except Exception as e:
        print(f"Błąd: {e}")

def main():
    client = PubTatorClient()
    test_relations(client)
    test_publications(client)
    test_get_publications_by_pmids(client)

if __name__ == "__main__":
    main() 