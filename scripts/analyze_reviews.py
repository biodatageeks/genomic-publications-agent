#!/usr/bin/env python3
"""
Skrypt analizujący publikacje biomedyczne zawierające warianty genetyczne, geny i choroby.
Wyszukuje relacje między tymi encjami i generuje tabelę oraz wizualizację wyników.
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

# Lista PMIDów do analizy, zebranych z plików w projekcie
PMIDS = [
    # Z plików w data/pubmed-articles
    "18836447", "21441262", "22996659", "23502222", "34799090",
    
    # Z plików literatury w plikach CSV
    "11175783", "11254675", "11254676", "11254677", "11254678", 
    "11286503", "11355022", "12021216", "12192640", "12459590", 
    "14684687", "14760718", "15146197", "15454494", "15489334", 
    "15616553", "15723069", "16007107", "16237147", "16331359", 
    "16380919", "16467226", "16628248", "16670017", "16757811", 
    "16825278", "17031701", "17142316", "17186469", "17515542", 
    "17662803", "17804648", "17967973", "17984403", "18156156", 
    "18220430", "18423520", "18684880", "19019335", "19060906", 
    "19525978", "19644445", "20012913", "20031530", "20072694",
    
    # PMIDy z innych źródeł (używane wcześniej w testach)
    "34261372", "33208827", "33417880", "33705364", "31324762"
]

def analyze_publications(pmids: List[str], 
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
    pubtator_client = PubTatorClient()
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
            "Liczba unikalnych publikacji": df["pmid"].nunique(),
            "Najczęstsze warianty": df["variant_text"].value_counts().head(10).to_dict(),
            "Najczęstsze geny": df["gene_text"].value_counts().head(10).to_dict(),
            "Najczęstsze choroby": df["disease_text"].value_counts().head(10).to_dict(),
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

def visualize_results(csv_file: str, output_prefix: str):
    """
    Wizualizuje wyniki analizy.
    
    Args:
        csv_file: Ścieżka do pliku CSV z relacjami
        output_prefix: Prefiks dla plików wyjściowych
    """
    # Wywołanie skryptu wizualizacyjnego
    import subprocess
    
    try:
        graph_output = f"{output_prefix}_graph.png"
        result = subprocess.run(
            ["python", "scripts/visualize_relationships.py", 
             "--input", csv_file, 
             "--output", graph_output],
            check=True, capture_output=True, text=True
        )
        logger.info(f"Wizualizacja zakończona sukcesem: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Błąd podczas wizualizacji: {e.stderr}")

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
                        help="Lista identyfikatorów PMID do analizy (opcjonalne, domyślnie używa predefiniowanych PMIDów)")
    
    args = parser.parse_args()
    
    # Upewnij się, że katalogi wyjściowe istnieją
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    if args.excel:
        os.makedirs(os.path.dirname(os.path.abspath(args.excel)), exist_ok=True)
    
    # Użyj PMIDów z argumentów lub z listy predefiniowanych
    pmids = args.pmids if args.pmids else PMIDS
    logger.info(f"Użycie {len(pmids)} PMIDów do analizy")
    
    # Uruchomienie analizy
    df = analyze_publications(
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
        
        # Generowanie statystyk i wizualizacji
        output_prefix = os.path.splitext(args.output)[0]
        visualize_results(args.output, output_prefix)
        
        # Wyświetlenie podsumowania
        print("\nPodsumowanie analizy:")
        print(f" - Liczba analizowanych publikacji: {df['pmid'].nunique()}")
        print(f" - Liczba znalezionych relacji: {len(df)}")
        print(f" - Liczba unikalnych wariantów: {df['variant_text'].nunique()}")
        print(f" - Liczba unikalnych genów: {df['gene_text'].nunique()}")
        print(f" - Liczba unikalnych chorób: {df['disease_text'].nunique()}")
        
        top_variants = df["variant_text"].value_counts().head(5)
        print("\nNajczęstsze warianty:")
        for variant, count in top_variants.items():
            if variant and str(variant).strip():
                print(f" - {variant}: {count} wystąpień")
        
        print("\nZakończono pomyślnie!")
    else:
        print("\nAnaliza nie powiodła się. Sprawdź logi.")

if __name__ == "__main__":
    main() 