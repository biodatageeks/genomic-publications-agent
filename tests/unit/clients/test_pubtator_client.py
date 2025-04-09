"""
Unit tests for the PubTator client.
"""
import pytest
from unittest.mock import Mock, patch
from src.clients.pubtator.client import PubTatorClient

@pytest.fixture
def pubtator_client():
    """Create a PubTator client instance for testing."""
    return PubTatorClient(timeout=1)

@pytest.fixture
def mock_publication_data():
    """Sample publication data for testing."""
    return {
        "PubTator3": [{
            "id": "12345678",
            "passages": [
                {
                    "infons": {"type": "title"},
                    "text": "Test Title"
                },
                {
                    "infons": {"type": "abstract"},
                    "text": "Test Abstract"
                }
            ],
            "annotations": [
                {
                    "infons": {"type": "Gene", "identifier": "GENE:123"},
                    "text": "Test Gene",
                    "locations": [{"offset": 0, "length": 8}]
                }
            ]
        }]
    }

def test_get_publication_success(pubtator_client, mock_publication_data):
    """Test successful publication retrieval."""
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: mock_publication_data
        )
        
        result = pubtator_client.get_publication("12345678")
        assert result is not None
        assert result["id"] == "12345678"
        assert len(result["passages"]) == 2
        assert len(result["annotations"]) == 1

def test_get_publication_not_found(pubtator_client):
    """Test publication retrieval when not found."""
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"PubTator3": []}
        )
        
        result = pubtator_client.get_publication("99999999")
        assert result is None

def test_get_publication_error(pubtator_client):
    """Test publication retrieval with error."""
    with patch('requests.Session.get') as mock_get:
        mock_get.side_effect = Exception("Test error")
        
        result = pubtator_client.get_publication("12345678")
        assert result is None

def test_get_publications(pubtator_client, mock_publication_data):
    """Test multiple publications retrieval."""
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: mock_publication_data
        )
        
        results = pubtator_client.get_publications(["12345678", "87654321"])
        assert len(results) == 2
        assert results["12345678"] is not None
        assert results["87654321"] is None 