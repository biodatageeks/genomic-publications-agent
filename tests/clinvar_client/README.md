# Testy dla ClinVar Client

Ten katalog zawiera testy jednostkowe i integracyjne dla klienta ClinVar, implementowane zgodnie z podejściem Test-Driven Development (TDD).

## Struktura testów

- `test_clinvar_client.py` - Główny plik testów dla klienta ClinVar
- `test_exceptions.py` - Testy dla klas wyjątków

## Podejście testowe

Testy są zorganizowane według następujących kategorii:

1. **Testy inicjalizacji** - Weryfikacja poprawnej inicjalizacji klienta i ustawień parametrów
2. **Testy żądań HTTP** - Weryfikacja poprawnego formowania zapytań HTTP
3. **Testy parsowania** - Weryfikacja poprawnego przetwarzania odpowiedzi XML i JSON
4. **Testy funkcji wyszukiwania** - Weryfikacja funkcji wyszukiwania (według koordynatów, genu, itp.)
5. **Testy obsługi błędów** - Weryfikacja poprawnej obsługi błędów i wyjątków
6. **Testy integracyjne** - Testy integracji z rzeczywistym API ClinVar
7. **Testy wydajnościowe** - Weryfikacja wydajności klienta

## Uruchamianie testów

Aby uruchomić wszystkie testy:

```bash
pytest tests/clinvar_client
```

Aby uruchomić tylko testy jednostkowe (bez testów integracyjnych):

```bash
pytest tests/clinvar_client -k "not integration"
```

Aby uruchomić tylko testy integracyjne:

```bash
pytest tests/clinvar_client -k "integration"
```

## Dane testowe

Katalog zawiera przykładowe dane testowe dla symulacji odpowiedzi API ClinVar:

- Przykładowe odpowiedzi JSON
- Przykładowe odpowiedzi XML
- Dane testowe dla przypadków brzegowych i błędów

## Uwagi

1. Testy integracyjne wymagają połączenia z internetem i mogą być ograniczone przez limity API.
2. Przy uruchamianiu testów integracyjnych zaleca się podanie własnego adresu e-mail i klucza API.
3. Testy jednostkowe używają mocków dla symulacji odpowiedzi API, więc nie wymagają połączenia z internetem. 