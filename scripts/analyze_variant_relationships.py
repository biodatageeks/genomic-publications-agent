#!/usr/bin/env python3
"""
Skrypt analizujący współwystępowanie wariantów genetycznych z innymi encjami biologicznymi
w wybranych publikacjach z dużą liczbą wariantów.
"""

import argparse
import logging
import os
import sys
import pandas as pd
from typing import List, Dict, Any, Optional

# Dodanie ścieżki do katalogu głównego projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pubtator_client.pubtator_client import PubTatorClient
from src.cooccurrence_context_analyzer.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer
from src.pubtator_client.exceptions import PubTatorError

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lista PMIDs wybranych publikacji z dużą liczbą wariantów
# Te publikacje zostały wybrane jako przykłady o bogatej zawartości wariantów
SELECTED_PMIDS = [
    "33417880",  # Publikacja o COVID-19 i wariantach SARS-CoV-2
    "33705364",  # Publikacja o wariantach BRAF w czerniaku
    "34268513",  # Publikacja o wariantach germinanych w raku trzustki
    "34002096",  # Publikacja o wariantach w raku prostaty
    "33208827",  # Publikacja o wariantach w genie BRCA1/2
]

def get_publications_with_variants(pubtator_client: PubTatorClient, 
                                   min_variants: int = 5, 
                                   max_publications: int = 10) -> List[str]:
    """
    Pomocnicza funkcja do znajdowania publikacji z dużą liczbą wariantów.
    
    Args:
        pubtator_client: Instancja klienta PubTator
        min_variants: Minimalna liczba wariantów w publikacji
        max_publications: Maksymalna liczba publikacji do zwrócenia
        
    Returns:
        Lista PMIDs publikacji z dużą liczbą wariantów
    """
    # Szukamy publikacji z adnotacjami wariantów
    # W rzeczywistej implementacji potrzebne byłoby bardziej zaawansowane wyszukiwanie
    # Na potrzeby demonstracji używamy predefiniowanej listy
    return SELECTED_PMIDS[:max_publications]

def analyze_publications_and_create_table(pmids: List[str], 
                                         output_csv: str, 
                                         output_excel: Optional[str] = None,
                                         email: str = "sitekwb@gmail.com") -> Optional[pd.DataFrame]:
    """
    Analizuje publikacje i tworzy tabelę z relacjami.
    
    Args:
        pmids: Lista PMIDs do analizy
        output_csv: Ścieżka do pliku wyjściowego CSV
        output_excel: Opcjonalna ścieżka do pliku wyjściowego Excel
        email: Adres email dla API PubTator (używany w metadanych)
        
    Returns:
        DataFrame z danymi relacji lub None, jeśli wystąpił błąd
    """
    logger.info(f"Rozpoczęcie analizy dla {len(pmids)} publikacji")
    
    # Inicjalizacja klientów
    pubtator_client = PubTatorClient()  # Usunięto parametr email
    analyzer = CooccurrenceContextAnalyzer(pubtator_client=pubtator_client)
    
    # Dodanie informacji o emailu do logu
    logger.info(f"Używany adres email kontaktowy: {email}")
    
    # Analiza publikacji
    try:
        relationships = analyzer.analyze_publications(pmids)
        logger.info(f"Znaleziono {len(relationships)} relacji w publikacjach")
        
        if not relationships:
            logger.warning("Nie znaleziono żadnych relacji wariantów!")
            return None
        
        # Zapisanie relacji do CSV
        analyzer.save_relationships_to_csv(relationships, output_csv)
        logger.info(f"Zapisano relacje do pliku CSV: {output_csv}")
        
        # Tworzenie DataFrame do dalszej analizy
        df = pd.read_csv(output_csv)
        
        # Obliczanie statystyk
        stats = {
            "Liczba unikalnych wariantów": df["variant_text"].nunique(),
            "Liczba unikalnych genów": df["gene_text"].nunique(),
            "Liczba unikalnych chorób": df["disease_text"].nunique(),
            "Najczęstsze warianty": df["variant_text"].value_counts().head(5).to_dict(),
            "Najczęstsze geny": df["gene_text"].value_counts().head(5).to_dict(),
            "Najczęstsze choroby": df["disease_text"].value_counts().head(5).to_dict(),
        }
        
        logger.info(f"Statystyki analizy: {stats}")
        
        # Opcjonalny zapis do Excela
        if output_excel:
            try:
                with pd.ExcelWriter(output_excel) as writer:
                    df.to_excel(writer, sheet_name="Relacje", index=False)
                    # Dodanie arkusza ze statystykami
                    stats_df = pd.DataFrame([stats])
                    stats_df.to_excel(writer, sheet_name="Statystyki", index=False)
                logger.info(f"Zapisano dane do pliku Excel: {output_excel}")
            except ImportError:
                logger.warning("Nie można zapisać do pliku Excel: brakuje modułu 'openpyxl'. "
                               "Zainstaluj go używając 'pip install openpyxl'.")
                logger.info("Dane zostały zapisane tylko w formacie CSV.")
            except Exception as e:
                logger.warning(f"Nie można zapisać do pliku Excel: {str(e)}")
        
        return df
    
    except PubTatorError as e:
        logger.error(f"Błąd podczas analizy publikacji: {str(e)}")
        return None

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Analiza współwystępowania wariantów genetycznych w publikacjach.")
    parser.add_argument("--output", "-o", type=str, default="variant_relationships.csv",
                        help="Ścieżka do pliku wyjściowego CSV (domyślnie: variant_relationships.csv)")
    parser.add_argument("--excel", "-e", type=str, default="variant_relationships.xlsx",
                        help="Ścieżka do pliku wyjściowego Excel (domyślnie: variant_relationships.xlsx)")
    parser.add_argument("--email", type=str, default="sitekwb@gmail.com",
                        help="Adres email kontaktowy (dla metadanych API)")
    parser.add_argument("--pmids", type=str, nargs="+",
                        help="Lista identyfikatorów PMID do analizy (opcjonalne, domyślnie używa predefiniowanej listy)")
    
    args = parser.parse_args()
    
    # Jeśli podano PMIDs, użyj ich, w przeciwnym razie użyj domyślnej listy
    pmids = args.pmids if args.pmids else SELECTED_PMIDS
    
    # Upewnij się, że katalogi wyjściowe istnieją
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    if args.excel:
        os.makedirs(os.path.dirname(os.path.abspath(args.excel)), exist_ok=True)
    
    # Uruchomienie analizy
    df = analyze_publications_and_create_table(
        pmids=pmids,
        output_csv=args.output,
        output_excel=args.excel,
        email=args.email
    )
    
    if df is not None:
        print(f"\nAnaliza zakończona sukcesem! Zapisano dane do plików:")
        print(f" - CSV: {args.output}")
        try:
            import openpyxl
            if args.excel:
                print(f" - Excel: {args.excel}")
        except ImportError:
            print("Uwaga: Nie można zapisać do pliku Excel - brakuje modułu 'openpyxl'.")
            print("Zainstaluj go używając: pip install openpyxl")
        
        print("\nPodsumowanie analizy:")
        print(f" - Liczba relacji: {len(df)}")
        print(f" - Liczba unikalnych wariantów: {df['variant_text'].nunique()}")
        print(f" - Liczba unikalnych genów: {df['gene_text'].nunique()}")
        print(f" - Liczba unikalnych chorób: {df['disease_text'].nunique()}")
        
        top_variants = df["variant_text"].value_counts().head(3)
        print("\nNajczęstsze warianty:")
        for variant, count in top_variants.items():
            if variant:
                print(f" - {variant}: {count} wystąpień")
        
        print("\nZakończono pomyślnie!")
    else:
        print("\nAnaliza nie powiodła się. Sprawdź logi.")

if __name__ == "__main__":
    main() 