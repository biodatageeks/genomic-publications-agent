#!/usr/bin/env python3
"""
CLI tool for analyzing publications to extract variant relationships.

This script provides a command-line interface for analyzing PubMed publications
to extract relationships between genomic variants and other biomedical entities
such as genes, diseases, and tissues.
"""

import argparse
import logging
import os
import sys
import time
from typing import List, Optional

from src.analysis.llm.context_analyzer import UnifiedLlmContextAnalyzer
from src.data.clients.pubtator import PubTatorClient
from src.core.config.config import Config


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configures logging for the application.
    
    Args:
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join("logs", "analysis.log"))
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")


def load_pmids_from_file(file_path: str) -> List[str]:
    """
    Loads PubMed IDs from a text file.
    
    Args:
        file_path: Path to the file containing PubMed IDs
        
    Returns:
        List of PubMed IDs
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    logger = logging.getLogger(__name__)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            pmids = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(pmids)} PMIDs from {file_path}")
        return pmids
    except FileNotFoundError:
        logger.error(f"PMID file not found: {file_path}")
        raise


def analyze_pmids(
    pmids: List[str],
    output_csv: str,
    output_json: Optional[str] = None,
    email: Optional[str] = None,
    llm_model: Optional[str] = None,
    debug_mode: bool = False,
    retry_on_failure: bool = True,
    max_retries: int = 3,
    retry_delay: int = 5,
    cache_storage_type: str = "memory"
) -> None:
    """
    Analyzes PubMed publications to extract variant relationships.
    
    Args:
        pmids: List of PubMed IDs to analyze
        output_csv: Path to the output CSV file
        output_json: Optional path to the output JSON file
        email: Email address for the PubTator API
        llm_model: Name of the LLM model to use
        debug_mode: Whether to enable debug mode
        retry_on_failure: Whether to retry in case of failure
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retry attempts in seconds
        cache_storage_type: Type of cache storage (memory or disk)
    """
    logger = logging.getLogger(__name__)
    
    # Create PubTator client
    pubtator_client = PubTatorClient(email=email)
    
    # Create LLM context analyzer
    analyzer = UnifiedLlmContextAnalyzer(
        pubtator_client=pubtator_client,
        llm_model_name=llm_model,
        use_cache=True,
        cache_storage_type=cache_storage_type,
        debug_mode=debug_mode
    )
    
    logger.info(f"Analyzing {len(pmids)} publications")
    
    # Analyze publications with retry logic
    retries = 0
    while True:
        try:
            # Analyze publications
            relationships = analyzer.analyze_publications(
                pmids=pmids,
                save_debug_info=debug_mode
            )
            
            # Save results to CSV
            analyzer.save_relationships_to_csv(relationships, output_csv)
            logger.info(f"Saved {len(relationships)} relationships to CSV: {output_csv}")
            
            # Save results to JSON if requested
            if output_json:
                analyzer.save_relationships_to_json(relationships, output_json)
                logger.info(f"Saved {len(relationships)} relationships to JSON: {output_json}")
            
            # Success!
            break
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            
            if not retry_on_failure or retries >= max_retries:
                logger.error(f"Failed after {retries} retries")
                raise
            
            retries += 1
            logger.info(f"Retrying ({retries}/{max_retries}) in {retry_delay} seconds...")
            time.sleep(retry_delay)


def main() -> None:
    """Main function of the CLI tool."""
    # Load configuration
    config = Config()
    default_email = config.get_contact_email()
    default_model = config.get_llm_model_name()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CLI tool for analyzing publications to extract variant relationships"
    )
    
    parser.add_argument("-p", "--pmids", nargs="+", help="List of PubMed IDs to analyze")
    parser.add_argument("-f", "--file", type=str, help="File containing PubMed IDs, one per line")
    parser.add_argument("-o", "--output", required=True, help="Path to the output CSV file")
    parser.add_argument("-j", "--json", help="Path to the output JSON file (optional)")
    parser.add_argument("-m", "--model", default=default_model,
                        help=f"Name of the LLM model to use (default: {default_model})")
    parser.add_argument("-e", "--email", default=default_email,
                        help=f"Email address for the PubTator API (default: {default_email})")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-retry", action="store_true", help="Disable automatic retries")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Maximum number of retry attempts (default: 3)")
    parser.add_argument("--retry-delay", type=int, default=5,
                        help="Delay between retry attempts in seconds (default: 5)")
    parser.add_argument("--cache-type", choices=["memory", "disk"], default="memory",
                        help="Type of cache storage (default: memory)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO", help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Collect PubMed IDs
    pmids = []
    
    if args.pmids:
        pmids.extend(args.pmids)
    
    if args.file:
        try:
            file_pmids = load_pmids_from_file(args.file)
            pmids.extend(file_pmids)
        except FileNotFoundError:
            sys.exit(1)
    
    if not pmids:
        logger.error("No PubMed IDs provided. Use --pmids or --file option.")
        sys.exit(1)
    
    # Remove duplicates and ensure unique PMIDs
    pmids = list(set(pmids))
    logger.info(f"Processing {len(pmids)} unique PubMed IDs")
    
    try:
        # Analyze publications
        analyze_pmids(
            pmids=pmids,
            output_csv=args.output,
            output_json=args.json,
            email=args.email,
            llm_model=args.model,
            debug_mode=args.debug,
            retry_on_failure=not args.no_retry,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            cache_storage_type=args.cache_type
        )
        
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 