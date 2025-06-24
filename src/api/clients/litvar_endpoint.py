"""
The LitVarEndpoint class enables communication with the LitVar2 API and retrieving
genomic variant information.
"""

import requests
import ast
import json
import pandas as pd
from typing import List, Dict, Any, Optional


class LitVarEndpoint:
    """
    Class for communication with the LitVar2 API (https://www.ncbi.nlm.nih.gov/research/litvar2-api/).
    
    Enables:
    - Searching for variants associated with specific genes
    - Retrieving variant details
    - Retrieving publication identifiers (PMID, PMCID) associated with variants
    - Saving retrieved data to JSON files
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
    
    def __init__(self):
        """
        Initialize the LitVar API client.
        """
        self.variants_data = []
        self.variant_details = {}
        self.pmids_data = {}
    
    def search_by_genes(self, genes: List[str]) -> List[Dict[str, Any]]:
        """
        Searches for variants associated with the given genes.
        
        Args:
            genes: List of gene names to search for
            
        Returns:
            List of dictionaries containing variant information
        """
        responses_dicts = []
        
        for gene in genes:
            url = f"{self.BASE_URL}/variant/search/gene/{gene}"
            response = requests.get(url)
            
            if response.status_code == 200:
                # Convert text response to list of dictionaries
                response_list = response.text.strip().split('\n')
                response_dicts = [ast.literal_eval(item) for item in response_list]
                # Add gene information to each dictionary
                gene_response_dicts = [{**item, "gene": gene} for item in response_dicts]
                responses_dicts.extend(gene_response_dicts)
        
        self.variants_data = responses_dicts
        return responses_dicts
    
    def get_variants_dataframe(self, variants_data: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Converts variant data to a pandas DataFrame.
        
        Args:
            variants_data: Optional list of dictionaries with variant data
            
        Returns:
            DataFrame with variant data
        """
        if variants_data is None:
            variants_data = self.variants_data
            
        return pd.DataFrame(variants_data)
    
    def get_variant_details(self, variant_ids: List[str]) -> Dict[str, Any]:
        """
        Retrieves detailed information about variants based on their identifiers.
        
        Args:
            variant_ids: List of variant identifiers (_id from search)
            
        Returns:
            Dictionary containing variant details
        """
        variant_details = {}
        
        for variant_id in variant_ids:
            url = f"{self.BASE_URL}/variant/get/{variant_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                variant_details[variant_id] = response.json()
        
        self.variant_details = variant_details
        return variant_details
    
    def get_pmids_pmcids(self, rsids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        Retrieves publication identifiers (PMID, PMCID) associated with variants.
        
        Args:
            rsids: List of variant rsid identifiers
            
        Returns:
            Dictionary mapping rsid to dictionary with PMID and PMCID lists
        """
        pmids_data = {}
        
        for rsid in rsids:
            url = f"{self.BASE_URL}/publications/get/{rsid}"
            response = requests.get(url)
            
            if response.status_code == 200:
                publications = response.json()
                pmids = [pub.get('pmid') for pub in publications if 'pmid' in pub]
                pmcids = [pub.get('pmcid') for pub in publications if 'pmcid' in pub]
                
                pmids_data[rsid] = {
                    'pmids': pmids,
                    'pmcids': pmcids
                }
        
        self.pmids_data = pmids_data
        return pmids_data
    
    def save_to_json(self, data: Any, file_path: str) -> None:
        """
        Saves data to a JSON file.
        
        Args:
            data: Data to save
            file_path: Path to the output file
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    
    def save_variants_data(self, file_path: str) -> None:
        """
        Saves variant data to a JSON file.
        
        Args:
            file_path: Path to the output file
        """
        self.save_to_json(self.variants_data, file_path)
    
    def save_variant_details(self, file_path: str) -> None:
        """
        Saves variant details to a JSON file.
        
        Args:
            file_path: Path to the output file
        """
        self.save_to_json(self.variant_details, file_path)
    
    def save_pmids_data(self, file_path: str) -> None:
        """
        Saves PMID/PMCID data to a JSON file.
        
        Args:
            file_path: Path to the output file
        """
        self.save_to_json(self.pmids_data, file_path)
    
    def process_gene_list(self, genes: List[str], 
                           variants_output_path: Optional[str] = None,
                           details_output_path: Optional[str] = None,
                           pmids_output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes a list of genes, retrieving variant information and associated publications.
        
        Args:
            genes: List of gene names
            variants_output_path: Optional path to the file with variant data
            details_output_path: Optional path to the file with variant details
            pmids_output_path: Optional path to the file with publication identifiers
            
        Returns:
            Dictionary containing all retrieved data
        """
        # Search for variants for genes
        variants_data = self.search_by_genes(genes)
        
        # Get rsids from variant data (only non-empty)
        rsids = [str(variant.get('rsid')) for variant in variants_data 
                if variant.get('rsid') and pd.notna(variant.get('rsid'))]
        
        # Get variant identifiers
        variant_ids = [str(variant.get('_id')) for variant in variants_data 
                      if variant.get('_id') is not None]
        
        # Get variant details
        variant_details = self.get_variant_details(variant_ids)
        
        # Get publication identifiers
        pmids_data = self.get_pmids_pmcids(rsids)
        
        # Save data to files if paths are provided
        if variants_output_path:
            self.save_variants_data(variants_output_path)
            
        if details_output_path:
            self.save_variant_details(details_output_path)
            
        if pmids_output_path:
            self.save_pmids_data(pmids_output_path)
        
        return {
            'variants_data': variants_data,
            'variant_details': variant_details,
            'pmids_data': pmids_data
        } 