"""
Testy dla modułu ClinvarRelationshipValidator.

Testy można uruchomić w trybie mock lub z prawdziwym API ClinVar.
Domyślnie testy używają mocków, aby nie obciążać API ClinVar.

Aby uruchomić testy z prawdziwym API:
pytest test_clinvar_relationship_validator.py --use-real-api --email your.email@example.com
"""

import os
import pytest
import tempfile
import json
import csv
from unittest.mock import Mock, patch, MagicMock

from src.services.validation import ClinvarRelationshipValidator, ValidationReport, ValidationError
from src.api.clients.exceptions import ClinVarError


# =========== FIXTURES I KONFIGURACJA =========== #

def pytest_addoption(parser):
    """Dodaje opcje wiersza poleceń do pytest."""
    parser.addoption(
        "--use-real-api", 
        action="store_true", 
        default=False,
        help="Użyj prawdziwego API ClinVar zamiast mocków"
    )
    
    parser.addoption(
        "--email", 
        action="store", 
        default="test@example.com",
        help="Email dla API ClinVar (wymagany przy --use-real-api)"
    )


@pytest.fixture
def use_real_api(request):
    """Fixture zwracający czy używać prawdziwego API."""
    try:
        return request.config.getoption("--use-real-api")
    except ValueError:
        return False


@pytest.fixture
def email(request):
    """Fixture zwracający email dla API ClinVar."""
    try:
        return request.config.getoption("--email")
    except ValueError:
        return "test@example.com"


@pytest.fixture
def mock_clinvar_client():
    """Fixture zwracający zmockowany klient ClinVar."""
    mock_client = Mock()
    
    # Konfiguracja domyślnych odpowiedzi mocka
    variant_info = {
        "id": "VCV000012345",
        "name": "NM_000546.5(TP53):c.215C>G (p.Pro72Arg)",
        "variation_type": "SNV",
        "clinical_significance": "benign",
        "genes": [
            {"symbol": "TP53", "id": "7157"}
        ],
        "phenotypes": [
            {"name": "Hereditary cancer-predisposing syndrome", "id": "OMIM:151623"}
        ],
        "coordinates": [
            {
                "assembly": "GRCh38",
                "chromosome": "17",
                "start": 7676154,
                "stop": 7676154,
                "reference_allele": "C",
                "alternate_allele": "G"
            }
        ]
    }
    
    unknown_variant_info = {
        "id": "VCV999999999",
        "name": "Unknown variant",
        "variation_type": "Unknown",
        "clinical_significance": "uncertain significance",
        "genes": [],
        "phenotypes": [],
        "coordinates": []
    }
    
    # Konfiguracja zachowania metod
    def get_variant_by_id_mock(variant_id):
        if variant_id in ["VCV000012345", "rs1042522"]:
            return variant_info
        elif variant_id in ["TP53 p.Pro72Arg"]:
            return variant_info
        elif variant_id == "UNKNOWN":
            return unknown_variant_info
        else:
            return None
            
    mock_client.get_variant_by_id.side_effect = get_variant_by_id_mock
    
    return mock_client


@pytest.fixture
def validator(use_real_api, email, mock_clinvar_client):
    """
    Fixture zwracający instancję ClinvarRelationshipValidator.
    
    W zależności od parametru use_real_api, zwraca walidator z prawdziwym
    klientem ClinVar lub z mockiem.
    """
    if use_real_api:
        # Używamy prawdziwego API ClinVar
        return ClinvarRelationshipValidator(email=email)
    else:
        # Używamy mocka
        return ClinvarRelationshipValidator(
            email="test@example.com", 
            clinvar_client=mock_clinvar_client
        )


@pytest.fixture
def sample_relationships():
    """Fixture zwracający przykładowe relacje do testów."""
    return [
        {
            "pmid": "12345678",
            "variant_text": "TP53 p.Pro72Arg",
            "variant_id": "VCV000012345",
            "gene_text": "TP53",
            "gene_id": "7157",
            "disease_text": "Hereditary cancer",
            "disease_id": "OMIM:151623",
            "passage_text": "The TP53 p.Pro72Arg variant is associated with hereditary cancer."
        },
        {
            "pmid": "23456789",
            "variant_text": "BRCA1 c.5382insC",
            "variant_id": "UNKNOWN",
            "gene_text": "BRCA1",
            "gene_id": "672",
            "disease_text": "Breast cancer",
            "disease_id": "OMIM:114480",
            "passage_text": "BRCA1 c.5382insC is a pathogenic variant associated with breast cancer."
        }
    ]


@pytest.fixture
def temp_csv_file():
    """Fixture tworzący tymczasowy plik CSV z relacjami."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pmid", "variant_text", "variant_id", "gene_text", "gene_id", 
            "disease_text", "disease_id", "passage_text"
        ])
        writer.writeheader()
        writer.writerow({
            "pmid": "12345678",
            "variant_text": "TP53 p.Pro72Arg",
            "variant_id": "VCV000012345",
            "gene_text": "TP53",
            "gene_id": "7157",
            "disease_text": "Hereditary cancer",
            "disease_id": "OMIM:151623",
            "passage_text": "The TP53 p.Pro72Arg variant is associated with hereditary cancer."
        })
        writer.writerow({
            "pmid": "23456789",
            "variant_text": "BRCA1 c.5382insC",
            "variant_id": "UNKNOWN",
            "gene_text": "BRCA1",
            "gene_id": "672",
            "disease_text": "Breast cancer",
            "disease_id": "OMIM:114480",
            "passage_text": "BRCA1 c.5382insC is a pathogenic variant associated with breast cancer."
        })
        tmp_path = f.name
    
    yield tmp_path
    
    # Usuń plik po teście
    os.unlink(tmp_path)


# =========== TESTY =========== #

class TestClinvarRelationshipValidator:
    """Testy dla klasy ClinvarRelationshipValidator."""
    
    def test_init(self, validator):
        """Test inicjalizacji walidatora."""
        assert validator is not None
        assert hasattr(validator, "clinvar_client")
        assert hasattr(validator, "logger")
    
    def test_validate_relationships(self, validator, sample_relationships):
        """Test walidacji listy relacji."""
        validation_report = validator.validate_relationships(sample_relationships)
        
        assert validation_report is not None
        assert isinstance(validation_report, ValidationReport)
        assert validation_report.total_relationships == len(sample_relationships)
    
    def test_validate_relationships_from_csv(self, validator, temp_csv_file):
        """Test walidacji relacji z pliku CSV."""
        validation_report = validator.validate_relationships_from_csv(temp_csv_file)
        
        assert validation_report is not None
        assert isinstance(validation_report, ValidationReport)
        assert validation_report.total_relationships == 2
    
    def test_get_validation_statistics(self, validator, sample_relationships):
        """Test pobierania statystyk walidacji."""
        validator.validate_relationships(sample_relationships)
        stats = validator.get_validation_statistics()
        
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "valid" in stats
        assert "invalid" in stats
        assert "errors" in stats
        assert "percent_valid" in stats
        assert stats["total"] == len(sample_relationships)
    
    def test_save_validation_report_json(self, validator, sample_relationships, tmpdir):
        """Test zapisywania raportu walidacji do formatu JSON."""
        validator.validate_relationships(sample_relationships)
        
        output_file = tmpdir.join("report.json")
        validator.save_validation_report(str(output_file))
        
        assert os.path.exists(output_file)
        
        # Sprawdź, czy plik zawiera oczekiwane dane
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert "statistics" in data
            assert "relationships" in data
            assert len(data["relationships"]) == len(sample_relationships)
    
    def test_save_validation_report_csv(self, validator, sample_relationships, tmpdir):
        """Test zapisywania raportu walidacji do formatu CSV."""
        validator.validate_relationships(sample_relationships)
        
        output_file = tmpdir.join("report.csv")
        validator.save_validation_report(str(output_file), format_type="csv")
        
        assert os.path.exists(output_file)
        
        # Sprawdź, czy plik zawiera oczekiwane dane
        with open(output_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(sample_relationships)
            assert "validation_result" in rows[0]
            assert "validation_reason" in rows[0]
    
    @pytest.mark.parametrize("variant_key, exists", [
        ("VCV000012345", True),
        ("rs1042522", True),
        ("TP53 p.Pro72Arg", True),
        ("UNKNOWN", True),  # ten powinien zwrócić "unknown variant" info
        ("nonexistent", False)
    ])
    def test_get_variant_info(self, validator, variant_key, exists):
        """Test pobierania informacji o wariancie z ClinVar."""
        # Używamy metody prywatnej bezpośrednio w celach testowych
        variant_info = validator._get_variant_info(variant_key)
        
        if exists:
            assert variant_info is not None
            assert "id" in variant_info
            assert "name" in variant_info
        else:
            assert variant_info is None
    
    def test_validate_variant_gene_relationship_valid(self, validator):
        """Test walidacji relacji wariant-gen, gdy relacja jest prawidłowa."""
        variant_info = {
            "genes": [
                {"symbol": "TP53", "id": "7157"},
                {"symbol": "MDM2", "id": "4193"}
            ]
        }
        
        # Sprawdź poprawną relację - przez ID
        assert validator._validate_variant_gene_relationship(variant_info, "7157", "") is True
        
        # Sprawdź poprawną relację - przez nazwę
        assert validator._validate_variant_gene_relationship(variant_info, "", "TP53") is True
    
    def test_validate_variant_gene_relationship_invalid(self, validator):
        """Test walidacji relacji wariant-gen, gdy relacja jest nieprawidłowa."""
        variant_info = {
            "genes": [
                {"symbol": "TP53", "id": "7157"}
            ]
        }
        
        # Sprawdź niepoprawną relację
        assert validator._validate_variant_gene_relationship(variant_info, "999", "BRCA1") is False
    
    def test_validate_variant_disease_relationship_valid(self, validator):
        """Test walidacji relacji wariant-choroba, gdy relacja jest prawidłowa."""
        variant_info = {
            "phenotypes": [
                {"name": "Hereditary cancer-predisposing syndrome", "id": "OMIM:151623"},
                {"name": "Li-Fraumeni syndrome", "id": "OMIM:151623"}
            ]
        }
        
        # Sprawdź poprawną relację - przez ID
        assert validator._validate_variant_disease_relationship(variant_info, "OMIM:151623", "") is True
        
        # Sprawdź poprawną relację - przez nazwę (podobieństwo tekstu)
        assert validator._validate_variant_disease_relationship(variant_info, "", "cancer syndrome") is True
    
    def test_validate_variant_disease_relationship_invalid(self, validator):
        """Test walidacji relacji wariant-choroba, gdy relacja jest nieprawidłowa."""
        variant_info = {
            "phenotypes": [
                {"name": "Hereditary cancer", "id": "OMIM:151623"}
            ]
        }
        
        # Sprawdź niepoprawną relację
        assert validator._validate_variant_disease_relationship(variant_info, "OMIM:999", "Diabetes") is False
    
    def test_text_similarity(self, validator):
        """Test funkcji sprawdzającej podobieństwo tekstów."""
        # Podobne teksty
        assert validator._text_similarity("Breast cancer", "Breast cancer susceptibility") is True
        assert validator._text_similarity("p53 tumor suppressor", "tumor suppressor p53") is True
        
        # Niepodobne teksty
        assert validator._text_similarity("BRCA1", "TP53") is False
        assert validator._text_similarity("Diabetes mellitus", "Cancer syndrome") is False
    
    @patch('src.api.clients.clinvar_client.ClinVarClient')
    def test_api_error_handling(self, mock_client_class, sample_relationships):
        """Test obsługi błędów API ClinVar."""
        # Skonfiguruj mock do zgłaszania wyjątku
        mock_client = mock_client_class.return_value
        # Zmień side_effect na słownik, aby niektóre wywołania powodowały błąd, a inne działały poprawnie
        def side_effect_func(variant_id):
            if variant_id == "VCV000012345":
                raise ClinVarError("API rate limit exceeded")
            return None
        
        mock_client.get_variant_by_id.side_effect = side_effect_func
        
        # Utwórz walidator z mockiem
        validator = ClinvarRelationshipValidator(
            email="test@example.com",
            clinvar_client=mock_client
        )
        
        # Wykonaj walidację i sprawdź obsługę błędu
        validation_report = validator.validate_relationships(sample_relationships)
        
        # Sprawdź, czy mamy co najmniej jedną relację z błędem
        assert validation_report.get_error_count() > 0
        
        # Sprawdź treść błędu
        error_relationships = validation_report.error_relationships
        assert any("API rate limit exceeded" in rel.get("validation_reason", "") for rel in error_relationships)
    
    def test_group_relationships_by_variant(self, validator, sample_relationships):
        """Test grupowania relacji według wariantów."""
        # Użyj metody prywatnej do grupowania
        variant_groups = validator._group_relationships_by_variant(sample_relationships)
        
        assert len(variant_groups) == 2
        assert "VCV000012345" in variant_groups
        assert "UNKNOWN" in variant_groups
        assert len(variant_groups["VCV000012345"]) == 1 