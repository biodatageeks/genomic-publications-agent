"""
Klasa EnhancerDataProcessor służy do przetwarzania danych dotyczących wariantów
genomowych i elementów wzmacniających (enhancerów) z plików CSV.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Union


class EnhancerDataProcessor:
    """
    Klasa przetwarzająca dane o wariantach genomowych i elementach wzmacniających
    z plików CSV.
    """
    
    def __init__(self):
        """
        Inicjalizacja procesora danych.
        """
        self.loe_data = None  # Dane dla LOE (Loss of Enhancer Function)
        self.mloe_data = None  # Dane dla mLOE (mild Loss of Enhancer Function)
        self.coordinates_search_list = []
    
    def load_data(self, loe_path: str, mloe_path: str) -> Dict[str, pd.DataFrame]:
        """
        Wczytuje dane z plików CSV.
        
        Args:
            loe_path: Ścieżka do pliku CSV z danymi LOE
            mloe_path: Ścieżka do pliku CSV z danymi mLOE
            
        Returns:
            Słownik zawierający wczytane ramki danych
        """
        self.loe_data = pd.read_csv(loe_path)
        self.mloe_data = pd.read_csv(mloe_path)
        
        return {
            "loe_data": self.loe_data,
            "mloe_data": self.mloe_data
        }
    
    def preprocess_pmid_cell(self, input_str: str) -> Optional[List[str]]:
        """
        Przetwarza komórkę zawierającą identyfikatory PMID.
        
        Args:
            input_str: Zawartość komórki PMID
            
        Returns:
            Lista identyfikatorów PMID lub None, jeśli format jest nieprawidłowy
        """
        if not input_str or not str(input_str).strip() or not str(input_str).strip()[0].isdigit():
            return None
            
        filtered_str = str(input_str).split('(')[0].strip()
        return [pmid.strip() for pmid in filtered_str.split(';')]
    
    def create_coordinates_search_list(self, data: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """
        Tworzy listę koordynatów do wyszukiwania na podstawie danych.
        
        Args:
            data: Opcjonalna ramka danych do przetworzenia (domyślnie: loe_data)
            
        Returns:
            Lista słowników z koordynatami i metadanymi
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("Brak danych. Najpierw wczytaj dane za pomocą load_data().")
            data = self.loe_data
            
        coordinates_search_list = []
        
        for _, row in data.iterrows():
            user_query_dict = {
                'gene': row['Gene'],
                'disease': row['Disease'],
                # Można dodać więcej pól, jeśli potrzeba:
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
        Zwraca identyfikatory PMID dla danego koordynatu HGVS.
        
        Args:
            hgvs_coordinate: Koordynat HGVS
            
        Returns:
            Lista identyfikatorów PMID
        """
        for item in self.coordinates_search_list:
            if item['hgvs_coordinate'] == hgvs_coordinate:
                return item['pmids']
        return []
    
    def get_metadata_for_coordinate(self, hgvs_coordinate: str) -> Dict[str, Any]:
        """
        Zwraca metadane dla danego koordynatu HGVS.
        
        Args:
            hgvs_coordinate: Koordynat HGVS
            
        Returns:
            Słownik z metadanymi
        """
        for item in self.coordinates_search_list:
            if item['hgvs_coordinate'] == hgvs_coordinate:
                return item['user_query_dict']
        return {}
    
    def save_to_csv(self, data: pd.DataFrame, output_path: str) -> None:
        """
        Zapisuje dane do pliku CSV.
        
        Args:
            data: Ramka danych do zapisania
            output_path: Ścieżka do pliku wyjściowego
        """
        data.to_csv(output_path, index=False)
        print(f"Zapisano dane do pliku: {output_path}")
    
    def save_to_json(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Zapisuje dane do pliku JSON.
        
        Args:
            data: Lista słowników do zapisania
            output_path: Ścieżka do pliku wyjściowego
        """
        import json
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        print(f"Zapisano dane do pliku: {output_path}")
    
    def filter_by_gene(self, gene: str, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filtruje dane na podstawie nazwy genu.
        
        Args:
            gene: Nazwa genu do filtrowania
            data: Opcjonalna ramka danych do filtrowania (domyślnie: loe_data)
            
        Returns:
            Przefiltrowana ramka danych
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("Brak danych. Najpierw wczytaj dane za pomocą load_data().")
            data = self.loe_data
            
        return data[data['Gene'] == gene]
    
    def filter_by_disease(self, disease: str, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Filtruje dane na podstawie nazwy choroby.
        
        Args:
            disease: Nazwa choroby do filtrowania
            data: Opcjonalna ramka danych do filtrowania (domyślnie: loe_data)
            
        Returns:
            Przefiltrowana ramka danych
        """
        if data is None:
            if self.loe_data is None:
                raise ValueError("Brak danych. Najpierw wczytaj dane za pomocą load_data().")
            data = self.loe_data
            
        return data[data['Disease'].str.contains(disease, case=False, na=False)]
    
    def process_and_export(self, loe_path: str, mloe_path: str,
                          output_csv_path: Optional[str] = None,
                          output_json_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Przeprowadza pełny proces przetwarzania danych.
        
        Args:
            loe_path: Ścieżka do pliku CSV z danymi LOE
            mloe_path: Ścieżka do pliku CSV z danymi mLOE
            output_csv_path: Opcjonalna ścieżka do pliku wyjściowego CSV
            output_json_path: Opcjonalna ścieżka do pliku wyjściowego JSON
            
        Returns:
            Słownik zawierający przetworzone dane
        """
        # Wczytaj dane
        self.load_data(loe_path, mloe_path)
        
        # Przetwórz koordynaty
        coordinates_search_list = self.create_coordinates_search_list()
        
        # Zapisz wyniki, jeśli podano ścieżki
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