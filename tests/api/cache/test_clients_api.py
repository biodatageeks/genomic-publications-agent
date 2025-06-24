"""
Testy integracyjne dla klientów API używających mechanizmu cache'a.

Te testy sprawdzają, czy klienci API (ClinVarClient, PubTatorClient) 
prawidłowo wykorzystują cache w rzeczywistych zapytaniach.
"""

import time
import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from src.api.clients.clinvar_client import ClinVarClient
from src.api.clients.pubtator_client import PubTatorClient
from src.api.cache.cache import DiskCache, MemoryCache


def create_mock_response(status_code=200, json_data=None, text=None, content=None):
    """Tworzy obiekt imitujący odpowiedź HTTP dla testów."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    
    if text is not None:
        mock_resp.text = text
    else:
        mock_resp.text = "{}"
        
    if content is not None:
        mock_resp.content = content
    else:
        mock_resp.content = b"{}"
        
    mock_resp.headers = {}
    mock_resp.url = "http://example.com/test"
        
    return mock_resp


@pytest.fixture
def temp_dir():
    """Fixture tworząca tymczasowy katalog dla testów."""
    dir_path = tempfile.mkdtemp(prefix="test_client_cache_")
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


class TestClinVarClientCache:
    """Testy dla cache'a ClinVarClient."""
    
    @patch('requests.get')
    def test_efetch_uses_cache(self, mock_get):
        """Test sprawdzający, czy ClinVarClient używa cache'a dla zapytań efetch."""
        # Tworzymy klienta z włączonym cache'em
        client = ClinVarClient(email="test@example.com", use_cache=True)
        
        # Konfiguracja mocka - zwracamy prosty XML
        xml_response = """<?xml version="1.0" ?>
        <VariationReport>
            <VariationName>Test Variant</VariationName>
            <VariationType>SNP</VariationType>
        </VariationReport>
        """
        mock_response = create_mock_response(text=xml_response)
        mock_get.return_value = mock_response
        
        # Wykonujemy dwa takie same zapytania
        params = {"db": "clinvar", "id": "12345", "retmode": "xml"}
        
        # Pierwszy request powinien trafić do API
        client._make_request("efetch.fcgi", params=params)
        
        # Drugi request powinien trafić do cache'a
        client._make_request("efetch.fcgi", params=params)
        
        # Sprawdzamy, czy wykonano tylko jedno faktyczne zapytanie HTTP
        assert mock_get.call_count == 1
    
    @patch('requests.get')
    def test_cache_invalidation(self, mock_get):
        """Test sprawdzający, czy invalidacja cache'a działa prawidłowo."""
        # Tworzymy klienta z włączonym cache'em
        client = ClinVarClient(email="test@example.com", use_cache=True)
        
        # Konfiguracja mocka - zwracamy prosty XML
        xml_response = """<?xml version="1.0" ?>
        <VariationReport>
            <VariationName>Test Variant</VariationName>
            <VariationType>SNP</VariationType>
        </VariationReport>
        """
        mock_response = create_mock_response(text=xml_response)
        mock_get.return_value = mock_response
        
        # Wykonujemy zapytanie
        params = {"db": "clinvar", "id": "12345", "retmode": "xml"}
        client._make_request("efetch.fcgi", params=params)
        
        # Upewniamy się, że cache jest zainicjalizowany
        if hasattr(client, 'cache') and client.cache is not None:
            # Ręczne wyczyszczenie cache'a
            client.cache.clear()
        
        # Wykonujemy drugie zapytanie - powinno trafić do API
        client._make_request("efetch.fcgi", params=params)
        
        # Sprawdzamy, czy wykonano dwa zapytania HTTP
        assert mock_get.call_count == 2
    
    @patch('requests.get')
    def test_disk_cache_persistence(self, mock_get, temp_dir):
        """Test sprawdzający, czy DiskCache w ClinVarClient zachowuje dane między instancjami."""
        # Konfiguracja mocka - zwracamy prosty XML
        xml_response = """<?xml version="1.0" ?>
        <VariationReport>
            <VariationName>Test Variant</VariationName>
            <VariationType>SNP</VariationType>
        </VariationReport>
        """
        mock_response = create_mock_response(text=xml_response)
        mock_get.return_value = mock_response
        
        # Tworzymy ręcznie DiskCache, który przekażemy klientom
        disk_cache = DiskCache(ttl=100, cache_dir=temp_dir)
        
        # Pierwszy klient z DiskCache
        client1 = ClinVarClient(
            email="test@example.com", 
            use_cache=True,
            cache_storage_type="disk"
        )
        # Ręczne ustawienie cache'a
        client1.cache = disk_cache
        
        # Wykonujemy zapytanie z pierwszym klientem
        params = {"db": "clinvar", "id": "12345", "retmode": "xml"}
        client1._make_request("efetch.fcgi", params=params)
        
        # Drugi klient z DiskCache
        client2 = ClinVarClient(
            email="test@example.com", 
            use_cache=True,
            cache_storage_type="disk"
        )
        # Ręczne ustawienie cache'a
        client2.cache = disk_cache
        
        # Wykonujemy to samo zapytanie z drugim klientem
        client2._make_request("efetch.fcgi", params=params)
        
        # Sprawdzamy, czy wykonano tylko jedno zapytanie HTTP
        assert mock_get.call_count == 1
    
    @patch('requests.get')
    def test_different_cache_ttl(self, mock_get):
        """Test sprawdzający, czy TTL cache'a działa prawidłowo."""
        # Tworzymy klienta z krótkim TTL
        client = ClinVarClient(
            email="test@example.com", 
            use_cache=True,
            cache_ttl=1  # 1 sekunda TTL
        )
        
        # Konfiguracja mocka - zwracamy prosty XML
        xml_response = """<?xml version="1.0" ?>
        <VariationReport>
            <VariationName>Test Variant</VariationName>
            <VariationType>SNP</VariationType>
        </VariationReport>
        """
        mock_response = create_mock_response(text=xml_response)
        mock_get.return_value = mock_response
        
        # Wykonujemy zapytanie
        params = {"db": "clinvar", "id": "12345", "retmode": "xml"}
        client._make_request("efetch.fcgi", params=params)
        
        # Czekamy na wygaśnięcie TTL
        time.sleep(1.1)
        
        # Wykonujemy to samo zapytanie - powinno trafić do API, bo cache wygasł
        client._make_request("efetch.fcgi", params=params)
        
        # Sprawdzamy, czy wykonano dwa zapytania HTTP
        assert mock_get.call_count == 2


class TestPubTatorClientCache:
    """Testy dla cache'a PubTatorClient."""
    
    @patch('requests.get')
    def test_get_uses_cache(self, mock_get):
        """Test sprawdzający, czy PubTatorClient używa cache'a dla zapytań GET."""
        # Tworzymy klienta z włączonym cache'em
        client = PubTatorClient(use_cache=True)
        
        # Konfiguracja mocka - zwracamy prosty JSON
        json_data = {
            "documents": [
                {
                    "id": "12345",
                    "passages": [
                        {
                            "text": "Test passage",
                            "annotations": []
                        }
                    ]
                }
            ]
        }
        mock_response = create_mock_response(json_data=json_data)
        mock_get.return_value = mock_response
        
        # Wykonujemy dwa takie same zapytania GET
        params = {"pmids": "12345", "concepts": "gene,disease"}
        
        # Pierwszy request powinien trafić do API
        client._make_request("publications", params=params)
        
        # Drugi request powinien trafić do cache'a
        client._make_request("publications", params=params)
        
        # Sprawdzamy, czy wykonano tylko jedno faktyczne zapytanie HTTP
        assert mock_get.call_count == 1
    
    @patch('requests.post')
    def test_post_not_cached(self, mock_post):
        """Test sprawdzający, czy zapytania POST nie są cache'owane."""
        # Tworzymy klienta z włączonym cache'em
        client = PubTatorClient(use_cache=True)
        
        # Konfiguracja mocka - zwracamy prosty JSON
        json_data = {"success": True, "id": "12345"}
        mock_response = create_mock_response(json_data=json_data)
        mock_post.return_value = mock_response
        
        # Wykonujemy dwa takie same zapytania POST
        params = {"text": "Test text", "concepts": "gene,disease"}
        
        response1 = client._make_request("text_annotation", method="POST", params=params)
        response2 = client._make_request("text_annotation", method="POST", params=params)
        
        # Sprawdzamy, czy wykonano dwa zapytania HTTP (POST nie powinno być cache'owane)
        assert mock_post.call_count == 2
    
    @patch('requests.get')
    def test_different_cache_ttl(self, mock_get):
        """Test sprawdzający, czy TTL cache'a działa prawidłowo."""
        # Tworzymy klienta z krótkim TTL
        client = PubTatorClient(
            use_cache=True,
            cache_ttl=1  # 1 sekunda TTL
        )
        
        # Konfiguracja mocka - zwracamy prosty JSON
        json_data = {
            "documents": [
                {
                    "id": "12345",
                    "passages": [
                        {
                            "text": "Test passage",
                            "annotations": []
                        }
                    ]
                }
            ]
        }
        mock_response = create_mock_response(json_data=json_data)
        mock_get.return_value = mock_response
        
        # Wykonujemy zapytanie
        params = {"pmids": "12345"}
        client._make_request("publications", params=params)
        
        # Czekamy na wygaśnięcie TTL
        time.sleep(1.1)
        
        # Wykonujemy to samo zapytanie - powinno trafić do API, bo cache wygasł
        client._make_request("publications", params=params)
        
        # Sprawdzamy, czy wykonano dwa zapytania HTTP
        assert mock_get.call_count == 2 