"""
Testy dla klasy LitVarEndpoint z modułu litvar_client.
"""
import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from src.litvar_client.litvar_endpoint import LitVarEndpoint


class TestLitVarEndpoint:
    """
    Testy dla klasy LitVarEndpoint.
    """
    
    def test_init(self):
        """Test inicjalizacji obiektu."""
        endpoint = LitVarEndpoint()
        assert endpoint.base_url == "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
    
    def test_init_custom_url(self):
        """Test inicjalizacji obiektu z niestandardowym URL."""
        custom_url = "https://example.com/api"
        endpoint = LitVarEndpoint(base_url=custom_url)
        assert endpoint.base_url == custom_url
    
    @patch('requests.get')
    def test_get_literature_by_variant(self, mock_get):
        """Test pobierania literatury według wariantu."""
        # Przygotowanie mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"rsid": "rs113488022", "pmids": ["12345678", "23456789"]}
            ]
        }
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_literature_by_variant("rs113488022")
        
        # Sprawdzenie, czy wywołanie zostało wykonane z odpowiednimi parametrami
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://www.ncbi.nlm.nih.gov/research/litvar2-api/variant/literature" in args[0]
        assert "id=rs113488022" in args[0]
        
        # Sprawdzenie zwróconych danych
        assert len(result) == 2
        assert "12345678" in result
        assert "23456789" in result
    
    @patch('requests.get')
    def test_get_literature_by_variant_empty_results(self, mock_get):
        """Test pobierania literatury dla wariantu bez wyników."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_literature_by_variant("nonexistent")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_get_literature_by_variant_no_results_key(self, mock_get):
        """Test pobierania literatury gdy brak klucza 'results' w odpowiedzi."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}  # Brak klucza 'results'
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_literature_by_variant("rs123456")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_get_literature_by_variant_error_status(self, mock_get):
        """Test obsługi błędu HTTP podczas pobierania literatury."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_literature_by_variant("rs123456")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_get_literature_by_variant_exception(self, mock_get):
        """Test obsługi wyjątku podczas pobierania literatury."""
        mock_get.side_effect = requests.exceptions.RequestException("Test error")
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_literature_by_variant("rs123456")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_get_variant_data(self, mock_get):
        """Test pobierania danych o wariancie."""
        # Przygotowanie mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "rs113488022",
                    "gene": "BRAF",
                    "hgvs": ["NM_004333.4:c.1799T>A", "NP_004324.2:p.Val600Glu"],
                    "diseases": ["melanoma", "colorectal cancer"]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_variant_data("rs113488022")
        
        # Sprawdzenie, czy wywołanie zostało wykonane z odpowiednimi parametrami
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://www.ncbi.nlm.nih.gov/research/litvar2-api/variant" in args[0]
        assert "id=rs113488022" in args[0]
        
        # Sprawdzenie zwróconych danych
        assert result["id"] == "rs113488022"
        assert result["gene"] == "BRAF"
        assert "NM_004333.4:c.1799T>A" in result["hgvs"]
        assert "melanoma" in result["diseases"]
    
    @patch('requests.get')
    def test_get_variant_data_empty_results(self, mock_get):
        """Test pobierania danych o wariancie bez wyników."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_variant_data("nonexistent")
        
        assert result == {}
    
    @patch('requests.get')
    def test_get_variant_data_error_status(self, mock_get):
        """Test obsługi błędu HTTP podczas pobierania danych o wariancie."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_variant_data("rs123456")
        
        assert result == {}
    
    @patch('requests.get')
    def test_get_variant_data_exception(self, mock_get):
        """Test obsługi wyjątku podczas pobierania danych o wariancie."""
        mock_get.side_effect = requests.exceptions.RequestException("Test error")
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_variant_data("rs123456")
        
        assert result == {}
    
    @patch('requests.get')
    def test_search_variants(self, mock_get):
        """Test wyszukiwania wariantów."""
        # Przygotowanie mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "rs113488022", "gene": "BRAF", "query": "V600E"},
                {"id": "rs113993960", "gene": "KRAS", "query": "G12D"}
            ]
        }
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.search_variants("V600E")
        
        # Sprawdzenie, czy wywołanie zostało wykonane z odpowiednimi parametrami
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://www.ncbi.nlm.nih.gov/research/litvar2-api/variant/autocomplete" in args[0]
        assert "query=V600E" in args[0]
        
        # Sprawdzenie zwróconych danych
        assert len(result) == 2
        assert result[0]["id"] == "rs113488022"
        assert result[1]["gene"] == "KRAS"
    
    @patch('requests.get')
    def test_search_variants_empty_results(self, mock_get):
        """Test wyszukiwania wariantów bez wyników."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.search_variants("nonexistent")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_search_variants_error_status(self, mock_get):
        """Test obsługi błędu HTTP podczas wyszukiwania wariantów."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        endpoint = LitVarEndpoint()
        result = endpoint.search_variants("V600E")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('requests.get')
    def test_search_variants_exception(self, mock_get):
        """Test obsługi wyjątku podczas wyszukiwania wariantów."""
        mock_get.side_effect = requests.exceptions.RequestException("Test error")
        
        endpoint = LitVarEndpoint()
        result = endpoint.search_variants("V600E")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @patch('src.litvar_client.litvar_endpoint.LitVarEndpoint.get_variant_data')
    def test_get_variant_by_coordinates(self, mock_get_variant_data):
        """Test pobierania wariantu według koordynatów."""
        # Przygotowanie mocka
        mock_get_variant_data.return_value = {
            "id": "rs113488022",
            "gene": "BRAF",
            "hgvs": ["NM_004333.4:c.1799T>A", "NP_004324.2:p.Val600Glu"],
            "diseases": ["melanoma"],
            "chromosome": "7",
            "position": "140453136"
        }
        
        endpoint = LitVarEndpoint()
        result = endpoint.get_variant_by_coordinates("chr7:140453136-140453136")
        
        # Sprawdzenie, czy wywołano odpowiednią metodę
        mock_get_variant_data.assert_called_once()
        
        # Sprawdzenie zwróconych danych
        assert result["id"] == "rs113488022"
        assert result["gene"] == "BRAF"
    
    def test_parse_coordinates(self):
        """Test parsowania koordynatów genomowych."""
        endpoint = LitVarEndpoint()
        
        # Test standardowych koordynatów
        chrom, pos = endpoint.parse_coordinates("chr7:140453136-140453136")
        assert chrom == "7"
        assert pos == "140453136"
        
        # Test koordynatów bez prefiksu 'chr'
        chrom, pos = endpoint.parse_coordinates("7:140453136-140453136")
        assert chrom == "7"
        assert pos == "140453136"
        
        # Test koordynatów z różnymi pozycjami start-end
        chrom, pos = endpoint.parse_coordinates("chr7:140453136-140453137")
        assert chrom == "7"
        assert pos == "140453136"  # Powinno zwrócić pierwszą pozycję
    
    def test_parse_coordinates_invalid(self):
        """Test parsowania nieprawidłowych koordynatów genomowych."""
        endpoint = LitVarEndpoint()
        
        # Test nieprawidłowego formatu
        with pytest.raises(ValueError):
            endpoint.parse_coordinates("invalid_format")
        
        # Test pustego ciągu znaków
        with pytest.raises(ValueError):
            endpoint.parse_coordinates("")
        
        # Test None
        with pytest.raises(ValueError):
            endpoint.parse_coordinates(None) 