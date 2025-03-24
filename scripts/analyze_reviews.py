#!/usr/bin/env python3
"""
Script for analyzing biomedical publications containing genetic variants, genes, and diseases.
Searches for relationships between these entities and generates a table and visualization of results.
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

# List of PMIDs to analyze, collected from project files
PMIDS = [
    # From files in data/pubmed-articles
    "18836447", "21441262", "22996659", "23502222", "34799090",
    
    # From literature files in CSV files
    "11175783", "11254675", "11254676", "11254677", "11254678", 
    "11286503", "11355022", "12021216", "12192640", "12459590", 
    "14684687", "14760718", "15146197", "15454494", "15489334", 
    "15616553", "15723069", "16007107", "16237147", "16331359", 
    "16380919", "16467226", "16628248", "16670017", "16757811", 
    "16825278", "17031701", "17142316", "17186469", "17515542", 
    "17662803", "17804648", "17967973", "17984403", "18156156", 
    "18220430", "18423520", "18684880", "19019335", "19060906", 
    "19525978", "19644445", "20012913", "20031530", "20072694",
    
    # PMIDs from other sources (previously used in tests)
    "34261372", "33208827", "33417880", "33705364", "31324762"
]

def analyze_publications(pmids: List[str], 
                        output_csv: str, 
                        output_excel: Optional[str] = None,
                        email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Analyzes publications and creates a table of relationships.
    
    Args:
        pmids: List of PMIDs to analyze
        output_csv: Path to output CSV file
        output_excel: Optional path to output Excel file
        email: Email address for PubTator API (uses config if None)
        
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
            "Number of unique publications": df["pmid"].nunique(),
            "Most common variants": df["variant_text"].value_counts().head(10).to_dict(),
            "Most common genes": df["gene_text"].value_counts().head(10).to_dict(),
            "Most common diseases": df["disease_text"].value_counts().head(10).to_dict(),
        }
        
        logger.info(f"Analysis statistics: {stats}")
        
        # Optional save to Excel
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

def visualize_results(csv_file: str, output_prefix: str):
    """
    Visualizes analysis results.
    
    Args:
        csv_file: Path to CSV file with relationships
        output_prefix: Prefix for output files
    """
    # Call visualization script
    import subprocess
    
    try:
        graph_output = f"{output_prefix}_graph.png"
        result = subprocess.run(
            ["python", "scripts/visualize_relationships.py", 
             "--input", csv_file, 
             "--output", graph_output],
            check=True, capture_output=True, text=True
        )
        logger.info(f"Visualization completed successfully: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during visualization: {e.stderr}")

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
                        help=f"Contact email for PubTator API (default: {default_email})")
    parser.add_argument("--pmids", type=str, nargs="+",
                        help="List of PMID identifiers to analyze (optional, uses predefined PMIDs by default)")
    
    args = parser.parse_args()
    
    # Ensure output directories exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    if args.excel:
        os.makedirs(os.path.dirname(os.path.abspath(args.excel)), exist_ok=True)
    
    # Use PMIDs from arguments or from predefined list
    pmids = args.pmids if args.pmids else PMIDS
    logger.info(f"Using {len(pmids)} PMIDs for analysis")
    
    # Run analysis
    df = analyze_publications(
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
        
        # Generate statistics and visualizations
        output_prefix = os.path.splitext(args.output)[0]
        visualize_results(args.output, output_prefix)
        
        # Display summary
        print("\nAnalysis summary:")
        print(f" - Number of analyzed publications: {df['pmid'].nunique()}")
        print(f" - Number of found relationships: {len(df)}")
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