#!/usr/bin/env python3
"""
Variant Metrics Evaluator - 01.07.2025

Calculate metrics comparing LLM-predicted variants vs reference variants.
Calculates: Precision, Recall, F1-score, and detailed analysis.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from datetime import datetime
import csv


class VariantMetricsEvaluator:
    """
    Evaluator for calculating metrics between predicted and reference variants.
    """
    
    def __init__(self, data_dir: str = "results/2025-07-01/data"):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(data_dir).parent / "reports"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def normalize_variant(self, variant: str) -> str:
        """
        Normalize variant notation for comparison.
        
        Args:
            variant: Raw variant string
            
        Returns:
            Normalized variant string
        """
        if not variant:
            return ""
        
        # Convert to lowercase and remove spaces
        normalized = variant.lower().strip()
        
        # Remove common prefixes if present
        prefixes_to_remove = ['variant:', 'var:', 'mutation:', 'mut:']
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Standardize HGVS notation
        # Handle cases like "c.123a>g" -> "c.123A>G"
        hgvs_pattern = r'([cgpn])\.(\d+)([atcg])>([atcg])'
        match = re.search(hgvs_pattern, normalized)
        if match:
            prefix, position, ref_base, alt_base = match.groups()
            normalized = f"{prefix}.{position}{ref_base.upper()}>{alt_base.upper()}"
        
        # Handle protein notation like "p.val600glu" -> "p.V600E"
        protein_pattern = r'p\.([a-z]{3})(\d+)([a-z]{3})'
        match = re.search(protein_pattern, normalized)
        if match:
            aa1, position, aa2 = match.groups()
            # Convert 3-letter amino acid codes to 1-letter
            aa_map = {
                'ala': 'A', 'arg': 'R', 'asn': 'N', 'asp': 'D', 'cys': 'C',
                'gln': 'Q', 'glu': 'E', 'gly': 'G', 'his': 'H', 'ile': 'I',
                'leu': 'L', 'lys': 'K', 'met': 'M', 'phe': 'F', 'pro': 'P',
                'ser': 'S', 'thr': 'T', 'trp': 'W', 'tyr': 'Y', 'val': 'V'
            }
            aa1_short = aa_map.get(aa1, aa1.upper())
            aa2_short = aa_map.get(aa2, aa2.upper())
            normalized = f"p.{aa1_short}{position}{aa2_short}"
        
        return normalized
    
    def load_data(self) -> Tuple[Dict, Dict, Dict]:
        """
        Load all data files.
        
        Returns:
            Tuple of (predicted_variants, pubtator_variants, litvar_variants)
        """
        self.logger.info("Loading data files...")
        
        # Load predicted variants (LLM)
        predicted_file = self.data_dir / "predicted_variants.json"
        with open(predicted_file, 'r') as f:
            predicted_variants = json.load(f)
        
        # Load PubTator reference variants
        pubtator_file = self.data_dir / "pubtator_variants.json"
        with open(pubtator_file, 'r') as f:
            pubtator_variants = json.load(f)
        
        # Load LitVar reference variants
        litvar_file = self.data_dir / "reference_variants.json"
        with open(litvar_file, 'r') as f:
            litvar_variants = json.load(f)
        
        return predicted_variants, pubtator_variants, litvar_variants
    
    def extract_variant_sets(self, gene_data: Dict[str, List[Dict]]) -> Dict[str, Set[str]]:
        """
        Extract normalized variant sets for each gene.
        
        Args:
            gene_data: Dictionary with gene -> list of variant records
            
        Returns:
            Dictionary with gene -> set of normalized variants
        """
        gene_variant_sets = {}
        
        for gene, variants in gene_data.items():
            variant_set = set()
            
            for variant_record in variants:
                # Extract variant text depending on the data structure
                if isinstance(variant_record, dict):
                    variant_text = variant_record.get('variant', '') or variant_record.get('name', '')
                else:
                    variant_text = str(variant_record)
                
                if variant_text:
                    normalized = self.normalize_variant(variant_text)
                    if normalized:
                        variant_set.add(normalized)
            
            gene_variant_sets[gene] = variant_set
        
        return gene_variant_sets
    
    def calculate_metrics(self, predicted_set: Set[str], reference_set: Set[str]) -> Dict[str, float]:
        """
        Calculate precision, recall, and F1-score.
        
        Args:
            predicted_set: Set of predicted variants
            reference_set: Set of reference variants
            
        Returns:
            Dictionary with metrics
        """
        if not predicted_set and not reference_set:
            return {
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0
            }
        
        true_positives = len(predicted_set & reference_set)
        false_positives = len(predicted_set - reference_set)
        false_negatives = len(reference_set - predicted_set)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }
    
    def evaluate_predicted_vs_pubtator(self, predicted_variants: Dict, pubtator_variants: Dict) -> Dict[str, Any]:
        """
        Evaluate LLM predictions vs PubTator annotations.
        
        Args:
            predicted_variants: LLM predicted variants
            pubtator_variants: PubTator reference variants
            
        Returns:
            Evaluation results
        """
        self.logger.info("Evaluating LLM predictions vs PubTator annotations...")
        
        predicted_sets = self.extract_variant_sets(predicted_variants)
        pubtator_sets = self.extract_variant_sets(pubtator_variants)
        
        gene_metrics = {}
        overall_predicted = set()
        overall_reference = set()
        
        # Get all genes that appear in either dataset
        all_genes = set(predicted_sets.keys()) | set(pubtator_sets.keys())
        
        for gene in all_genes:
            predicted_set = predicted_sets.get(gene, set())
            reference_set = pubtator_sets.get(gene, set())
            
            metrics = self.calculate_metrics(predicted_set, reference_set)
            metrics['predicted_count'] = len(predicted_set)
            metrics['reference_count'] = len(reference_set)
            metrics['predicted_variants'] = list(predicted_set)
            metrics['reference_variants'] = list(reference_set)
            metrics['true_positive_variants'] = list(predicted_set & reference_set)
            metrics['false_positive_variants'] = list(predicted_set - reference_set)
            metrics['false_negative_variants'] = list(reference_set - predicted_set)
            
            gene_metrics[gene] = metrics
            
            # Accumulate for overall metrics
            overall_predicted.update(predicted_set)
            overall_reference.update(reference_set)
        
        # Calculate overall metrics
        overall_metrics = self.calculate_metrics(overall_predicted, overall_reference)
        overall_metrics['total_genes'] = len(all_genes)
        
        return {
            "comparison": "LLM_predictions_vs_PubTator",
            "overall_metrics": overall_metrics,
            "gene_metrics": gene_metrics,
            "evaluation_date": datetime.now().isoformat()
        }
    
    def evaluate_predicted_vs_litvar(self, predicted_variants: Dict, litvar_variants: Dict) -> Dict[str, Any]:
        """
        Evaluate LLM predictions vs LitVar data.
        
        Args:
            predicted_variants: LLM predicted variants
            litvar_variants: LitVar reference variants
            
        Returns:
            Evaluation results
        """
        self.logger.info("Evaluating LLM predictions vs LitVar data...")
        
        predicted_sets = self.extract_variant_sets(predicted_variants)
        litvar_sets = self.extract_variant_sets(litvar_variants)
        
        gene_metrics = {}
        overall_predicted = set()
        overall_reference = set()
        
        # Get all genes that appear in either dataset
        all_genes = set(predicted_sets.keys()) | set(litvar_sets.keys())
        
        for gene in all_genes:
            predicted_set = predicted_sets.get(gene, set())
            reference_set = litvar_sets.get(gene, set())
            
            metrics = self.calculate_metrics(predicted_set, reference_set)
            metrics['predicted_count'] = len(predicted_set)
            metrics['reference_count'] = len(reference_set)
            metrics['predicted_variants'] = list(predicted_set)
            metrics['reference_variants'] = list(reference_set)
            metrics['true_positive_variants'] = list(predicted_set & reference_set)
            metrics['false_positive_variants'] = list(predicted_set - reference_set)
            metrics['false_negative_variants'] = list(reference_set - predicted_set)
            
            gene_metrics[gene] = metrics
            
            # Accumulate for overall metrics
            overall_predicted.update(predicted_set)
            overall_reference.update(reference_set)
        
        # Calculate overall metrics
        overall_metrics = self.calculate_metrics(overall_predicted, overall_reference)
        overall_metrics['total_genes'] = len(all_genes)
        
        return {
            "comparison": "LLM_predictions_vs_LitVar",
            "overall_metrics": overall_metrics,
            "gene_metrics": gene_metrics,
            "evaluation_date": datetime.now().isoformat()
        }
    
    def save_metrics_to_json(self, metrics: Dict[str, Any], filename: str):
        """
        Save metrics to JSON file.
        
        Args:
            metrics: Metrics dictionary
            filename: Output filename
        """
        output_file = self.reports_dir / filename
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.logger.info(f"Metrics saved to {output_file}")
    
    def save_summary_to_csv(self, pubtator_metrics: Dict, litvar_metrics: Dict):
        """
        Save summary metrics to CSV.
        
        Args:
            pubtator_metrics: Metrics for PubTator comparison
            litvar_metrics: Metrics for LitVar comparison
        """
        output_file = self.reports_dir / "metrics_summary.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'comparison', 'precision', 'recall', 'f1_score', 
                'true_positives', 'false_positives', 'false_negatives',
                'total_genes'
            ])
            
            # Write PubTator metrics
            pub_overall = pubtator_metrics['overall_metrics']
            writer.writerow([
                'LLM_vs_PubTator',
                f"{pub_overall['precision']:.3f}",
                f"{pub_overall['recall']:.3f}",
                f"{pub_overall['f1_score']:.3f}",
                pub_overall['true_positives'],
                pub_overall['false_positives'], 
                pub_overall['false_negatives'],
                pub_overall['total_genes']
            ])
            
            # Write LitVar metrics
            lit_overall = litvar_metrics['overall_metrics']
            writer.writerow([
                'LLM_vs_LitVar',
                f"{lit_overall['precision']:.3f}",
                f"{lit_overall['recall']:.3f}",
                f"{lit_overall['f1_score']:.3f}",
                lit_overall['true_positives'],
                lit_overall['false_positives'],
                lit_overall['false_negatives'], 
                lit_overall['total_genes']
            ])
        
        self.logger.info(f"Summary saved to {output_file}")
    
    def generate_experiment_summary(self, pubtator_metrics: Dict, litvar_metrics: Dict):
        """
        Generate markdown summary report.
        
        Args:
            pubtator_metrics: Metrics for PubTator comparison
            litvar_metrics: Metrics for LitVar comparison
        """
        output_file = self.reports_dir / "experiment_summary.md"
        
        with open(output_file, 'w') as f:
            f.write("# FOX Genes Variant Extraction Experiment - 01.07.2025\n\n")
            f.write("## Experiment Overview\n\n")
            f.write("This experiment compared LLM-based variant extraction against reference sources:\n")
            f.write("- **PubTator**: Manually curated variant annotations\n")
            f.write("- **LitVar**: Literature-derived variant database\n\n")
            
            # PubTator results
            f.write("## Results vs PubTator\n\n")
            pub_overall = pubtator_metrics['overall_metrics']
            f.write(f"- **Precision**: {pub_overall['precision']:.3f}\n")
            f.write(f"- **Recall**: {pub_overall['recall']:.3f}\n")
            f.write(f"- **F1-Score**: {pub_overall['f1_score']:.3f}\n")
            f.write(f"- **True Positives**: {pub_overall['true_positives']}\n")
            f.write(f"- **False Positives**: {pub_overall['false_positives']}\n")
            f.write(f"- **False Negatives**: {pub_overall['false_negatives']}\n")
            f.write(f"- **Total Genes**: {pub_overall['total_genes']}\n\n")
            
            # LitVar results
            f.write("## Results vs LitVar\n\n")
            lit_overall = litvar_metrics['overall_metrics']
            f.write(f"- **Precision**: {lit_overall['precision']:.3f}\n")
            f.write(f"- **Recall**: {lit_overall['recall']:.3f}\n")
            f.write(f"- **F1-Score**: {lit_overall['f1_score']:.3f}\n")
            f.write(f"- **True Positives**: {lit_overall['true_positives']}\n")
            f.write(f"- **False Positives**: {lit_overall['false_positives']}\n")
            f.write(f"- **False Negatives**: {lit_overall['false_negatives']}\n")
            f.write(f"- **Total Genes**: {lit_overall['total_genes']}\n\n")
            
            # Top performing genes
            f.write("## Top Performing Genes (vs PubTator)\n\n")
            gene_scores = [(gene, metrics['f1_score']) for gene, metrics in pubtator_metrics['gene_metrics'].items()]
            gene_scores.sort(key=lambda x: x[1], reverse=True)
            
            for gene, f1_score in gene_scores[:10]:
                f.write(f"- **{gene}**: F1 = {f1_score:.3f}\n")
            
            f.write(f"\n## Experiment Date\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"Summary report saved to {output_file}")
    
    def run_evaluation(self):
        """
        Run the complete evaluation.
        """
        self.logger.info("=== STARTING VARIANT METRICS EVALUATION ===")
        
        try:
            # Load data
            predicted_variants, pubtator_variants, litvar_variants = self.load_data()
            
            # Evaluate LLM vs PubTator
            pubtator_metrics = self.evaluate_predicted_vs_pubtator(predicted_variants, pubtator_variants)
            self.save_metrics_to_json(pubtator_metrics, "llm_vs_pubtator_metrics.json")
            
            # Evaluate LLM vs LitVar
            litvar_metrics = self.evaluate_predicted_vs_litvar(predicted_variants, litvar_variants)
            self.save_metrics_to_json(litvar_metrics, "llm_vs_litvar_metrics.json")
            
            # Save summary
            self.save_summary_to_csv(pubtator_metrics, litvar_metrics)
            
            # Generate report
            self.generate_experiment_summary(pubtator_metrics, litvar_metrics)
            
            # Log summary
            self.logger.info("=== EVALUATION COMPLETED ===")
            self.logger.info(f"LLM vs PubTator - Precision: {pubtator_metrics['overall_metrics']['precision']:.3f}, "
                           f"Recall: {pubtator_metrics['overall_metrics']['recall']:.3f}, "
                           f"F1: {pubtator_metrics['overall_metrics']['f1_score']:.3f}")
            self.logger.info(f"LLM vs LitVar - Precision: {litvar_metrics['overall_metrics']['precision']:.3f}, "
                           f"Recall: {litvar_metrics['overall_metrics']['recall']:.3f}, "
                           f"F1: {litvar_metrics['overall_metrics']['f1_score']:.3f}")
            
        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}")
            raise


def main():
    """Main function to run the evaluation."""
    evaluator = VariantMetricsEvaluator()
    evaluator.run_evaluation()


if __name__ == "__main__":
    main() 