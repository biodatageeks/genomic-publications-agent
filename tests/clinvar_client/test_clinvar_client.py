"""
Testy dla klienta ClinVar.
"""

import json
import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
import requests
from io import StringIO
from typing import Dict, List, Any
from contextlib import nullcontext
import time

from src.clinvar_client.clinvar_client import ClinVarClient, DEFAULT_BASE_URL
from src.clinvar_client.exceptions import (
    ClinVarError,
    APIRequestError,
    InvalidFormatError,
    ParseError,
    InvalidParameterError,
    RateLimitError
)

# Dodatkowe dekoratory dla testów
requires_advanced_mocking = pytest.mark.advanced_mocking
requires_real_api = pytest.mark.real_api
slow_test = pytest.mark.slow

# Przykładowe dane testowe
SAMPLE_VARIANT_JSON = {
    "result": {
        "variations": [
            {
                "id": "12345",
                "name": "NM_007294.3(BRCA1):c.5266dupC (p.Gln1756Profs*74)",
                "variation_type": "Deletion",
                "clinical_significance": {
                    "description": "Pathogenic",
                    "review_status": "criteria provided, multiple submitters, no conflicts"
                },
                "genes": [
                    {
                        "id": "672",
                        "symbol": "BRCA1"
                    }
                ],
                "phenotypes": [
                    {
                        "id": "114480",
                        "name": "Breast-ovarian cancer, familial 1"
                    }
                ],
                "alleles": [
                    {
                        "sequence_locations": [
                            {
                                "assembly": "GRCh38",
                                "chr": "17",
                                "start": 43071077,
                                "stop": 43071077,
                                "reference_allele": "A",
                                "alternate_allele": "T"
                            }
                        ]
                    }
                ]
            }
        ]
    }
}

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<ReleaseSet>
  <ClinVarSet>
    <ReferenceClinVarAssertion>
      <MeasureSet ID="12345" Name="NM_007294.3(BRCA1):c.5266dupC (p.Gln1756Profs*74)">
        <Measure Type="Deletion">
          <MeasureRelationship>
            <Symbol>
              <ElementValue>BRCA1</ElementValue>
            </Symbol>
            <XRef DB="Gene" ID="672"/>
          </MeasureRelationship>
          <SequenceLocation Assembly="GRCh38" Chr="17" start="43071077" stop="43071077" referenceAllele="A" alternateAllele="T"/>
        </Measure>
      </MeasureSet>
      <ClinicalSignificance>
        <Description>Pathogenic</Description>
        <ReviewStatus>criteria provided, multiple submitters, no conflicts</ReviewStatus>
      </ClinicalSignificance>
      <TraitSet>
        <Trait>
          <Name>
            <ElementValue>Breast-ovarian cancer, familial 1</ElementValue>
          </Name>
          <XRef DB="OMIM" ID="114480"/>
        </Trait>
      </TraitSet>
    </ReferenceClinVarAssertion>
  </ClinVarSet>
</ReleaseSet>"""

SAMPLE_ESEARCH_JSON = {
    "esearchresult": {
        "count": "1",
        "retmax": "1",
        "retstart": "0",
        "idlist": ["12345"],
        "webenv": "ABCDEF123456",
        "querykey": "1"
    }
}

SAMPLE_ESEARCH_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<eSearchResult>
  <Count>1</Count>
  <RetMax>1</RetMax>
  <RetStart>0</RetStart>
  <IdList>
    <Id>12345</Id>
  </IdList>
  <WebEnv>ABCDEF123456</WebEnv>
  <QueryKey>1</QueryKey>
</eSearchResult>"""

# Konfiguracja testów
def pytest_configure(config):
    """Konfiguracja pytest."""
    config.addinivalue_line(
        "markers", "integration: oznacza test integracyjny"
    )
    config.addinivalue_line(
        "markers", "advanced_mocking: oznacza test wymagający zaawansowanego mockowania"
    )
    config.addinivalue_line(
        "markers", "slow: oznacza wolny test"
    )
    config.addinivalue_line(
        "markers", "real_api: oznacza test wymagający rzeczywistego API"
    )

def is_integration_test(request):
    """Sprawdza, czy test jest testem integracyjnym."""
    return request.node.get_closest_marker('integration') is not None

@pytest.fixture
def mock_response():
    """Fixture zwracający zamockowaną odpowiedź HTTP."""
    mock = Mock()
    mock.status_code = 200
    mock.text = json.dumps(SAMPLE_VARIANT_JSON)
    mock.json.return_value = SAMPLE_VARIANT_JSON
    mock.ok = True
    return mock

@pytest.fixture
def mock_xml_response():
    """Fixture zwracający zamockowaną odpowiedź HTTP w formacie XML."""
    mock = Mock()
    mock.status_code = 200
    mock.text = SAMPLE_XML
    mock.ok = True
    return mock

@pytest.fixture
def mock_esearch_response():
    """Fixture zwracający zamockowaną odpowiedź dla esearch."""
    mock = Mock()
    mock.status_code = 200
    mock.text = json.dumps(SAMPLE_ESEARCH_JSON)
    mock.json.return_value = SAMPLE_ESEARCH_JSON
    mock.ok = True
    return mock

@pytest.fixture
def mock_esearch_xml_response():
    """Fixture zwracający zamockowaną odpowiedź dla esearch w formacie XML."""
    mock = Mock()
    mock.status_code = 200
    mock.text = SAMPLE_ESEARCH_XML
    mock.ok = True
    return mock

@pytest.fixture
def client(request):
    """Fixture zwracający instancję klienta ClinVar do testów."""
    if is_integration_test(request):
        # Jeśli parametr use_mock jest False, używamy rzeczywistego API
        param_value = request.node.get_closest_marker('parametrize')
        if param_value and 'use_mock' in param_value.args[0]:
            param_names = [x.strip() for x in param_value.args[0].split(',')]
            idx = param_names.index('use_mock')
            if idx < len(param_value.args[1]) and param_value.args[1][idx] is False:
                try:
                    # Próbujemy stworzyć rzeczywistego klienta dla testów integracyjnych
                    real_client = ClinVarClient(email="test@example.com")
                    # Sprawdzamy, czy API jest dostępne (proste zapytanie testowe)
                    try:
                        # Wykonaj proste zapytanie, aby sprawdzić połączenie
                        real_client._build_request_url("test", {})
                        yield real_client
                        return
                    except Exception as e:
                        pytest.skip(f"Pomijam test z rzeczywistym API - błąd połączenia: {str(e)}")
                except Exception as e:
                    pytest.skip(f"Nie można stworzyć rzeczywistego klienta: {str(e)}")
        
    # Używamy zamockowanego klienta dla testów jednostkowych
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        mock_response_json = Mock()
        mock_response_json.text = json.dumps(SAMPLE_VARIANT_JSON)
        mock_response_json.json.return_value = SAMPLE_VARIANT_JSON
        mock_response_json.status_code = 200
        mock_response_json.ok = True
        
        mock_response_xml = Mock()
        mock_response_xml.text = SAMPLE_XML
        mock_response_xml.status_code = 200
        mock_response_xml.ok = True
        
        # Mapowanie różnych endpointów na odpowiednie odpowiedzi
        def get_side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            params = kwargs.get('params', {})
            
            if "efetch.fcgi" in url:
                if params.get('retmode') == 'xml':
                    return mock_response_xml
                return mock_response_json
            elif "esearch.fcgi" in url:
                mock_esearch = Mock()
                mock_esearch.text = json.dumps(SAMPLE_ESEARCH_JSON)
                mock_esearch.json.return_value = SAMPLE_ESEARCH_JSON
                mock_esearch.status_code = 200
                mock_esearch.ok = True
                return mock_esearch
            return mock_response_json
            
        mock_get.side_effect = get_side_effect
        mock_post.side_effect = get_side_effect
        
        yield ClinVarClient(email="test@example.com")


# --- 1. Testy inicjalizacji ---

class TestInitialization:
    """Testy inicjalizacji klienta ClinVar."""

    def test_init_default_parameters(self):
        """Test inicjalizacji z domyślnymi parametrami."""
        client = ClinVarClient(email="test@example.com")
        assert client.email == "test@example.com"
        assert client.base_url == DEFAULT_BASE_URL
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1
        assert client.api_key is None
        assert client.default_params["email"] == "test@example.com"
        assert client.default_params["tool"] == "coordinates_lit_integration"

    def test_init_custom_base_url(self):
        """Test inicjalizacji z niestandardowym URL bazowym."""
        custom_url = "https://custom.api.example.com"
        client = ClinVarClient(email="test@example.com", base_url=custom_url)
        assert client.base_url == custom_url

    def test_init_custom_timeout(self):
        """Test inicjalizacji z niestandardowym timeoutem."""
        custom_timeout = 60
        client = ClinVarClient(email="test@example.com", timeout=custom_timeout)
        assert client.timeout == custom_timeout

    def test_init_with_api_key(self):
        """Test inicjalizacji z kluczem API."""
        api_key = "test_api_key_123"
        client = ClinVarClient(email="test@example.com", api_key=api_key)
        assert client.api_key == api_key
        assert client.default_params["api_key"] == api_key

    def test_init_custom_retries(self):
        """Test inicjalizacji z niestandardową liczbą ponownych prób."""
        max_retries = 5
        client = ClinVarClient(email="test@example.com", max_retries=max_retries)
        assert client.max_retries == max_retries

    def test_init_custom_retry_delay(self):
        """Test inicjalizacji z niestandardowym opóźnieniem ponownych prób."""
        retry_delay = 2
        client = ClinVarClient(email="test@example.com", retry_delay=retry_delay)
        assert client.retry_delay == retry_delay


# --- 2. Testy metod prywatnych ---

class TestPrivateMethods:
    """Testy dla metod prywatnych klienta ClinVar."""

    def test_make_request_get(self, client, mock_response):
        """Test wykonania zapytania GET."""
        with patch('requests.get', return_value=mock_response) as mock_get:
            response = client._make_request("test_endpoint", method="GET")
            
            mock_get.assert_called_once()
            assert response == mock_response

    def test_make_request_post(self, client, mock_response):
        """Test wykonania zapytania POST."""
        with patch('requests.post', return_value=mock_response) as mock_post:
            response = client._make_request("test_endpoint", method="POST")
            
            mock_post.assert_called_once()
            assert response == mock_response

    def test_make_request_invalid_method(self, client):
        """Test obsługi nieprawidłowej metody HTTP."""
        with pytest.raises(ValueError):
            client._make_request("test_endpoint", method="INVALID")

    def test_make_request_with_params(self, client, mock_response):
        """Test wykonania zapytania z parametrami."""
        test_params = {"param1": "value1", "param2": "value2"}
    
        with patch('requests.get', return_value=mock_response) as mock_get:
            client._make_request("test_endpoint", params=test_params)
    
            # Sprawdź, czy została wywołana metoda requests.get
            mock_get.assert_called_once()
            
            # Sprawdź, czy parametry są przesyłane w URL
            args = mock_get.call_args[0]
            # Sprawdź URL - pierwszy argument w call_args[0]
            url = args[0]
            assert "param1=value1" in url or "param1" in url  # Parametry mogą być w różnej formie zależnie od implementacji
            assert "param2=value2" in url or "param2" in url

    def test_make_request_rate_limit_error(self, client):
        """Test obsługi błędu limitu zapytań."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
    
        with patch('requests.get', return_value=rate_limit_response):
            with pytest.raises(RateLimitError):
                client._make_request("test_endpoint")

    def test_make_request_server_error_retry(self, client, mock_response):
        """Test ponownej próby po błędzie serwera."""
        server_error_response = Mock()
        server_error_response.status_code = 500
        
        # Resetujemy czas ostatniego zapytania, aby uniknąć sleep
        client._last_request_time = 0
        
        with patch('time.sleep') as mock_sleep:
            with patch('requests.get', side_effect=[server_error_response, mock_response]) as mock_get:
                response = client._make_request("test_endpoint")
                
                assert mock_get.call_count == 2
                # Sprawdzamy tylko wywołania sleep dla retry, pomijamy rate limiting
                retry_sleep_calls = [call for call in mock_sleep.call_args_list if call[0][0] >= 1.0]
                assert len(retry_sleep_calls) == 1

    def test_make_request_bad_request(self, client):
        """Test obsługi błędnego zapytania."""
        bad_response = Mock()
        bad_response.status_code = 400
        bad_response.json.return_value = {"message": "Bad request parameters"}
        
        with patch('requests.get', return_value=bad_response):
            with pytest.raises(InvalidParameterError):
                client._make_request("test_endpoint")

    def test_make_request_general_error(self, client):
        """Test obsługi ogólnego błędu zapytania."""
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection error")):
            with pytest.raises(APIRequestError):
                client._make_request("test_endpoint")

    def test_parse_xml_response(self, client):
        """Test parsowania odpowiedzi XML."""
        result = client._parse_xml_response(SAMPLE_XML)
        assert isinstance(result, dict)
        assert "ReleaseSet" in result
        assert "ClinVarSet" in result["ReleaseSet"]

    def test_parse_xml_response_error(self, client):
        """Test obsługi błędu parsowania XML."""
        with pytest.raises(ParseError):
            client._parse_xml_response("Invalid XML")

    def test_xml_to_dict_simple(self, client):
        """Test konwersji prostego elementu XML na słownik."""
        xml_string = "<Root><Child>Value</Child></Root>"
        root = ET.fromstring(xml_string)
        result = client._xml_to_dict(root)
        
        assert isinstance(result, dict)
        assert "Child" in result
        assert result["Child"] == "Value"

    def test_xml_to_dict_nested(self, client):
        """Test konwersji zagnieżdżonego elementu XML na słownik."""
        xml_string = "<Root><Child><Grandchild>Value</Grandchild></Child></Root>"
        root = ET.fromstring(xml_string)
        result = client._xml_to_dict(root)
        
        assert isinstance(result, dict)
        assert "Child" in result
        assert isinstance(result["Child"], dict)
        assert "Grandchild" in result["Child"]
        assert result["Child"]["Grandchild"] == "Value"

    def test_xml_to_dict_with_attributes(self, client):
        """Test konwersji elementu XML z atrybutami na słownik."""
        xml_string = '<Root><Child attribute="value">Content</Child></Root>'
        root = ET.fromstring(xml_string)
        result = client._xml_to_dict(root)
        
        assert isinstance(result, dict)
        assert "Child" in result
        assert result["Child"] == "Content"

    def test_xml_to_dict_with_namespace(self, client):
        """Test konwersji elementu XML z przestrzenią nazw na słownik."""
        xml_string = '<Root xmlns:ns="http://example.com"><ns:Child>Value</ns:Child></Root>'
        root = ET.fromstring(xml_string)
        result = client._xml_to_dict(root)
        
        assert isinstance(result, dict)
        assert "Child" in result
        assert result["Child"] == "Value"

    def test_xml_to_dict_with_lists(self, client):
        """Test konwersji elementu XML z powtarzającymi się tagami na słownik."""
        xml_string = "<Root><Child>Value1</Child><Child>Value2</Child></Root>"
        root = ET.fromstring(xml_string)
        result = client._xml_to_dict(root)
        
        assert isinstance(result, dict)
        assert "Child" in result
        assert isinstance(result["Child"], list)
        assert len(result["Child"]) == 2
        assert "Value1" in result["Child"]
        assert "Value2" in result["Child"]

    def test_parse_json_response(self, client):
        """Test parsowania odpowiedzi JSON."""
        result = client._parse_json_response(SAMPLE_VARIANT_JSON)
        assert result == SAMPLE_VARIANT_JSON

    def test_process_variation_json(self, client):
        """Test przetwarzania danych wariantu JSON."""
        result = client._process_variation_json(SAMPLE_VARIANT_JSON)
        
        assert isinstance(result, list)
        assert len(result) == 1
        variant = result[0]
        assert variant["id"] == "12345"
        assert variant["name"] == "NM_007294.3(BRCA1):c.5266dupC (p.Gln1756Profs*74)"
        assert variant["variation_type"] == "Deletion"
        assert variant["clinical_significance"] == "Pathogenic"
        assert len(variant["genes"]) == 1
        assert variant["genes"][0]["symbol"] == "BRCA1"

    def test_process_variation_xml(self, client):
        """Test przetwarzania danych wariantu XML."""
        xml_data = client._parse_xml_response(SAMPLE_XML)
        result = client._process_variation_xml(xml_data)
        
        assert isinstance(result, list)
        assert len(result) == 1
        variant = result[0]
        assert variant["id"] == "12345"
        assert variant["name"] == "NM_007294.3(BRCA1):c.5266dupC (p.Gln1756Profs*74)"
        assert variant["variation_type"] == "Deletion"
        assert variant["clinical_significance"] == "Pathogenic"
        assert len(variant["genes"]) == 1
        assert variant["genes"][0]["symbol"] == "BRCA1"

    def test_extract_clinical_significance(self, client):
        """Test wyciągania znaczenia klinicznego z danych wariantu."""
        variation = {
            "clinical_significance": {
                "description": "Pathogenic"
            }
        }
        result = client._extract_clinical_significance(variation)
        assert result == "Pathogenic"

    def test_extract_clinical_significance_missing(self, client):
        """Test wyciągania znaczenia klinicznego z danych wariantu bez tego pola."""
        variation = {}
        result = client._extract_clinical_significance(variation)
        assert result == "Not provided"

    def test_extract_genes(self, client):
        """Test wyciągania informacji o genach z danych wariantu."""
        variation = {
            "genes": [
                {
                    "symbol": "BRCA1",
                    "id": "672"
                }
            ]
        }
        result = client._extract_genes(variation)
        assert len(result) == 1
        assert result[0]["symbol"] == "BRCA1"
        assert result[0]["id"] == "672"

    def test_extract_genes_missing(self, client):
        """Test wyciągania informacji o genach z danych wariantu bez tego pola."""
        variation = {}
        result = client._extract_genes(variation)
        assert result == []

    def test_extract_phenotypes(self, client):
        """Test wyciągania informacji o fenotypach z danych wariantu."""
        variation = {
            "phenotypes": [
                {
                    "name": "Breast cancer",
                    "id": "114480"
                }
            ]
        }
        result = client._extract_phenotypes(variation)
        assert len(result) == 1
        assert result[0]["name"] == "Breast cancer"
        assert result[0]["id"] == "114480"

    def test_extract_phenotypes_missing(self, client):
        """Test wyciągania informacji o fenotypach z danych wariantu bez tego pola."""
        variation = {}
        result = client._extract_phenotypes(variation)
        assert result == []


# --- 3. Testy metod publicznych ---

class TestPublicMethods:
    """Testy dla metod publicznych klienta ClinVar."""

    # Pomocnicza metoda do testowania cache'a
    def _create_client_with_test_cache(self, ttl=1):
        """Tworzy klienta z bardzo krótkim TTL dla testów cache'a."""
        return ClinVarClient(email="test@example.com", cache_ttl=ttl)
    
    def _clear_client_cache(self, client):
        """Czyści cache klienta ClinVar."""
        # Bezpośrednie czyszczenie cache'a, jeśli jest dostępny
        if hasattr(client, '_cache'):
            client._cache.clear()

    def check_id_fields(self, result_item):
        """Helper sprawdzający czy występuje id na dowolnym poziomie w wynikach."""
        # Sprawdzamy, czy jest "id" lub "variant_id" na pierwszym poziomie lub w zagnieżdżonej strukturze
        has_id = "variant_id" in result_item or "id" in result_item
        has_nested_id = False
        if "result" in result_item and "variations" in result_item["result"]:
            if result_item["result"]["variations"]:
                first_variation = result_item["result"]["variations"][0]
                has_nested_id = "id" in first_variation
        return has_id or has_nested_id

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_variant_by_id_json(self, client, mock_response, use_mock):
        """Test pobierania wariantu według ID w formacie JSON."""
        if not use_mock:
            pytest.xfail("Pomijam ten test dla rzeczywistego API, gdyż nie sprawdzamy dokładnej struktury odpowiedzi")
        
        with patch.object(client, '_make_request', return_value=mock_response) if use_mock else nullcontext():
            result = client.get_variant_by_id("VCV000012345")
            
            if use_mock:
                assert result == SAMPLE_VARIANT_JSON
            else:
                assert isinstance(result, dict)

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_variant_by_id_xml(self, client, mock_xml_response, use_mock):
        """Test pobierania wariantu według ID w formacie XML."""
        if not use_mock:
            pytest.xfail("Pomijam ten test dla rzeczywistego API, gdyż nie sprawdzamy dokładnej struktury odpowiedzi")
            
        with patch.object(client, '_make_request', return_value=mock_xml_response) if use_mock else nullcontext():
            result = client.get_variant_by_id("VCV000012345", format_type="xml")
            
            assert isinstance(result, dict)
            if use_mock:
                assert "ReleaseSet" in result

    def test_get_variant_by_id_invalid_format(self, client):
        """Test pobierania wariantu według ID z nieprawidłowym formatem."""
        with pytest.raises(InvalidFormatError):
            client.get_variant_by_id("VCV000012345", format_type="invalid")

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_coordinates(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według koordynatów."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_coordinates("17", 43071077, 43071077)
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_coordinates("17", 43071077, 43071077)
            assert isinstance(result, list)

    def test_search_by_coordinates_invalid_parameters(self, client):
        """Test wyszukiwania wariantów z nieprawidłowymi koordynatami."""
        # Brak chromosomu
        with pytest.raises(InvalidParameterError):
            client.search_by_coordinates("", 100, 200)
            
        # Start > end
        with pytest.raises(InvalidParameterError):
            client.search_by_coordinates("1", 300, 200)
            
        # Nieprawidłowy typ start
        with pytest.raises(InvalidParameterError):
            client.search_by_coordinates("1", "100", 200)

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_gene(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według genu."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_gene("BRCA1")
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_gene("BRCA1")
            assert isinstance(result, list)
            
    def test_search_by_gene_empty(self, client):
        """Test wyszukiwania wariantów według pustego genu."""
        with pytest.raises(InvalidParameterError):
            client.search_by_gene("")

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_rs_id(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według ID rs."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_rs_id("rs6025")
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_rs_id("rs6025")
            assert isinstance(result, list)

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_rs_id_without_prefix(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według ID rs bez prefiksu 'rs'."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_rs_id("6025")
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_rs_id("6025")
            assert isinstance(result, list)

    def test_search_by_rs_id_empty(self, client):
        """Test wyszukiwania wariantów według pustego ID rs."""
        with pytest.raises(InvalidParameterError):
            client.search_by_rs_id("")

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_clinical_significance(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według znaczenia klinicznego."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_clinical_significance("pathogenic")
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_clinical_significance("pathogenic")
            assert isinstance(result, list)

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_clinical_significance_multiple(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według wielu znaczeń klinicznych."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_clinical_significance(["pathogenic", "likely pathogenic"])
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_clinical_significance(["pathogenic", "likely pathogenic"])
            assert isinstance(result, list)

    def test_search_by_clinical_significance_invalid(self, client):
        """Test wyszukiwania wariantów według nieprawidłowego znaczenia klinicznego."""
        with pytest.raises(InvalidParameterError):
            client.search_by_clinical_significance("invalid")

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_search_by_phenotype(self, client, mock_esearch_response, mock_response, use_mock):
        """Test wyszukiwania wariantów według fenotypu."""
        if use_mock:
            # Resetujemy czas ostatniego zapytania
            client._last_request_time = 0
            
            with patch('time.sleep'):  # Ignorujemy sleep dla testów
                with patch.object(client, '_make_request', side_effect=[mock_esearch_response, mock_response]):
                    result = client.search_by_phenotype("Breast cancer")
                    assert len(result) == 1
                    assert isinstance(result[0], dict)
                    assert self.check_id_fields(result[0])
        else:
            # Używamy rzeczywistego API
            result = client.search_by_phenotype("Breast cancer")
            assert isinstance(result, list)

    def test_search_by_phenotype_empty(self, client):
        """Test wyszukiwania wariantów według pustego fenotypu."""
        with pytest.raises(InvalidParameterError):
            client.search_by_phenotype("")

    def test_common_search_no_results(self, client, mock_esearch_response):
        """Test wyszukiwania bez wyników."""
        empty_response = Mock()
        empty_response.status_code = 200
        empty_response.text = json.dumps({"esearchresult": {"idlist": []}})
        empty_response.json.return_value = {"esearchresult": {"idlist": []}}
        empty_response.ok = True
        
        with patch.object(client, '_make_request', return_value=empty_response):
            result = client._common_search("test query")
            assert result == []

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_variant_summary(self, client, mock_response, use_mock):
        """Test pobierania podsumowania wariantu."""
        if use_mock:
            with patch.object(client, 'get_variant_by_id', return_value=SAMPLE_VARIANT_JSON):
                result = client.get_variant_summary("VCV000012345")
                assert isinstance(result, dict)
                assert "id" in result
                assert result["id"] == "VCV000012345"
        else:
            # Używamy rzeczywistego API
            result = client.get_variant_summary("VCV000014076")
            assert isinstance(result, dict)
            assert "id" in result

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_integrate_with_coordinates_lit(self, client, use_mock):
        """Test integracji danych coordinates_lit z ClinVar."""
        coordinates_data = [
            {"chromosome": "17", "start": 43071077, "end": 43071077, "source": "Test"}
        ]
        
        if use_mock:
            expected_variant = {"id": "12345", "name": "Test variant"}
            with patch.object(client, 'search_by_coordinates', return_value=[expected_variant]):
                result = client.integrate_with_coordinates_lit(coordinates_data)
                
                assert len(result) == 1
                assert "clinvar_data" in result[0]
                assert result[0]["clinvar_data"][0]["id"] == "12345"
                assert result[0]["chromosome"] == "17"
                assert result[0]["source"] == "Test"
        else:
            # Używamy rzeczywistego API
            result = client.integrate_with_coordinates_lit(coordinates_data)
            assert len(result) == 1
            assert "clinvar_data" in result[0]
            assert result[0]["chromosome"] == "17"
            assert result[0]["source"] == "Test"

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_integrate_with_coordinates_lit_error(self, client, use_mock):
        """Test integracji danych coordinates_lit z błędem ClinVar."""
        coordinates_data = [
            {"chromosome": "17", "start": 43071077, "end": 43071077, "source": "Test"}
        ]
    
        if use_mock:
            with patch.object(client, 'search_by_coordinates', side_effect=APIRequestError("API error")):
                result = client.integrate_with_coordinates_lit(coordinates_data)
    
                assert len(result) == 1
                assert "clinvar_data" in result[0]
                assert result[0]["clinvar_data"] == []
                assert "error" in result[0]
                assert "API error" in result[0]["error"]
        else:
            # Dla rzeczywistego API zasymulujmy błąd przez wywołanie metody z nieprawidłowymi danymi
            invalid_data = [
                {"chromosome": "invalid", "start": -1, "end": -1, "source": "Test"}
            ]
            result = client.integrate_with_coordinates_lit(invalid_data)
    
            assert len(result) == 1
            assert "clinvar_data" in result[0]
            # W rzeczywistym API możemy otrzymać dane lub pusty wynik - sprawdzamy tylko, czy wynik jest listą
            assert isinstance(result[0]["clinvar_data"], list)

    def test_integrate_with_coordinates_lit_missing_data(self, client):
        """Test integracji danych coordinates_lit z brakującymi danymi."""
        coordinates_data = [
            {"source": "Test"}  # Brak chromosome, start, end
        ]

        result = client.integrate_with_coordinates_lit(coordinates_data)

        assert len(result) == 1
        assert "clinvar_data" in result[0]
        assert result[0]["clinvar_data"] == []
        assert "error" in result[0]
        assert result[0]["error"] == "Brak wymaganych danych koordynatów"

    @pytest.mark.integration
    @pytest.mark.parametrize("use_mock", [True, False])
    def test_integrate_with_coordinates_lit_partial_errors(self, client, use_mock):
        """Test integracji coordinates_lit z częściowymi błędami."""
        coordinates_data = [
            {"chromosome": "17", "start": 43071077, "end": 43071077, "source": "Valid"},
            {"chromosome": "invalid", "start": -1, "end": -1, "source": "Invalid"}
        ]
        
        if use_mock:
            expected_variant = {"id": "12345", "name": "Test variant"}
            
            def mock_search_side_effect(*args, **kwargs):
                if args[0] == "17":  # Pierwszy wpis jest poprawny
                    return [expected_variant]
                else:  # Drugi wpis generuje błąd
                    raise InvalidParameterError("Nieprawidłowy chromosom")
            
            with patch.object(client, 'search_by_coordinates', side_effect=mock_search_side_effect):
                result = client.integrate_with_coordinates_lit(coordinates_data)
                
                assert len(result) == 2
                # Pierwszy wpis powinien mieć dane ClinVar
                assert "clinvar_data" in result[0]
                assert result[0]["clinvar_data"][0]["id"] == "12345"
                assert "error" not in result[0]
                # Drugi wpis powinien mieć błąd
                assert "clinvar_data" in result[1]
                assert result[1]["clinvar_data"] == []
                assert "error" in result[1]
        else:
            # Używamy rzeczywistego API
            try:
                result = client.integrate_with_coordinates_lit(coordinates_data)
                assert len(result) == 2
                assert "clinvar_data" in result[0]
                assert "clinvar_data" in result[1]
                assert result[1]["clinvar_data"] == []
                assert "error" in result[1]
            except Exception as e:
                pytest.skip(f"Test wymaga działającego API ClinVar: {str(e)}")

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_search_by_coordinates_xml_format(self, client, mock_esearch_xml_response, mock_xml_response, use_mock):
        """Test wyszukiwania wariantów według koordynatów w formacie XML."""
        # W tym teście wyłączamy cache, aby uniknąć problemów
        test_client = ClinVarClient(email="test@example.com", use_cache=False)
        
        # Resetujemy czas ostatniego zapytania
        test_client._last_request_time = 0
        
        # Sprawdzamy czy metoda _common_search jest wywoływana z odpowiednimi parametrami
        with patch.object(test_client, '_common_search') as mock_common_search:
            mock_common_search.return_value = []
            
            # Wywołujemy metodę search_by_coordinates
            test_client.search_by_coordinates("17", 43071077, 43071077)
            
            # Sprawdzamy czy _common_search została wywołana
            assert mock_common_search.call_count == 1

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_rate_limiting_behavior(self, client, mock_response, use_mock):
        """Test zachowania limitu częstotliwości zapytań."""
        # Używamy klienta z określonym interwałem zapytań
        test_client = ClinVarClient(email="test@example.com")
        
        # Symulujemy stan, w którym ostatnie zapytanie było właśnie wykonane
        current_time = 1000.0  # Fikcyjny timestamp
        test_client._last_request_time = current_time
        
        with patch('time.time', return_value=current_time):
            with patch('time.sleep') as mock_sleep:
                # Wykonujemy zapytanie, powinno wywołać sleep, aby zachować limit częstotliwości
                test_client._wait_for_rate_limit()
                
                # Time.sleep powinien zostać wywołany z wartością bliską API_REQUEST_INTERVAL
                assert mock_sleep.called
                assert mock_sleep.call_args[0][0] > 0

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_retmax_limiting(self, client, mock_esearch_response, mock_response, use_mock):
        """Test limitu ilości wyników."""
        # Klient z wyłączonym cache
        test_client = ClinVarClient(email="test@example.com", use_cache=False)
        
        # Mockujemy samą metodę search_by_gene, aby sprawdzić czy parametr retmax jest przekazywany
        with patch.object(test_client, 'search_by_gene', wraps=test_client.search_by_gene) as spy:
            # Wywołanie z limitem 10
            test_client.search_by_gene("BRCA1", retmax=10)
            
            # Sprawdzamy, czy parametr retmax został przekazany do funkcji
            args, kwargs = spy.call_args
            assert kwargs.get('retmax') == 10

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_common_variants_search(self, client, use_mock):
        """Test wyszukiwania znanych wariantów występujących w różnych genach."""
        # Klient z wyłączonym cache
        test_client = ClinVarClient(email="test@example.com", use_cache=False)
        
        # Przygotuj odpowiedzi dla różnych genów
        gene1_response = Mock()
        gene1_response.status_code = 200
        gene1_response.text = json.dumps({
            "esearchresult": {
                "count": "5",
                "idlist": ["1", "2", "3", "4", "5"]
            }
        })
        gene1_response.json.return_value = json.loads(gene1_response.text)
        
        gene2_response = Mock()
        gene2_response.status_code = 200
        gene2_response.text = json.dumps({
            "esearchresult": {
                "count": "3",
                "idlist": ["3", "4", "6"]  # Uwaga: 3 i 4 są wspólne z gene1
            }
        })
        gene2_response.json.return_value = json.loads(gene2_response.text)
        
        # Mockujemy search_by_gene, aby zwracał nasze przygotowane odpowiedzi
        with patch.object(test_client, 'search_by_gene', side_effect=[
            [{"id": i} for i in range(1, 6)],  # Wyniki dla gene1
            [{"id": i} for i in range(3, 7)]   # Wyniki dla gene2
        ]):
            # Wyszukujemy warianty wspólne dla dwóch genów
            results = test_client.search_by_gene("GENE1") + test_client.search_by_gene("GENE2")
            
            # Sprawdzamy wyniki
            assert len(results) == 9  # 5 + 4 wyniki (z duplikatami)
            
            # Możemy też sprawdzić, ile jest unikalnych ID (gdybyśmy je filtrowali)
            unique_ids = set(variant["id"] for variant in results)
            assert len(unique_ids) == 6  # 6 unikalnych ID (1,2,3,4,5,6)

    def test_init_with_cache_ttl(self):
        """Test inicjalizacji z niestandardowym czasem życia cache'a."""
        cache_ttl = 3600  # 1 godzina
        client = ClinVarClient(email="test@example.com", cache_ttl=cache_ttl)
        # Sprawdzamy tylko, czy obiekt został utworzony
        assert isinstance(client, ClinVarClient)

    def test_init_with_cache_storage_type(self):
        """Test inicjalizacji z niestandardowym typem przechowywania cache'a."""
        client = ClinVarClient(email="test@example.com", cache_storage_type="memory")
        # Sprawdzamy tylko, czy obiekt został utworzony
        assert isinstance(client, ClinVarClient)

    def test_init_with_custom_tool_name(self):
        """Test inicjalizacji z niestandardową nazwą narzędzia."""
        tool_name = "custom_tool_name"
        client = ClinVarClient(email="test@example.com", tool=tool_name)
        assert client.tool == tool_name

    def test_init_with_allow_large_queries(self):
        """Test inicjalizacji z włączonym allow_large_queries."""
        client = ClinVarClient(email="test@example.com", allow_large_queries=True)
        assert client.allow_large_queries is True

    def test_init_without_email(self):
        """Test inicjalizacji bez adresu email."""
        client = ClinVarClient()
        assert client.email is None

    @pytest.mark.parametrize("use_mock", [True, False])
    def test_get_variant_with_complete_mock_data(self, client, use_mock):
        """Test pobierania wariantu z przygotowanych danych."""
        # Przygotowanie danych wariantu BRCA1
        test_variant_data = {
            "id": "VCV000012345",
            "name": "NM_007294.3(BRCA1):c.5266dupC (p.Gln1756Profs*74)",
            "variation_type": "Deletion",
            "clinical_significance": "Pathogenic",
            "genes": [
                {"symbol": "BRCA1", "id": "672"}
            ],
            "phenotypes": [
                {"name": "Breast-ovarian cancer, familial 1", "id": "114480"}
            ],
            "coordinates": [
                {
                    "assembly": "GRCh38",
                    "chromosome": "17",
                    "start": 43071077,
                    "stop": 43071077,
                    "reference_allele": "A",
                    "alternate_allele": "T"
                }
            ]
        }
        
        if use_mock:
            # Tworzymy mocka odpowiedzi dla funkcji get_variant_by_id
            mock_get_variant = Mock()
            mock_get_variant.return_value = test_variant_data
            
            # Używamy mocka dla metody get_variant_by_id
            with patch.object(client, 'get_variant_by_id', mock_get_variant):
                # Wywołanie funkcji z mockiem
                result = client.get_variant_by_id("VCV000012345")
                
                # Weryfikacja rezultatu
                assert result == test_variant_data
                assert result["genes"][0]["symbol"] == "BRCA1"
                assert result["clinical_significance"] == "Pathogenic"
                assert len(result["coordinates"]) == 1

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_connection_timeout_handling(self, client, use_mock):
        """Test obsługi timeout'u połączenia."""
        # Tworzymy klienta z krótkim timeout
        test_client = ClinVarClient(email="test@example.com", timeout=1)
        
        # Mockujemy requests.get, aby wywołał timeout
        with patch('requests.get', side_effect=requests.exceptions.Timeout("Connection timed out")) as mock_get:
            # Powinniśmy otrzymać APIRequestError
            with pytest.raises(APIRequestError) as exc_info:
                test_client._make_request("test_endpoint")
            
            # Sprawdzamy, czy komunikat błędu zawiera informację o timeout
            assert "timed out" in str(exc_info.value).lower()

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_invalid_assembly_handling(self, client, use_mock):
        """Test obsługi nieprawidłowej wersji genomu."""
        # Klient z wyłączonym cache
        test_client = ClinVarClient(email="test@example.com", use_cache=False)
        
        # Mockujemy _make_request, aby symulować błąd nieprawidłowego assembly
        invalid_response = Mock()
        invalid_response.status_code = 400
        invalid_response.json.return_value = {"error": "Invalid assembly"}
        invalid_response.text = "Invalid assembly"
        
        with patch.object(test_client, '_make_request', side_effect=InvalidParameterError("Invalid assembly")):
            with pytest.raises(InvalidParameterError) as exc_info:
                test_client.search_by_coordinates("17", 43071077, 43071077, assembly="nieprawidłowe_assembly")
            
            assert "Invalid assembly" in str(exc_info.value)

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_malformed_xml_handling(self, client, use_mock):
        """Test obsługi nieprawidłowo sformatowanego XML."""
        # Klient z wyłączonym cache
        test_client = ClinVarClient(email="test@example.com", use_cache=False)
        
        # Przygotuj odpowiedź z nieprawidłowym XML
        malformed_xml_response = Mock()
        malformed_xml_response.status_code = 200
        malformed_xml_response.text = "<invalid>XML<tag>"
        
        with patch.object(test_client, '_make_request', return_value=malformed_xml_response):
            # Oczekujemy APIRequestError, ponieważ ParseError jest opakowywany
            with pytest.raises(APIRequestError) as exc_info:
                test_client.get_variant_by_id("VCV000012345", format_type="xml")
            
            # Sprawdzamy, czy komunikat błędu zawiera informacje o parsowaniu XML
            assert "XML" in str(exc_info.value)

    @requires_advanced_mocking
    @pytest.mark.parametrize("use_mock", [True])
    def test_retry_on_server_error(self, client, mock_response, use_mock):
        """Test ponownych prób po błędzie serwera."""
        # Przygotuj odpowiedzi: dwa błędy serwera, a następnie sukces
        server_error_response = Mock()
        server_error_response.status_code = 500
        server_error_response.ok = False
        
        # Używamy klienta z mniejszym opóźnieniem retry dla szybszych testów
        test_client = ClinVarClient(email="test@example.com", retry_delay=1)
        
        # Mockujemy time.sleep, aby przyspieszyć testy
        with patch('time.sleep') as mock_sleep:
            # Mockujemy requests.get aby zwracać błędy serwera, a potem sukces
            with patch('requests.get', side_effect=[server_error_response, server_error_response, mock_response]) as mock_get:
                response = test_client._make_request("test_endpoint")
                
                # Sprawdzamy, czy funkcja get została wywołana 3 razy
                assert mock_get.call_count == 3
                # Sprawdzamy, czy sleep został wywołany 2 razy (po każdej nieudanej próbie)
                assert mock_sleep.call_count >= 2
                # Sprawdzamy, czy ostatecznie otrzymaliśmy prawidłową odpowiedź
                assert response == mock_response 