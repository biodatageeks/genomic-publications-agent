#!/usr/bin/env python3
"""
Script for analyzing co-occurrence of genetic variants with other biological entities
in selected publications with a high number of variants.
"""

import argparse
import logging
import os
import sys
import pandas as pd
from typing import List, Dict, Any, Optional

# Add path to the main project directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pubtator_client.pubtator_client import PubTatorClient
from src.cooccurrence_context_analyzer.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer
from src.pubtator_client.exceptions import PubTatorError
from src.Config import Config

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of PMIDs of selected publications with a high number of variants
# These publications were chosen as examples with rich variant content
SELECTED_PMIDS = [
    "33417880",  # Publication about COVID-19 and SARS-CoV-2 variants
    "33705364",  # Publication about BRAF variants in melanoma
    "34268513",  # Publication about germline variants in pancreatic cancer
    "34002096",  # Publication about variants in prostate cancer
    "33208827",  # Publication about variants in BRCA1/2 gene
]

def get_publications_with_variants(pubtator_client: PubTatorClient, 
                                   min_variants: int = 5, 
                                   max_publications: int = 10) -> List[str]:
    """
    Helper function for finding publications with a high number of variants.
    
    Args:
        pubtator_client: PubTator client instance
        min_variants: Minimum number of variants in a publication
        max_publications: Maximum number of publications to return
        
    Returns:
        List of PMIDs of publications with a high number of variants
    """
    # Search for publications with variant annotations
    # In a real implementation, more advanced search would be needed
    # For demonstration purposes, we use a predefined list
    return SELECTED_PMIDS[:max_publications]

def analyze_publications_and_create_table(pmids: List[str], 
                                         output_csv: str, 
                                         output_excel: Optional[str] = None,
                                         email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Analyzes publications and creates a table with relationships.
    
    Args:
        pmids: List of PMIDs to analyze
        output_csv: Path to output CSV file
        output_excel: Optional path to output Excel file
        email: Email address for PubTator API (used in metadata)
        
    Returns:
        DataFrame with relationship data or None if an error occurred
    """
    # Load config
    config = Config()
    
    # Use email from config if not provided
    if email is None:
        email = config.get_contact_email()
    
    # Ensure email is not None
    assert email is not None, "Email must be specified either directly or in config"
    
    logger.info(f"Starting analysis for {len(pmids)} publications")
    
    # Initialize clients
    pubtator_client = PubTatorClient(email=email)
    analyzer = CooccurrenceContextAnalyzer(pubtator_client=pubtator_client)
    
    # Add email information to log
    logger.info(f"Using contact email: {email}")
    
    # Analyze publications
    try:
        relationships = analyzer.analyze_publications(pmids)
        logger.info(f"Found {len(relationships)} relationships in publications")
        
        if not relationships:
            logger.warning("No variant relationships found!")
            return None
        
        # Save relationships to CSV
        analyzer.save_relationships_to_csv(relationships, output_csv)
        logger.info(f"Saved relationships to CSV file: {output_csv}")
        
        # Create DataFrame for further analysis
        df = pd.read_csv(output_csv)
        
        # Calculate statistics
        stats = {
            "Number of unique variants": df["variant_text"].nunique(),
            "Number of unique genes": df["gene_text"].nunique(),
            "Number of unique diseases": df["disease_text"].nunique(),
            "Most common variants": df["variant_text"].value_counts().head(5).to_dict(),
            "Most common genes": df["gene_text"].value_counts().head(5).to_dict(),
            "Most common diseases": df["disease_text"].value_counts().head(5).to_dict(),
        }
        
        logger.info(f"Analysis statistics: {stats}")
        
        # Optional Excel export
        if output_excel:
            try:
                with pd.ExcelWriter(output_excel) as writer:
                    df.to_excel(writer, sheet_name="Relationships", index=False)
                    # Add statistics sheet
                    stats_df = pd.DataFrame([stats])
                    stats_df.to_excel(writer, sheet_name="Statistics", index=False)
                logger.info(f"Saved data to Excel file: {output_excel}")
            except ImportError:
                logger.warning("Cannot save to Excel file: missing 'openpyxl' module. "
                               "Install it using 'pip install openpyxl'.")
                logger.info("Data has been saved only in CSV format.")
            except Exception as e:
                logger.warning(f"Cannot save to Excel file: {str(e)}")
        
        return df
    
    except PubTatorError as e:
        logger.error(f"Error during publication analysis: {str(e)}")
        return None

def main():
    """Main script function."""
    # Load configuration
    config = Config()
    default_email = config.get_contact_email()
    
    parser = argparse.ArgumentParser(description="Analysis of genetic variant co-occurrence in publications.")
    parser.add_argument("--output", "-o", type=str, default="variant_relationships.csv",
                        help="Path to output CSV file (default: variant_relationships.csv)")
    parser.add_argument("--excel", "-e", type=str, default="variant_relationships.xlsx",
                        help="Path to output Excel file (default: variant_relationships.xlsx)")
    parser.add_argument("--email", type=str, default=default_email,
                        help=f"Contact email address (for API metadata) (default: {default_email})")
    parser.add_argument("--pmids", type=str, nargs="+",
                        help="List of PMID identifiers to analyze (optional, defaults to predefined list)")
    
    args = parser.parse_args()
    
    # If PMIDs are provided, use them, otherwise use the default list
    pmids = args.pmids if args.pmids else SELECTED_PMIDS
    
    # Ensure output directories exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    if args.excel:
        os.makedirs(os.path.dirname(os.path.abspath(args.excel)), exist_ok=True)
    
    # Run analysis
    df = analyze_publications_and_create_table(
        pmids=pmids,
        output_csv=args.output,
        output_excel=args.excel,
        email=args.email
    )
    
    if df is not None:
        print(f"\nAnalysis completed successfully! Data saved to files:")
        print(f" - CSV: {args.output}")
        try:
            import openpyxl
            if args.excel:
                print(f" - Excel: {args.excel}")
        except ImportError:
            print("Note: Cannot save to Excel file - missing 'openpyxl' module.")
            print("Install it using: pip install openpyxl")
        
        print("\nAnalysis summary:")
        print(f" - Number of relationships: {len(df)}")
        print(f" - Number of unique variants: {df['variant_text'].nunique()}")
        print(f" - Number of unique genes: {df['gene_text'].nunique()}")
        print(f" - Number of unique diseases: {df['disease_text'].nunique()}")
        
        top_variants = df["variant_text"].value_counts().head(5)
        print("\nMost common variants:")
        for variant, count in top_variants.items():
            if variant and str(variant).strip():
                print(f" - {variant}: {count} occurrences")
        
        print("\nCompleted successfully!")
    else:
        print("\nAnalysis failed. Check logs.")

if __name__ == "__main__":
    main() 