#!/usr/bin/env python3
"""
Complete FOX Genes Variant Extraction Experiment - 01.07.2025

Full experiment using simplified modules to avoid import issues.
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

# Import working modules
from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
from api.clients.litvar_endpoint import LitVarEndpoint

# Import our simplified modules
from experiment_modules import SimplePubTatorClient, SimpleVariantRecognizer


class CompleteFoxExperiment:
    """Complete FOX genes variant extraction experiment."""
    
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
                logging.FileHandler(self.logs_dir / "complete_experiment.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize clients
        self.pmid_finder = FoxGenePMIDFinder()
        self.litvar_client = LitVarEndpoint()
        self.pubtator_client = SimplePubTatorClient()
        self.variant_recognizer = SimpleVariantRecognizer()
        
        self.logger.info(f"Initialized complete experiment in {self.output_dir}")
    
    def step1_load_genes_and_get_pmids(self, genes_file: str) -> Dict[str, int]:
        """Steps 1-3: Load FOX genes and get PMID counts."""
        self.logger.info("=== STEPS 1-3: Loading genes and getting PMID counts ===")
        
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
            
            temp_finder = FoxGenePMIDFinder()
            temp_finder.genes = [gene]
            gene_pmids = temp_finder.find_pmids_for_genes()
            
            count = len(gene_pmids)
            gene_pmid_counts[gene] = count
            all_pmids.update(gene_pmids)
            
            self.logger.info(f"Gene {gene}: {count} PMIDs")
            time.sleep(0.5)
        
        # Save results to CSV
        csv_output = self.data_dir / "gene_pmids_counts.csv"
        with open(csv_output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['gene', 'pmid_count'])
            for gene, count in gene_pmid_counts.items():
                writer.writerow([gene, count])
        
        total_pmids = len(all_pmids)
        self.logger.info(f"Total unique PMIDs: {total_pmids}")
        self.logger.info(f"Results saved to {csv_output}")
        
        return gene_pmid_counts
    
    def step4_extract_reference_variants_litvar(self, genes: List[str]) -> Dict[str, List[Dict]]:
        """Step 4: Extract variants from LitVar."""
        self.logger.info("=== STEP 4: Extracting reference variants from LitVar ===")
        
        gene_variants = {}
        
        for gene in genes:
            self.logger.info(f"Getting variants for gene: {gene}")
            try:
                variants = self.litvar_client.search_by_genes([gene])
                gene_variants[gene] = variants
                self.logger.info(f"Gene {gene}: {len(variants)} variants found")
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Error getting variants for {gene}: {e}")
                gene_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "reference_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_variants, f, indent=2)
        
        total_variants = sum(len(variants) for variants in gene_variants.values())
        self.logger.info(f"Total variants from LitVar: {total_variants}")
        
        return gene_variants
    
    def step5_extract_predicted_variants_llm(self, genes: List[str], max_pubs_per_gene: int = 20) -> Dict[str, List[Dict]]:
        """Step 5: Extract variants using simplified LLM (pattern matching)."""
        self.logger.info("=== STEP 5: Extracting predicted variants using simplified LLM ===")
        
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
                
                # Extract variants using simplified LLM for each publication
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
                            # Use simplified LLM to extract variants
                            variants = self.variant_recognizer.recognize_variants_text(full_text)
                            
                            # Store with metadata
                            for variant in variants:
                                gene_variants.append({
                                    "pmid": pub.id,
                                    "variant": variant,
                                    "gene": gene,
                                    "source": "simplified_llm_prediction"
                                })
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing publication {pub.id}: {e}")
                
                gene_predicted_variants[gene] = gene_variants
                self.logger.info(f"Gene {gene}: {len(gene_variants)} predicted variants")
                
                time.sleep(1.0)  # Rate limiting
                
            except Exception as e:
                self.logger.error(f"Error processing gene {gene}: {e}")
                gene_predicted_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "predicted_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_predicted_variants, f, indent=2)
        
        total_predicted = sum(len(variants) for variants in gene_predicted_variants.values())
        self.logger.info(f"Total predicted variants: {total_predicted}")
        
        return gene_predicted_variants
    
    def step6_extract_reference_variants_pubtator(self, genes: List[str], max_pubs_per_gene: int = 20) -> Dict[str, List[Dict]]:
        """Step 6: Extract reference variants from PubTator."""
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
                                "source": "pubtator_annotation",
                                "type": annotation.get("type", "")
                            })
                    
                    except Exception as e:
                        self.logger.warning(f"Error extracting variants from {pub.id}: {e}")
                
                gene_reference_variants[gene] = gene_variants
                self.logger.info(f"Gene {gene}: {len(gene_variants)} reference variants")
                
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error processing gene {gene}: {e}")
                gene_reference_variants[gene] = []
        
        # Save to JSON
        output_file = self.data_dir / "pubtator_variants.json"
        with open(output_file, 'w') as f:
            json.dump(gene_reference_variants, f, indent=2)
        
        total_reference = sum(len(variants) for variants in gene_reference_variants.values())
        self.logger.info(f"Total reference variants from PubTator: {total_reference}")
        
        return gene_reference_variants
    
    def step7_calculate_metrics(self):
        """Step 7: Calculate metrics using the evaluator."""
        self.logger.info("=== STEP 7: Calculating metrics ===")
        
        # Import and run the evaluator
        from variant_metrics_evaluator import VariantMetricsEvaluator
        
        evaluator = VariantMetricsEvaluator(str(self.data_dir))
        evaluator.run_evaluation()
        
        self.logger.info("Metrics calculation completed")
    
    def run_complete_experiment(self, genes_file: str = "external_data/enhancer_tables_from_uw/fox_unique_genes.txt", test_mode: bool = True):
        """Run the complete experiment."""
        start_time = datetime.now()
        self.logger.info(f"=== STARTING COMPLETE FOX EXPERIMENT at {start_time} ===")
        
        if test_mode:
            self.logger.info("Running in TEST MODE with 3 genes")
            # Use test genes
            test_genes = ["FOXA1", "FOXB1", "FOXC1"]
            test_genes_file = self.data_dir / "test_fox_genes.txt"
            with open(test_genes_file, 'w') as f:
                for gene in test_genes:
                    f.write(f"{gene}\n")
            genes_file = str(test_genes_file)
        
        try:
            # Step 1-3: Get gene PMID counts
            gene_pmid_counts = self.step1_load_genes_and_get_pmids(genes_file)
            genes = list(gene_pmid_counts.keys())
            
            # Step 4: Get reference variants from LitVar
            litvar_variants = self.step4_extract_reference_variants_litvar(genes)
            
            # Step 5: Get predicted variants using simplified LLM
            predicted_variants = self.step5_extract_predicted_variants_llm(genes)
            
            # Step 6: Get reference variants from PubTator
            pubtator_variants = self.step6_extract_reference_variants_pubtator(genes)
            
            # Step 7: Calculate metrics
            self.step7_calculate_metrics()
            
            # Generate summary
            self.generate_summary(gene_pmid_counts, litvar_variants, predicted_variants, pubtator_variants)
            
            self.logger.info("=== COMPLETE EXPERIMENT FINISHED SUCCESSFULLY ===")
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            raise
        
        end_time = datetime.now()
        duration = end_time - start_time
        self.logger.info(f"Total experiment duration: {duration}")
    
    def generate_summary(self, gene_pmids, litvar_variants, predicted_variants, pubtator_variants):
        """Generate experiment summary."""
        summary = {
            "experiment_date": datetime.now().isoformat(),
            "genes_tested": list(gene_pmids.keys()),
            "total_genes": len(gene_pmids),
            "total_pmids": sum(gene_pmids.values()),
            "litvar_variants": sum(len(v) for v in litvar_variants.values()),
            "predicted_variants": sum(len(v) for v in predicted_variants.values()),
            "pubtator_variants": sum(len(v) for v in pubtator_variants.values()),
            "gene_details": {
                gene: {
                    "pmids": gene_pmids.get(gene, 0),
                    "litvar_variants": len(litvar_variants.get(gene, [])),
                    "predicted_variants": len(predicted_variants.get(gene, [])),
                    "pubtator_variants": len(pubtator_variants.get(gene, []))
                }
                for gene in gene_pmids.keys()
            }
        }
        
        summary_file = self.reports_dir / "experiment_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Experiment summary saved to {summary_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("FOX EXPERIMENT SUMMARY")
        print("="*60)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Genes tested: {summary['total_genes']}")
        print(f"Total PMIDs: {summary['total_pmids']}")
        print(f"LitVar variants: {summary['litvar_variants']}")
        print(f"Predicted variants: {summary['predicted_variants']}")
        print(f"PubTator variants: {summary['pubtator_variants']}")
        print("\nPer-gene breakdown:")
        for gene, details in summary['gene_details'].items():
            print(f"  {gene}: {details['pmids']} PMIDs, "
                  f"{details['litvar_variants']} LitVar, "
                  f"{details['predicted_variants']} predicted, "
                  f"{details['pubtator_variants']} PubTator")
        print("="*60)


def main():
    """Main function to run the complete experiment."""
    experiment = CompleteFoxExperiment()
    
    # Run experiment in test mode (3 genes)
    experiment.run_complete_experiment(test_mode=True)


if __name__ == "__main__":
    main() 