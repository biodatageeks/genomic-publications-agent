#!/usr/bin/env python3
"""
Script for visualizing relationships between variants, genes, and diseases.
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import networkx as nx
import argparse
from collections import Counter

# Add path to the main project directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_relationship_graph(csv_file, output_image):
    """
    Creates a graph of relationships between variants, genes, and diseases.
    
    Args:
        csv_file: Path to CSV file with relationships
        output_image: Path to save the graph image
    """
    try:
        # Load data
        df = pd.read_csv(csv_file)
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes (variants, genes, diseases)
        variants = set(df['variant_text'].dropna().unique())
        genes = set(df['gene_text'].dropna().unique())
        diseases = set(df['disease_text'].dropna().unique())
        
        # Remove empty strings
        variants = {v for v in variants if v}
        genes = {g for g in genes if g}
        diseases = {d for d in diseases if d}
        
        # Add variants as nodes
        for variant in variants:
            G.add_node(variant, type='variant')
            
        # Add genes as nodes
        for gene in genes:
            G.add_node(gene, type='gene')
            
        # Add diseases as nodes
        for disease in diseases:
            G.add_node(disease, type='disease')
            
        # Add edges between variants and genes
        for _, row in df.iterrows():
            variant = row['variant_text']
            gene = row['gene_text']
            disease = row['disease_text']
            
            if variant and gene and variant in variants and gene in genes:
                G.add_edge(variant, gene)
                
            if variant and disease and variant in variants and disease in diseases:
                G.add_edge(variant, disease)
                
            if gene and disease and gene in genes and disease in diseases:
                G.add_edge(gene, disease)
        
        # Define node colors
        colors = []
        for node in G.nodes():
            if node in variants:
                colors.append('skyblue')
            elif node in genes:
                colors.append('lightgreen')
            elif node in diseases:
                colors.append('salmon')
        
        # Define node positions
        pos = nx.spring_layout(G, seed=42)
        
        # Visualize graph
        plt.figure(figsize=(12, 10))
        nx.draw_networkx(G, pos, node_color=colors, with_labels=True, 
                         node_size=700, font_size=10, 
                         font_weight='bold', alpha=0.7)
        
        # Add legend
        variant_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='skyblue',
                                  markersize=15, label='Variant')
        gene_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen',
                               markersize=15, label='Gene')
        disease_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='salmon',
                                  markersize=15, label='Disease')
        
        plt.legend(handles=[variant_patch, gene_patch, disease_patch], loc='upper right')
        
        plt.title('Relationship Graph between Variants, Genes, and Diseases')
        plt.tight_layout()
        plt.savefig(output_image, dpi=300)
        plt.close()
        
        print(f"Graph has been saved to file: {output_image}")
        
        # Generate statistics
        print(f"\nGraph statistics:")
        print(f" - Number of nodes: {G.number_of_nodes()}")
        print(f" - Number of edges: {G.number_of_edges()}")
        print(f" - Number of variants: {len(variants)}")
        print(f" - Number of genes: {len(genes)}")
        print(f" - Number of diseases: {len(diseases)}")
        
    except ImportError as e:
        print(f"Error: Missing required libraries. {str(e)}")
        print("Install required libraries: pip install matplotlib networkx")
    except Exception as e:
        print(f"Error while creating graph: {str(e)}")

def main():
    """Main script function."""
    parser = argparse.ArgumentParser(description="Visualization of relationships between variants, genes, and diseases.")
    parser.add_argument("--input", "-i", type=str, default="variant_relationships.csv",
                        help="Path to CSV file with relationships (default: variant_relationships.csv)")
    parser.add_argument("--output", "-o", type=str, default="variant_relationships_graph.png",
                        help="Path to output graph file (default: variant_relationships_graph.png)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File {args.input} does not exist.")
        return
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    create_relationship_graph(args.input, args.output)

if __name__ == "__main__":
    main() 