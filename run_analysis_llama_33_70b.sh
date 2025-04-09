#!/bin/bash

# Script to run enhanced coordinate generation and comparative analysis
# using the UnifiedLlmContextAnalyzer and Llama 3.3-70B model

# Make sure directories exist
mkdir -p data/pmids data/csv data/results/experiments data/results/images

# Set variables
INPUT_PMIDS="data/pmids/input_pmids.txt"
CONFIRMED_DATA="data/Enhancer candidates - DiseaseEnhancer - to verify.csv"
OUTPUT_CSV="data/csv/output_llama_3.3_70b_unified.csv"
ANALYSIS_PREFIX="data/results/images/analysis_unified_llama_3.3_70b"
MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
RESULTS_JSON="data/results/experiments/threshold_analysis_results_llama_33_70b.json"

echo "=== Starting analysis pipeline with model: $MODEL_NAME ==="
echo

# Step 1: Generate coordinates using the enhanced script with Llama 3.3-70B
echo "Step 1: Generating coordinates using enhanced script..."
python scripts/enhanced_generate_coordinate_csv.py \
    -f $INPUT_PMIDS \
    -o $OUTPUT_CSV \
    -m "$MODEL_NAME" \
    --debug \
    --cache-type disk

# Check if the previous command was successful
if [ $? -ne 0 ]; then
    echo "Error: Coordinate generation failed"
    exit 1
fi

echo "Coordinates successfully generated: $OUTPUT_CSV"
echo

# Step 2: Run comparative analysis with different thresholds
echo "Step 2: Running comparative analyses with different thresholds..."

# Create or clear the JSON file
echo "[]" > $RESULTS_JSON

# Run analysis with no threshold (baseline)
echo "Running analysis with no threshold (baseline)..."
python scripts/analiza_porownawcza_fixed3.py \
    --pred $OUTPUT_CSV \
    --confirmed "$CONFIRMED_DATA" \
    --prefix "${ANALYSIS_PREFIX}_baseline" \
    --output-json $RESULTS_JSON

# Run analysis with each threshold value from 0 to 10
for threshold in 0 1 2 3 4 5 6 7 8 9 10
do
    echo "Running analysis with threshold >= $threshold..."
    python scripts/analiza_porownawcza_fixed3.py \
        --pred $OUTPUT_CSV \
        --confirmed "$CONFIRMED_DATA" \
        --prefix "${ANALYSIS_PREFIX}_threshold_${threshold}" \
        --threshold $threshold \
        --output-json $RESULTS_JSON
done

# Check if the final command was successful
if [ $? -ne 0 ]; then
    echo "Error: Comparative analysis failed"
    exit 1
fi

echo "All analyses completed successfully. Results saved to: $RESULTS_JSON"
echo

# Display summary of results
echo "=== Analysis Summary ==="
echo "Input PMIDs: $INPUT_PMIDS"
echo "Confirmed data: $CONFIRMED_DATA"
echo "Generated coordinates: $OUTPUT_CSV"
echo "Analysis results prefix: $ANALYSIS_PREFIX"
echo "Results JSON: $RESULTS_JSON"
echo 
echo "Generated images:"
for img in ${ANALYSIS_PREFIX}_*.png; do
    echo "- $img"
done

# Generate a summary table of precision and recall for different thresholds
echo
echo "=== Threshold Comparison Summary ==="
echo "Threshold | Gene Precision | Gene Recall | Gene F1 | Disease Precision | Disease Recall | Disease F1"
echo "---------|----------------|-------------|---------|-------------------|---------------|----------"

# Use jq to extract and format the metrics if jq is available
if command -v jq &> /dev/null; then
    jq -r 'sort_by(.score_threshold // 0) | .[] | 
    [(.score_threshold // "None"), 
     (.gene_precision | tostring | .[0:6]), 
     (.gene_recall | tostring | .[0:6]), 
     (.gene_f1 | tostring | .[0:6]), 
     (.disease_precision | tostring | .[0:6]), 
     (.disease_recall | tostring | .[0:6]), 
     (.disease_f1 | tostring | .[0:6])] | 
    " \(.[])"' $RESULTS_JSON | 
    awk '{printf "%-9s | %-14s | %-11s | %-7s | %-17s | %-13s | %-10s\n", $1, $2, $3, $4, $5, $6, $7}'
else
    echo "Install jq for better formatting of JSON results"
    cat $RESULTS_JSON
fi

# Generate CSV from threshold results
echo "Converting threshold results to CSV..."
python scripts/analysis/threshold_to_csv_with_model.py \
    --json_files $RESULTS_JSON \
    --output "data/csv/threshold_metrics_llama_33_70b.csv"

echo
echo "=== Analysis complete ===" 