"""
Testy dla klasy ValidationReport.

Ten moduł zawiera testy jednostkowe dla klasy ValidationReport,
która jest używana do przechowywania wyników walidacji relacji
między wariantami genetycznymi, genami i chorobami.
"""

import os
import pytest
import json
import csv
import tempfile

from src.clinvar_relationship_validator import ValidationReport


@pytest.fixture
def empty_report():
    """Fixture zwracający pusty raport walidacji."""
    return ValidationReport()


@pytest.fixture
def filled_report():
    """Fixture zwracający wypełniony raport walidacji."""
    report = ValidationReport()
    
    # Dodaj przykładowe relacje
    report.add_valid_relationship(
        {"pmid": "1234", "variant_text": "TP53 p.Pro72Arg", "gene_text": "TP53"},
        "Potwierdzona relacja wariant-gen"
    )
    
    report.add_invalid_relationship(
        {"pmid": "5678", "variant_text": "BRCA1 c.5382insC", "gene_text": "BRCA2"},
        "Brak potwierdzenia relacji w ClinVar"
    )
    
    report.add_error_relationship(
        {"pmid": "9012", "variant_text": "UNKNOWN", "gene_text": "UNKNOWN"},
        "Błąd API ClinVar: rate limit exceeded"
    )
    
    return report


class TestValidationReport:
    """Testy dla klasy ValidationReport."""
    
    def test_init(self, empty_report):
        """Test inicjalizacji pustego raportu."""
        assert empty_report.total_relationships == 0
        assert len(empty_report.valid_relationships) == 0
        assert len(empty_report.invalid_relationships) == 0
        assert len(empty_report.error_relationships) == 0
    
    def test_add_valid_relationship(self, empty_report):
        """Test dodawania poprawnej relacji."""
        relationship = {"pmid": "1234", "variant_text": "TP53 p.Pro72Arg"}
        reason = "Potwierdzona relacja"
        
        empty_report.add_valid_relationship(relationship, reason)
        
        assert empty_report.total_relationships == 1
        assert len(empty_report.valid_relationships) == 1
        assert empty_report.valid_relationships[0]["validation_result"] == "valid"
        assert empty_report.valid_relationships[0]["validation_reason"] == reason
    
    def test_add_invalid_relationship(self, empty_report):
        """Test dodawania niepoprawnej relacji."""
        relationship = {"pmid": "5678", "variant_text": "BRCA1 c.5382insC"}
        reason = "Brak potwierdzenia"
        
        empty_report.add_invalid_relationship(relationship, reason)
        
        assert empty_report.total_relationships == 1
        assert len(empty_report.invalid_relationships) == 1
        assert empty_report.invalid_relationships[0]["validation_result"] == "invalid"
        assert empty_report.invalid_relationships[0]["validation_reason"] == reason
    
    def test_add_error_relationship(self, empty_report):
        """Test dodawania relacji z błędem."""
        relationship = {"pmid": "9012", "variant_text": "UNKNOWN"}
        error = "Błąd API"
        
        empty_report.add_error_relationship(relationship, error)
        
        assert empty_report.total_relationships == 1
        assert len(empty_report.error_relationships) == 1
        assert empty_report.error_relationships[0]["validation_result"] == "error"
        assert empty_report.error_relationships[0]["validation_reason"] == error
    
    def test_get_all_relationships(self, filled_report):
        """Test pobierania wszystkich relacji."""
        all_relationships = filled_report.get_all_relationships()
        
        assert len(all_relationships) == 3
        assert filled_report.total_relationships == 3
        
        # Sprawdź, czy wszystkie typy relacji są uwzględnione
        results = [rel["validation_result"] for rel in all_relationships]
        assert "valid" in results
        assert "invalid" in results
        assert "error" in results
    
    def test_get_counts(self, filled_report):
        """Test pobierania liczników relacji."""
        assert filled_report.get_valid_count() == 1
        assert filled_report.get_invalid_count() == 1
        assert filled_report.get_error_count() == 1
    
    def test_get_percentage_valid(self, filled_report):
        """Test obliczania procentu poprawnych relacji."""
        # 1 poprawna z 3 wszystkich = 33.33%
        assert filled_report.get_percentage_valid() == pytest.approx(33.33, 0.01)
    
    def test_get_percentage_valid_empty(self, empty_report):
        """Test obliczania procentu poprawnych relacji dla pustego raportu."""
        assert empty_report.get_percentage_valid() == 0.0
    
    def test_get_statistics(self, filled_report):
        """Test pobierania statystyk."""
        stats = filled_report.get_statistics()
        
        assert stats["total"] == 3
        assert stats["valid"] == 1
        assert stats["invalid"] == 1
        assert stats["errors"] == 1
        assert stats["percent_valid"] == pytest.approx(33.33, 0.01)
    
    def test_save_to_json(self, filled_report, tmpdir):
        """Test zapisywania raportu do pliku JSON."""
        output_file = tmpdir.join("report.json")
        filled_report.save_to_json(str(output_file))
        
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            data = json.load(f)
            
            assert "statistics" in data
            assert "relationships" in data
            assert len(data["relationships"]) == 3
            assert data["statistics"]["total"] == 3
    
    def test_save_to_csv(self, filled_report, tmpdir):
        """Test zapisywania raportu do pliku CSV."""
        output_file = tmpdir.join("report.csv")
        filled_report.save_to_csv(str(output_file))
        
        assert os.path.exists(output_file)
        
        with open(output_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 3
            assert all("validation_result" in row for row in rows)
            assert all("validation_reason" in row for row in rows)
            
            results = [row["validation_result"] for row in rows]
            assert "valid" in results
            assert "invalid" in results
            assert "error" in results 