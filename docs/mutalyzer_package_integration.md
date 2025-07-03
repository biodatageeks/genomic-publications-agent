# Integracja z oficjalnym pakietem Mutalyzer

## Przegląd

W odpowiedzi na feedback użytkownika, zaimplementowaliśmy integrację z oficjalnym pakietem Mutalyzer dostępnym na PyPI zamiast tworzenia własnej implementacji od podstaw.

## Oficjalny pakiet Mutalyzer

### Informacje podstawowe
- **Pakiet**: `mutalyzer` (dostępny na PyPI)
- **Dokumentacja**: https://mutalyzer.readthedocs.io/en/latest/
- **Repozytorium**: https://github.com/mutalyzer/mutalyzer
- **Instalacja**: `pip install mutalyzer`

### Główne funkcjonalności
- Walidacja i normalizacja wariantów HGVS
- Obsługa różnych systemów koordynatów (c., g., r., p., n., m.)
- Mapowanie między różnymi reprezentacjami
- Obsługa białek i RNA
- Cache referencyjnych sekwencji
- Interface CLI i Python API

## Stan implementacji

### ✅ Zrealizowane
1. **Integracja z mutalyzer.normalizer**
   - Import i użycie funkcji `normalize()` z oficjalnego pakietu
   - Obsługa pełnych odpowiedzi z bogatymi metadanymi
   - Konwersja błędów z formatu Mutalyzer na nasze modele

2. **Aktualizacja MutalyzerClient**
   - Implementacja lokalnego przetwarzania używając oficjalnego pakietu
   - Zachowanie fallback'u na zdalne API
   - Obsługa zarówno walidacji składniowej jak i semantycznej

3. **Bogata odpowiedź z oficjalnego pakietu**
   ```python
   {
     "input_description": "NM_003002.2:c.274G>T",
     "normalized_description": "NM_003002.2:c.274G>T",
     "corrected_description": "NM_003002.2:c.274G>T", 
     "protein": {
       "description": "NM_003002.2(NP_002993.1):p.(Asp92Tyr)",
       "reference": "MAVLWR...",
       "predicted": "MAVLWR..."
     },
     "rna": {
       "description": "NM_003002.2:r.(274g>u)"
     },
     "infos": [...],
     "errors": [...]
   }
   ```

### 🔍 Odkrycia podczas implementacji

1. **Format odpowiedzi znacznie bogatszy**
   - Oficjalny pakiet zwraca strukturalne modele wariantów
   - Automatyczne generowanie opisów białkowych i RNA
   - Dodatkowe informacje diagnostyczne w polu `infos`

2. **Obsługa błędów**
   - Szczegółowe kody błędów (ESYNTAXUC, EMAPPING, etc.)
   - Informacje o pozycji błędu w tekście
   - Sugestie poprawek

3. **Wymagania systemowe**
   - Wymaga dostępu do NCBI (dla pobierania sekwencji referencyjnych)
   - Zalecane ustawienie email'a dla NCBI
   - Opcjonalny cache lokalny dla lepszej wydajności

## Przykład użycia

### Podstawowe użycie
```python
from mutalyzer.normalizer import normalize

# Normalizacja wariantu
result = normalize("NM_003002.2:c.274G>T")

# Sprawdzenie rezultatu
if result.get("errors"):
    print("Błędy:", result["errors"])
else:
    print("Znormalizowany:", result["normalized_description"])
    print("Białko:", result["protein"]["description"])
```

### W kontekście naszego API
```python
from src.api.clients.mutalyzer_client import MutalyzerClient

client = MutalyzerClient(use_local=True)
result = await client.check_variant("NM_003002.2:c.274G>T")
```

## Korzyści z użycia oficjalnego pakietu

### ✅ Zalety
1. **Aktualność** - Zawsze najnowsze reguły HGVS
2. **Kompletność** - Pełna obsługa wszystkich typów wariantów
3. **Wsparcie społeczności** - Aktywnie rozwijany projekt
4. **Standardowość** - Używany przez LOVD i inne bazy danych
5. **Dokumentacja** - Oficjalna dokumentacja i przykłady

### ⚠️ Wyzwania
1. **Zależności** - Wymaga BioPython i dostępu do NCBI
2. **Konfiguracja** - Wymaga ustawienia email'a dla NCBI
3. **Cache** - Zalecane skonfigurowanie lokalnego cache
4. **Wydajność** - Pierwsze wywołania mogą być wolne

## Rekomendacje

### Implementacja produkcyjna
1. **Skonfiguruj cache lokalny**
   ```bash
   mkdir cache
   echo "MUTALYZER_CACHE_DIR = $(pwd)/cache" > config.txt
   echo "EMAIL = your.email@domain.com" >> config.txt
   ```

2. **Ustaw zmienne środowiskowe**
   ```bash
   export MUTALYZER_SETTINGS="$(pwd)/config.txt"
   export MUTALYZER_CACHE_DIR="/app/cache"
   ```

3. **Prekonfiguruj popularne referencje**
   ```bash
   mutalyzer_retriever --id NM_003002.2 --parse --split --output cache
   ```

### Optymalizacja testów
1. **Mock dla testów jednostkowych** - Unikaj rzeczywistych wywołań NCBI
2. **Cache testowy** - Przygotuj małą bazę referencji dla testów
3. **Izolacja testów** - Oddzielne cache dla każdego środowiska

## Następne kroki

### Krótkoterminowe
1. ✅ Integracja z oficjalnym pakietem - **ZREALIZOWANE**
2. 🔄 Poprawki w testach dla nowego formatu odpowiedzi
3. 🔄 Aktualizacja dokumentacji API

### Długoterminowe
1. 📋 Konfiguracja cache produkcyjnego
2. 📋 Monitorowanie wydajności
3. 📋 Integracja z mutalyzer mapper dla zaawansowanych funkcji

## Porównanie: przed i po integracji

### Przed (własna implementacja)
```python
# Symulacja/mock odpowiedzi
{
  "is_valid": True,
  "normalized_description": "c.274G>T"
}
```

### Po (oficjalny pakiet)
```python
# Pełna odpowiedź z oficjalnego Mutalyzer
{
  "is_valid": True,
  "normalized_description": "NM_003002.2:c.274G>T",
  "protein_description": "NM_003002.2(NP_002993.1):p.(Asp92Tyr)",
  "rna_description": "NM_003002.2:r.(274g>u)",
  "raw_mutalyzer_result": { /* pełne dane z Mutalyzer */ }
}
```

## Wnioski

Integracja z oficjalnym pakietem Mutalyzer znacząco poprawia jakość i funkcjonalność naszego API:

1. **Autentyczność** - Używamy tej samej biblioteki co oficjalne serwisy
2. **Kompletność** - Dostęp do wszystkich funkcji Mutalyzer
3. **Aktualność** - Automatyczne updates z nowymi regułami HGVS
4. **Społeczność** - Wsparcie szerokiej społeczności bioinformatycznej

Ta zmiana sprawia, że nasze API staje się profesjonalnym narzędziem gotowym do użycia w środowiskach produkcyjnych.