#!/usr/bin/env python3
"""
Skrypt do analizy publikacji biomedycznych przy użyciu LlmContextAnalyzer.
Wykorzystuje model językowy do analizy relacji między bytami biomedycznymi.
"""

import argparse
import logging
import sys
import os
import pandas as pd
from typing import List, Optional

from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer
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
                        llm_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
                        email: str = "przyklad@example.com") -> Optional[pd.DataFrame]:
    """
    Analizuje publikacje i tworzy tabelę z relacjami przy użyciu LLM.
    
    Args:
        pmids: Lista PMIDs do analizy
        output_csv: Ścieżka do pliku wyjściowego CSV
        output_json: Opcjonalna ścieżka do pliku wyjściowego JSON
        llm_model: Nazwa modelu LLM do użycia
        email: Adres email dla API PubTator (używany w metadanych)
        
    Returns:
        DataFrame z danymi relacji lub None, jeśli wystąpił błąd
    """
    logger.info(f"Rozpoczęcie analizy dla {len(pmids)} publikacji przy użyciu modelu {llm_model}")
    
    # Inicjalizacja klientów
    pubtator_client = PubTatorClient()
    analyzer = LlmContextAnalyzer(pubtator_client=pubtator_client, llm_model_name=llm_model)
    
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
    parser = argparse.ArgumentParser(description="Analiza publikacji biomedycznych z użyciem LLM")
    
    parser.add_argument("-p", "--pmids", nargs="+", required=True,
                        help="Lista PMIDs do analizy")
    parser.add_argument("-o", "--output", required=True, 
                        help="Ścieżka do pliku wyjściowego CSV")
    parser.add_argument("-j", "--json", 
                        help="Opcjonalna ścieżka do pliku wyjściowego JSON")
    parser.add_argument("-m", "--model", default="meta-llama/Meta-Llama-3.1-8B-Instruct",
                        help="Nazwa modelu LLM do użycia")
    parser.add_argument("-e", "--email", default="przyklad@example.com",
                        help="Adres email dla API PubTator")
    
    args = parser.parse_args()
    
    # Analiza publikacji
    df = analyze_publications(
        pmids=args.pmids,
        output_csv=args.output,
        output_json=args.json,
        llm_model=args.model,
        email=args.email
    )
    
    if df is not None:
        logger.info(f"Analiza zakończona pomyślnie. Znaleziono {len(df)} wpisów relacji.")
    else:
        logger.error("Analiza zakończona niepowodzeniem.")
        sys.exit(1)


if __name__ == "__main__":
    main() 