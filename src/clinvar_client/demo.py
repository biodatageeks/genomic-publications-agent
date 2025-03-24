"""
Demonstration of using the ClinVar client.

This module contains examples of using the ClinVar client for various operations,
such as variant search, variant information retrieval,
and integration with the coordinates_lit tool.
"""

import json
import logging
from typing import Dict, List, Any

from .clinvar_client import ClinVarClient
from .exceptions import ClinVarError, APIRequestError, InvalidParameterError


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_client() -> ClinVarClient:
    """
    Creates and configures an instance of the ClinVar client.
    
    Returns:
        Configured instance of ClinVarClient
    """
    # Replace the email address below with your own
    email = "your.email@domain.com"
    
    # Optionally, you can add your API key to increase the query limit
    # api_key = "your_api_key"
    
    return ClinVarClient(email=email)


def example_get_variant_by_id() -> None:
    """
    Example of retrieving variant information based on the ClinVar identifier.
    """
    client = setup_client()
    
    # Sample ClinVar identifiers
    vcv_id = "VCV000014076"  # Variant in the BRCA1 gene
    
    try:
        # Get variant information in JSON format
        variant_info = client.get_variant_by_id(vcv_id)
        print(f"\n--- Variant information for {vcv_id} ---")
        print(f"Name: {variant_info.get('name', 'N/A')}")
        print(f"Clinical significance: {variant_info.get('clinical_significance', 'N/A')}")
        
        # Display genes
        genes = variant_info.get('genes', [])
        if genes:
            print("\nRelated genes:")
            for gene in genes:
                print(f"  - {gene.get('symbol', 'N/A')} (ID: {gene.get('id', 'N/A')})")
        
        # Display phenotypes
        phenotypes = variant_info.get('phenotypes', [])
        if phenotypes:
            print("\nRelated phenotypes:")
            for phenotype in phenotypes:
                print(f"  - {phenotype.get('name', 'N/A')} (ID: {phenotype.get('id', 'N/A')})")
        
        # Display genomic coordinates
        coordinates = variant_info.get('coordinates', [])
        if coordinates:
            print("\nGenomic coordinates:")
            for coords in coordinates:
                print(f"  - {coords.get('assembly', 'N/A')}: "
                      f"{coords.get('chromosome', 'N/A')}:"
                      f"{coords.get('start', 'N/A')}-{coords.get('stop', 'N/A')}")
                print(f"    Ref: {coords.get('reference_allele', 'N/A')}, "
                      f"Alt: {coords.get('alternate_allele', 'N/A')}")
    
    except ClinVarError as e:
        logger.error(f"Error while retrieving variant information: {str(e)}")


def example_search_by_coordinates() -> None:
    """
    Example of searching for variants based on genomic coordinates.
    """
    client = setup_client()
    
    # Sample coordinates: BRCA1 gene region
    chromosome = "17"
    start = 43044295
    end = 43125483
    
    try:
        print(f"\n--- Searching for variants in region {chromosome}:{start}-{end} ---")
        variants = client.search_by_coordinates(
            chromosome=chromosome,
            start=start,
            end=end
        )
        
        print(f"Found {len(variants)} variants")
        
        # Display the first 5 variants
        for i, variant in enumerate(variants[:5], 1):
            print(f"\nVariant {i}:")
            print(f"  ID: {variant.get('id', 'N/A')}")
            print(f"  Name: {variant.get('name', 'N/A')}")
            print(f"  Type: {variant.get('variation_type', 'N/A')}")
            print(f"  Clinical significance: {variant.get('clinical_significance', 'N/A')}")
            
            # Display genes
            genes = variant.get('genes', [])
            if genes:
                print("  Genes:", ", ".join([g.get('symbol', 'N/A') for g in genes]))
    
    except InvalidParameterError as e:
        logger.error(f"Invalid parameters: {str(e)}")
    except APIRequestError as e:
        logger.error(f"API error: {str(e)}")
    except ClinVarError as e:
        logger.error(f"General ClinVar error: {str(e)}")


def example_search_by_gene() -> None:
    """
    Example of searching for variants based on gene symbol.
    """
    client = setup_client()
    
    # Sample gene
    gene_symbol = "BRCA1"
    
    try:
        print(f"\n--- Searching for variants for gene {gene_symbol} ---")
        variants = client.search_by_gene(gene_symbol)
        
        print(f"Found {len(variants)} variants")
        
        # Analyze clinical significance
        significance_counts = {}
        for variant in variants:
            significance = variant.get('clinical_significance', 'Not provided')
            significance_counts[significance] = significance_counts.get(significance, 0) + 1
        
        print("\nDistribution of clinical significance:")
        for significance, count in significance_counts.items():
            print(f"  {significance}: {count} variants")
        
        # Display the first 3 pathogenic variants
        print("\nSample pathogenic variants:")
        pathogenic_count = 0
        for variant in variants:
            if variant.get('clinical_significance', '').lower() == 'pathogenic':
                pathogenic_count += 1
                print(f"  - {variant.get('name', 'N/A')}")
                if pathogenic_count >= 3:
                    break
    
    except ClinVarError as e:
        logger.error(f"Error while searching for variants for gene: {str(e)}")


def example_search_by_clinical_significance() -> None:
    """
    Example of searching for variants based on clinical significance.
    """
    client = setup_client()
    
    # Sample clinical significance
    significance = "pathogenic"
    
    try:
        print(f"\n--- Searching for variants with clinical significance: {significance} ---")
        variants = client.search_by_clinical_significance(significance)
        
        print(f"Found {len(variants)} variants")
        
        # Analyze genes
        gene_counts = {}
        for variant in variants:
            for gene in variant.get('genes', []):
                gene_symbol = gene.get('symbol', 'N/A')
                if gene_symbol != 'N/A':
                    gene_counts[gene_symbol] = gene_counts.get(gene_symbol, 0) + 1
        
        # Find the top 5 genes
        top_genes = sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("\nTop 5 genes with pathogenic variants:")
        for gene, count in top_genes:
            print(f"  {gene}: {count} variants")
    
    except InvalidParameterError as e:
        logger.error(f"Invalid clinical significance: {str(e)}")
    except ClinVarError as e:
        logger.error(f"Error while searching for variants: {str(e)}")


def example_search_by_rs_id() -> None:
    """
    Example of searching for variants based on rs identifier.
    """
    client = setup_client()
    
    # Sample rs identifier
    rs_id = "rs6025"  # Factor V Leiden
    
    try:
        print(f"\n--- Searching for variants for identifier {rs_id} ---")
        variants = client.search_by_rs_id(rs_id)
        
        print(f"Found {len(variants)} variants")
        
        for variant in variants:
            print(f"\nVariant: {variant.get('name', 'N/A')}")
            print(f"Clinical significance: {variant.get('clinical_significance', 'N/A')}")
            
            # Display phenotypes
            phenotypes = variant.get('phenotypes', [])
            if phenotypes:
                print("Related phenotypes:")
                for phenotype in phenotypes:
                    print(f"  - {phenotype.get('name', 'N/A')}")
            
            # Display coordinates
            coordinates = variant.get('coordinates', [])
            if coordinates:
                for coords in coordinates:
                    print(f"Coordinates: {coords.get('chromosome', 'N/A')}:"
                          f"{coords.get('start', 'N/A')}-{coords.get('stop', 'N/A')}")
    
    except ClinVarError as e:
        logger.error(f"Error while searching for variants for rs ID: {str(e)}")


def example_search_by_phenotype() -> None:
    """
    Example of searching for variants based on phenotype.
    """
    client = setup_client()
    
    # Sample phenotype
    phenotype = "Breast cancer"
    
    try:
        print(f"\n--- Searching for variants for phenotype: {phenotype} ---")
        variants = client.search_by_phenotype(phenotype)
        
        print(f"Found {len(variants)} variants")
        
        # Analyze genes
        gene_counts = {}
        for variant in variants:
            for gene in variant.get('genes', []):
                gene_symbol = gene.get('symbol', 'N/A')
                if gene_symbol != 'N/A':
                    gene_counts[gene_symbol] = gene_counts.get(gene_symbol, 0) + 1
        
        # Find the top 5 genes
        top_genes = sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("\nTop 5 genes associated with the phenotype:")
        for gene, count in top_genes:
            print(f"  {gene}: {count} variants")
            
        # Analyze clinical significance
        significance_counts = {}
        for variant in variants:
            significance = variant.get('clinical_significance', 'Not provided')
            significance_counts[significance] = significance_counts.get(significance, 0) + 1
        
        print("\nDistribution of clinical significance:")
        for significance, count in sorted(significance_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {significance}: {count} variants")
    
    except ClinVarError as e:
        logger.error(f"Error while searching for variants for phenotype: {str(e)}")


def example_integrate_with_coordinates_lit() -> None:
    """
    Example of integrating coordinates_lit data with ClinVar data.
    """
    client = setup_client()
    
    # Sample coordinates_lit data
    coordinates_data = [
        {
            "chromosome": "17",
            "start": 43044295,
            "end": 43125483",
            "source": "Publication 1",
            "title": "Analysis of mutations in the BRCA1 gene"
        },
        {
            "chromosome": "13",
            "start": 32315474,
            "end": 32400266",
            "source": "Publication 2",
            "title": "Analysis of mutations in the BRCA2 gene"
        }
    ]
    
    try:
        print("\n--- Integrating coordinates_lit data with ClinVar ---")
        enriched_data = client.integrate_with_coordinates_lit(coordinates_data)
        
        for i, entry in enumerate(enriched_data, 1):
            print(f"\nRegion {i}: {entry['title']}")
            print(f"Coordinates: {entry['chromosome']}:{entry['start']}-{entry['end']}")
            print(f"Source: {entry['source']}")
            
            clinvar_data = entry.get('clinvar_data', [])
            print(f"Number of ClinVar variants found: {len(clinvar_data)}")
            
            if clinvar_data:
                # Analyze clinical significance
                significance_counts = {}
                for variant in clinvar_data:
                    significance = variant.get('clinical_significance', 'Not provided')
                    significance_counts[significance] = significance_counts.get(significance, 0) + 1
                
                print("Distribution of clinical significance:")
                for significance, count in significance_counts.items():
                    print(f"  {significance}: {count} variants")
                
                # Sample variants
                print("\nSample variants:")
                for j, variant in enumerate(clinvar_data[:3], 1):
                    print(f"  {j}. {variant.get('name', 'N/A')} - "
                          f"{variant.get('clinical_significance', 'N/A')}")
        
        # Save enriched data to a JSON file
        with open('clinvar_enriched_data.json', 'w') as f:
            json.dump(enriched_data, f, indent=2)
        print("\nEnriched data saved to file clinvar_enriched_data.json")
    
    except ClinVarError as e:
        logger.error(f"Error while integrating data: {str(e)}")


def example_get_variant_summary() -> None:
    """
    Example of retrieving a variant summary.
    """
    client = setup_client()
    
    # Sample variant identifier
    variant_id = "VCV000014076"
    
    try:
        print(f"\n--- Variant summary for {variant_id} ---")
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
        logger.error(f"Error while retrieving variant summary: {str(e)}")


def run_all_examples() -> None:
    """
    Runs all examples of using the ClinVar client.
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
            logger.error(f"Unexpected error while running example {example.__name__}: {str(e)}")


if __name__ == "__main__":
    print("=== ClinVar client demonstration ===\n")
    print("NOTE: To run these examples, you need to update the email address in the setup_client() function.")
    print("You can run all examples or uncomment selected examples below.\n")
    
    # Run all examples
    # run_all_examples()
    
    # Or run selected examples:
    example_get_variant_by_id()
    example_search_by_coordinates()
    # example_search_by_gene()
    # example_search_by_clinical_significance()
    # example_search_by_rs_id()
    # example_search_by_phenotype()
    # example_integrate_with_coordinates_lit()
    # example_get_variant_summary() 