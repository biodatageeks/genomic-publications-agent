"""
Testy dla endpoints API Mutalyzer
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from src.api.app import create_app
from src.models.mutalyzer import (
    VariantCheckRequest,
    VariantCheckResponse,
    VariantNormalizationRequest,
    VariantNormalizationResponse,
    BatchVariantRequest,
    BatchVariantResponse,
    MutalyzerError,
    ErrorType,
    VariantType,
    MoleculeType
)


@pytest.fixture
def client():
    """Fixture dla TestClient"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_mutalyzer_service():
    """Mock service dla Mutalyzer"""
    # Reset the singleton before patching
    import src.api.endpoints.mutalyzer as mutalyzer_module
    mutalyzer_module._mutalyzer_service = None
    
    with patch('src.api.endpoints.mutalyzer.get_mutalyzer_service') as mock:
        service_mock = AsyncMock()
        mock.return_value = service_mock
        yield service_mock
    
    # Clean up after test
    mutalyzer_module._mutalyzer_service = None


@pytest.fixture
def valid_variant_examples():
    """Przykłady poprawnych wariantów"""
    return [
        {
            "variant": "c.123A>T",
            "description": "Substytucja punktowa w cDNA",
            "type": VariantType.SUBSTITUTION
        },
        {
            "variant": "c.123_124delAT",
            "description": "Delecja dwóch nukleotydów",
            "type": VariantType.DELETION
        },
        {
            "variant": "c.123_124insATGC",
            "description": "Insercja czterech nukleotydów",
            "type": VariantType.INSERTION
        },
        {
            "variant": "g.12345C>T",
            "description": "Wariant genomowy",
            "type": VariantType.SUBSTITUTION
        },
        {
            "variant": "p.Arg123Cys",
            "description": "Zmiana aminokwasu w białku",
            "type": VariantType.SUBSTITUTION
        }
    ]


@pytest.fixture
def invalid_variant_examples():
    """Przykłady niepoprawnych wariantów"""
    return [
        {
            "variant": "c123A>T",
            "error": "Missing dot after prefix"
        },
        {
            "variant": "c.123A>>T",
            "error": "Invalid substitution syntax"
        },
        {
            "variant": "c.123_124del",
            "error": "Missing deleted sequence"
        },
        {
            "variant": "c.999999A>T",
            "error": "Position out of range"
        },
        {
            "variant": "c.123X>T",
            "error": "Invalid reference nucleotide"
        }
    ]


class TestVariantCheckEndpoint:
    """Testy dla endpoint'a sprawdzania wariantów"""
    
    @pytest.mark.asyncio
    async def test_check_valid_variant(self, client, mock_mutalyzer_service):
        """Test sprawdzania poprawnego wariantu"""
        
        # Mock odpowiedzi
        mock_response = VariantCheckResponse(
            is_valid=True,
            syntax_valid=True,
            semantic_valid=True,
            original_description="c.123A>T",
            normalized_description="c.123A>T",
            reference_found=True,
            errors=None
        )
        mock_mutalyzer_service.check_variant.return_value = mock_response
        
        # Request
        request_data = {
            "variant_description": "c.123A>T",
            "check_syntax_only": False,
            "normalize": True
        }
        
        response = client.post("/mutalyzer/check", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["syntax_valid"] is True
        assert data["semantic_valid"] is True
        assert data["original_description"] == "c.123A>T"
        assert data["normalized_description"] == "c.123A>T"
        
        # Sprawdź czy service został wywołany poprawnie
        mock_mutalyzer_service.check_variant.assert_called_once()
        call_args = mock_mutalyzer_service.check_variant.call_args[0][0]
        assert call_args.variant_description == "c.123A>T"
        assert call_args.check_syntax_only is False
        assert call_args.normalize is True
    
    @pytest.mark.asyncio
    async def test_check_invalid_variant_syntax(self, client, mock_mutalyzer_service):
        """Test sprawdzania wariantu z błędną składnią"""
        
        mock_response = VariantCheckResponse(
            is_valid=False,
            syntax_valid=False,
            semantic_valid=False,
            original_description="c123A>T",
            normalized_description=None,
            reference_found=False,
            errors=[
                MutalyzerError(
                    error_type=ErrorType.SYNTAX_ERROR,
                    message="Missing dot after prefix"
                )
            ]
        )
        mock_mutalyzer_service.check_variant.return_value = mock_response
        
        request_data = {
            "variant_description": "c123A>T",
            "check_syntax_only": True
        }
        
        response = client.post("/mutalyzer/check", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["syntax_valid"] is False
        assert data["semantic_valid"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error_type"] == "syntax_error"
        assert "Missing dot after prefix" in data["errors"][0]["message"]
    
    @pytest.mark.asyncio 
    async def test_check_variant_semantic_error(self, client, mock_mutalyzer_service):
        """Test sprawdzania wariantu z błędem semantycznym"""
        
        mock_response = VariantCheckResponse(
            is_valid=False,
            syntax_valid=True,
            semantic_valid=False,
            original_description="c.999999A>T",
            normalized_description=None,
            reference_found=False,
            errors=[
                MutalyzerError(
                    error_type=ErrorType.SEMANTIC_ERROR,
                    message="Position out of range"
                )
            ]
        )
        mock_mutalyzer_service.check_variant.return_value = mock_response
        
        request_data = {
            "variant_description": "c.999999A>T"
        }
        
        response = client.post("/mutalyzer/check", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["syntax_valid"] is True
        assert data["semantic_valid"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error_type"] == "semantic_error"
    
    @pytest.mark.asyncio
    async def test_check_variant_empty_description(self, client, mock_mutalyzer_service):
        """Test sprawdzania pustego opisu wariantu"""
        
        request_data = {
            "variant_description": "",
            "check_syntax_only": True
        }
        
        response = client.post("/mutalyzer/check", json=request_data)
        
        # Pydantic validation powinno to złapać
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_check_variant_service_exception(self, client, mock_mutalyzer_service):
        """Test obsługi wyjątku z serwisu"""
        
        mock_mutalyzer_service.check_variant.side_effect = Exception("Service error")
        
        request_data = {
            "variant_description": "c.123A>T"
        }
        
        response = client.post("/mutalyzer/check", json=request_data)
        
        assert response.status_code == 200  # Endpoint obsługuje błędy gracefully
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) == 1
        assert "Unexpected error" in data["errors"][0]["message"]


class TestVariantNormalizationEndpoint:
    """Testy dla endpoint'a normalizacji wariantów"""
    
    @pytest.mark.asyncio
    async def test_normalize_valid_variant(self, client, mock_mutalyzer_service):
        """Test normalizacji poprawnego wariantu"""
        
        mock_response = VariantNormalizationResponse(
            is_valid=True,
            original_description="c.123A>T",
            normalized_description="c.123A>T",
            normalized_dna="c.123A>T",
            normalized_rna="r.123a>u",
            normalized_protein="p.Ala41Val",
            genomic_coordinates={
                "chromosome": "chr1",
                "start": 12345,
                "end": 12345
            }
        )
        mock_mutalyzer_service.normalize_variant.return_value = mock_response
        
        request_data = {
            "variant_description": "c.123A>T",
            "target_format": "hgvs",
            "include_protein_description": True,
            "include_rna_description": True
        }
        
        response = client.post("/mutalyzer/normalize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["normalized_dna"] == "c.123A>T"
        assert data["normalized_rna"] == "r.123a>u"
        assert data["normalized_protein"] == "p.Ala41Val"
        assert "genomic_coordinates" in data
    
    @pytest.mark.asyncio
    async def test_normalize_invalid_variant(self, client, mock_mutalyzer_service):
        """Test normalizacji niepoprawnego wariantu"""
        
        mock_response = VariantNormalizationResponse(
            is_valid=False,
            original_description="invalid_variant",
            normalized_description=None,
            errors=[
                MutalyzerError(
                    error_type=ErrorType.SYNTAX_ERROR,
                    message="Invalid variant format"
                )
            ]
        )
        mock_mutalyzer_service.normalize_variant.return_value = mock_response
        
        request_data = {
            "variant_description": "invalid_variant"
        }
        
        response = client.post("/mutalyzer/normalize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["normalized_description"] is None
        assert len(data["errors"]) == 1


class TestBatchProcessingEndpoint:
    """Testy dla endpoint'a przetwarzania wsadowego"""
    
    @pytest.mark.asyncio
    async def test_batch_processing_valid_variants(self, client, mock_mutalyzer_service, valid_variant_examples):
        """Test przetwarzania wsadowego poprawnych wariantów"""
        
        # Mock odpowiedzi batch
        batch_results = []
        for example in valid_variant_examples:
            batch_results.append(
                VariantCheckResponse(
                    is_valid=True,
                    syntax_valid=True,
                    semantic_valid=True,
                    original_description=example["variant"],
                    normalized_description=example["variant"],
                    reference_found=True
                )
            )
        
        mock_batch_response = BatchVariantResponse(
            total_variants=len(valid_variant_examples),
            successful_variants=len(valid_variant_examples),
            failed_variants=0,
            results=batch_results,
            processing_time_ms=150.5
        )
        mock_mutalyzer_service.process_batch.return_value = mock_batch_response
        
        # Przygotuj request
        variants = [
            {"variant_description": example["variant"]}
            for example in valid_variant_examples
        ]
        
        request_data = {
            "variants": variants,
            "parallel_processing": True,
            "fail_fast": False
        }
        
        response = client.post("/mutalyzer/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_variants"] == len(valid_variant_examples)
        assert data["successful_variants"] == len(valid_variant_examples)
        assert data["failed_variants"] == 0
        assert len(data["results"]) == len(valid_variant_examples)
        assert data["processing_time_ms"] == 150.5
    
    @pytest.mark.asyncio
    async def test_batch_processing_mixed_variants(self, client, mock_mutalyzer_service):
        """Test przetwarzania wsadowego mieszanych wariantów (poprawne i niepoprawne)"""
        
        # Mock wyników: 2 poprawne, 1 niepoprawny
        batch_results = [
            VariantCheckResponse(
                is_valid=True,
                syntax_valid=True,
                semantic_valid=True,
                original_description="c.123A>T",
                normalized_description="c.123A>T",
                reference_found=True
            ),
            VariantCheckResponse(
                is_valid=False,
                syntax_valid=False,
                semantic_valid=False,
                original_description="invalid_variant",
                normalized_description=None,
                reference_found=False,
                errors=[
                    MutalyzerError(
                        error_type=ErrorType.SYNTAX_ERROR,
                        message="Invalid format"
                    )
                ]
            ),
            VariantCheckResponse(
                is_valid=True,
                syntax_valid=True,
                semantic_valid=True,
                original_description="g.456C>G",
                normalized_description="g.456C>G",
                reference_found=True
            )
        ]
        
        mock_batch_response = BatchVariantResponse(
            total_variants=3,
            successful_variants=2,
            failed_variants=1,
            results=batch_results,
            processing_time_ms=89.3
        )
        mock_mutalyzer_service.process_batch.return_value = mock_batch_response
        
        request_data = {
            "variants": [
                {"variant_description": "c.123A>T"},
                {"variant_description": "invalid_variant"},
                {"variant_description": "g.456C>G"}
            ]
        }
        
        response = client.post("/mutalyzer/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_variants"] == 3
        assert data["successful_variants"] == 2
        assert data["failed_variants"] == 1
        assert len(data["results"]) == 3
        
        # Sprawdź konkretne wyniki
        assert data["results"][0]["is_valid"] is True
        assert data["results"][1]["is_valid"] is False
        assert data["results"][2]["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_batch_processing_too_many_variants(self, client, mock_mutalyzer_service):
        """Test ograniczenia liczby wariantów w batch"""
        
        # Przygotuj za dużo wariantów (więcej niż 1000)
        variants = [
            {"variant_description": f"c.{i}A>T"}
            for i in range(1001)
        ]
        
        request_data = {
            "variants": variants
        }
        
        response = client.post("/mutalyzer/batch", json=request_data)
        
        # Pydantic validation powinno to złapać
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_batch_processing_empty_variants(self, client, mock_mutalyzer_service):
        """Test pustej listy wariantów"""
        
        request_data = {
            "variants": []
        }
        
        response = client.post("/mutalyzer/batch", json=request_data)
        
        # Pydantic validation - min_items=1
        assert response.status_code == 422


class TestStatsEndpoint:
    """Testy dla endpoint'a statystyk"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, client, mock_mutalyzer_service):
        """Test pobierania statystyk"""
        
        mock_cache_stats = {
            "size": 150,
            "max_size": 10000,
            "hits": 850,
            "misses": 200,
            "hit_rate": 0.81,
            "evictions": 5
        }
        
        mock_analytics_stats = {
            "total_requests": 1050,
            "successful_requests": 950,
            "failed_requests": 100,
            "success_rate": 0.905,
            "average_processing_time_ms": 45.6,
            "min_processing_time_ms": 12.3,
            "max_processing_time_ms": 234.5,
            "most_common_variant_types": {
                "substitution": 650,
                "deletion": 200,
                "insertion": 100
            },
            "most_common_error_types": {
                "syntax_error": 60,
                "semantic_error": 40
            },
            "uptime_hours": 48.5,
            "requests_per_hour": 21.6
        }
        
        mock_mutalyzer_service.get_cache_stats.return_value = mock_cache_stats
        mock_mutalyzer_service.get_analytics_summary.return_value = mock_analytics_stats
        
        response = client.get("/mutalyzer/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Mutalyzer API"
        assert data["status"] == "running"
        assert data["cache"] == mock_cache_stats
        assert data["analytics"] == mock_analytics_stats
    
    @pytest.mark.asyncio
    async def test_get_stats_service_error(self, client, mock_mutalyzer_service):
        """Test obsługi błędu podczas pobierania statystyk"""
        
        mock_mutalyzer_service.get_cache_stats.side_effect = Exception("Stats error")
        
        response = client.get("/mutalyzer/stats")
        
        assert response.status_code == 500


class TestAdminEndpoints:
    """Testy dla endpoints administracyjnych"""
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, client, mock_mutalyzer_service):
        """Test czyszczenia cache"""
        
        response = client.post("/mutalyzer/admin/clear-cache")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cleared successfully" in data["message"]
        
        mock_mutalyzer_service.clear_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_analytics(self, client, mock_mutalyzer_service):
        """Test resetowania analityki"""
        
        response = client.post("/mutalyzer/admin/reset-analytics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reset successfully" in data["message"]
        
        mock_mutalyzer_service.reset_analytics.assert_called_once()


class TestHealthCheckEndpoint:
    """Testy dla endpoint'a health check"""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client, mock_mutalyzer_service):
        """Test health check - serwis działa"""
        
        mock_health_response = VariantCheckResponse(
            is_valid=False,  # Nie ważne dla health check
            syntax_valid=True,  # To jest ważne
            semantic_valid=False,
            original_description="c.123A>T",
            timestamp=datetime.now()
        )
        mock_mutalyzer_service.check_variant.return_value = mock_health_response
        
        response = client.get("/mutalyzer/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Mutalyzer API"
        assert data["version"] == "1.0.0"
        assert data["checks"]["syntax_validation"] is True
        assert data["checks"]["service_reachable"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, client, mock_mutalyzer_service):
        """Test health check - serwis działa ale z problemami"""
        
        mock_health_response = VariantCheckResponse(
            is_valid=False,
            syntax_valid=False,  # Problem z walidacją składni
            semantic_valid=False,
            original_description="c.123A>T",
            timestamp=datetime.now()
        )
        mock_mutalyzer_service.check_variant.return_value = mock_health_response
        
        response = client.get("/mutalyzer/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["syntax_validation"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client, mock_mutalyzer_service):
        """Test health check - serwis nie działa"""
        
        mock_mutalyzer_service.check_variant.side_effect = Exception("Service down")
        
        response = client.get("/mutalyzer/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Service down" in data["error"]
        assert data["checks"]["syntax_validation"] is False
        assert data["checks"]["service_reachable"] is False


class TestVariantExamplesEndpoint:
    """Testy dla endpoint'a przykładów wariantów"""
    
    def test_get_all_examples(self, client):
        """Test pobierania wszystkich przykładów"""
        
        response = client.get("/mutalyzer/variants/examples")
        
        assert response.status_code == 200
        data = response.json()
        
        # Sprawdź strukturę
        assert "valid" in data
        assert "invalid_syntax" in data
        assert "invalid_semantic" in data
        assert "complex" in data
        
        # Sprawdź czy są przykłady
        assert len(data["valid"]) > 0
        assert len(data["invalid_syntax"]) > 0
        assert len(data["invalid_semantic"]) > 0
        assert len(data["complex"]) > 0
        
        # Sprawdź strukturę przykładów
        valid_example = data["valid"][0]
        assert "variant" in valid_example
        assert "description" in valid_example
        assert "type" in valid_example
    
    def test_get_examples_by_category(self, client):
        """Test pobierania przykładów według kategorii"""
        
        response = client.get("/mutalyzer/variants/examples?category=valid")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert len(data) == 1  # Tylko jedna kategoria
        assert len(data["valid"]) > 0
    
    def test_get_examples_invalid_category(self, client):
        """Test niepoprawnej kategorii"""
        
        response = client.get("/mutalyzer/variants/examples?category=nonexistent")
        
        assert response.status_code == 400
        assert "Unknown category" in response.json()["detail"]


class TestRootEndpoint:
    """Testy dla głównego endpoint'a"""
    
    def test_root_endpoint(self, client):
        """Test głównego endpoint'a informacyjnego"""
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Mutalyzer API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/mutalyzer/check" in data["endpoints"]["check_variant"]
        assert "/mutalyzer/normalize" in data["endpoints"]["normalize_variant"]
        assert "/mutalyzer/batch" in data["endpoints"]["batch_processing"]


# Test pokrycia funkcjonalności
class TestCoverageScenarios:
    """Testy różnych scenariuszy dla 100% pokrycia"""
    
    @pytest.mark.asyncio
    async def test_all_variant_types(self, client, mock_mutalyzer_service):
        """Test wszystkich typów wariantów"""
        
        variant_types = [
            ("c.123A>T", VariantType.SUBSTITUTION),
            ("c.123_124delAT", VariantType.DELETION),
            ("c.123_124insATGC", VariantType.INSERTION),
            ("c.123_124dupAT", VariantType.DUPLICATION),
            ("c.123_456inv", VariantType.INVERSION),
            ("c.[123A>T;456C>G]", VariantType.COMPLEX)
        ]
        
        for variant_desc, variant_type in variant_types:
            mock_response = VariantCheckResponse(
                is_valid=True,
                syntax_valid=True,
                semantic_valid=True,
                original_description=variant_desc,
                normalized_description=variant_desc,
                reference_found=True
            )
            mock_mutalyzer_service.check_variant.return_value = mock_response
            
            request_data = {"variant_description": variant_desc}
            response = client.post("/mutalyzer/check", json=request_data)
            
            assert response.status_code == 200
            assert response.json()["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_all_molecule_types(self, client, mock_mutalyzer_service):
        """Test wszystkich typów molekuł"""
        
        molecule_tests = [
            ("c.123A>T", MoleculeType.DNA),
            ("r.123a>u", MoleculeType.RNA),
            ("p.Ala123Val", MoleculeType.PROTEIN)
        ]
        
        for variant_desc, molecule_type in molecule_tests:
            mock_response = VariantCheckResponse(
                is_valid=True,
                syntax_valid=True,
                semantic_valid=True,
                original_description=variant_desc,
                normalized_description=variant_desc,
                reference_found=True
            )
            mock_mutalyzer_service.check_variant.return_value = mock_response
            
            request_data = {
                "variant_description": variant_desc,
                "molecule_type": molecule_type.value
            }
            response = client.post("/mutalyzer/check", json=request_data)
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_all_error_types(self, client, mock_mutalyzer_service):
        """Test wszystkich typów błędów"""
        
        error_types = [
            ErrorType.SYNTAX_ERROR,
            ErrorType.SEMANTIC_ERROR,
            ErrorType.REFERENCE_ERROR,
            ErrorType.MAPPING_ERROR,
            ErrorType.VALIDATION_ERROR
        ]
        
        for error_type in error_types:
            mock_response = VariantCheckResponse(
                is_valid=False,
                syntax_valid=False,
                semantic_valid=False,
                original_description="invalid_variant",
                normalized_description=None,
                reference_found=False,
                errors=[
                    MutalyzerError(
                        error_type=error_type,
                        message=f"Test error of type {error_type.value}"
                    )
                ]
            )
            mock_mutalyzer_service.check_variant.return_value = mock_response
            
            request_data = {"variant_description": "invalid_variant"}
            response = client.post("/mutalyzer/check", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is False
            assert data["errors"][0]["error_type"] == error_type.value