#!/usr/bin/env python3
"""
Enhanced version of the script for generating a CSV table with genes, diseases, and variants based on PubMed IDs.
Uses the UnifiedLlmContextAnalyzer class for better JSON error handling and relationship scoring.
"""

import argparse
import logging
import os
import sys
import time
from typing import List, Optional

# Add the path to the main project directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.generate_coordinate_csv import analyze_pmids
from src.llm_context_analyzer.unified_llm_context_analyzer import UnifiedLlmContextAnalyzer
from src.Config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def enhanced_analyze_pmids(pmids: List[str],
                         output_csv: str,
                         email: Optional[str] = None,
                         llm_model: Optional[str] = None,
                         use_llm: bool = True,
                         only_llm: bool = False,
                         debug_mode: bool = False,
                         retry_on_failure: bool = True,
                         max_retries: int = 3,
                         retry_delay: int = 5,
                         cache_storage_type: str = "memory"):
    """
    Enhanced version of the function to analyze PubMed IDs.
    Uses UnifiedLlmContextAnalyzer for better error handling and adds retry capability in case of failure.
    
    Args:
        pmids: List of PubMed IDs to analyze
        output_csv: Path to the output CSV file
        email: Email address for the PubTator API (optional)
        llm_model: Name of the LLM model to use (optional)
        use_llm: Whether to use LLM analysis
        only_llm: Whether to use only LLM analysis (no co-occurrence)
        debug_mode: Whether to enable debug mode
        retry_on_failure: Whether to retry in case of failure
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retry attempts (in seconds)
        cache_storage_type: Type of cache storage (memory or disk)
        
    Returns:
        DataFrame with the results
    """
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        try:
            if retries > 0:
                logger.info(f"Retry attempt {retries}/{max_retries}...")
            
            # Run the standard analysis, but with enhanced parameters
            return analyze_pmids(
                pmids=pmids,
                output_csv=output_csv,
                email=email,
                llm_model=llm_model,
                use_llm=use_llm,
                only_llm=only_llm,
                debug_mode=debug_mode,
                llm_context_analyzer_class=UnifiedLlmContextAnalyzer,  # Use the new unified analyzer
                cache_storage_type=cache_storage_type  # Pass cache_storage_type parameter
            )
        
        except Exception as e:
            last_error = e
            logger.error(f"Error during analysis: {str(e)}")
            
            if not retry_on_failure or retries >= max_retries:
                break
            
            retries += 1
            logger.info(f"Waiting {retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
    
    # If all attempts failed, raise the last error
    if last_error:
        raise last_error
    
    return None


def main():
    """Main function of the script."""
    # Load configuration
    config = Config()
    default_email = config.get_contact_email()
    default_model = config.get_llm_model_name()
    
    parser = argparse.ArgumentParser(
        description="Enhanced script for generating a CSV table with genes, diseases, and variants"
    )
    
    parser.add_argument("-p", "--pmids", nargs="+", required=False,
                        help="List of PubMed IDs to analyze")
    parser.add_argument("-f", "--file", type=str,
                        help="File containing PubMed IDs, one per line")
    parser.add_argument("-o", "--output", required=True, 
                        help="Path to the output CSV file")
    parser.add_argument("-m", "--model", default=default_model,
                        help=f"Name of the LLM model to use (default: {default_model})")
    parser.add_argument("-e", "--email", default=default_email,
                        help=f"Email address for the PubTator API (default: {default_email})")
    parser.add_argument("--no-llm", action="store_true",
                        help="Disable LLM analysis (use only co-occurrence)")
    parser.add_argument("--only-llm", action="store_true",
                        help="Use only LLM analysis (disable co-occurrence)")
    parser.add_argument("--debug", action="store_true",
                        help="Save debugging information (raw LLM output)")
    parser.add_argument("--no-retry", action="store_true",
                        help="Disable automatic retries in case of failure")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Maximum number of retry attempts in case of failure (default: 3)")
    parser.add_argument("--retry-delay", type=int, default=5,
                        help="Delay between retry attempts in seconds (default: 5)")
    parser.add_argument("--cache-type", choices=["memory", "disk"], default="memory", 
                        help="Type of cache storage (memory or disk), default: memory")
    
    args = parser.parse_args()
    
    # Collect PubMed IDs from arguments or file
    pmids = []
    
    if args.pmids:
        pmids.extend(args.pmids)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_pmids = [line.strip() for line in f if line.strip()]
                pmids.extend(file_pmids)
        except Exception as e:
            logger.error(f"Error reading PMID file: {str(e)}")
            sys.exit(1)
    
    if not pmids:
        logger.error("No PubMed IDs provided. Use the --pmids or --file option.")
        sys.exit(1)
    
    # Perform the analysis
    try:
        df = enhanced_analyze_pmids(
            pmids=pmids,
            output_csv=args.output,
            email=args.email,
            llm_model=args.model,
            use_llm=not args.no_llm,
            only_llm=args.only_llm,
            debug_mode=args.debug,
            retry_on_failure=not args.no_retry,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            cache_storage_type=args.cache_type
        )
        
        if df is not None:
            logger.info(f"Analysis completed successfully. Generated CSV with {len(df)} entries.")
        else:
            logger.info("Analysis completed successfully, but no data was returned.")
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 