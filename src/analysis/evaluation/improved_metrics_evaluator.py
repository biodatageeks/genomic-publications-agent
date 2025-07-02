"""
Improved Variant Metrics Evaluator with HGVS normalization.

This module provides enhanced metrics calculation with standardized
variant normalization for more accurate comparisons.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from datetime import datetime
import csv

from src.utils.variant_normalizer import HGVSNormalizer, normalize_variants_for_comparison


class ImprovedVariantMetricsEvaluator:
    """
    Enhanced evaluator for calculating metrics between predicted and reference variants
    with standardized HGVS normalization.
    """
    
    def __init__(self, data_dir: str = "results/2025-07-01/data"):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(data_dir).parent / "reports"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize HGVS normalizer
        self.normalizer = HGVSNormalizer()
        
    def normalize_variant(self, variant: str) -> str:
        """
        Normalize variant notation using HGVS standards.
        
        Args:
            variant: Raw variant string
            
        Returns:
            Normalized variant string
        """
        if not variant:
            return ""
        
        # Use the HGVS normalizer
        normalized_variant = self.normalizer.normalize_variant(variant)
        return normalized_variant.normalized
    
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
    
    def extract_variant_sets(self, gene_data: Dict[str, List[Dict]], 
                           use_normalization: bool = True) -> Dict[str, Set[str]]:
        """
        Extract normalized variant sets for each gene.
        
        Args:
            gene_data: Dictionary with gene -> list of variant records
            use_normalization: Whether to apply HGVS normalization
            
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
                    if use_normalization:
                        normalized = self.normalize_variant(variant_text)
                    else:
                        normalized = variant_text.lower().strip()
                    
                    if normalized:
                        variant_set.add(normalized)
            
            gene_variant_sets[gene] = variant_set
        
        return gene_variant_sets
    
    def calculate_metrics(self, predicted_set: Set[str], reference_set: Set[str]) -> Dict[str, Any]:
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
    
    def analyze_variant_overlap(self, predicted_set: Set[str], reference_set: Set[str]) -> Dict[str, Any]:
        """
        Analyze the overlap between predicted and reference variants in detail.
        
        Args:
            predicted_set: Set of predicted variants
            reference_set: Set of reference variants
            
        Returns:
            Detailed analysis of variant overlap
        """
        true_positives = predicted_set & reference_set
        false_positives = predicted_set - reference_set
        false_negatives = reference_set - predicted_set
        
        # Analyze patterns in false positives
        fp_patterns = defaultdict(int)
        for fp in false_positives:
            if re.match(r'^[a-z][0-9]*[kmh]$', fp.lower()):
                fp_patterns['histone_marks'] += 1
            elif re.match(r'^[a-z][0-9]+[a-z]$', fp.lower()) and len(fp) <= 4:
                fp_patterns['lab_codes'] += 1
            elif re.match(r'^c\.123[a-z]>[a-z]$', fp.lower()):
                fp_patterns['mock_variants'] += 1
            elif re.match(r'^rs\d+$', fp.lower()):
                fp_patterns['dbsnp_ids'] += 1
            elif re.match(r'^p\.[a-z]\d+[a-z]$', fp.lower()):
                fp_patterns['protein_variants'] += 1
            else:
                fp_patterns['other'] += 1
        
        return {
            'true_positives': list(true_positives),
            'false_positives': list(false_positives),
            'false_negatives': list(false_negatives),
            'fp_patterns': dict(fp_patterns),
            'overlap_ratio': len(true_positives) / len(predicted_set | reference_set) if (predicted_set | reference_set) else 0.0
        }
    
    def evaluate_predicted_vs_pubtator(self, predicted_variants: Dict, pubtator_variants: Dict,
                                     use_normalization: bool = True) -> Dict[str, Any]:
        """
        Evaluate LLM predictions vs PubTator annotations with normalization.
        
        Args:
            predicted_variants: LLM predicted variants
            pubtator_variants: PubTator reference variants
            use_normalization: Whether to apply HGVS normalization
            
        Returns:
            Evaluation results
        """
        self.logger.info(f"Evaluating LLM predictions vs PubTator annotations (normalization: {use_normalization})...")
        
        predicted_sets = self.extract_variant_sets(predicted_variants, use_normalization)
        pubtator_sets = self.extract_variant_sets(pubtator_variants, use_normalization)
        
        gene_metrics = {}
        overall_predicted = set()
        overall_reference = set()
        
        # Get all genes that appear in either dataset
        all_genes = set(predicted_sets.keys()) | set(pubtator_sets.keys())
        
        for gene in all_genes:
            predicted_set = predicted_sets.get(gene, set())
            reference_set = pubtator_sets.get(gene, set())
            
            metrics = self.calculate_metrics(predicted_set, reference_set)
            overlap_analysis = self.analyze_variant_overlap(predicted_set, reference_set)
            
            # Add additional metrics data
            metrics['predicted_count'] = len(predicted_set)
            metrics['reference_count'] = len(reference_set)
            metrics['predicted_variants'] = list(predicted_set)
            metrics['reference_variants'] = list(reference_set)
            metrics['overlap_analysis'] = overlap_analysis
            
            gene_metrics[gene] = metrics
            
            # Accumulate for overall metrics
            overall_predicted.update(predicted_set)
            overall_reference.update(reference_set)
        
        # Calculate overall metrics
        overall_metrics = self.calculate_metrics(overall_predicted, overall_reference)
        overall_overlap = self.analyze_variant_overlap(overall_predicted, overall_reference)
        overall_metrics['total_genes'] = len(all_genes)
        overall_metrics['overlap_analysis'] = overall_overlap
        
        return {
            "comparison": f"LLM_predictions_vs_PubTator{'_normalized' if use_normalization else '_raw'}",
            "normalization_enabled": use_normalization,
            "overall_metrics": overall_metrics,
            "gene_metrics": gene_metrics,
            "evaluation_date": datetime.now().isoformat()
        }
    
    def evaluate_predicted_vs_litvar(self, predicted_variants: Dict, litvar_variants: Dict,
                                   use_normalization: bool = True) -> Dict[str, Any]:
        """
        Evaluate LLM predictions vs LitVar data with normalization.
        
        Args:
            predicted_variants: LLM predicted variants
            litvar_variants: LitVar reference variants
            use_normalization: Whether to apply HGVS normalization
            
        Returns:
            Evaluation results
        """
        self.logger.info(f"Evaluating LLM predictions vs LitVar data (normalization: {use_normalization})...")
        
        predicted_sets = self.extract_variant_sets(predicted_variants, use_normalization)
        litvar_sets = self.extract_variant_sets(litvar_variants, use_normalization)
        
        gene_metrics = {}
        overall_predicted = set()
        overall_reference = set()
        
        # Get all genes that appear in either dataset
        all_genes = set(predicted_sets.keys()) | set(litvar_sets.keys())
        
        for gene in all_genes:
            predicted_set = predicted_sets.get(gene, set())
            reference_set = litvar_sets.get(gene, set())
            
            metrics = self.calculate_metrics(predicted_set, reference_set)
            overlap_analysis = self.analyze_variant_overlap(predicted_set, reference_set)
            
            # Add additional metrics data
            metrics['predicted_count'] = len(predicted_set)
            metrics['reference_count'] = len(reference_set)
            metrics['predicted_variants'] = list(predicted_set)
            metrics['reference_variants'] = list(reference_set)
            metrics['overlap_analysis'] = overlap_analysis
            
            gene_metrics[gene] = metrics
            
            # Accumulate for overall metrics
            overall_predicted.update(predicted_set)
            overall_reference.update(reference_set)
        
        # Calculate overall metrics
        overall_metrics = self.calculate_metrics(overall_predicted, overall_reference)
        overall_overlap = self.analyze_variant_overlap(overall_predicted, overall_reference)
        overall_metrics['total_genes'] = len(all_genes)
        overall_metrics['overlap_analysis'] = overall_overlap
        
        return {
            "comparison": f"LLM_predictions_vs_LitVar{'_normalized' if use_normalization else '_raw'}",
            "normalization_enabled": use_normalization,
            "overall_metrics": overall_metrics,
            "gene_metrics": gene_metrics,
            "evaluation_date": datetime.now().isoformat()
        }
    
    def compare_normalization_impact(self, predicted_variants: Dict, reference_variants: Dict) -> Dict[str, Any]:
        """
        Compare metrics with and without normalization to show impact.
        
        Args:
            predicted_variants: LLM predicted variants
            reference_variants: Reference variants (PubTator or LitVar)
            
        Returns:
            Comparison of normalized vs raw metrics
        """
        self.logger.info("Comparing normalization impact...")
        
        # Evaluate with normalization
        normalized_results = self.evaluate_predicted_vs_pubtator(
            predicted_variants, reference_variants, use_normalization=True
        )
        
        # Evaluate without normalization
        raw_results = self.evaluate_predicted_vs_pubtator(
            predicted_variants, reference_variants, use_normalization=False
        )
        
        # Calculate improvement
        norm_f1 = normalized_results['overall_metrics']['f1_score']
        raw_f1 = raw_results['overall_metrics']['f1_score']
        improvement = norm_f1 - raw_f1
        
        return {
            'normalized_metrics': normalized_results['overall_metrics'],
            'raw_metrics': raw_results['overall_metrics'],
            'improvement': {
                'f1_score_improvement': improvement,
                'precision_improvement': normalized_results['overall_metrics']['precision'] - raw_results['overall_metrics']['precision'],
                'recall_improvement': normalized_results['overall_metrics']['recall'] - raw_results['overall_metrics']['recall']
            }
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
        output_file = self.reports_dir / "improved_metrics_summary.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'comparison', 'normalization', 'precision', 'recall', 'f1_score', 
                'true_positives', 'false_positives', 'false_negatives',
                'total_genes', 'overlap_ratio'
            ])
            
            # Write PubTator metrics
            pub_overall = pubtator_metrics['overall_metrics']
            writer.writerow([
                'LLM_vs_PubTator',
                pubtator_metrics.get('normalization_enabled', True),
                f"{pub_overall['precision']:.3f}",
                f"{pub_overall['recall']:.3f}",
                f"{pub_overall['f1_score']:.3f}",
                pub_overall['true_positives'],
                pub_overall['false_positives'], 
                pub_overall['false_negatives'],
                pub_overall['total_genes'],
                f"{pub_overall.get('overlap_analysis', {}).get('overlap_ratio', 0.0):.3f}"
            ])
            
            # Write LitVar metrics
            lit_overall = litvar_metrics['overall_metrics']
            writer.writerow([
                'LLM_vs_LitVar',
                litvar_metrics.get('normalization_enabled', True),
                f"{lit_overall['precision']:.3f}",
                f"{lit_overall['recall']:.3f}",
                f"{lit_overall['f1_score']:.3f}",
                lit_overall['true_positives'],
                lit_overall['false_positives'],
                lit_overall['false_negatives'], 
                lit_overall['total_genes'],
                f"{lit_overall.get('overlap_analysis', {}).get('overlap_ratio', 0.0):.3f}"
            ])
        
        self.logger.info(f"Summary saved to {output_file}")
    
    def generate_improved_summary_report(self, pubtator_metrics: Dict, litvar_metrics: Dict):
        """
        Generate enhanced markdown summary report.
        
        Args:
            pubtator_metrics: Metrics for PubTator comparison
            litvar_metrics: Metrics for LitVar comparison
        """
        output_file = self.reports_dir / "improved_experiment_summary.md"
        
        with open(output_file, 'w') as f:
            f.write("# Improved FOX Genes Variant Extraction Experiment\n\n")
            f.write("## Experiment Overview\n\n")
            f.write("This experiment used **improved variant recognition and HGVS normalization** ")
            f.write("to compare LLM-based variant extraction against reference sources:\n")
            f.write("- **PubTator3**: Manually curated variant annotations\n")
            f.write("- **LitVar**: Literature-derived variant database\n\n")
            
            f.write("### Key Improvements\n")
            f.write("1. **Removed mock data contamination** (no more fake c.123A>G variants)\n")
            f.write("2. **Added HGVS normalization** for standardized comparison\n")
            f.write("3. **Implemented false positive filtering** for lab codes and histone marks\n")
            f.write("4. **Enhanced context validation** for better precision\n\n")
            
            # PubTator results
            f.write("## Results vs PubTator (With HGVS Normalization)\n\n")
            pub_overall = pubtator_metrics['overall_metrics']
            f.write(f"- **Precision**: {pub_overall['precision']:.3f}\n")
            f.write(f"- **Recall**: {pub_overall['recall']:.3f}\n")
            f.write(f"- **F1-Score**: {pub_overall['f1_score']:.3f}\n")
            f.write(f"- **True Positives**: {pub_overall['true_positives']}\n")
            f.write(f"- **False Positives**: {pub_overall['false_positives']}\n")
            f.write(f"- **False Negatives**: {pub_overall['false_negatives']}\n")
            f.write(f"- **Total Genes**: {pub_overall['total_genes']}\n")
            f.write(f"- **Overlap Ratio**: {pub_overall.get('overlap_analysis', {}).get('overlap_ratio', 0.0):.3f}\n\n")
            
            # False positive analysis
            if 'overlap_analysis' in pub_overall:
                fp_patterns = pub_overall['overlap_analysis'].get('fp_patterns', {})
                if fp_patterns:
                    f.write("### False Positive Analysis (PubTator)\n")
                    for pattern, count in fp_patterns.items():
                        f.write(f"- **{pattern.replace('_', ' ').title()}**: {count} variants\n")
                    f.write("\n")
            
            # LitVar results
            f.write("## Results vs LitVar (With HGVS Normalization)\n\n")
            lit_overall = litvar_metrics['overall_metrics']
            f.write(f"- **Precision**: {lit_overall['precision']:.3f}\n")
            f.write(f"- **Recall**: {lit_overall['recall']:.3f}\n")
            f.write(f"- **F1-Score**: {lit_overall['f1_score']:.3f}\n")
            f.write(f"- **True Positives**: {lit_overall['true_positives']}\n")
            f.write(f"- **False Positives**: {lit_overall['false_positives']}\n")
            f.write(f"- **False Negatives**: {lit_overall['false_negatives']}\n")
            f.write(f"- **Total Genes**: {lit_overall['total_genes']}\n")
            f.write(f"- **Overlap Ratio**: {lit_overall.get('overlap_analysis', {}).get('overlap_ratio', 0.0):.3f}\n\n")
            
            # Top performing genes
            f.write("## Top Performing Genes (vs PubTator)\n\n")
            gene_scores = [(gene, metrics['f1_score']) for gene, metrics in pubtator_metrics['gene_metrics'].items()]
            gene_scores.sort(key=lambda x: x[1], reverse=True)
            
            for gene, f1_score in gene_scores[:10]:
                f.write(f"- **{gene}**: F1 = {f1_score:.3f}\n")
            
            f.write(f"\n## Technical Details\n\n")
            f.write(f"- **HGVS Normalization**: {'Enabled' if pubtator_metrics.get('normalization_enabled', True) else 'Disabled'}\n")
            f.write(f"- **False Positive Filtering**: Enabled\n")
            f.write(f"- **Context Validation**: Enabled\n")
            f.write(f"- **Mock Data Removal**: Enabled\n")
            
            f.write(f"\n## Experiment Date\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"Improved summary report saved to {output_file}")
    
    def run_evaluation(self, compare_normalization: bool = True):
        """
        Run the complete improved evaluation.
        
        Args:
            compare_normalization: Whether to compare normalized vs raw metrics
        """
        self.logger.info("=== STARTING IMPROVED VARIANT METRICS EVALUATION ===")
        
        try:
            # Load data
            predicted_variants, pubtator_variants, litvar_variants = self.load_data()
            
            # Evaluate LLM vs PubTator (with normalization)
            pubtator_metrics = self.evaluate_predicted_vs_pubtator(
                predicted_variants, pubtator_variants, use_normalization=True
            )
            self.save_metrics_to_json(pubtator_metrics, "improved_llm_vs_pubtator_metrics.json")
            
            # Evaluate LLM vs LitVar (with normalization)
            litvar_metrics = self.evaluate_predicted_vs_litvar(
                predicted_variants, litvar_variants, use_normalization=True
            )
            self.save_metrics_to_json(litvar_metrics, "improved_llm_vs_litvar_metrics.json")
            
            # Compare normalization impact if requested
            if compare_normalization:
                normalization_comparison = self.compare_normalization_impact(
                    predicted_variants, pubtator_variants
                )
                self.save_metrics_to_json(normalization_comparison, "normalization_impact_analysis.json")
                
                self.logger.info(f"Normalization impact - F1 improvement: {normalization_comparison['improvement']['f1_score_improvement']:.3f}")
            
            # Save summary
            self.save_summary_to_csv(pubtator_metrics, litvar_metrics)
            
            # Generate report
            self.generate_improved_summary_report(pubtator_metrics, litvar_metrics)
            
            # Log summary
            self.logger.info("=== IMPROVED EVALUATION COMPLETED ===")
            self.logger.info(f"LLM vs PubTator - Precision: {pubtator_metrics['overall_metrics']['precision']:.3f}, "
                           f"Recall: {pubtator_metrics['overall_metrics']['recall']:.3f}, "
                           f"F1: {pubtator_metrics['overall_metrics']['f1_score']:.3f}")
            self.logger.info(f"LLM vs LitVar - Precision: {litvar_metrics['overall_metrics']['precision']:.3f}, "
                           f"Recall: {litvar_metrics['overall_metrics']['recall']:.3f}, "
                           f"F1: {litvar_metrics['overall_metrics']['f1_score']:.3f}")
            
        except Exception as e:
            self.logger.error(f"Improved evaluation failed: {e}")
            raise


def main():
    """Main function to run the improved evaluation."""
    evaluator = ImprovedVariantMetricsEvaluator()
    evaluator.run_evaluation()


if __name__ == "__main__":
    main()