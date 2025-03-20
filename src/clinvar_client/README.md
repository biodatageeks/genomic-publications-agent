# ClinVar Client

Klient API ClinVar do integracji z narzędziem coordinates_lit, umożliwiający wyszukiwanie i analizę wariantów genetycznych.

## Funkcjonalności

- Pobieranie informacji o wariantach na podstawie identyfikatorów ClinVar (VCV, RCV)
- Wyszukiwanie wariantów według koordynatów genomowych
- Wyszukiwanie wariantów dla określonych genów
- Wyszukiwanie wariantów według identyfikatorów rs (dbSNP)
- Wyszukiwanie wariantów o określonym znaczeniu klinicznym
- Wyszukiwanie wariantów powiązanych z fenotypami
- Integracja danych z ClinVar z koordynatami z coordinates_lit

## Wymagania

- Python 3.6+
- requests
- logging

## Przykłady użycia

### Inicjalizacja klienta

```python
from src.clinvar_client.clinvar_client import ClinVarClient

# Inicjalizacja klienta z adresem email (wymaganym przez NCBI)
client = ClinVarClient(email="twoj.email@domena.pl")

# Opcjonalnie z kluczem API dla zwiększenia limitu zapytań
client = ClinVarClient(email="twoj.email@domena.pl", api_key="twoj_klucz_api")
```

### Pobieranie informacji o wariancie według ID

```python
# Pobieranie informacji o wariancie w formacie JSON
variant_info = client.get_variant_by_id("VCV000124789")
print(f"Znaczenie kliniczne: {variant_info['clinical_significance']}")

# Pobieranie informacji o wariancie w formacie XML
variant_info_xml = client.get_variant_by_id("VCV000124789", format_type="xml")
```

### Wyszukiwanie wariantów według koordynatów genomowych

```python
# Wyszukiwanie wariantów w regionie chromosomowym
variants = client.search_by_coordinates(chromosome="1", start=100000, end=200000)
for variant in variants:
    print(f"Wariant: {variant['name']} - {variant['clinical_significance']}")
```

### Wyszukiwanie wariantów według genu

```python
# Wyszukiwanie wariantów dla genu BRCA1
brca1_variants = client.search_by_gene("BRCA1")
print(f"Znaleziono {len(brca1_variants)} wariantów dla genu BRCA1")
```

### Wyszukiwanie według znaczenia klinicznego

```python
# Wyszukiwanie wariantów patogennych
pathogenic_variants = client.search_by_clinical_significance("pathogenic")

# Wyszukiwanie wariantów o wielu znaczeniach klinicznych
variants = client.search_by_clinical_significance(["pathogenic", "likely pathogenic"])
```

### Integracja z coordinates_lit

```python
# Przykładowe dane z coordinates_lit
coordinates_data = [
    {"chromosome": "1", "start": 100000, "end": 200000, "source": "Publication 1"},
    {"chromosome": "X", "start": 30000000, "end": 31000000, "source": "Publication 2"}
]

# Integracja danych ClinVar z koordynatami
enriched_data = client.integrate_with_coordinates_lit(coordinates_data)

# Analiza wyników
for entry in enriched_data:
    print(f"Region: {entry['chromosome']}:{entry['start']}-{entry['end']}")
    print(f"Źródło: {entry['source']}")
    print(f"Liczba wariantów ClinVar: {len(entry['clinvar_data'])}")
```

## Obsługa błędów

Klient ClinVar implementuje zestaw niestandardowych wyjątków dla różnych typów błędów:

- `ClinVarError` - Bazowy wyjątek dla wszystkich błędów
- `APIRequestError` - Błędy podczas wykonywania zapytania API
- `InvalidFormatError` - Niewspierane formaty odpowiedzi
- `ParseError` - Błędy parsowania odpowiedzi
- `InvalidParameterError` - Nieprawidłowe parametry zapytania
- `RateLimitError` - Przekroczenie limitu zapytań do API

## Uwagi

- API NCBI E-utilities wymaga adresu email użytkownika.
- Aby zwiększyć limit zapytań (z 3 na sekundę do 10 na sekundę), można zarejestrować klucz API NCBI.
- Klient obsługuje odpowiedzi w formatach JSON i XML.
- Implementacja automatycznego ponawiania prób w przypadku błędów serwera lub ograniczeń szybkości. 