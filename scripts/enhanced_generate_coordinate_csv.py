#!/usr/bin/env python3
"""
Ulepszona wersja skryptu do generowania tabeli CSV z genami, chorobami i wariantami na podstawie identyfikatorów PubMed.
Wykorzystuje ulepszoną klasę EnhancedLlmContextAnalyzer do lepszej obsługi błędów parsowania JSON.
"""

import argparse
import logging
import os
import sys
import time
from typing import List, Optional

# Dodaj ścieżkę do głównego katalogu projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.generate_coordinate_csv import analyze_pmids
from src.llm_context_analyzer.enhanced_llm_context_analyzer import EnhancedLlmContextAnalyzer
from src.Config import Config

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def enhanced_analyze_pmids(pmids: List[str],
                         output_csv: str,
                         email: Optional[str] = None,
                         llm_model: Optional[str] = None,
                         use_llm: bool = True,
                         only_llm: bool = False,
                         debug_mode: bool = False,
                         retry_on_failure: bool = True,
                         max_retries: int = 3,
                         retry_delay: int = 5):
    """
    Ulepszona wersja funkcji do analizy identyfikatorów PubMed.
    Używa EnhancedLlmContextAnalyzer do lepszej obsługi błędów i dodaje możliwość 
    ponownych prób w przypadku niepowodzenia.
    
    Args:
        pmids: Lista identyfikatorów PubMed do analizy
        output_csv: Ścieżka do pliku wyjściowego CSV
        email: Adres email do API PubTator (opcjonalny)
        llm_model: Nazwa modelu LLM do użycia (opcjonalny)
        use_llm: Czy używać analizy LLM
        only_llm: Czy używać tylko analizy LLM (bez współwystępowania)
        debug_mode: Czy włączyć tryb debugowania
        retry_on_failure: Czy próbować ponownie w przypadku niepowodzenia
        max_retries: Maksymalna liczba ponownych prób
        retry_delay: Opóźnienie między kolejnymi próbami (w sekundach)
        
    Returns:
        DataFrame z wynikami
    """
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        try:
            if retries > 0:
                logger.info(f"Ponowna próba {retries}/{max_retries}...")
            
            # Uruchom standardową analizę, ale z ulepszonymi parametrami
            return analyze_pmids(
                pmids=pmids,
                output_csv=output_csv,
                email=email,
                llm_model=llm_model,
                use_llm=use_llm,
                only_llm=only_llm,
                debug_mode=debug_mode,
                llm_context_analyzer_class=EnhancedLlmContextAnalyzer  # Użyj ulepszonej klasy analizatora
            )
        
        except Exception as e:
            last_error = e
            logger.error(f"Błąd podczas analizy: {str(e)}")
            
            if not retry_on_failure or retries >= max_retries:
                break
            
            retries += 1
            logger.info(f"Oczekiwanie {retry_delay} sekund przed ponowną próbą...")
            time.sleep(retry_delay)
    
    # Jeśli wszystkie próby zawiodły, podnieś ostatni błąd
    if last_error:
        raise last_error
    
    return None


def main():
    """Główna funkcja skryptu."""
    # Załaduj konfigurację
    config = Config()
    default_email = config.get_contact_email()
    default_model = config.get_llm_model_name()
    
    parser = argparse.ArgumentParser(
        description="Ulepszona wersja skryptu do generowania tabeli CSV z genami, chorobami i wariantami"
    )
    
    parser.add_argument("-p", "--pmids", nargs="+", required=False,
                        help="Lista identyfikatorów PubMed do analizy")
    parser.add_argument("-f", "--file", type=str,
                        help="Plik zawierający identyfikatory PubMed, jeden na linię")
    parser.add_argument("-o", "--output", required=True, 
                        help="Ścieżka do pliku wyjściowego CSV")
    parser.add_argument("-m", "--model", default=default_model,
                        help=f"Nazwa modelu LLM do użycia (domyślnie: {default_model})")
    parser.add_argument("-e", "--email", default=default_email,
                        help=f"Adres email do API PubTator (domyślnie: {default_email})")
    parser.add_argument("--no-llm", action="store_true",
                        help="Wyłącz analizę LLM (używaj tylko współwystępowania)")
    parser.add_argument("--only-llm", action="store_true",
                        help="Używaj tylko analizy LLM (wyłącz współwystępowanie)")
    parser.add_argument("--debug", action="store_true",
                        help="Zapisz informacje debugowania (surowe wyjście LLM)")
    parser.add_argument("--no-retry", action="store_true",
                        help="Wyłącz automatyczne ponowne próby w przypadku niepowodzenia")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Maksymalna liczba ponownych prób w przypadku niepowodzenia (domyślnie: 3)")
    parser.add_argument("--retry-delay", type=int, default=5,
                        help="Opóźnienie między kolejnymi próbami w sekundach (domyślnie: 5)")
    
    args = parser.parse_args()
    
    # Zbierz identyfikatory PubMed z argumentów lub pliku
    pmids = []
    
    if args.pmids:
        pmids.extend(args.pmids)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_pmids = [line.strip() for line in f if line.strip()]
                pmids.extend(file_pmids)
        except Exception as e:
            logger.error(f"Błąd odczytu pliku PMID: {str(e)}")
            sys.exit(1)
    
    if not pmids:
        logger.error("Nie podano identyfikatorów PubMed. Użyj opcji --pmids lub --file.")
        sys.exit(1)
    
    # Wykonaj analizę
    try:
        df = enhanced_analyze_pmids(
            pmids=pmids,
            output_csv=args.output,
            email=args.email,
            llm_model=args.model,
            use_llm=not args.no_llm,
            only_llm=args.only_llm,
            debug_mode=args.debug,
            retry_on_failure=not args.no_retry,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay
        )
        
        if df is not None:
            logger.info(f"Analiza zakończona pomyślnie. Wygenerowano CSV z {len(df)} wpisami.")
        else:
            logger.info("Analiza zakończona pomyślnie, ale nie zwrócono danych.")
    except Exception as e:
        logger.error(f"Analiza nie powiodła się: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 