#!/usr/bin/env python3
"""
Moduł narzędziowy zawierający wspólne funkcje używane w różnych skryptach.
"""
import os
import sys
import json
import logging
from typing import Set, Dict, Any, List, Optional, Union

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Stałe definicje katalogów
DIRS = {
    'pmids': 'data/pmids',
    'csv': 'data/csv',
    'batch_results': 'data/batch_results',
    'results': 'data/results',
    'experiments': 'data/results/experiments',
    'images': 'data/results/images',
    'temp': 'data/temp',
}

def ensure_dirs_exist() -> None:
    """
    Tworzy wszystkie wymagane katalogi, jeśli nie istnieją.
    """
    for dir_path in DIRS.values():
        os.makedirs(dir_path, exist_ok=True)

def get_path(file_path: str, default_dir: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku, dodając prefiks katalogu, jeśli nie podano pełnej ścieżki.
    
    Args:
        file_path: Ścieżka do pliku
        default_dir: Domyślny katalog, jeśli nie podano pełnej ścieżki
        
    Returns:
        Pełna ścieżka do pliku
    """
    if not file_path:
        raise ValueError("Ścieżka do pliku nie może być pusta")
        
    if '/' not in file_path:
        os.makedirs(default_dir, exist_ok=True)
        return os.path.join(default_dir, file_path)
    else:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        return file_path

def get_pmids_path(file_path: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku z PMID-ami.
    
    Args:
        file_path: Ścieżka do pliku
        
    Returns:
        Pełna ścieżka do pliku
    """
    return get_path(file_path, DIRS['pmids'])

def get_csv_path(file_path: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku CSV.
    
    Args:
        file_path: Ścieżka do pliku
        
    Returns:
        Pełna ścieżka do pliku
    """
    return get_path(file_path, DIRS['csv'])

def get_experiments_path(file_path: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku z wynikami eksperymentów.
    
    Args:
        file_path: Ścieżka do pliku
        
    Returns:
        Pełna ścieżka do pliku
    """
    return get_path(file_path, DIRS['experiments'])

def get_images_path(file_path: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku obrazu.
    
    Args:
        file_path: Ścieżka do pliku
        
    Returns:
        Pełna ścieżka do pliku
    """
    return get_path(file_path, DIRS['images'])

def load_pmids_from_file(input_file: str) -> Set[str]:
    """
    Wczytuje PMID-y z pliku tekstowego.
    
    Args:
        input_file: Ścieżka do pliku z listą PMID-ów
        
    Returns:
        Zbiór unikalnych PMID-ów
    """
    try:
        input_file = get_pmids_path(input_file)
        with open(input_file, 'r', encoding='utf-8') as f:
            pmids = {line.strip() for line in f if line.strip()}
        logger.info(f"Wczytano {len(pmids)} PMIDów z pliku {input_file}")
        return pmids
    except Exception as e:
        logger.error(f"Błąd odczytu pliku {input_file}: {str(e)}")
        raise Exception(f"Nie można wczytać pliku z PMIDami: {e}")

def load_csv_pmids(csv_file: str, pmid_column: int = 0, has_header: bool = True) -> Set[str]:
    """
    Wczytuje PMID-y z pliku CSV.
    
    Args:
        csv_file: Ścieżka do pliku CSV
        pmid_column: Indeks kolumny z PMID-ami (domyślnie 0 - pierwsza kolumna)
        has_header: Czy plik CSV ma nagłówek
        
    Returns:
        Zbiór unikalnych PMID-ów
    """
    try:
        csv_file = get_csv_path(csv_file)
        pmids = set()
        with open(csv_file, 'r', encoding='utf-8') as f:
            if has_header:
                next(f)  # Pomiń nagłówek
            for line in f:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) > pmid_column:
                        pmid = parts[pmid_column].strip()
                        if pmid:
                            pmids.add(pmid)
        logger.info(f"Wczytano {len(pmids)} PMIDów z pliku CSV {csv_file}")
        return pmids
    except Exception as e:
        logger.error(f"Błąd odczytu pliku CSV {csv_file}: {str(e)}")
        raise Exception(f"Nie można wczytać pliku CSV: {e}")

def save_pmids_to_file(pmids: Set[str], output_file: str) -> None:
    """
    Zapisuje PMID-y do pliku tekstowego.
    
    Args:
        pmids: Zbiór PMID-ów do zapisania
        output_file: Ścieżka do pliku wyjściowego
    """
    try:
        output_file = get_pmids_path(output_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            for pmid in sorted(pmids):
                f.write(f"{pmid}\n")
        logger.info(f"Zapisano {len(pmids)} PMIDów do pliku {output_file}")
    except Exception as e:
        logger.error(f"Błąd zapisywania do pliku {output_file}: {str(e)}")
        raise Exception(f"Nie można zapisać pliku z PMIDami: {e}")

def load_json_file(json_file: str) -> Dict[str, Any]:
    """
    Wczytuje dane z pliku JSON.
    
    Args:
        json_file: Ścieżka do pliku JSON
        
    Returns:
        Dane z pliku JSON
    """
    try:
        json_file = get_experiments_path(json_file)
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Błąd odczytu pliku JSON {json_file}: {str(e)}")
        raise Exception(f"Nie można wczytać pliku JSON: {e}")

def save_json_file(data: Union[Dict[str, Any], List[Any]], output_file: str) -> None:
    """
    Zapisuje dane do pliku JSON.
    
    Args:
        data: Dane do zapisania
        output_file: Ścieżka do pliku wyjściowego
    """
    try:
        output_file = get_experiments_path(output_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Zapisano dane do pliku JSON {output_file}")
    except Exception as e:
        logger.error(f"Błąd zapisywania do pliku JSON {output_file}: {str(e)}")
        raise Exception(f"Nie można zapisać pliku JSON: {e}")

def append_to_json_file(new_item: Any, json_file: str) -> None:
    """
    Dodaje nowy element do listy w pliku JSON.
    Jeśli plik nie istnieje, tworzy nowy z jednym elementem.
    Jeśli plik istnieje, ale nie zawiera listy, tworzy nową listę z elementem.
    
    Args:
        new_item: Element do dodania
        json_file: Ścieżka do pliku JSON
    """
    json_file = get_experiments_path(json_file)
    
    # Sprawdź, czy plik istnieje i zawiera dane
    existing_items = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_items = json.load(f)
                if not isinstance(existing_items, list):
                    existing_items = [existing_items]
        except (json.JSONDecodeError, Exception):
            existing_items = []
    
    # Dodaj nowy element i zapisz
    existing_items.append(new_item)
    
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_items, f, indent=2)
        logger.info(f"Dodano nowy element do pliku JSON {json_file}")
    except Exception as e:
        logger.error(f"Błąd zapisywania do pliku JSON {json_file}: {str(e)}")
        raise Exception(f"Nie można zapisać pliku JSON: {e}")

def initialize_json_file(json_file: str, initial_data: Any = None) -> None:
    """
    Inicjalizuje plik JSON z pustą listą lub podanymi danymi.
    
    Args:
        json_file: Ścieżka do pliku JSON
        initial_data: Dane początkowe (domyślnie pusta lista)
    """
    try:
        json_file = get_experiments_path(json_file)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data if initial_data is not None else [], f)
        logger.info(f"Zainicjalizowano plik JSON {json_file}")
    except Exception as e:
        logger.error(f"Błąd inicjalizacji pliku JSON {json_file}: {str(e)}")
        raise Exception(f"Nie można zainicjalizować pliku JSON: {e}") 