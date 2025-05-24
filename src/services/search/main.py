"""
Main script for finding PMIDs associated with FOX family genes.

This script provides a command-line interface to the FoxGenePMIDFinder class.
"""

import argparse
import logging
import sys
from src.services.search.fox_gene_pmid_finder import FoxGenePMIDFinder


def main():
    """
    Main entry point for the FOX gene PMID finder script.
    
    Parses command-line arguments and runs the PMID finding process.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Find PMIDs associated with FOX family genes using LitVar API'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/input/fox_unique_genes.txt',
        help='Path to input file containing FOX gene symbols (default: data/input/fox_unique_genes.txt)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='data/pmids/fox_pmids.txt',
        help='Path to output file for PMIDs (default: data/pmids/fox_pmids.txt)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit the number of genes to process (default: process all)'
    )
    parser.add_argument(
        '--skip', '-s',
        type=int,
        default=0,
        help='Skip the first N genes (default: 0)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize the PMID finder
        finder = FoxGenePMIDFinder()
        
        # Load genes from file
        genes = finder.load_genes_from_file(args.input)
        
        # Apply skip and limit if specified
        start_idx = args.skip
        if start_idx >= len(genes):
            logger.warning(f"Skip value {start_idx} exceeds the number of genes {len(genes)}")
            return 1
            
        end_idx = None if args.limit is None else start_idx + args.limit
        limited_genes = genes[start_idx:end_idx]
        
        if args.limit is not None or args.skip > 0:
            logger.info(f"Processing genes {start_idx} to {end_idx if end_idx is not None else len(genes)} of {len(genes)} genes")
            finder.genes = limited_genes
        
        # Find PMIDs and save to file
        finder.find_pmids_for_genes()
        finder.save_pmids_to_file(args.output)
        
        logger.info(f"Successfully saved PMIDs to {args.output}")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 