#!/usr/bin/env python3
"""
Fox Genes Variant Extraction Experiment - 01.07.2025

Experiment comparing LLM-based variant extraction vs reference sources.
Steps:
1. Load FOX genes and get PMIDs count per gene
2. Extract variants based on gene names (LitVar)
3. Extract variants from publication texts using LLM (predicted)
4. Extract variants from PubTator (reference)
5. Calculate metrics: predicted vs reference
"""

import os
import sys
import json
import csv
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime
from collections import defaultdict

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
from api.clients.litvar_endpoint import LitVarEndpoint
from api.clients.pubtator_client import PubTatorClient
from analysis.bio_ner.variant_recognizer import VariantRecognizer


class FoxVariantExperiment:
    """
    Main orchestrator for FOX genes variant extraction experiment.
    """
    
    def __init__(self, output_dir: str = "results/2025-07-01"):
        self.output_dir = Path(output_dir)
        self.data_dir = self.output_dir / "data"
        self.reports_dir = self.output_dir / "reports"
        self.logs_dir = self.output_dir / "logs"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.logs_dir / "experiment.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize clients
        self.pmid_finder = FoxGenePMIDFinder()
        self.litvar_client = LitVarEndpoint()
        self.pubtator_client = PubTatorClient()
        self.variant_recognizer = VariantRecognizer()
        
        self.logger.info(f"Initialized experiment in {self.output_dir}")
    
    def step1_load_genes_and_get_pmids(self, genes_file: str) -> Dict[str, int]:
        """
        Step 1-3: Load FOX genes and get PMID counts per gene.
        
        Args:
            genes_file: Path to file with FOX genes
            
        Returns:
            Dictionary mapping gene names to PMID counts
        """
        self.logger.info("=== STEP 1-3: Loading genes and getting PMID counts ===")
        
        # Load genes
        genes = self.pmid_finder.load_genes_from_file(genes_file)
        self.logger.info(f"Loaded {len(genes)} FOX genes")
        
        # Save genes to data directory
        genes_output = self.data_dir / "fox_genes.txt"
        with open(genes_output, 'w') as f:
            for gene in genes:
                f.write(f"{gene}\n")
        
        # Get PMIDs for each gene and count them
        gene_pmid_counts = {}
        all_pmids = set()
        
        for gene in genes:
            self.logger.info(f"Getting PMIDs for gene: {gene}")
            
            # Create temporary finder for single gene
            temp_finder = FoxGenePMIDFinder()
            temp_finder.genes = [gene]
            gene_pmids = temp_finder.find_pmids_for_genes()
            
            count = len(gene_pmids)
            gene_pmid_counts[gene] = count
            all_pmids.update(gene_pmids)
            
            self.logger.info(f"Gene {gene}: {count} PMIDs")
            time.sleep(0.5)  # Rate limiting
        
        # Save results to CSV
        csv_output = self.data_dir / "gene_pmids_counts.csv"
        with open(csv_output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['gene', 'pmid_count'])
            for gene, count in gene_pmid_counts.items():
                writer.writerow([gene, count])
        
        total_pmids = len(all_pmids)
        self.logger.info(f"Total unique PMIDs across all genes: {total_pmids}")
        self.logger.info(f"Results saved to {csv_output}")
        
        return gene_pmid_counts
    
    def step4_extract_reference_variants_litvar(self, genes: List[str]) -> Dict[str, List[Dict]]:
        """
        Step 4: Extract variants based on gene names using LitVar.
        
        Args:
            genes: List of gene names
            
        Returns:
            Dictionary mapping genes to their variants
        """
        self.logger.info("=== STEP 4: Extracting reference variants from LitVar ===")
        
        gene_variants = {}
        
        for gene in genes:
            self.logger.info(f"Getting variants for gene: {gene}")
            try:
                variants = self.litvar_client.search_by_genes([gene])
                gene_variants[gene] = variants
                self.logger.info(f"Gene {gene}: {len(variants)} variants found")
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Error getting variants for {gene}: {e}")
                gene_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "reference_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_variants, f, indent=2)
        
        total_variants = sum(len(variants) for variants in gene_variants.values())
        self.logger.info(f"Total variants from LitVar: {total_variants}")
        self.logger.info(f"Results saved to {output_file}")
        
        return gene_variants
    
    def step5_extract_predicted_variants_llm(self, genes: List[str], max_pubs_per_gene: int = 100) -> Dict[str, List[Dict]]:
        """
        Step 5: Extract variants from publication texts using LLM.
        
        Args:
            genes: List of gene names
            max_pubs_per_gene: Maximum publications to process per gene
            
        Returns:
            Dictionary with predicted variants per gene
        """
        self.logger.info("=== STEP 5: Extracting predicted variants using LLM ===")
        
        gene_predicted_variants = {}
        
        for gene in genes:
            self.logger.info(f"Processing publications for gene: {gene}")
            
            try:
                # Get PMIDs for this gene (limited)
                temp_finder = FoxGenePMIDFinder()
                temp_finder.genes = [gene]
                pmids = list(temp_finder.find_pmids_for_genes())
                
                # Limit to max_pubs_per_gene
                if len(pmids) > max_pubs_per_gene:
                    pmids = pmids[:max_pubs_per_gene]
                    self.logger.info(f"Limited to {max_pubs_per_gene} publications for {gene}")
                
                # Get publications from PubTator
                publications = self.pubtator_client.get_publications_by_pmids(pmids)
                
                # Extract variants using LLM for each publication
                gene_variants = []
                for pub in publications:
                    try:
                        # Combine title and abstract text
                        text_parts = []
                        for passage in pub.passages:
                            if passage.text:
                                text_parts.append(passage.text)
                        
                        full_text = " ".join(text_parts)
                        
                        if full_text:
                            # Use LLM to extract variants
                            variants = self.variant_recognizer.recognize_variants_text(full_text)
                            
                            # Store with metadata
                            for variant in variants:
                                gene_variants.append({
                                    "pmid": pub.id,
                                    "variant": variant,
                                    "gene": gene,
                                    "source": "llm_prediction"
                                })
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing publication {pub.id}: {e}")
                
                gene_predicted_variants[gene] = gene_variants
                self.logger.info(f"Gene {gene}: {len(gene_variants)} predicted variants")
                
                time.sleep(1.0)  # Rate limiting for LLM calls
                
            except Exception as e:
                self.logger.error(f"Error processing gene {gene}: {e}")
                gene_predicted_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "predicted_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_predicted_variants, f, indent=2)
        
        total_predicted = sum(len(variants) for variants in gene_predicted_variants.values())
        self.logger.info(f"Total predicted variants: {total_predicted}")
        self.logger.info(f"Results saved to {output_file}")
        
        return gene_predicted_variants
    
    def step6_extract_reference_variants_pubtator(self, genes: List[str], max_pubs_per_gene: int = 100) -> Dict[str, List[Dict]]:
        """
        Step 6: Extract reference variants from PubTator annotations.
        
        Args:
            genes: List of gene names
            max_pubs_per_gene: Maximum publications to process per gene
            
        Returns:
            Dictionary with reference variants per gene from PubTator
        """
        self.logger.info("=== STEP 6: Extracting reference variants from PubTator ===")
        
        gene_reference_variants = {}
        
        for gene in genes:
            self.logger.info(f"Getting PubTator variants for gene: {gene}")
            
            try:
                # Get PMIDs for this gene (limited)
                temp_finder = FoxGenePMIDFinder()
                temp_finder.genes = [gene]
                pmids = list(temp_finder.find_pmids_for_genes())
                
                # Limit to max_pubs_per_gene
                if len(pmids) > max_pubs_per_gene:
                    pmids = pmids[:max_pubs_per_gene]
                
                # Get publications with PubTator annotations
                publications = self.pubtator_client.get_publications_by_pmids(pmids)
                
                # Extract variant annotations
                gene_variants = []
                for pub in publications:
                    try:
                        variant_annotations = self.pubtator_client.extract_variant_annotations(pub)
                        
                        for annotation in variant_annotations:
                            gene_variants.append({
                                "pmid": pub.id,
                                "variant": annotation.get("text", ""),
                                "variant_id": annotation.get("id", ""),
                                "gene": gene,
                                "source": "pubtator_annotation"
                            })
                    
                    except Exception as e:
                        self.logger.warning(f"Error extracting variants from {pub.id}: {e}")
                
                gene_reference_variants[gene] = gene_variants
                self.logger.info(f"Gene {gene}: {len(gene_variants)} reference variants")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                self.logger.error(f"Error processing gene {gene}: {e}")
                gene_reference_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "pubtator_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_reference_variants, f, indent=2)
        
        total_reference = sum(len(variants) for variants in gene_reference_variants.values())
        self.logger.info(f"Total reference variants from PubTator: {total_reference}")
        self.logger.info(f"Results saved to {output_file}")
        
        return gene_reference_variants
    
    def run_experiment(self, genes_file: str = "external_data/enhancer_tables_from_uw/fox_unique_genes.txt"):
        """
        Run the complete experiment.
        
        Args:
            genes_file: Path to file with FOX genes
        """
        start_time = datetime.now()
        self.logger.info(f"=== STARTING FOX VARIANT EXPERIMENT at {start_time} ===")
        
        try:
            # Step 1-3: Get gene PMID counts
            gene_pmid_counts = self.step1_load_genes_and_get_pmids(genes_file)
            genes = list(gene_pmid_counts.keys())
            
            # Step 4: Get reference variants from LitVar
            litvar_variants = self.step4_extract_reference_variants_litvar(genes)
            
            # Step 5: Get predicted variants using LLM
            predicted_variants = self.step5_extract_predicted_variants_llm(genes)
            
            # Step 6: Get reference variants from PubTator
            pubtator_variants = self.step6_extract_reference_variants_pubtator(genes)
            
            # Step 7: Calculate metrics (will implement in next script)
            self.logger.info("=== EXPERIMENT COMPLETED SUCCESSFULLY ===")
            self.logger.info("Next: Run variant_metrics_evaluator.py to calculate metrics")
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            raise
        
        end_time = datetime.now()
        duration = end_time - start_time
        self.logger.info(f"Total experiment duration: {duration}")


def main():
    """Main function to run the experiment."""
    experiment = FoxVariantExperiment()
    experiment.run_experiment()


if __name__ == "__main__":
    main() 