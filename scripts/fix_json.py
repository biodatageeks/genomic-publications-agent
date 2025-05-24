#!/usr/bin/env python3
"""
Narzędzie do naprawy niepoprawnych odpowiedzi JSON z modeli LLM.
"""

import sys
import json
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def clean_json_response(response: str) -> str:
    """
    Czyści odpowiedź LLM, aby uzyskać poprawny format JSON.
    
    Args:
        response: Odpowiedź z LLM
        
    Returns:
        Oczyszczony ciąg JSON
    """
    # Znajdź pierwszy '{' i ostatni '}'
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
        # Jeśli nie znaleziono poprawnego JSON, zwróć pusty obiekt
        logger.warning("Nie można znaleźć obiektu JSON w odpowiedzi")
        return "{}"
    
    # Wyodrębnij JSON z odpowiedzi
    json_str = response[start_idx:end_idx+1]
    return json_str

def fix_trailing_commas(json_str: str) -> str:
    """
    Naprawia błędy związane z przecinkami końcowymi w JSON.
    
    Args:
        json_str: Ciąg JSON do naprawy
        
    Returns:
        Naprawiony ciąg JSON
    """
    # Usuń przecinki po ostatnim elemencie w obiektach
    json_str = re.sub(r',(\s*})', r'\1', json_str)
    
    # Usuń przecinki po ostatnim elemencie w tablicach
    json_str = re.sub(r',(\s*])', r'\1', json_str)
    
    return json_str

def fix_missing_quotes(json_str: str) -> str:
    """
    Próbuje naprawić brakujące cudzysłowy w kluczach i wartościach.
    
    Args:
        json_str: Ciąg JSON do naprawy
        
    Returns:
        Naprawiony ciąg JSON
    """
    # Napraw klucze bez cudzysłowów
    json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', json_str)
    
    return json_str

def fix_inconsistent_quotes(json_str: str) -> str:
    """
    Naprawia niekonsekwentne cudzysłowy (miesza ' i ").
    
    Args:
        json_str: Ciąg JSON do naprawy
        
    Returns:
        Naprawiony ciąg JSON
    """
    # Zamień wszystkie pojedyncze cudzysłowy na podwójne
    in_string = False
    result = []
    
    i = 0
    while i < len(json_str):
        char = json_str[i]
        
        if char == '"':
            # Rozpocznij lub zakończ ciąg znaków z podwójnymi cudzysłowami
            in_string = not in_string
            result.append(char)
        elif char == "'" and not in_string:
            # Zamień pojedyncze cudzysłowy na podwójne poza ciągami znaków
            result.append('"')
        else:
            result.append(char)
        
        i += 1
    
    return ''.join(result)

def attempt_json_fix(json_str: str) -> str:
    """
    Próbuje naprawić niepoprawny JSON, stosując różne metody naprawcze.
    
    Args:
        json_str: Potencjalnie niepoprawny ciąg JSON
        
    Returns:
        Naprawiony ciąg JSON (lub oryginalny, jeśli naprawa się nie powiodła)
    """
    try:
        # Najpierw sprawdź, czy JSON jest już poprawny
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError as e:
        logger.info(f"Wykryto błąd JSON: {str(e)}")
        
        # Zastosuj różne metody naprawcze
        fixed_json = json_str
        
        # Krok 1: Napraw przecinki końcowe
        fixed_json = fix_trailing_commas(fixed_json)
        
        # Krok 2: Napraw brakujące cudzysłowy
        fixed_json = fix_missing_quotes(fixed_json)
        
        # Krok 3: Napraw niekonsekwentne cudzysłowy
        fixed_json = fix_inconsistent_quotes(fixed_json)
        
        try:
            # Sprawdź, czy naprawiony JSON jest poprawny
            json.loads(fixed_json)
            logger.info("Naprawiono JSON")
            return fixed_json
        except json.JSONDecodeError:
            logger.warning("Nie udało się naprawić JSON")
            return json_str

def main():
    if len(sys.argv) < 2:
        print("Sposób użycia: python fix_json.py <plik_json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Najpierw wyczyść, aby uzyskać tylko część JSON
        cleaned_json = clean_json_response(content)
        
        # Próba naprawy błędów w JSON
        fixed_json = attempt_json_fix(cleaned_json)
        
        # Zapisz naprawiony JSON do nowego pliku
        output_file = input_file + '.fixed'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(fixed_json)
        
        print(f"Naprawiony JSON zapisano do: {output_file}")
        
        # Spróbuj załadować i zwizualizować naprawiony JSON
        try:
            data = json.loads(fixed_json)
            print("\nZawartość JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError as e:
            print(f"Nie udało się sparsować naprawionego JSON: {str(e)}")
    
    except Exception as e:
        print(f"Błąd: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 