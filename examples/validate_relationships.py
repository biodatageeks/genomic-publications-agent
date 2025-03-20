#!/usr/bin/env python3
"""
Przykład użycia modułu ClinvarRelationshipValidator.

Ten skrypt pokazuje, jak używać walidatora relacji ClinVar do weryfikacji
wykrytych relacji genów, wariantów i chorób z danych literatury.

Użycie:
    python validate_relationships.py --input relationships.csv --output validation_report.json --email your.email@example.com
"""

import argparse
import logging
import sys
import os
from typing import Dict, List, Any

from src.clinvar_relationship_validator import ClinvarRelationshipValidator


def setup_logging(verbose: bool = False):
    """
    Konfiguruje system logowania.
    
    Args:
        verbose: Czy wyświetlać szczegółowe logi
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    
    # Wycisz zbyt szczegółowe logi z bibliotek
    if not verbose:
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def parse_arguments():
    """
    Przetwarza argumenty wiersza poleceń.
    
    Returns:
        Przetworzone argumenty
    """
    parser = argparse.ArgumentParser(
        description="Walidacja relacji geny-warianty-choroby przy użyciu danych ClinVar"
    )
    
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Ścieżka do pliku CSV z relacjami wygenerowanymi przez CooccurrenceContextAnalyzer"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Ścieżka do pliku wyjściowego z raportem walidacji (JSON lub CSV)"
    )
    
    parser.add_argument(
        "--email",
        "-e",
        required=True,
        help="Adres email używany do zapytań API NCBI/ClinVar"
    )
    
    parser.add_argument(
        "--api-key",
        "-k",
        help="Opcjonalny klucz API NCBI dla zwiększenia limitu zapytań"
    )
    
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv"],
        default="json",
        help="Format raportu wyjściowego (domyślnie: json)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Wyłącza cache'owanie zapytań API"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Wyświetla szczegółowe komunikaty logowania"
    )
    
    return parser.parse_args()


def main():
    """Główna funkcja programu."""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger("validate_relationships")
    
    # Sprawdź, czy plik wejściowy istnieje
    if not os.path.exists(args.input):
        logger.error(f"Plik wejściowy nie istnieje: {args.input}")
        sys.exit(1)
    
    # Utwórz walidator relacji
    logger.info("Inicjalizacja walidatora relacji ClinVar...")
    validator = ClinvarRelationshipValidator(
        email=args.email,
        api_key=args.api_key,
        use_cache=not args.no_cache
    )
    
    try:
        # Walidacja relacji
        logger.info(f"Rozpoczynam walidację relacji z pliku: {args.input}")
        validation_report = validator.validate_relationships_from_csv(args.input)
        
        # Zapisz raport walidacji
        logger.info(f"Zapisuję raport walidacji do pliku: {args.output}")
        validator.save_validation_report(args.output, format_type=args.format)
        
        # Wyświetl statystyki
        stats = validation_report.get_statistics()
        
        logger.info("=== Statystyki walidacji ===")
        logger.info(f"Łączna liczba relacji: {stats['total']}")
        logger.info(f"Potwierdzone relacje: {stats['valid']} ({stats['percent_valid']:.2f}%)")
        logger.info(f"Niepotwierdzone relacje: {stats['invalid']}")
        logger.info(f"Relacje z błędami: {stats['errors']}")
        logger.info("==========================")
        
        logger.info(f"Walidacja zakończona pomyślnie. Raport zapisany w: {args.output}")
        
    except Exception as e:
        logger.error(f"Błąd podczas walidacji relacji: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 