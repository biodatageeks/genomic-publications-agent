"""
This module provides the FoxGenePMIDFinder class for retrieving PMIDs associated with FOX family genes.

It uses NCBI's E-utilities API to directly search PubMed for publications related to FOX genes.
"""

import os
import json
from typing import List, Dict, Set, Any
import logging
import time
import requests

class FoxGenePMIDFinder:
    """
    Class for finding and extracting PMIDs associated with FOX family genes.
    
    Uses the NCBI E-utilities API to search for publications directly in PubMed.
    """
    
    def __init__(self):
        """
        Initialize the FoxGenePMIDFinder instance.
        """
        self.genes = []
        self.pmids = set()
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_genes_from_file(self, file_path: str) -> List[str]:
        """
        Load a list of gene symbols from a text file.
        
        Args:
            file_path: Path to the file containing gene symbols (one per line)
            
        Returns:
            List of gene symbols
        
        Raises:
            FileNotFoundError: If the file does not exist
        """
        self.logger.info(f"Loading genes from {file_path}")
        
        try:
            with open(file_path, 'r') as file:
                self.genes = [line.strip() for line in file if line.strip()]
            
            self.logger.info(f"Loaded {len(self.genes)} genes")
            return self.genes
        
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
    
    def find_pmids_for_genes(self) -> Set[str]:
        """
        Find PMIDs associated with the loaded gene list using direct PubMed search.
        
        Returns:
            Set of unique PMIDs
        
        Raises:
            ValueError: If no genes have been loaded
        """
        if not self.genes:
            self.logger.error("No genes loaded. Call load_genes_from_file() first.")
            raise ValueError("No genes loaded. Call load_genes_from_file() first.")
        
        self.logger.info(f"Searching for publications associated with {len(self.genes)} genes")
        
        all_pmids = set()
        
        for gene in self.genes:
            try:
                self.logger.info(f"Searching for publications for gene: {gene}")
                
                # Construct a search query for human studies related to the gene
                # Format: "GENE[Gene Name] AND human[Organism]"
                search_term = f"{gene}[Gene Name] AND human[Organism]"
                
                # Step 1: Use ESearch to find IDs
                esearch_url = f"{self.base_url}/esearch.fcgi"
                params = {
                    "db": "pubmed",
                    "term": search_term,
                    "retmax": 1000,  # Limit to 1000 results per gene
                    "retmode": "json"
                }
                
                response = requests.get(esearch_url, params=params)
                
                if response.status_code == 200:
                    try:
                        results = response.json()
                        id_list = results.get('esearchresult', {}).get('idlist', [])
                        
                        if id_list:
                            self.logger.info(f"Found {len(id_list)} publications for gene {gene}")
                            all_pmids.update(id_list)
                        else:
                            self.logger.warning(f"No publications found for gene {gene}")
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Could not parse JSON response for gene {gene}: {str(e)}")
                else:
                    self.logger.warning(f"Failed to get publications for gene {gene}: status {response.status_code}")
                
                # Add a small delay to avoid exceeding NCBI's rate limits
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error processing gene {gene}: {str(e)}")
        
        self.pmids = all_pmids
        self.logger.info(f"Found {len(all_pmids)} unique PMIDs")
        
        return all_pmids
    
    def save_pmids_to_file(self, output_file_path: str) -> None:
        """
        Save the list of unique PMIDs to a text file.
        
        Args:
            output_file_path: Path to the output file
            
        Raises:
            ValueError: If no PMIDs have been found
        """
        if not self.pmids:
            self.logger.error("No PMIDs found. Call find_pmids_for_genes() first.")
            raise ValueError("No PMIDs found. Call find_pmids_for_genes() first.")
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        # Write PMIDs to file, one per line
        with open(output_file_path, 'w') as file:
            for pmid in sorted(self.pmids):
                file.write(f"{pmid}\n")
        
        self.logger.info(f"Saved {len(self.pmids)} PMIDs to {output_file_path}")
    
    def process_and_save(self, input_file_path: str, output_file_path: str) -> None:
        """
        Process the input gene file and save the resulting PMIDs to the output file.
        
        This is a convenience method that chains together the individual steps:
        loading genes, finding PMIDs, and saving to file.
        
        Args:
            input_file_path: Path to the input file with gene symbols
            output_file_path: Path to the output file for PMIDs
        """
        self.logger.info(f"Processing gene file: {input_file_path}")
        
        # Load genes, find PMIDs, and save to file
        self.load_genes_from_file(input_file_path)
        self.find_pmids_for_genes()
        self.save_pmids_to_file(output_file_path)
        
        self.logger.info("Processing complete") 