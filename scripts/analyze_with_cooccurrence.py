#!/usr/bin/env python3
"""
Script for analyzing biomedical publications with co-occurrence analysis.
"""

import argparse
import logging
import os
import sys
import pandas as pd
from typing import List, Optional

# Add path to the main project directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cooccurrence_context_analyzer.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer
from src.pubtator_client.pubtator_client import PubTatorClient
from src.Config import Config

# Logging configuration
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
                        email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Analyzes publications and creates a table of relationships using co-occurrence.
    
    Args:
        pmids: List of PMIDs to analyze
        output_csv: Path to output CSV file
        output_json: Optional path to output JSON file
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
    
    try:
        # Analyze publications
        logger.info("Starting publication analysis...")
        relationships = analyzer.analyze_publications(pmids)
        logger.info(f"Found {len(relationships)} relationships in publications")
        
        # Save to files
        analyzer.save_relationships_to_csv(relationships, output_csv)
        logger.info(f"Saved data to CSV file: {output_csv}")
        
        if output_json:
            analyzer.save_relationships_to_json(relationships, output_json)
            logger.info(f"Saved data to JSON file: {output_json}")
        
        # Convert to DataFrame
        df = pd.read_csv(output_csv)
        return df
        
    except Exception as e:
        logger.error(f"An error occurred during analysis: {str(e)}")
        return None


def main():
    """Main script function."""
    # Load configuration
    config = Config()
    default_email = config.get_contact_email()
    
    parser = argparse.ArgumentParser(description="Analysis of biomedical entity co-occurrence in publications")
    
    parser.add_argument("-p", "--pmids", nargs="+", required=True,
                        help="List of PMIDs to analyze")
    parser.add_argument("-o", "--output", required=True, 
                        help="Path to output CSV file")
    parser.add_argument("-j", "--json", 
                        help="Optional path to output JSON file")
    parser.add_argument("-e", "--email", default=default_email,
                        help=f"Email address for PubTator API (default: {default_email})")
    
    args = parser.parse_args()
    
    # Analyze publications
    df = analyze_publications(
        pmids=args.pmids,
        output_csv=args.output,
        output_json=args.json,
        email=args.email
    )
    
    if df is not None:
        logger.info(f"Analysis completed successfully. Found {len(df)} relationship entries.")
    else:
        logger.error("Analysis failed.")
        sys.exit(1)


if __name__ == "__main__":
    main() 