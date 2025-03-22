"""
Klasa LitVarEndpoint umożliwia komunikację z API LitVar2 i pobieranie informacji o wariantach genomowych.
"""

import requests
import ast
import json
import pandas as pd
from typing import List, Dict, Any, Optional


class LitVarEndpoint:
    """
    Klasa do komunikacji z API LitVar2 (https://www.ncbi.nlm.nih.gov/research/litvar2-api/).
    
    Umożliwia:
    - Wyszukiwanie wariantów powiązanych z określonymi genami
    - Pobieranie szczegółów dotyczących wariantów
    - Pobieranie identyfikatorów publikacji (PMID, PMCID) powiązanych z wariantami
    - Zapisywanie pobranych danych do plików JSON
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
    
    def __init__(self):
        """
        Inicjalizacja klienta API LitVar.
        """
        self.variants_data = []
        self.variant_details = {}
        self.pmids_data = {}
    
    def search_by_genes(self, genes: List[str]) -> List[Dict[str, Any]]:
        """
        Wyszukuje warianty powiązane z podanymi genami.
        
        Args:
            genes: Lista nazw genów do wyszukania
            
        Returns:
            Lista słowników zawierających informacje o wariantach
        """
        responses_dicts = []
        
        for gene in genes:
            url = f"{self.BASE_URL}/variant/search/gene/{gene}"
            response = requests.get(url)
            
            if response.status_code == 200:
                # Konwersja odpowiedzi tekstowej na listę słowników
                response_list = response.text.strip().split('\n')
                response_dicts = [ast.literal_eval(item) for item in response_list]
                # Dodanie informacji o genie do każdego słownika
                gene_response_dicts = [{**item, "gene": gene} for item in response_dicts]
                responses_dicts.extend(gene_response_dicts)
        
        self.variants_data = responses_dicts
        return responses_dicts
    
    def get_variants_dataframe(self, variants_data: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Konwertuje dane wariantów na DataFrame pandas.
        
        Args:
            variants_data: Opcjonalna lista słowników z danymi o wariantach
            
        Returns:
            DataFrame z danymi o wariantach
        """
        if variants_data is None:
            variants_data = self.variants_data
            
        return pd.DataFrame(variants_data)
    
    def get_variant_details(self, variant_ids: List[str]) -> Dict[str, Any]:
        """
        Pobiera szczegółowe informacje o wariantach na podstawie ich identyfikatorów.
        
        Args:
            variant_ids: Lista identyfikatorów wariantów (_id z wyszukiwania)
            
        Returns:
            Słownik zawierający szczegóły wariantów
        """
        variant_details = {}
        
        for variant_id in variant_ids:
            url = f"{self.BASE_URL}/variant/get/{variant_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                variant_details[variant_id] = response.json()
        
        self.variant_details = variant_details
        return variant_details
    
    def get_pmids_pmcids(self, rsids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        Pobiera identyfikatory publikacji (PMID, PMCID) powiązane z wariantami.
        
        Args:
            rsids: Lista identyfikatorów rsid wariantów
            
        Returns:
            Słownik mapujący rsid na słownik z listami PMID i PMCID
        """
        pmids_data = {}
        
        for rsid in rsids:
            url = f"{self.BASE_URL}/publications/get/{rsid}"
            response = requests.get(url)
            
            if response.status_code == 200:
                publications = response.json()
                pmids = [pub.get('pmid') for pub in publications if 'pmid' in pub]
                pmcids = [pub.get('pmcid') for pub in publications if 'pmcid' in pub]
                
                pmids_data[rsid] = {
                    'pmids': pmids,
                    'pmcids': pmcids
                }
        
        self.pmids_data = pmids_data
        return pmids_data
    
    def save_to_json(self, data: Any, file_path: str) -> None:
        """
        Zapisuje dane do pliku JSON.
        
        Args:
            data: Dane do zapisania
            file_path: Ścieżka do pliku wyjściowego
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    
    def save_variants_data(self, file_path: str) -> None:
        """
        Zapisuje dane wariantów do pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku wyjściowego
        """
        self.save_to_json(self.variants_data, file_path)
    
    def save_variant_details(self, file_path: str) -> None:
        """
        Zapisuje szczegóły wariantów do pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku wyjściowego
        """
        self.save_to_json(self.variant_details, file_path)
    
    def save_pmids_data(self, file_path: str) -> None:
        """
        Zapisuje dane PMID/PMCID do pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku wyjściowego
        """
        self.save_to_json(self.pmids_data, file_path)
    
    def process_gene_list(self, genes: List[str], 
                           variants_output_path: Optional[str] = None,
                           details_output_path: Optional[str] = None,
                           pmids_output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Przetwarza listę genów, pobierając informacje o wariantach i powiązanych publikacjach.
        
        Args:
            genes: Lista nazw genów
            variants_output_path: Opcjonalna ścieżka do pliku z danymi wariantów
            details_output_path: Opcjonalna ścieżka do pliku ze szczegółami wariantów
            pmids_output_path: Opcjonalna ścieżka do pliku z identyfikatorami publikacji
            
        Returns:
            Słownik zawierający wszystkie pobrane dane
        """
        # Wyszukaj warianty dla genów
        variants_data = self.search_by_genes(genes)
        
        # Pobierz rsids z danych wariantów (tylko niepuste)
        rsids = [str(variant.get('rsid')) for variant in variants_data 
                if variant.get('rsid') and pd.notna(variant.get('rsid'))]
        
        # Pobierz identyfikatory wariantów
        variant_ids = [str(variant.get('_id')) for variant in variants_data 
                      if variant.get('_id') is not None]
        
        # Pobierz szczegóły wariantów
        variant_details = self.get_variant_details(variant_ids)
        
        # Pobierz identyfikatory publikacji
        pmids_data = self.get_pmids_pmcids(rsids)
        
        # Zapisz dane do plików, jeśli podano ścieżki
        if variants_output_path:
            self.save_variants_data(variants_output_path)
            
        if details_output_path:
            self.save_variant_details(details_output_path)
            
        if pmids_output_path:
            self.save_pmids_data(pmids_output_path)
        
        return {
            'variants_data': variants_data,
            'variant_details': variant_details,
            'pmids_data': pmids_data
        } 