"""
Demonstracja użycia klienta ClinVar.

Ten moduł zawiera przykłady użycia klienta ClinVar do różnych operacji,
takich jak wyszukiwanie wariantów, pobieranie informacji o wariantach,
oraz integracja z narzędziem coordinates_lit.
"""

import json
import logging
from typing import Dict, List, Any

from .clinvar_client import ClinVarClient
from .exceptions import ClinVarError, APIRequestError, InvalidParameterError


# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_client() -> ClinVarClient:
    """
    Tworzy i konfiguruje instancję klienta ClinVar.
    
    Returns:
        Skonfigurowana instancja ClinVarClient
    """
    # Zastąp poniższy adres email swoim adresem
    email = "twoj.email@domena.pl"
    
    # Opcjonalnie możesz dodać swój klucz API dla zwiększenia limitu zapytań
    # api_key = "twoj_klucz_api"
    
    return ClinVarClient(email=email)


def example_get_variant_by_id() -> None:
    """
    Przykład pobierania informacji o wariancie na podstawie identyfikatora ClinVar.
    """
    client = setup_client()
    
    # Przykładowe identyfikatory ClinVar
    vcv_id = "VCV000014076"  # Wariant w genie BRCA1
    
    try:
        # Pobierz informacje o wariancie w formacie JSON
        variant_info = client.get_variant_by_id(vcv_id)
        print(f"\n--- Informacje o wariancie {vcv_id} ---")
        print(f"Nazwa: {variant_info.get('name', 'N/A')}")
        print(f"Znaczenie kliniczne: {variant_info.get('clinical_significance', 'N/A')}")
        
        # Wyświetl geny
        genes = variant_info.get('genes', [])
        if genes:
            print("\nPowiązane geny:")
            for gene in genes:
                print(f"  - {gene.get('symbol', 'N/A')} (ID: {gene.get('id', 'N/A')})")
        
        # Wyświetl fenotypy
        phenotypes = variant_info.get('phenotypes', [])
        if phenotypes:
            print("\nPowiązane fenotypy:")
            for phenotype in phenotypes:
                print(f"  - {phenotype.get('name', 'N/A')} (ID: {phenotype.get('id', 'N/A')})")
        
        # Wyświetl koordynaty genomowe
        coordinates = variant_info.get('coordinates', [])
        if coordinates:
            print("\nKoordynaty genomowe:")
            for coords in coordinates:
                print(f"  - {coords.get('assembly', 'N/A')}: "
                      f"{coords.get('chromosome', 'N/A')}:"
                      f"{coords.get('start', 'N/A')}-{coords.get('stop', 'N/A')}")
                print(f"    Ref: {coords.get('reference_allele', 'N/A')}, "
                      f"Alt: {coords.get('alternate_allele', 'N/A')}")
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas pobierania informacji o wariancie: {str(e)}")


def example_search_by_coordinates() -> None:
    """
    Przykład wyszukiwania wariantów na podstawie koordynatów genomowych.
    """
    client = setup_client()
    
    # Przykładowe koordynaty: Rejon genu BRCA1
    chromosome = "17"
    start = 43044295
    end = 43125483
    
    try:
        print(f"\n--- Wyszukiwanie wariantów w regionie {chromosome}:{start}-{end} ---")
        variants = client.search_by_coordinates(
            chromosome=chromosome,
            start=start,
            end=end
        )
        
        print(f"Znaleziono {len(variants)} wariantów")
        
        # Wyświetl pierwsze 5 wariantów
        for i, variant in enumerate(variants[:5], 1):
            print(f"\nWariant {i}:")
            print(f"  ID: {variant.get('id', 'N/A')}")
            print(f"  Nazwa: {variant.get('name', 'N/A')}")
            print(f"  Typ: {variant.get('variation_type', 'N/A')}")
            print(f"  Znaczenie kliniczne: {variant.get('clinical_significance', 'N/A')}")
            
            # Wyświetl geny
            genes = variant.get('genes', [])
            if genes:
                print("  Geny:", ", ".join([g.get('symbol', 'N/A') for g in genes]))
    
    except InvalidParameterError as e:
        logger.error(f"Nieprawidłowe parametry: {str(e)}")
    except APIRequestError as e:
        logger.error(f"Błąd API: {str(e)}")
    except ClinVarError as e:
        logger.error(f"Ogólny błąd ClinVar: {str(e)}")


def example_search_by_gene() -> None:
    """
    Przykład wyszukiwania wariantów na podstawie symbolu genu.
    """
    client = setup_client()
    
    # Przykładowy gen
    gene_symbol = "BRCA1"
    
    try:
        print(f"\n--- Wyszukiwanie wariantów dla genu {gene_symbol} ---")
        variants = client.search_by_gene(gene_symbol)
        
        print(f"Znaleziono {len(variants)} wariantów")
        
        # Analiza znaczenia klinicznego
        significance_counts = {}
        for variant in variants:
            significance = variant.get('clinical_significance', 'Not provided')
            significance_counts[significance] = significance_counts.get(significance, 0) + 1
        
        print("\nRozkład znaczenia klinicznego:")
        for significance, count in significance_counts.items():
            print(f"  {significance}: {count} wariantów")
        
        # Wyświetl pierwsze 3 warianty patogenne
        print("\nPrzykładowe warianty patogenne:")
        pathogenic_count = 0
        for variant in variants:
            if variant.get('clinical_significance', '').lower() == 'pathogenic':
                pathogenic_count += 1
                print(f"  - {variant.get('name', 'N/A')}")
                if pathogenic_count >= 3:
                    break
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas wyszukiwania wariantów dla genu: {str(e)}")


def example_search_by_clinical_significance() -> None:
    """
    Przykład wyszukiwania wariantów na podstawie znaczenia klinicznego.
    """
    client = setup_client()
    
    # Przykładowe znaczenie kliniczne
    significance = "pathogenic"
    
    try:
        print(f"\n--- Wyszukiwanie wariantów o znaczeniu klinicznym: {significance} ---")
        variants = client.search_by_clinical_significance(significance)
        
        print(f"Znaleziono {len(variants)} wariantów")
        
        # Analiza genów
        gene_counts = {}
        for variant in variants:
            for gene in variant.get('genes', []):
                gene_symbol = gene.get('symbol', 'N/A')
                if gene_symbol != 'N/A':
                    gene_counts[gene_symbol] = gene_counts.get(gene_symbol, 0) + 1
        
        # Znajdź top 5 genów
        top_genes = sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("\nTop 5 genów z wariantami patogennymi:")
        for gene, count in top_genes:
            print(f"  {gene}: {count} wariantów")
    
    except InvalidParameterError as e:
        logger.error(f"Nieprawidłowe znaczenie kliniczne: {str(e)}")
    except ClinVarError as e:
        logger.error(f"Błąd podczas wyszukiwania wariantów: {str(e)}")


def example_search_by_rs_id() -> None:
    """
    Przykład wyszukiwania wariantów na podstawie identyfikatora rs.
    """
    client = setup_client()
    
    # Przykładowy identyfikator rs
    rs_id = "rs6025"  # Czynnik V Leiden
    
    try:
        print(f"\n--- Wyszukiwanie wariantów dla identyfikatora {rs_id} ---")
        variants = client.search_by_rs_id(rs_id)
        
        print(f"Znaleziono {len(variants)} wariantów")
        
        for variant in variants:
            print(f"\nWariant: {variant.get('name', 'N/A')}")
            print(f"Znaczenie kliniczne: {variant.get('clinical_significance', 'N/A')}")
            
            # Wyświetl fenotypy
            phenotypes = variant.get('phenotypes', [])
            if phenotypes:
                print("Powiązane fenotypy:")
                for phenotype in phenotypes:
                    print(f"  - {phenotype.get('name', 'N/A')}")
            
            # Wyświetl koordynaty
            coordinates = variant.get('coordinates', [])
            if coordinates:
                for coords in coordinates:
                    print(f"Koordynaty: {coords.get('chromosome', 'N/A')}:"
                          f"{coords.get('start', 'N/A')}-{coords.get('stop', 'N/A')}")
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas wyszukiwania wariantów dla rs ID: {str(e)}")


def example_search_by_phenotype() -> None:
    """
    Przykład wyszukiwania wariantów na podstawie fenotypu.
    """
    client = setup_client()
    
    # Przykładowy fenotyp
    phenotype = "Breast cancer"
    
    try:
        print(f"\n--- Wyszukiwanie wariantów dla fenotypu: {phenotype} ---")
        variants = client.search_by_phenotype(phenotype)
        
        print(f"Znaleziono {len(variants)} wariantów")
        
        # Analiza genów
        gene_counts = {}
        for variant in variants:
            for gene in variant.get('genes', []):
                gene_symbol = gene.get('symbol', 'N/A')
                if gene_symbol != 'N/A':
                    gene_counts[gene_symbol] = gene_counts.get(gene_symbol, 0) + 1
        
        # Znajdź top 5 genów
        top_genes = sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("\nTop 5 genów związanych z fenotypem:")
        for gene, count in top_genes:
            print(f"  {gene}: {count} wariantów")
            
        # Analiza znaczenia klinicznego
        significance_counts = {}
        for variant in variants:
            significance = variant.get('clinical_significance', 'Not provided')
            significance_counts[significance] = significance_counts.get(significance, 0) + 1
        
        print("\nRozkład znaczenia klinicznego:")
        for significance, count in sorted(significance_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {significance}: {count} wariantów")
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas wyszukiwania wariantów dla fenotypu: {str(e)}")


def example_integrate_with_coordinates_lit() -> None:
    """
    Przykład integracji danych z coordinates_lit z danymi ClinVar.
    """
    client = setup_client()
    
    # Przykładowe dane z coordinates_lit
    coordinates_data = [
        {
            "chromosome": "17",
            "start": 43044295,
            "end": 43125483,
            "source": "Publication 1",
            "title": "Analiza mutacji w genie BRCA1"
        },
        {
            "chromosome": "13",
            "start": 32315474,
            "end": 32400266,
            "source": "Publication 2",
            "title": "Analiza mutacji w genie BRCA2"
        }
    ]
    
    try:
        print("\n--- Integracja danych coordinates_lit z ClinVar ---")
        enriched_data = client.integrate_with_coordinates_lit(coordinates_data)
        
        for i, entry in enumerate(enriched_data, 1):
            print(f"\nRegion {i}: {entry['title']}")
            print(f"Koordynaty: {entry['chromosome']}:{entry['start']}-{entry['end']}")
            print(f"Źródło: {entry['source']}")
            
            clinvar_data = entry.get('clinvar_data', [])
            print(f"Liczba znalezionych wariantów ClinVar: {len(clinvar_data)}")
            
            if clinvar_data:
                # Analiza znaczenia klinicznego
                significance_counts = {}
                for variant in clinvar_data:
                    significance = variant.get('clinical_significance', 'Not provided')
                    significance_counts[significance] = significance_counts.get(significance, 0) + 1
                
                print("Rozkład znaczenia klinicznego:")
                for significance, count in significance_counts.items():
                    print(f"  {significance}: {count} wariantów")
                
                # Przykładowe warianty
                print("\nPrzykładowe warianty:")
                for j, variant in enumerate(clinvar_data[:3], 1):
                    print(f"  {j}. {variant.get('name', 'N/A')} - "
                          f"{variant.get('clinical_significance', 'N/A')}")
        
        # Zapis wzbogaconych danych do pliku JSON
        with open('clinvar_enriched_data.json', 'w') as f:
            json.dump(enriched_data, f, indent=2)
        print("\nWzbogacone dane zapisano do pliku clinvar_enriched_data.json")
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas integracji danych: {str(e)}")


def example_get_variant_summary() -> None:
    """
    Przykład pobierania podsumowania wariantu.
    """
    client = setup_client()
    
    # Przykładowy identyfikator wariantu
    variant_id = "VCV000014076"
    
    try:
        print(f"\n--- Podsumowanie wariantu {variant_id} ---")
        summary = client.get_variant_summary(variant_id)
        
        for key, value in summary.items():
            if isinstance(value, list):
                if value:
                    print(f"{key}:")
                    for item in value:
                        if isinstance(item, dict):
                            print(f"  - {item}")
                        else:
                            print(f"  - {item}")
                else:
                    print(f"{key}: []")
            else:
                print(f"{key}: {value}")
    
    except ClinVarError as e:
        logger.error(f"Błąd podczas pobierania podsumowania wariantu: {str(e)}")


def run_all_examples() -> None:
    """
    Uruchamia wszystkie przykłady użycia klienta ClinVar.
    """
    examples = [
        example_get_variant_by_id,
        example_search_by_coordinates,
        example_search_by_gene,
        example_search_by_clinical_significance,
        example_search_by_rs_id,
        example_search_by_phenotype,
        example_integrate_with_coordinates_lit,
        example_get_variant_summary
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "-" * 80)
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas wykonywania przykładu {example.__name__}: {str(e)}")


if __name__ == "__main__":
    print("=== Demonstracja klienta ClinVar ===\n")
    print("UWAGA: Aby uruchomić te przykłady, należy zaktualizować adres email w funkcji setup_client().")
    print("Możesz uruchomić wszystkie przykłady lub odkomentować wybrane przykłady poniżej.\n")
    
    # Uruchom wszystkie przykłady
    # run_all_examples()
    
    # Lub uruchom wybrane przykłady:
    example_get_variant_by_id()
    example_search_by_coordinates()
    # example_search_by_gene()
    # example_search_by_clinical_significance()
    # example_search_by_rs_id()
    # example_search_by_phenotype()
    # example_integrate_with_coordinates_lit()
    # example_get_variant_summary() 