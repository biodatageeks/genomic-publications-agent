#!/usr/bin/env python3
"""
Utility module containing common functions used in various scripts.
"""
import os
import sys
import json
import logging
from typing import Set, Dict, Any, List, Optional, Union

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directory constant definitions
DIRS = {
    'pmids': 'data/pmids',
    'csv': 'data/csv',
    'batch_results': 'data/batch_results',
    'results': 'data/results',
    'experiments': 'data/results/experiments',
    'images': 'data/results/images',
    'temp': 'data/temp',
}

def ensure_dirs_exist() -> None:
    """
    Creates all required directories if they don't exist.
    """
    for dir_path in DIRS.values():
        os.makedirs(dir_path, exist_ok=True)

def get_path(file_path: str, default_dir: str) -> str:
    """
    Returns the full path to a file, adding directory prefix if full path not provided.
    
    Args:
        file_path: Path to the file
        default_dir: Default directory if full path not provided
        
    Returns:
        Full path to the file
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
        
    if '/' not in file_path:
        os.makedirs(default_dir, exist_ok=True)
        return os.path.join(default_dir, file_path)
    else:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        return file_path

def get_pmids_path(file_path: str) -> str:
    """
    Returns the full path to a PMIDs file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Full path to the file
    """
    return get_path(file_path, DIRS['pmids'])

def get_csv_path(file_path: str) -> str:
    """
    Returns the full path to a CSV file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Full path to the file
    """
    return get_path(file_path, DIRS['csv'])

def get_experiments_path(file_path: str) -> str:
    """
    Returns the full path to an experiments results file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Full path to the file
    """
    return get_path(file_path, DIRS['experiments'])

def get_images_path(file_path: str) -> str:
    """
    Returns the full path to an image file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Full path to the file
    """
    return get_path(file_path, DIRS['images'])

def load_pmids_from_file(input_file: str) -> Set[str]:
    """
    Loads PMIDs from a text file.
    
    Args:
        input_file: Path to the file containing PMIDs list
        
    Returns:
        Set of unique PMIDs
    """
    try:
        input_file = get_pmids_path(input_file)
        with open(input_file, 'r', encoding='utf-8') as f:
            pmids = {line.strip() for line in f if line.strip()}
        logger.info(f"Loaded {len(pmids)} PMIDs from file {input_file}")
        return pmids
    except Exception as e:
        logger.error(f"Error reading file {input_file}: {str(e)}")
        raise Exception(f"Cannot load PMIDs file: {e}")

def load_csv_pmids(csv_file: str, pmid_column: int = 0, has_header: bool = True) -> Set[str]:
    """
    Loads PMIDs from a CSV file.
    
    Args:
        csv_file: Path to the CSV file
        pmid_column: Index of the PMID column (default 0 - first column)
        has_header: Whether the CSV file has a header
        
    Returns:
        Set of unique PMIDs
    """
    try:
        csv_file = get_csv_path(csv_file)
        pmids = set()
        with open(csv_file, 'r', encoding='utf-8') as f:
            if has_header:
                next(f)  # Skip header
            for line in f:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) > pmid_column:
                        pmid = parts[pmid_column].strip()
                        if pmid:
                            pmids.add(pmid)
        logger.info(f"Loaded {len(pmids)} PMIDs from CSV file {csv_file}")
        return pmids
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_file}: {str(e)}")
        raise Exception(f"Cannot load CSV file: {e}")

def save_pmids_to_file(pmids: Set[str], output_file: str) -> None:
    """
    Saves PMIDs to a text file.
    
    Args:
        pmids: Set of PMIDs to save
        output_file: Path to the output file
    """
    try:
        output_file = get_pmids_path(output_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            for pmid in sorted(pmids):
                f.write(f"{pmid}\n")
        logger.info(f"Saved {len(pmids)} PMIDs to file {output_file}")
    except Exception as e:
        logger.error(f"Error writing to file {output_file}: {str(e)}")
        raise Exception(f"Cannot save PMIDs file: {e}")

def load_json_file(json_file: str) -> Dict[str, Any]:
    """
    Loads data from a JSON file.
    
    Args:
        json_file: Path to the JSON file
        
    Returns:
        Data from the JSON file
    """
    try:
        json_file = get_experiments_path(json_file)
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading JSON file {json_file}: {str(e)}")
        raise Exception(f"Cannot load JSON file: {e}")

def save_json_file(data: Union[Dict[str, Any], List[Any]], output_file: str) -> None:
    """
    Saves data to a JSON file.
    
    Args:
        data: Data to save
        output_file: Path to the output file
    """
    try:
        output_file = get_experiments_path(output_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved data to JSON file {output_file}")
    except Exception as e:
        logger.error(f"Error writing to JSON file {output_file}: {str(e)}")
        raise Exception(f"Cannot save JSON file: {e}")

def append_to_json_file(new_item: Any, json_file: str) -> None:
    """
    Adds a new item to a list in a JSON file.
    If the file doesn't exist, creates a new one with one item.
    If the file exists but doesn't contain a list, creates a new list with the item.
    
    Args:
        new_item: Item to add
        json_file: Path to the JSON file
    """
    json_file = get_experiments_path(json_file)
    
    # Check if file exists and contains data
    existing_items = []
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_items = json.load(f)
                if not isinstance(existing_items, list):
                    existing_items = [existing_items]
        except (json.JSONDecodeError, Exception):
            existing_items = []
    
    # Add new item and save
    existing_items.append(new_item)
    
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_items, f, indent=2)
        logger.info(f"Added new item to JSON file {json_file}")
    except Exception as e:
        logger.error(f"Error writing to JSON file {json_file}: {str(e)}")
        raise Exception(f"Cannot save JSON file: {e}")

def initialize_json_file(json_file: str, initial_data: Any = None) -> None:
    """
    Initializes a JSON file with an empty list or provided data.
    
    Args:
        json_file: Path to the JSON file
        initial_data: Initial data (default empty list)
    """
    try:
        json_file = get_experiments_path(json_file)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data if initial_data is not None else [], f)
        logger.info(f"Initialized JSON file {json_file}")
    except Exception as e:
        logger.error(f"Error initializing JSON file {json_file}: {str(e)}")
        raise Exception(f"Cannot initialize JSON file: {e}")