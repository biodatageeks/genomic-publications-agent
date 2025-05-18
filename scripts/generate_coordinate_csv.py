#!/usr/bin/env python3
"""
Script for generating a CSV table with genes, diseases, and variants based on PubMed IDs.
Uses cooccurrence and LLM analysis methods to extract relationships from publications.
"""

import argparse
import logging
import os
import sys
import re
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import csv
import datetime

# Add path to the main project directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cooccurrence_context_analyzer.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer
from src.pubtator_client.pubtator_client import PubTatorClient
from src.core.config.config import Config

# Logowanie zostanie skonfigurowane w oparciu o argumenty uruchomienia

logger = logging.getLogger(__name__)


def extract_coordinates_from_variant(variant_id: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Extract chromosome, start, and end coordinates from variant identifier.
    
    Args:
        variant_id: Variant identifier string
        
    Returns:
        Tuple of (chromosome, start, end) or (None, None, None) if not found
    """
    # Try to extract from HGVS format
    hgvs_match = re.search(r'HGVS:([\w.:>_]+)', variant_id)
    if hgvs_match:
        hgvs = hgvs_match.group(1)
        
        # Example: NC_000007.13:g.117188683G>A
        chrom_match = re.search(r'NC_0+(\d+)', hgvs)
        if chrom_match:
            chrom = chrom_match.group(1)
            pos_match = re.search(r'\.(\d+)([ACGT])>([ACGT])', hgvs)
            if pos_match:
                pos = int(pos_match.group(1))
                return f"chr{chrom}", pos, pos
        
        # Handle c.notation with position range
        c_pos_match = re.search(r'c\.(\d+)_(\d+)([ACGT])>([ACGT])', hgvs)
        if c_pos_match:
            # Need to find corresponding gene to determine chromosome
            gene_match = re.search(r'CorrespondingGene:(\d+)', variant_id)
            if gene_match:
                gene_id = gene_match.group(1)
                chrom, gene_start = get_gene_coordinates(gene_id)
                if chrom and gene_start:
                    # Position is relative to gene start
                    pos1 = int(c_pos_match.group(1))
                    pos2 = int(c_pos_match.group(2))
                    # This is approximate and would need actual transcript info
                    return chrom, gene_start + pos1, gene_start + pos2
    
    # Try to extract from general position format
    # Example: chr1:12345-12346 or 1:12345-12346
    pos_match = re.search(r'(?:chr)?(\d+|X|Y):(\d+)(?:-(\d+))?', variant_id)
    if pos_match:
        chrom = pos_match.group(1)
        start = int(pos_match.group(2))
        end = int(pos_match.group(3)) if pos_match.group(3) else start
        return f"chr{chrom}", start, end
    
    # Check for rs ID
    rs_match = re.search(r'[rR][sS][#:]?(\d+)', variant_id)
    if rs_match:
        # For RS IDs, we would need to look up the coordinates in a database
        # This is a placeholder; in a real implementation, you might query dbSNP
        rs_id = rs_match.group(1)
        # For testing purposes, return dummy values for well-known variants
        rs_coordinates = {
            '642961': ('chr1', 209989270, 209989270),  # IRF6 variant
            '2435357': ('chr10', 43582014, 43582014),  # RET variant
            '121918697': ('chr7', 91855888, 91855888),  # TYR variant (p.R338W)
            '2596623': ('chr7', 91921468, 91921468),  # TYR variant
            '2596622': ('chr7', 91921595, 91921595),  # TYR variant
            '73346254': ('chr8', 37992287, 37992287),  # PROSC variant
            '4498267': ('chr8', 37995632, 37995632),   # PROSC variant
            '4431364': ('chr8', 37996942, 37996942)    # PROSC variant
        }
        
        if rs_id in rs_coordinates:
            return rs_coordinates[rs_id]
    
    # Try to extract from SUB format
    # Example: c|SUB|G||A
    sub_match = re.search(r'c\|SUB\|([ACGT])\|\|([ACGT])', variant_id)
    if sub_match:
        # Since we don't have position information in this format,
        # we need to infer it from other fields or return None
        # Look for CorrespondingGene which might help identify position
        gene_match = re.search(r'CorrespondingGene:(\d+)', variant_id)
        if gene_match:
            gene_id = gene_match.group(1)
            chrom, gene_start = get_gene_coordinates(gene_id)
            if chrom and gene_start:
                # Without specific position, we return gene coordinates
                return chrom, gene_start, gene_start
    
    # Handle protein substitution (p.X123Y format)
    p_sub_match = re.search(r'p\|SUB\|([A-Z])\|(\d+)\|([A-Z])', variant_id)
    if p_sub_match:
        gene_match = re.search(r'CorrespondingGene:(\d+)', variant_id)
        if gene_match:
            gene_id = gene_match.group(1)
            chrom, gene_start = get_gene_coordinates(gene_id)
            if chrom and gene_start:
                # For protein variants, we can only return gene coordinates
                return chrom, gene_start, gene_start
    
    # Additional formats could be handled here
    
    return None, None, None


def get_gene_coordinates(gene_id: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Get chromosome and start position for a gene.
    
    Args:
        gene_id: Entrez Gene ID
        
    Returns:
        Tuple of (chromosome, start_position) or (None, None) if not found
    """
    # Placeholder function that would normally query a database
    # For demonstration, we'll return coordinates for a few example genes
    gene_coordinates = {
        '54139': ('chr1', 209979239),  # IRF6
        '5979': ('chr10', 43077069),   # RET
        '7068': ('chr7', 91851332),    # TYR
        '5626': ('chr8', 37991945)     # PROSC
    }
    
    if gene_id in gene_coordinates:
        return gene_coordinates[gene_id]
    
    return None, None


def determine_variant_type(variant_text: str, variant_id: str) -> str:
    """
    Determine the variant type from variant text or ID.
    
    Args:
        variant_text: Variant text description
        variant_id: Variant identifier
        
    Returns:
        Variant type classification (SNP, deletion, insertion, etc.)
    """
    if 'deletion' in variant_text.lower() or '>del' in variant_id or 'DEL' in variant_id:
        return 'deletion'
    elif 'insertion' in variant_text.lower() or '>ins' in variant_id or 'INS' in variant_id:
        return 'insertion'
    elif 'duplication' in variant_text.lower() or 'DUP' in variant_id:
        return 'duplication'
    elif 'translocation' in variant_text.lower() or 't(' in variant_text:
        return 'translocation'
    elif 'SUB' in variant_id or '>' in variant_id:
        return 'substitution'
    else:
        return 'unknown'


def extract_hgvs_notation(variant_id: str) -> Optional[str]:
    """
    Extract HGVS notation from variant identifier.
    
    Args:
        variant_id: Variant identifier string
        
    Returns:
        HGVS notation or None if not found
    """
    hgvs_match = re.search(r'HGVS:([^;]+)', variant_id)
    if hgvs_match:
        return hgvs_match.group(1)
    return None


def merge_variant_data(cooccurrence_data: List[Dict], llm_data: List[Dict]) -> List[Dict]:
    """
    Merge data from cooccurrence and LLM analysis.
    
    Args:
        cooccurrence_data: List of relationship dictionaries from cooccurrence analysis
        llm_data: List of relationship dictionaries from LLM analysis
        
    Returns:
        Merged and processed list of variant relationships
    """
    # Create a dictionary to hold merged data
    merged_data = {}
    
    # Log input data sizes
    logger.info(f"Merging data: {len(cooccurrence_data)} cooccurrence relationships, {len(llm_data)} LLM relationships")
    
    # Process cooccurrence data
    for rel in cooccurrence_data:
        variant_text = rel.get('variant_text', '')
        variant_id = rel.get('variant_id', '')
        
        # Log current cooccurrence relationship
        logger.debug(f"Processing cooccurrence: {variant_text} ({variant_id})")
        
        # Create a key for this variant
        key = f"{rel.get('pmid', '')}_{variant_text}_{variant_id}"
        
        if key not in merged_data:
            chr_val, start_val, end_val = extract_coordinates_from_variant(variant_id)
            variant_type = determine_variant_type(variant_text, variant_id)
            hgvs = extract_hgvs_notation(variant_id)
            
            merged_data[key] = {
                'pmid': rel.get('pmid', ''),
                'chr': chr_val,
                'start': start_val,
                'end': end_val,
                'id': variant_id,
                'variant_name': hgvs or variant_text,
                'variant_type': variant_type,
                'genes': set(),
                'gene_scores': {},  # Dodane: słownik dla scoringu genów
                'diseases': set(),
                'disease_scores': {},  # Dodane: słownik dla scoringu chorób
                'variant_mode': 'unknown',
                'passage_text': rel.get('passage_text', '')
            }
        
        # Add genes and diseases
        for gene in rel.get('genes', []):
            gene_text = gene.get('text', '')
            gene_id = gene.get('id', '')
            if gene_text and gene_id:
                merged_data[key]['genes'].add(f"{gene_text} ({gene_id})")
        
        for disease in rel.get('diseases', []):
            disease_text = disease.get('text', '')
            disease_id = disease.get('id', '')
            if disease_text and disease_id:
                merged_data[key]['diseases'].add(f"{disease_text} ({disease_id})")
    
    # Process LLM data to enhance the merged data
    for rel in llm_data:
        variant_text = rel.get('variant_text', '')
        variant_id = rel.get('variant_id', '')
        
        # Log current LLM relationship
        logger.debug(f"Processing LLM: {variant_text} ({variant_id})")
        
        # Create a key for this variant
        key = f"{rel.get('pmid', '')}_{variant_text}_{variant_id}"
        
        # If key doesn't exist yet, create new entry
        if key not in merged_data:
            logger.debug(f"Creating new entry for LLM relationship: {key}")
            chr_val, start_val, end_val = extract_coordinates_from_variant(variant_id)
            variant_type = determine_variant_type(variant_text, variant_id)
            hgvs = extract_hgvs_notation(variant_id)
            
            merged_data[key] = {
                'pmid': rel.get('pmid', ''),
                'chr': chr_val,
                'start': start_val,
                'end': end_val,
                'id': variant_id,
                'variant_name': hgvs or variant_text,
                'variant_type': variant_type,
                'genes': set(),
                'gene_scores': {},  # Dodane: słownik dla scoringu genów
                'diseases': set(),
                'disease_scores': {},  # Dodane: słownik dla scoringu chorób
                'variant_mode': 'unknown',
                'passage_text': rel.get('passage_text', '')
            }
        
        if key in merged_data:
            # Extract relationship information
            relationships = rel.get('llm_relationships', [])
            logger.debug(f"Found {len(relationships)} LLM relationships")
            
            # Check if genes and diseases are directly in the relationship
            if 'genes' in rel:
                for gene in rel.get('genes', []):
                    gene_text = gene.get('text', '')
                    gene_id = gene.get('id', '')
                    relationship_score = gene.get('relationship_score', 0)
                    if gene_text and gene_id:
                        logger.debug(f"Adding gene from direct LLM data: {gene_text} ({gene_id}) with score {relationship_score}")
                        gene_key = f"{gene_text} ({gene_id})"
                        merged_data[key]['genes'].add(gene_key)
                        # Zapisz scoring dla genu
                        merged_data[key]['gene_scores'][gene_key] = relationship_score
            
            if 'diseases' in rel:
                for disease in rel.get('diseases', []):
                    disease_text = disease.get('text', '')
                    disease_id = disease.get('id', '')
                    relationship_score = disease.get('relationship_score', 0)
                    if disease_text and disease_id:
                        logger.debug(f"Adding disease from direct LLM data: {disease_text} ({disease_id}) with score {relationship_score}")
                        disease_key = f"{disease_text} ({disease_id})"
                        merged_data[key]['diseases'].add(disease_key)
                        # Zapisz scoring dla choroby
                        merged_data[key]['disease_scores'][disease_key] = relationship_score
            
            for relationship in relationships:
                if relationship.get('has_relationship', False):
                    entity_type = relationship.get('entity_type', '')
                    entity_text = relationship.get('entity_text', '')
                    entity_id = relationship.get('entity_id', '')
                    explanation = relationship.get('explanation', '')
                    relationship_score = relationship.get('relationship_score', 0)
                    
                    logger.debug(f"Processing relationship: {entity_type} {entity_text} ({entity_id}) with score {relationship_score}")
                    
                    if entity_type == 'gene' and entity_text and entity_id:
                        gene_key = f"{entity_text} ({entity_id})"
                        merged_data[key]['genes'].add(gene_key)
                        # Zapisz scoring dla genu
                        merged_data[key]['gene_scores'][gene_key] = relationship_score
                    
                    elif entity_type == 'disease' and entity_text and entity_id:
                        disease_key = f"{entity_text} ({entity_id})"
                        merged_data[key]['diseases'].add(disease_key)
                        # Zapisz scoring dla choroby
                        merged_data[key]['disease_scores'][disease_key] = relationship_score
                    
                    # Try to determine variant mode from explanation
                    if 'enhancer' in explanation.lower():
                        merged_data[key]['variant_mode'] = 'enhancer'
                    elif 'loss of function' in explanation.lower() or 'loss-of-function' in explanation.lower():
                        merged_data[key]['variant_mode'] = 'loss of function'
                    elif 'gain of function' in explanation.lower() or 'gain-of-function' in explanation.lower():
                        merged_data[key]['variant_mode'] = 'gain of function'
    
    # Log the number of merged entries
    logger.info(f"Merged data contains {len(merged_data)} entries")
    
    # Convert sets to strings for DataFrame compatibility and handle scoring
    result = []
    for key, data in merged_data.items():
        # Przekształć zbiory na ciągi znaków, zapisując przy tym scoring
        genes_str = []
        gene_scores_str = []
        
        for gene in data['genes']:
            genes_str.append(gene)
            score = data['gene_scores'].get(gene, 0)
            gene_scores_str.append(str(score))
        
        diseases_str = []
        disease_scores_str = []
        
        for disease in data['diseases']:
            diseases_str.append(disease)
            score = data['disease_scores'].get(disease, 0)
            disease_scores_str.append(str(score))
        
        # Zastąp zbiory ciągami znaków
        data['genes'] = '; '.join(genes_str)
        data['gene_score'] = '; '.join(gene_scores_str)
        data['diseases'] = '; '.join(diseases_str)
        data['disease_score'] = '; '.join(disease_scores_str)
        
        # Usuń słowniki scoringu, które nie będą już potrzebne
        del data['gene_scores']
        del data['disease_scores']
        
        result.append(data)
    
    return result


def analyze_pmids(pmids: List[str],
                  output_csv: str,
                  email: Optional[str] = None,
                  llm_model: Optional[str] = None,
                  use_llm: bool = True,
                  only_llm: bool = False,
                  debug_mode: bool = False,
                  llm_context_analyzer_class = None,
                  cache_storage_type: str = "memory") -> pd.DataFrame:
    """
    Analyze PubMed IDs using both cooccurrence and LLM methods to create a structured CSV.
    
    Args:
        pmids: List of PubMed IDs to analyze
        output_csv: Path to output CSV file
        email: Email for PubTator API (optional)
        llm_model: LLM model to use (optional)
        use_llm: Whether to use LLM analysis (default: True)
        only_llm: Whether to use only LLM analysis (default: False)
        debug_mode: Whether to save debug information (raw LLM output)
        llm_context_analyzer_class: Class to use for LLM analysis (default: LlmContextAnalyzer)
        cache_storage_type: Type of cache to use (memory or disk) (default: memory)
        
    Returns:
        DataFrame with processed results
    """
    # Load configuration
    config = Config()
    
    # Use config values if parameters not provided
    if email is None:
        email = config.get_contact_email()
    
    if llm_model is None:
        llm_model = config.get_llm_model_name()
    
    # Default analyzer class if not provided
    if llm_context_analyzer_class is None:
        llm_context_analyzer_class = LlmContextAnalyzer
    
    # Ensure we have required values
    assert email is not None, "Email must be specified either directly or in config"
    assert llm_model is not None, "Model name must be specified either directly or in config"
    
    # Remove duplicate PMIDs
    unique_pmids = list(set(pmids))
    logger.info(f"Analyzing {len(unique_pmids)} unique PubMed IDs (from {len(pmids)} total)")
    
    # Initialize clients
    pubtator_client = PubTatorClient(email=email)
    
    try:
        # Step 1: Perform cooccurrence analysis
        cooccurrence_results = []
        temp_cooccurrence_file = None
        if not only_llm:
            logger.info("Starting cooccurrence analysis...")
            cooccurrence_analyzer = CooccurrenceContextAnalyzer(pubtator_client=pubtator_client)
            cooccurrence_results = cooccurrence_analyzer.analyze_publications(unique_pmids)
            logger.info(f"Found {len(cooccurrence_results)} relationships using cooccurrence")
            
            # Save intermediate results
            temp_cooccurrence_file = f"{output_csv}_cooccurrence_temp.json"
            cooccurrence_analyzer.save_relationships_to_json(cooccurrence_results, temp_cooccurrence_file)
        else:
            logger.info("Cooccurrence analysis disabled, skipping...")
        
        # Step 2: Perform LLM analysis if enabled
        llm_results = []
        if use_llm:
            # Użyj dostarczonej klasy analizatora zamiast domyślnej
            llm_analyzer = llm_context_analyzer_class(
                pubtator_client=pubtator_client, 
                llm_model_name=llm_model,
                cache_storage_type=cache_storage_type
            )
            logger.info(f"Starting LLM analysis using model {llm_model}...")
            llm_results = llm_analyzer.analyze_publications(unique_pmids)
            logger.info(f"Found {len(llm_results)} relationships using LLM")
            
            # Save intermediate results
            temp_llm_file = f"{output_csv}_llm_temp.json"
            llm_analyzer.save_relationships_to_json(llm_results, temp_llm_file)
            
            # Clean up temporary LLM file
            if os.path.exists(temp_llm_file) and not debug_mode:
                os.remove(temp_llm_file)
        else:
            logger.info("LLM analysis disabled, skipping...")
        
        # Step 3: Merge and process results
        logger.info("Merging and processing results...")
        merged_results = merge_variant_data(cooccurrence_results, llm_results)
        
        # Step 4: Create DataFrame and save to CSV
        df = pd.DataFrame(merged_results)
        
        # Reorder columns to match required format
        columns = [
            'chr', 'start', 'end', 'id', 'genes', 'diseases', 
            'variant_type', 'variant_name', 'variant_mode', 'pmid',
            'gene_score', 'disease_score'
        ]
        
        # Filter and reorder columns
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]
        
        # Save to CSV
        df.to_csv(output_csv, index=False)
        logger.info(f"Results saved to {output_csv}")
        
        # Clean up temporary files
        if temp_cooccurrence_file and os.path.exists(temp_cooccurrence_file) and not debug_mode:
            os.remove(temp_cooccurrence_file)
        
        # Zapisz surowe dane LLM do CSV, jeśli włączony tryb debug
        if debug_mode and use_llm:
            output_base = os.path.splitext(output_csv)[0]
            debug_output = f"{output_base}_llm_debug.csv"
            debug_json = f"{output_base}_raw_llm_data.json"
            
            # Zapisz kopię oryginalnego pliku JSON
            if os.path.exists(temp_llm_file):
                try:
                    with open(temp_llm_file, 'r') as f:
                        llm_data = json.load(f)
                    
                    # Zapisz kopię oryginalnych danych LLM
                    with open(debug_json, 'w') as f:
                        json.dump(llm_data, f, indent=2)
                    logger.info(f"Saved raw LLM data to {debug_json}")
                    
                    # Zapisz dodatkowe informacje o strukturze danych
                    data_structure = {
                        "total_entries": len(llm_data),
                        "first_entry_keys": list(llm_data[0].keys()) if llm_data else [],
                        "has_genes": any("genes" in entry and entry["genes"] for entry in llm_data),
                        "has_diseases": any("diseases" in entry and entry["diseases"] for entry in llm_data),
                        "has_llm_relationships": any("llm_relationships" in entry for entry in llm_data),
                        "entry_counts": {
                            "genes": sum(1 for entry in llm_data if "genes" in entry and entry["genes"]),
                            "diseases": sum(1 for entry in llm_data if "diseases" in entry and entry["diseases"]),
                            "tissues": sum(1 for entry in llm_data if "tissues" in entry and entry["tissues"]),
                            "species": sum(1 for entry in llm_data if "species" in entry and entry["species"]),
                            "chemicals": sum(1 for entry in llm_data if "chemicals" in entry and entry["chemicals"])
                        }
                    }
                    
                    with open(f"{output_base}_data_structure.json", 'w') as f:
                        json.dump(data_structure, f, indent=2)
                    logger.info(f"Saved data structure info to {output_base}_data_structure.json")
                except Exception as e:
                    logger.error(f"Error analyzing LLM data structure: {str(e)}")
            
            # Sprawdź, czy plik istnieje
            if os.path.exists(temp_llm_file):
                with open(temp_llm_file, 'r') as f:
                    llm_data = json.load(f)
                    
                headers = ["pmid", "variant_text", "variant_id", "entity_type", "entity_text", 
                           "entity_id", "has_relationship", "explanation", "relationship_score", "passage_text"]
                
                with open(debug_output, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    
                    for rel in llm_data:
                        pmid = rel.get("pmid", "")
                        variant_text = rel.get("variant_text", "")
                        variant_id = rel.get("variant_id", "")
                        passage_text = rel.get("passage_text", "")
                        
                        # Zapisz relacje LLM
                        for entity_type in ["genes", "diseases", "tissues", "species", "chemicals"]:
                            if entity_type in rel and rel[entity_type]:
                                for entity in rel[entity_type]:
                                    writer.writerow({
                                        "pmid": pmid,
                                        "variant_text": variant_text,
                                        "variant_id": variant_id,
                                        "entity_type": entity_type[:-1] if entity_type != "species" else "species",  # usuń 's' z końca oprócz species
                                        "entity_text": entity.get("text", ""),
                                        "entity_id": entity.get("id", ""),
                                        "has_relationship": "True",
                                        "explanation": entity.get("explanation", ""),
                                        "relationship_score": entity.get("relationship_score", 0),
                                        "passage_text": passage_text
                                    })
                
                logger.info(f"Debug data saved to {debug_output}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise


def setup_logging(log_file=None, log_level=logging.INFO, log_format='json'):
    """
    Konfiguruje system logowania.
    
    Args:
        log_file: Ścieżka do pliku logu (opcjonalna)
        log_level: Poziom logowania
        log_format: Format logów ('json' lub 'text')
        
    Returns:
        Skonfigurowany logger
    """
    handlers = []
    
    # Zawsze dodajemy handler konsoli
    handlers.append(logging.StreamHandler(sys.stdout))
    
    # Dodaj handler pliku, jeśli podano ścieżkę
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    # Wybierz format logów
    if log_format.lower() == 'json':
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":%(message)s}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Nadpisz funkcję formatującą dla obsługi JSON
        def _format_log_record(record):
            if isinstance(record.msg, str):
                record.msg = json.dumps(record.msg)
            return record
        
        # Dodaj niestandardowy filtr do każdego handlera
        for handler in handlers:
            handler.addFilter(lambda record: _format_log_record(record))
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Zastosuj formatter do wszystkich handlerów
    for handler in handlers:
        handler.setFormatter(formatter)
    
    # Konfiguruj główny logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def main():
    """Main script function."""
    # Load configuration
    config = Config()
    default_email = config.get_contact_email()
    default_model = config.get_llm_model_name()
    
    parser = argparse.ArgumentParser(
        description="Generate CSV table with genes, diseases, and variants from PubMed IDs"
    )
    
    parser.add_argument("-p", "--pmids", nargs="+", required=False,
                        help="List of PMIDs to analyze")
    parser.add_argument("-f", "--file", type=str,
                        help="File containing PMIDs, one per line")
    parser.add_argument("-o", "--output", required=True, 
                        help="Path to output CSV file")
    parser.add_argument("-m", "--model", default=default_model,
                        help=f"Name of the LLM model to use (default: {default_model})")
    parser.add_argument("-e", "--email", default=default_email,
                        help=f"Email address for PubTator API (default: {default_email})")
    parser.add_argument("--no-llm", action="store_true",
                        help="Disable LLM analysis (use only cooccurrence)")
    parser.add_argument("--only-llm", action="store_true",
                        help="Use only LLM analysis (disable cooccurrence)")
    parser.add_argument("--debug", action="store_true",
                        help="Save debug information (raw LLM output)")
    parser.add_argument("--limit", type=int,
                        help="Limit the number of PMIDs to analyze (first N)")
    parser.add_argument("--log-file", type=str,
                        help="Path to log file (if not specified, logs only to console)")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Log level (default: INFO)")
    parser.add_argument("--log-format", type=str, default="text",
                        choices=["text", "json"],
                        help="Log format (default: text)")
    
    args = parser.parse_args()
    
    # Utwórz katalog logów, jeśli podano plik logu
    if args.log_file:
        log_dir = os.path.dirname(os.path.abspath(args.log_file))
        os.makedirs(log_dir, exist_ok=True)
        
        # Dodaj datę do nazwy pliku logu, jeśli nie została dodana
        if not any(part in os.path.basename(args.log_file) for part in [str(datetime.date.today()), datetime.datetime.now().strftime('%Y%m%d')]):
            base, ext = os.path.splitext(args.log_file)
            args.log_file = f"{base}_{datetime.datetime.now().strftime('%Y%m%d')}{ext}"
    
    # Konfiguruj logowanie
    global logger
    log_level = getattr(logging, args.log_level.upper())
    logger = setup_logging(args.log_file, log_level, args.log_format)
    
    # Collect PMIDs from arguments or file
    pmids = []
    
    if args.pmids:
        pmids.extend(args.pmids)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_pmids = [line.strip() for line in f if line.strip()]
                pmids.extend(file_pmids)
        except Exception as e:
            logger.error(f"Error reading PMID file: {str(e)}")
            sys.exit(1)
    
    if not pmids:
        logger.error("No PMIDs provided. Use --pmids or --file option.")
        sys.exit(1)
    
    # Ogranicz PMIDy do pierwszych N, jeśli podano limit
    if args.limit and args.limit > 0:
        original_count = len(pmids)
        pmids = pmids[:args.limit]
        logger.info(f"Limited analysis to first {len(pmids)} PMIDs (from {original_count} total)")
    
    # Execute analysis
    try:
        df = analyze_pmids(
            pmids=pmids,
            output_csv=args.output,
            email=args.email,
            llm_model=args.model,
            use_llm=not args.no_llm,
            only_llm=args.only_llm,
            debug_mode=args.debug
        )
        
        logger.info(f"Analysis completed successfully. Generated CSV with {len(df)} entries.")
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 