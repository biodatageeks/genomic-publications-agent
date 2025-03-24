"""
The EnhancerDataProcessor class is used for processing genomic variant data
and enhancer elements from CSV files.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Union


class EnhancerDataProcessor:
    """
    Class for processing genomic variant and enhancer element data
    from CSV files.
    """
    
    def __init__(self):
        """
        Initialize the data processor.
        """
        self.loe_data = None  # Data for LOE (Loss of Enhancer Function)
        self.mloe_data = None  # Data for mLOE (mild Loss of Enhancer Function)
        self.coordinates_search_list = []
    
    def load_data(self, loe_path: str, mloe_path: str) -> Dict[str, pd.DataFrame]:
        """
        Loads data from CSV files.
        
        Args:
            loe_path: Path to the CSV file with LOE data
            mloe_path: Path to the CSV file with mLOE data
            
        Returns:
            Dictionary containing loaded dataframes
        """
        self.loe_data = pd.read_csv(loe_path)
        self.mloe_data = pd.read_csv(mloe_path)
        
        return {
            "loe_data": self.loe_data,
            "mloe_data": self.mloe_data
        }
    
    def preprocess_pmid_cell(self, input_str: str) -> Optional[List[str]]:
        """
        Processes a cell containing PMID identifiers.
        
        Args:
            input_str: Content of the PMID cell
            
        Returns:
            List of PMID identifiers or None if the format is invalid
        """
        if not input_str or not str(input_str).strip() or not str(input_str).strip()[0].isdigit():
            return None
            
        filtered_str = str(input_str).split('(')[0].strip()
        return [pmid.strip() for pmid in filtered_str.split(';')]
    
    def create_coordinates_search_list(self, data: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """
        Creates a list of coordinates for searching based on the data.
        
        Args:
            data: Optional dataframe to process (default: loe_data)
            
        Returns:
            List of dictionaries with coordinates and metadata
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("No data available. First load data using load_data().")
            data = self.loe_data
            
        coordinates_search_list = []
        
        for _, row in data.iterrows():
            user_query_dict = {
                'gene': row['Gene'],
                'disease': row['Disease'],
                # Additional fields can be added if needed:
                # 'disease severity': row['Disease severity'],
                # 'Regulatory element(s) impacted': row['Regulatory element(s) impacted'],
                # 'Distance to promoter': row['Distance to promoter'],
                # 'Pathogenicity': row['ClinVar classification'],
            }
            
            hgvs_coordinate = row['Variant ID']
            pmids = self.preprocess_pmid_cell(row['PMID(s)'])
            
            if pmids is None:
                print(f'PMID(s) cell is not in the correct format: {row["PMID(s)"]}')
                continue
                
            coordinates_search_list.append({
                'hgvs_coordinate': hgvs_coordinate,
                'pmids': pmids,
                'user_query_dict': user_query_dict
            })
            
        self.coordinates_search_list = coordinates_search_list
        return coordinates_search_list
    
    def get_pmids_for_coordinate(self, hgvs_coordinate: str) -> List[str]:
        """
        Returns PMID identifiers for a given HGVS coordinate.
        
        Args:
            hgvs_coordinate: HGVS coordinate
            
        Returns:
            List of PMID identifiers
        """
        for item in self.coordinates_search_list:
            if item['hgvs_coordinate'] == hgvs_coordinate:
                return item['pmids']
        return []
    
    def get_metadata_for_coordinate(self, hgvs_coordinate: str) -> Dict[str, Any]:
        """
        Returns metadata for a given HGVS coordinate.
        
        Args:
            hgvs_coordinate: HGVS coordinate
            
        Returns:
            Dictionary with metadata
        """
        for item in self.coordinates_search_list:
            if item['hgvs_coordinate'] == hgvs_coordinate:
                return item['user_query_dict']
        return {}
    
    def save_to_csv(self, data: pd.DataFrame, output_path: str) -> None:
        """
        Saves data to a CSV file.
        
        Args:
            data: DataFrame to save
            output_path: Path to the output file
        """
        data.to_csv(output_path, index=False)
        print(f"Data saved to file: {output_path}")
    
    def save_to_json(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Saves data to a JSON file.
        
        Args:
            data: List of dictionaries to save
            output_path: Path to the output file
        """
        import json
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        print(f"Data saved to file: {output_path}")
    
    def filter_by_gene(self, gene: str, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filters data based on gene name.
        
        Args:
            gene: Gene name to filter by
            data: Optional dataframe to filter (default: loe_data)
            
        Returns:
            Filtered dataframe
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("No data available. First load data using load_data().")
            data = self.loe_data
            
        return data[data['Gene'] == gene]
    
    def filter_by_disease(self, disease: str, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filters data based on disease name.
        
        Args:
            disease: Disease name to filter by
            data: Optional dataframe to filter (default: loe_data)
            
        Returns:
            Filtered dataframe
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("No data available. First load data using load_data().")
            data = self.loe_data
            
        return data[data['Disease'].str.contains(disease, case=False, na=False)]
    
    def process_and_export(self, loe_path: str, mloe_path: str,
                          output_csv_path: Optional[str] = None,
                          output_json_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs the complete data processing process.
        
        Args:
            loe_path: Path to the CSV file with LOE data
            mloe_path: Path to the CSV file with mLOE data
            output_csv_path: Optional path to the output CSV file
            output_json_path: Optional path to the output JSON file
            
        Returns:
            Dictionary containing processed data
        """
        # Load data
        self.load_data(loe_path, mloe_path)
        
        # Process coordinates
        coordinates_search_list = self.create_coordinates_search_list()
        
        # Save results if paths are provided
        if output_csv_path:
            combined_data = pd.concat([self.loe_data, self.mloe_data], ignore_index=True)
            self.save_to_csv(combined_data, output_csv_path)
            
        if output_json_path:
            self.save_to_json(coordinates_search_list, output_json_path)
            
        return {
            "loe_data": self.loe_data,
            "mloe_data": self.mloe_data,
            "coordinates_search_list": coordinates_search_list
        } 