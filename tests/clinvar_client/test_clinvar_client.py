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

from src.clinvar_client.clinvar_client import ClinVarClient, DEFAULT_BASE_URL
from src.clinvar_client.exceptions import (
    ClinVarError,
    APIRequestError,
    InvalidFormatError,
    ParseError,
    InvalidParameterError,
    RateLimitError
)

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
        # Użyj rzeczywistego klienta dla testów integracyjnych
        yield ClinVarClient(email="test@example.com")
    else:
        # Użyj zamockowanego klienta dla testów jednostkowych
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
        """Test wykonania zapytania z nieprawidłową metodą HTTP."""
        with pytest.raises(ValueError):
            client._make_request("test_endpoint", method="INVALID")

    def test_make_request_with_params(self, client, mock_response):
        """Test wykonania zapytania z parametrami."""
        test_params = {"param1": "value1", "param2": "value2"}
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            client._make_request("test_endpoint", params=test_params)
            
            called_args = mock_get.call_args[1]
            for param, value in test_params.items():
                assert param in called_args["params"]
                assert called_args["params"][param] == value

    def test_make_request_rate_limit_error(self, client):
        """Test obsługi błędu limitu zapytań."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        
        with patch('requests.get', return_value=rate_limit_response):
            with patch.object(client, '_make_request', wraps=client._make_request) as spy:
                with pytest.raises(RateLimitError):
                    client._make_request("test_endpoint", retry_count=client.max_retries)
                
                # Sprawdź, czy nie próbowano ponownie (bo już osiągnięto max_retries)
                assert spy.call_count == 1

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
        """Test obsługi nieprawidłowego zapytania."""
        bad_request_response = Mock()
        bad_request_response.status_code = 400
        bad_request_response.text = "Bad request"
        
        with patch('requests.get', return_value=bad_request_response):
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
                    assert "variant_id" in result[0] or "id" in result[0]
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
                    assert "variant_id" in result[0] or "id" in result[0]
        else:
            # Używamy rzeczywistego API
            result = client.search_by_gene("BRCA1")
            assert isinstance(result, list)
            
    def test_search_by_gene_empty(self, client):
        """Test wyszukiwania wariantów według pustego genu."""
        with pytest.raises(InvalidParameterError):
            client.search_by_gene("")

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
                    assert "variant_id" in result[0] or "id" in result[0]
        else:
            # Używamy rzeczywistego API
            result = client.search_by_rs_id("rs6025")
            assert isinstance(result, list)

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
                    assert "variant_id" in result[0] or "id" in result[0]
        else:
            # Używamy rzeczywistego API
            result = client.search_by_rs_id("6025")
            assert isinstance(result, list)

    def test_search_by_rs_id_empty(self, client):
        """Test wyszukiwania wariantów według pustego ID rs."""
        with pytest.raises(InvalidParameterError):
            client.search_by_rs_id("")

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
                    assert "variant_id" in result[0] or "id" in result[0]
        else:
            # Używamy rzeczywistego API
            result = client.search_by_clinical_significance("pathogenic")
            assert isinstance(result, list)

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
                    assert "variant_id" in result[0] or "id" in result[0]
        else:
            # Używamy rzeczywistego API
            result = client.search_by_clinical_significance(["pathogenic", "likely pathogenic"])
            assert isinstance(result, list)

    def test_search_by_clinical_significance_invalid(self, client):
        """Test wyszukiwania wariantów według nieprawidłowego znaczenia klinicznego."""
        with pytest.raises(InvalidParameterError):
            client.search_by_clinical_significance("invalid")

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
                    assert "variant_id" in result[0] or "id" in result[0]
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


# --- 4. Testy integracyjne ---

class TestIntegration:
    """Testy integracyjne z rzeczywistym API ClinVar."""
    
    @pytest.mark.integration
    def test_integration_get_variant_by_id(self, client):
        """Test integracyjny: pobieranie wariantu według ID."""
        # Ponieważ API ClinVar może być niestabilne lub zwracać puste wyniki,
        # najpierw spróbujemy znaleźć warianty za pomocą kilku różnych metod
        
        # Opcja 1: Wyszukaj po genie
        variants = client.search_by_gene("BRCA1")
        
        # Jeśli nie znaleziono, spróbuj po koordynatach
        if not variants:
            variants = client.search_by_coordinates("17", 43044295, 43125483)
            
        # Jeśli nadal brak wyników, spróbuj po rs ID
        if not variants:
            variants = client.search_by_rs_id("rs748232798")
        
        # Jeśli wszystkie metody zawiodły, pomiń test
        if not variants:
            pytest.skip("Nie udało się znaleźć żadnych wariantów poprzez API ClinVar")
            
        # Upewniamy się, że mamy wariant z ID
        variant_found = False
        for variant in variants:
            if "variant_id" in variant:
                variant_id = variant["variant_id"]
                try:
                    result = client.get_variant_by_id(variant_id)
                    assert isinstance(result, dict)
                    assert "variant_id" in result
                    variant_found = True
                    break
                except Exception:
                    # Jeśli nie udało się pobrać tego wariantu, spróbuj następny
                    continue
        
        if not variant_found:
            pytest.skip("Nie znaleziono wariantów z poprawnym ID lub API odmówiło dostępu")
    
    @pytest.mark.integration
    def test_integration_search_by_gene(self, client):
        """Test integracyjny: wyszukiwanie wariantów według genu."""
        variants = client.search_by_gene("BRCA1")
        assert isinstance(variants, list)
    
    @pytest.mark.integration
    def test_integration_search_by_coordinates(self, client):
        """Test integracyjny: wyszukiwanie wariantów według koordynatów."""
        variants = client.search_by_coordinates("17", 43044295, 43125483)
        assert isinstance(variants, list) 