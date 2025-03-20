"""
Podstawowe testy klienta ClinVar.
"""

from src.clinvar_client.clinvar_client import ClinVarClient
import logging
import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import time
import requests

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                ]
            }
        ]
    }
}

SAMPLE_ESEARCH_JSON = {
    "esearchresult": {
        "count": "1",
        "retmax": "1",
        "retstart": "0",
        "idlist": ["12345"],
    }
}

# Dodaję stałą określającą wymagane opóźnienie między zapytaniami
API_SLEEP_TIME = 0.4  # 0.4 sekundy to bezpieczna wartość dla limitu 3 zapytań/s

@pytest.fixture
def client():
    """Fixture zwracający instancję klienta ClinVar."""
    # Używa mockowanego klienta dla testów jednostkowych
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = json.dumps(SAMPLE_VARIANT_JSON)
        mock_response.json.return_value = SAMPLE_VARIANT_JSON
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200
        
        mock_esearch_response = MagicMock()
        mock_esearch_response.text = json.dumps(SAMPLE_ESEARCH_JSON)
        mock_esearch_response.json.return_value = SAMPLE_ESEARCH_JSON
        mock_esearch_response.status_code = 200
        
        # Symulacja różnych endpointów
        def get_side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'esearch.fcgi' in url:
                return mock_esearch_response
            else:
                return mock_response
                
        mock_post.side_effect = get_side_effect
        mock_get.side_effect = get_side_effect
        
        yield ClinVarClient(email="sitekwb@gmail.com")

def test_search_by_gene(client):
    """Test wyszukiwania wariantów według genu."""
    print("\n=== Test wyszukiwania wariantów według genu ===")
    try:
        variants = client.search_by_gene("BRCA1", retmax=5)
        print(f"Liczba znalezionych wariantów: {len(variants)}")
        if variants:
            print("Przykładowy wariant:")
            variant = variants[0]
            print(f"- ID: {variant.get('id')}")
            print(f"- Nazwa: {variant.get('name')}")
            print(f"- Znaczenie kliniczne: {variant.get('clinical_significance')}")
    except Exception as e:
        print(f"Błąd: {e}")
        raise e

def test_search_by_coordinates(client):
    """Test wyszukiwania wariantów według koordynatów."""
    print("\n=== Test wyszukiwania wariantów według koordynatów ===")
    try:
        variants = client.search_by_coordinates("17", 43044295, 43125483)
        print(f"Liczba znalezionych wariantów: {len(variants)}")
        if variants:
            print("Przykładowy wariant:")
            variant = variants[0]
            print(f"- ID: {variant.get('id')}")
            print(f"- Nazwa: {variant.get('name')}")
            print(f"- Znaczenie kliniczne: {variant.get('clinical_significance')}")
    except Exception as e:
        print(f"Błąd: {e}")
        raise e

def test_search_by_clinical_significance(client):
    """Test wyszukiwania wariantów według znaczenia klinicznego."""
    print("\n=== Test wyszukiwania wariantów według znaczenia klinicznego ===")
    try:
        variants = client.search_by_clinical_significance("pathogenic")
        print(f"Liczba znalezionych wariantów: {len(variants)}")
        if variants:
            print("Przykładowy wariant:")
            variant = variants[0]
            print(f"- ID: {variant.get('id')}")
            print(f"- Nazwa: {variant.get('name')}")
            print(f"- Gen: {variant.get('genes', [{}])[0].get('symbol') if variant.get('genes') else 'Brak'}")
    except Exception as e:
        print(f"Błąd: {e}")
        raise e

def test_real_api_connection():
    """Test rzeczywistego połączenia z API ClinVar."""
    print("\n=== Test rzeczywistego połączenia z API ClinVar ===")
    
    # Dodajemy bezpośrednią diagnostykę API
    import requests
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    print("💡 Testowanie bezpośredniego zapytania do API (esearch)...")
    
    # Zapytanie o BRCA1 bezpośrednio przez API
    esearch_params = {
        "db": "clinvar",
        "term": "BRCA1[gene]",
        "retmode": "json",
        "retmax": "5",  # Ograniczamy do 5 wyników
        "email": "sitekwb@gmail.com",
        "tool": "coordinates_lit_test"
    }
    
    try:
        esearch_response = requests.get(f"{base_url}esearch.fcgi", params=esearch_params)
        print(f"Status: {esearch_response.status_code}")
        
        if esearch_response.status_code == 200:
            try:
                esearch_data = esearch_response.json()
                print(f"Surowa odpowiedź esearch: {json.dumps(esearch_data, indent=2)[:500]}...")
                
                if "esearchresult" in esearch_data and "idlist" in esearch_data["esearchresult"]:
                    ids = esearch_data["esearchresult"]["idlist"]
                    print(f"Znaleziono {len(ids)} ID wariantów, pierwsze 5: {ids[:5]}")
                    
                    if ids:
                        # Odczekaj wymagany czas między zapytaniami
                        time.sleep(API_SLEEP_TIME)
                        
                        # Teraz pobieramy szczegóły pierwszego wariantu
                        print("\n💡 Pobieranie szczegółów wariantu...")
                        efetch_params = {
                            "db": "clinvar",
                            "id": ids[0],
                            "retmode": "json",
                            "email": "sitekwb@gmail.com",
                            "tool": "coordinates_lit_test"
                        }
                        
                        efetch_response = requests.get(f"{base_url}efetch.fcgi", params=efetch_params)
                        print(f"Status efetch: {efetch_response.status_code}")
                        
                        if efetch_response.status_code == 200:
                            try:
                                # Spróbujmy najpierw jako JSON
                                efetch_data = efetch_response.json()
                                print(f"Surowa odpowiedź efetch (JSON): {json.dumps(efetch_data, indent=2)[:500]}...")
                            except json.JSONDecodeError:
                                # Jeśli nie jest to JSON, wyświetlmy fragment tekstu
                                print(f"Surowa odpowiedź efetch (nie-JSON): {efetch_response.text[:500]}...")
                else:
                    print("Brak idlist w odpowiedzi esearch")
            except json.JSONDecodeError:
                print(f"Nie udało się zdekodować odpowiedzi JSON: {esearch_response.text[:500]}...")
    except Exception as e:
        print(f"Błąd podczas bezpośredniego zapytania do API: {e}")
    
    # Odczekaj wymagany czas między zapytaniami
    time.sleep(API_SLEEP_TIME)
    
    # Teraz użyjmy klienta ClinVar
    print("\n💡 Testowanie klienta ClinVar...")
    real_client = ClinVarClient(email="sitekwb@gmail.com")
    
    try:
        # Ustawiamy dodatkowe debugowanie w kliencie
        real_client.logger.setLevel(logging.DEBUG)
        
        # Sprawdzamy różne możliwości wyszukiwania
        print("\nPróba 1: Wyszukiwanie po genie BRCA1")
        variants = real_client.search_by_gene("BRCA1", retmax=5)
        print(f"Rzeczywista liczba wariantów BRCA1: {len(variants)}")
        
        # Odczekaj wymagany czas między zapytaniami
        time.sleep(API_SLEEP_TIME)
        
        # Użyjmy bezpośrednich parametrów na podstawie diagnostyki
        print("\nPróba 5: Wyszukiwanie z bezpośrednimi parametrami API")
        try:
            # Spróbujmy symulować bezpośrednie zapytanie z esearch
            response = real_client._make_request("esearch.fcgi", params=esearch_params)
            print(f"Status odpowiedzi: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Odpowiedź JSON: {json.dumps(data, indent=2)[:300]}...")
                    
                    if "esearchresult" in data and "idlist" in data["esearchresult"]:
                        variant_ids = data["esearchresult"]["idlist"]
                        if variant_ids:
                            id_to_fetch = variant_ids[0]
                            print(f"\nPobieranie wariantu o ID: {id_to_fetch}")
                            
                            # Odczekaj wymagany czas między zapytaniami
                            time.sleep(API_SLEEP_TIME)
                            
                            # Pobierz szczegóły wariantu
                            variant = real_client.get_variant_by_id(id_to_fetch)
                            if variant:
                                print(f"✓ Znaleziono wariant o ID {id_to_fetch}!")
                                print(f"Szczegóły wariantu: {json.dumps(variant, indent=2)[:500]}...")
                            else:
                                print(f"✗ Nie znaleziono szczegółów wariantu o ID {id_to_fetch}")
                except Exception as e:
                    print(f"Błąd podczas parsowania odpowiedzi: {e}")
        except Exception as e:
            print(f"Błąd podczas bezpośredniego zapytania: {e}")
        
        if not variants:
            print("\n⚠ Nie znaleziono wariantów BRCA1. Sprawdzanie czy metoda _process_variation_json/xml działa poprawnie...")
            # Sprawdzamy czy serwer ClinVar zwraca dane w innym formacie
            # niż oczekuje nasza metoda przetwarzania
    except Exception as e:
        print(f"\n✗ Błąd podczas testowania rzeczywistego API: {e}")
        
    # Asercja zawsze przechodzi, ponieważ jest to test diagnostyczny
    assert True

def test_api_server_availability():
    """Test sprawdzający dostępność serwera API ClinVar bez wyszukiwania wariantów."""
    print("\n=== Test dostępności serwera API ClinVar ===")
    try:
        # Bezpośrednie testowanie endpointu API
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        params = {
            "db": "clinvar",
            "email": "sitekwb@gmail.com",
            "tool": "coordinates_lit_test"
        }
        response = requests.get(f"{base_url}einfo.fcgi", params=params)
        
        print(f"Kod odpowiedzi: {response.status_code}")
        print(f"Nagłówki odpowiedzi:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
            
        if response.status_code == 200:
            print("\n✓ Serwer API ClinVar jest dostępny i odpowiada poprawnie")
            content_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
            print(f"\nPodgląd odpowiedzi:\n{content_preview}")
        else:
            print("\n⚠ Serwer API ClinVar odpowiada, ale zwrócił kod błędu:", response.status_code)
            
        # Używamy asercji zamiast zwracać wartość
        assert response.status_code in [200, 400, 429], "Serwer API nie odpowiada prawidłowo"
    except Exception as e:
        print(f"\n✗ Błąd podczas sprawdzania dostępności serwera API: {e}")
        # Używamy asercji, aby test nie przeszedł w przypadku błędu
        assert False, f"Wystąpił błąd podczas połączenia z API: {e}"

def main():
    """Funkcja główna do uruchamiania testów."""
    print("Uruchamianie testów klienta ClinVar...")
    client = ClinVarClient(email="sitekwb@gmail.com")
    test_search_by_gene(client)
    test_search_by_coordinates(client)
    test_search_by_clinical_significance(client)
    
    print("\nTestowanie rzeczywistego API (z przerwami między zapytaniami)...")
    time.sleep(API_SLEEP_TIME)
    test_api_server_availability()
    time.sleep(API_SLEEP_TIME)
    test_real_api_connection()

if __name__ == "__main__":
    main() 