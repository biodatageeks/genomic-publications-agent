#!/usr/bin/env python3
"""
Skrypt do analizy publikacji biomedycznych przy użyciu CooccurrenceContextAnalyzer.
Wykrywa relacje między bytami biomedycznymi na podstawie ich współwystępowania.
"""

import argparse
import logging
import sys
import os
import pandas as pd
from typing import List, Optional

from src.cooccurrence_context_analyzer.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer
from src.pubtator_client.pubtator_client import PubTatorClient

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def analyze_publications(pmids: List[str], 
                        output_csv: str, 
                        output_json: Optional[str] = None,
                        email: str = "przyklad@example.com") -> Optional[pd.DataFrame]:
    """
    Analizuje publikacje i tworzy tabelę z relacjami na podstawie współwystępowania.
    
    Args:
        pmids: Lista PMIDs do analizy
        output_csv: Ścieżka do pliku wyjściowego CSV
        output_json: Opcjonalna ścieżka do pliku wyjściowego JSON
        email: Adres email dla API PubTator (używany w metadanych)
        
    Returns:
        DataFrame z danymi relacji lub None, jeśli wystąpił błąd
    """
    logger.info(f"Rozpoczęcie analizy dla {len(pmids)} publikacji przy użyciu współwystępowania")
    
    # Inicjalizacja klientów
    pubtator_client = PubTatorClient()
    analyzer = CooccurrenceContextAnalyzer(pubtator_client=pubtator_client)
    
    # Dodanie informacji o emailu do logu
    logger.info(f"Używany adres email kontaktowy: {email}")
    
    try:
        # Analiza publikacji
        logger.info("Rozpoczęcie analizy publikacji...")
        relationships = analyzer.analyze_publications(pmids)
        logger.info(f"Znaleziono {len(relationships)} relacji w publikacjach")
        
        # Zapis do plików
        analyzer.save_relationships_to_csv(relationships, output_csv)
        logger.info(f"Zapisano dane do pliku CSV: {output_csv}")
        
        if output_json:
            analyzer.save_relationships_to_json(relationships, output_json)
            logger.info(f"Zapisano dane do pliku JSON: {output_json}")
        
        # Konwersja do DataFrame
        df = pd.read_csv(output_csv)
        return df
        
    except Exception as e:
        logger.error(f"Wystąpił błąd podczas analizy: {str(e)}")
        return None


def main():
    """Funkcja główna skryptu."""
    parser = argparse.ArgumentParser(description="Analiza publikacji biomedycznych na podstawie współwystępowania")
    
    parser.add_argument("-p", "--pmids", nargs="+", required=True,
                        help="Lista PMIDs do analizy")
    parser.add_argument("-o", "--output", required=True, 
                        help="Ścieżka do pliku wyjściowego CSV")
    parser.add_argument("-j", "--json", 
                        help="Opcjonalna ścieżka do pliku wyjściowego JSON")
    parser.add_argument("-e", "--email", default="przyklad@example.com",
                        help="Adres email dla API PubTator")
    
    args = parser.parse_args()
    
    # Analiza publikacji
    df = analyze_publications(
        pmids=args.pmids,
        output_csv=args.output,
        output_json=args.json,
        email=args.email
    )
    
    if df is not None:
        logger.info(f"Analiza zakończona pomyślnie. Znaleziono {len(df)} wpisów relacji.")
    else:
        logger.error("Analiza zakończona niepowodzeniem.")
        sys.exit(1)


if __name__ == "__main__":
    main() 