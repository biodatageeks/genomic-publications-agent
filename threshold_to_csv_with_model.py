import json
import csv
import os
import argparse

def extract_model_name_from_file(filename):
    """Extrapolate model name from the filename pattern"""
    if "33_70b" in filename.lower() or "3.3_70b" in filename.lower():
        return "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    else:
        return "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

def process_json_file(json_file, model_name=None):
    """Process a single JSON file and return data with model information"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # If model name not provided, try to extract from filename
    if model_name is None:
        model_name = extract_model_name_from_file(json_file)
    
    # Add model information to each item
    for item in data:
        item['model'] = model_name
    
    return data

def main():
    parser = argparse.ArgumentParser(description="Convert threshold analysis JSON results to CSV with model information")
    parser.add_argument("--json_files", nargs="+", required=True, help="JSON files with threshold analysis results")
    parser.add_argument("--output", default="threshold_metrics_combined.csv", help="Output CSV file")
    parser.add_argument("--models", nargs="*", help="List of model names (in the same order as json_files)")
    
    args = parser.parse_args()
    
    all_data = []
    
    # Process each JSON file
    for i, json_file in enumerate(args.json_files):
        # Use provided model name if available
        model_name = args.models[i] if args.models and i < len(args.models) else None
        file_data = process_json_file(json_file, model_name)
        all_data.extend(file_data)
    
    # Sort data by model and threshold
    sorted_data = sorted(all_data, key=lambda x: (x['model'], 
                                                  float('-inf') if x['score_threshold'] is None else x['score_threshold']))
    
    # Write to CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.writer(f)
        # Headers
        writer.writerow(['model', 'threshold', 'gene_precision', 'gene_recall', 'gene_f1', 
                         'disease_precision', 'disease_recall', 'disease_f1'])
        
        # Data
        for item in sorted_data:
            threshold = item['score_threshold'] if item['score_threshold'] is not None else 'None'
            writer.writerow([
                item['model'],
                threshold,
                item['gene_precision'],
                item['gene_recall'],
                item['gene_f1'],
                item['disease_precision'],
                item['disease_recall'],
                item['disease_f1']
            ])
    
    print(f'Zapisano dane do pliku {args.output}')

if __name__ == "__main__":
    main() 