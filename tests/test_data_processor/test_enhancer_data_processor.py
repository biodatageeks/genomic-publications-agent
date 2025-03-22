"""
Testy dla klasy EnhancerDataProcessor z modułu data_processor.
"""
import os
import json
import pytest
import pandas as pd
from typing import List, Dict, Any
from unittest.mock import patch, mock_open, MagicMock

from src.data_processor.enhancer_data_processor import EnhancerDataProcessor


class TestEnhancerDataProcessor:
    """
    Testy dla klasy EnhancerDataProcessor.
    """
    
    def test_init(self):
        """Test inicjalizacji obiektu."""
        processor = EnhancerDataProcessor()
        assert processor.loe_data is None
        assert processor.mloe_data is None
        assert processor.coordinates_search_list == []
    
    @pytest.fixture
    def sample_loe_data(self):
        """Przygotowanie przykładowych danych LOE."""
        data = pd.DataFrame({
            'HGVS_COORDINATE': ['chr1:12345-12345', 'chr2:23456-23456'],
            'Variant': ['c.123A>G', 'p.V600E'],
            'Gene': ['BRCA1', 'BRAF'],
            'Disease': ['Breast cancer', 'Melanoma'],
            'PMID': ['12345678', '23456789;34567890'],
            'Cell': ['MCF7', 'A375']
        })
        return data
    
    @pytest.fixture
    def sample_mloe_data(self):
        """Przygotowanie przykładowych danych MLOE."""
        data = pd.DataFrame({
            'HGVS_COORDINATE': ['chr1:12345-12345', 'chr3:34567-34567'],
            'Variant': ['c.123A>G', 'c.456T>C'],
            'Gene': ['BRCA1', 'TP53'],
            'Disease': ['Breast cancer', 'Lung cancer'],
            'PMID': ['12345678;45678901', '56789012'],
            'Cell': ['MCF7;HEK293', 'A549']
        })
        return data
    
    @patch('pandas.read_csv')
    def test_load_data(self, mock_read_csv, sample_loe_data, sample_mloe_data):
        """Test wczytywania danych z plików CSV."""
        mock_read_csv.side_effect = [sample_loe_data, sample_mloe_data]
        
        processor = EnhancerDataProcessor()
        processor.load_data("loe.csv", "mloe.csv")
        
        assert processor.loe_data is not None
        assert processor.mloe_data is not None
        assert mock_read_csv.call_count == 2
        assert len(processor.loe_data) == 2
        assert len(processor.mloe_data) == 2
    
    def test_preprocess_pmid_cell(self):
        """Test przetwarzania identyfikatorów PMID z ciągu znaków."""
        processor = EnhancerDataProcessor()
        
        # Test dla pojedynczego PMID
        result = processor.preprocess_pmid_cell("12345678")
        assert result == ["12345678"]
        
        # Test dla wielu PMID oddzielonych średnikiem
        result = processor.preprocess_pmid_cell("12345678;23456789;34567890")
        assert result == ["12345678", "23456789", "34567890"]
        
        # Test dla ciągu znaków z białymi znakami
        result = processor.preprocess_pmid_cell(" 12345678 ; 23456789 ")
        assert result == ["12345678", "23456789"]
        
        # Test dla pustego ciągu znaków
        result = processor.preprocess_pmid_cell("")
        assert result == []
        
        # Test dla None
        result = processor.preprocess_pmid_cell(None)
        assert result == []
    
    def test_create_coordinates_search_list(self, sample_loe_data):
        """Test tworzenia listy koordynatów do wyszukiwania."""
        processor = EnhancerDataProcessor()
        
        # Test z przekazanym DataFrame
        result = processor.create_coordinates_search_list(sample_loe_data)
        assert len(result) == 2
        assert "chr1:12345-12345" in result
        assert "chr2:23456-23456" in result
        
        # Test z zapisem do instancji
        processor.loe_data = sample_loe_data
        processor.create_coordinates_search_list()
        assert len(processor.coordinates_search_list) == 2
        assert "chr1:12345-12345" in processor.coordinates_search_list
        assert "chr2:23456-23456" in processor.coordinates_search_list
    
    def test_get_pmids_for_coordinate(self, sample_loe_data, sample_mloe_data):
        """Test pobierania PMID dla danego koordynatu HGVS."""
        processor = EnhancerDataProcessor()
        processor.loe_data = sample_loe_data
        processor.mloe_data = sample_mloe_data
        
        # Test dla koordynatu występującego w obu zbiorach danych
        pmids = processor.get_pmids_for_coordinate("chr1:12345-12345")
        assert len(pmids) == 3
        assert "12345678" in pmids
        assert "45678901" in pmids
        
        # Test dla koordynatu występującego tylko w LOE
        pmids = processor.get_pmids_for_coordinate("chr2:23456-23456")
        assert len(pmids) == 2
        assert "23456789" in pmids
        assert "34567890" in pmids
        
        # Test dla koordynatu występującego tylko w MLOE
        pmids = processor.get_pmids_for_coordinate("chr3:34567-34567")
        assert len(pmids) == 1
        assert "56789012" in pmids
        
        # Test dla nieistniejącego koordynatu
        pmids = processor.get_pmids_for_coordinate("chr4:45678-45678")
        assert len(pmids) == 0
    
    def test_get_metadata_for_coordinate(self, sample_loe_data, sample_mloe_data):
        """Test pobierania metadanych dla danego koordynatu HGVS."""
        processor = EnhancerDataProcessor()
        processor.loe_data = sample_loe_data
        processor.mloe_data = sample_mloe_data
        
        # Test dla koordynatu występującego w obu zbiorach danych
        metadata = processor.get_metadata_for_coordinate("chr1:12345-12345")
        assert len(metadata) == 2
        assert metadata[0]["Gene"] == "BRCA1"
        assert metadata[0]["Disease"] == "Breast cancer"
        assert metadata[0]["source"] == "LOE"
        assert metadata[1]["source"] == "MLOE"
        
        # Test dla nieistniejącego koordynatu
        metadata = processor.get_metadata_for_coordinate("chr4:45678-45678")
        assert len(metadata) == 0
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_json(self, mock_file):
        """Test zapisywania danych do pliku JSON."""
        processor = EnhancerDataProcessor()
        data = [
            {"HGVS_COORDINATE": "chr1:12345-12345", "Gene": "BRCA1", "PMIDs": ["12345678"]},
            {"HGVS_COORDINATE": "chr2:23456-23456", "Gene": "BRAF", "PMIDs": ["23456789"]}
        ]
        
        processor.save_to_json(data, "output.json")
        
        mock_file.assert_called_once_with("output.json", "w", encoding="utf-8")
        handle = mock_file()
        handle.write.assert_called_once()
        
        # Sprawdź, czy zapisano prawidłowy JSON
        json_str = handle.write.call_args[0][0]
        parsed_data = json.loads(json_str)
        assert len(parsed_data) == 2
        assert parsed_data[0]["HGVS_COORDINATE"] == "chr1:12345-12345"
        assert parsed_data[1]["Gene"] == "BRAF"
    
    @patch('pandas.DataFrame.to_csv')
    def test_save_to_csv(self, mock_to_csv):
        """Test zapisywania danych do pliku CSV."""
        processor = EnhancerDataProcessor()
        data = pd.DataFrame({
            'HGVS_COORDINATE': ['chr1:12345-12345', 'chr2:23456-23456'],
            'Gene': ['BRCA1', 'BRAF'],
            'PMIDs': [['12345678'], ['23456789']]
        })
        
        processor.save_to_csv(data, "output.csv")
        
        mock_to_csv.assert_called_once_with("output.csv", index=False)
    
    def test_filter_by_gene(self, sample_loe_data):
        """Test filtrowania danych według nazwy genu."""
        processor = EnhancerDataProcessor()
        
        # Test z przekazanym DataFrame
        result = processor.filter_by_gene("BRCA1", sample_loe_data)
        assert len(result) == 1
        assert result.iloc[0]["Gene"] == "BRCA1"
        
        # Test dla nieistniejącego genu
        result = processor.filter_by_gene("UNKNOWN", sample_loe_data)
        assert len(result) == 0
        
        # Test z obiektem instancji
        processor.loe_data = sample_loe_data
        result = processor.filter_by_gene("BRAF")
        assert len(result) == 1
        assert result.iloc[0]["Gene"] == "BRAF"
    
    def test_filter_by_disease(self, sample_loe_data):
        """Test filtrowania danych według nazwy choroby."""
        processor = EnhancerDataProcessor()
        
        # Test z przekazanym DataFrame
        result = processor.filter_by_disease("Breast cancer", sample_loe_data)
        assert len(result) == 1
        assert result.iloc[0]["Disease"] == "Breast cancer"
        
        # Test dla nieistniejącej choroby
        result = processor.filter_by_disease("UNKNOWN", sample_loe_data)
        assert len(result) == 0
        
        # Test z obiektem instancji
        processor.loe_data = sample_loe_data
        result = processor.filter_by_disease("Melanoma")
        assert len(result) == 1
        assert result.iloc[0]["Disease"] == "Melanoma"
    
    @patch('src.data_processor.enhancer_data_processor.EnhancerDataProcessor.load_data')
    @patch('src.data_processor.enhancer_data_processor.EnhancerDataProcessor.create_coordinates_search_list')
    @patch('src.data_processor.enhancer_data_processor.EnhancerDataProcessor.save_to_csv')
    @patch('src.data_processor.enhancer_data_processor.EnhancerDataProcessor.save_to_json')
    def test_process_and_export(self, mock_save_json, mock_save_csv, mock_create_list, mock_load_data):
        """Test pełnego procesu przetwarzania i eksportu danych."""
        processor = EnhancerDataProcessor()
        
        # Uruchom metodę process_and_export
        processor.process_and_export("loe.csv", "mloe.csv", "output.csv", "output.json")
        
        # Sprawdź, czy odpowiednie metody zostały wywołane
        mock_load_data.assert_called_once_with("loe.csv", "mloe.csv")
        mock_create_list.assert_called_once()
        mock_save_csv.assert_called_once()
        mock_save_json.assert_called_once()
    
    def test_process_and_export_no_output(self):
        """Test przetwarzania bez podania ścieżek wyjściowych."""
        processor = EnhancerDataProcessor()
        
        # Mockuj metody, które normalne wywołałyby odczyt/zapis do pliku
        with patch('src.data_processor.enhancer_data_processor.EnhancerDataProcessor.load_data') as mock_load:
            processor.process_and_export("loe.csv", "mloe.csv", None, None)
            mock_load.assert_called_once_with("loe.csv", "mloe.csv")
            # Nic nie powinno zapisać, jeśli nie podano ścieżek wyjściowych
    
    def test_integration(self, tmp_path):
        """Test integracyjny dla całego procesu."""
        # Stwórz tymczasowe pliki CSV
        loe_path = tmp_path / "loe.csv"
        mloe_path = tmp_path / "mloe.csv"
        output_csv_path = tmp_path / "output.csv"
        output_json_path = tmp_path / "output.json"
        
        # Przygotuj dane testowe
        loe_data = pd.DataFrame({
            'HGVS_COORDINATE': ['chr1:12345-12345', 'chr2:23456-23456'],
            'Variant': ['c.123A>G', 'p.V600E'],
            'Gene': ['BRCA1', 'BRAF'],
            'Disease': ['Breast cancer', 'Melanoma'],
            'PMID': ['12345678', '23456789;34567890'],
            'Cell': ['MCF7', 'A375']
        })
        
        mloe_data = pd.DataFrame({
            'HGVS_COORDINATE': ['chr1:12345-12345', 'chr3:34567-34567'],
            'Variant': ['c.123A>G', 'c.456T>C'],
            'Gene': ['BRCA1', 'TP53'],
            'Disease': ['Breast cancer', 'Lung cancer'],
            'PMID': ['12345678;45678901', '56789012'],
            'Cell': ['MCF7;HEK293', 'A549']
        })
        
        # Zapisz dane testowe do plików
        loe_data.to_csv(loe_path, index=False)
        mloe_data.to_csv(mloe_path, index=False)
        
        # Wykonaj test z użyciem rzeczywistych plików
        with patch('pandas.read_csv', side_effect=[loe_data, mloe_data]):
            processor = EnhancerDataProcessor()
            processor.process_and_export(str(loe_path), str(mloe_path), str(output_csv_path), str(output_json_path))
            
            # Sprawdź, czy pliki wyjściowe zostały utworzone
            assert os.path.exists(output_csv_path)
            assert os.path.exists(output_json_path)
    
    # Test obsługi błędów
    
    @patch('pandas.read_csv', side_effect=FileNotFoundError("Test error"))
    def test_load_data_file_not_found(self, mock_read_csv):
        """Test obsługi błędu brakującego pliku."""
        processor = EnhancerDataProcessor()
        with pytest.raises(FileNotFoundError):
            processor.load_data("nonexistent.csv", "mloe.csv")
    
    def test_create_coordinates_search_list_no_data(self):
        """Test tworzenia listy koordynatów bez danych."""
        processor = EnhancerDataProcessor()
        result = processor.create_coordinates_search_list(None)
        assert result == [] 