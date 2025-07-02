"""
Testy jednostkowe dla MutalyzerService
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.mutalyzer_service import (
    MutalyzerService,
    MutalyzerCache,
    MutalyzerAnalytics
)
from src.api.clients.mutalyzer_client import MutalyzerClient, MutalyzerClientError
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


class TestMutalyzerCache:
    """Testy dla cache systemu"""
    
    def test_cache_init(self):
        """Test inicjalizacji cache"""
        cache = MutalyzerCache(max_size=100, ttl_hours=12)
        
        assert cache.max_size == 100
        assert cache.ttl == timedelta(hours=12)
        assert len(cache.cache) == 0
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 0
        assert cache.stats["evictions"] == 0
    
    def test_cache_set_get(self):
        """Test podstawowego set/get"""
        cache = MutalyzerCache()
        
        test_data = {"result": "valid", "normalized": "c.123A>T"}
        cache.set("test_key", test_data)
        
        result = cache.get("test_key")
        assert result == test_data
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0
    
    def test_cache_miss(self):
        """Test miss w cache"""
        cache = MutalyzerCache()
        
        result = cache.get("nonexistent_key")
        assert result is None
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 1
    
    def test_cache_expiration(self):
        """Test wygasania wpisów w cache"""
        cache = MutalyzerCache(ttl_hours=0)  # Natychmiastowe wygasanie
        
        test_data = {"result": "valid"}
        cache.set("test_key", test_data)
        
        # Powinno wygasnąć natychmiast
        result = cache.get("test_key")
        assert result is None
        assert cache.stats["misses"] == 1
    
    def test_cache_eviction(self):
        """Test usuwania najstarszych wpisów"""
        cache = MutalyzerCache(max_size=3)
        
        # Dodaj 5 wpisów (więcej niż max_size)
        for i in range(5):
            cache.set(f"key_{i}", {"data": i})
        
        # Sprawdź czy niektóre zostały usunięte
        assert len(cache.cache) <= 3
        assert cache.stats["evictions"] > 0
    
    def test_cache_cleanup_expired(self):
        """Test czyszczenia wygasłych wpisów"""
        cache = MutalyzerCache()
        
        # Dodaj wpis i ręcznie ustaw stary timestamp
        old_time = datetime.now() - timedelta(hours=25)  # Starszy niż TTL
        cache.cache["old_key"] = ({"data": "old"}, old_time)
        cache.cache["new_key"] = ({"data": "new"}, datetime.now())
        
        # Próba pobrania powinno wyczyścić stary wpis
        cache._cleanup_expired()
        
        assert "old_key" not in cache.cache
        assert "new_key" in cache.cache
    
    def test_cache_stats(self):
        """Test statystyk cache"""
        cache = MutalyzerCache()
        
        # Wykonaj operacje
        cache.set("key1", {"data": 1})
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.get_stats()
        
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestMutalyzerAnalytics:
    """Testy dla systemu analityki"""
    
    def test_analytics_init(self):
        """Test inicjalizacji analityki"""
        analytics = MutalyzerAnalytics()
        
        assert analytics.stats["total_requests"] == 0
        assert analytics.stats["successful_requests"] == 0
        assert analytics.stats["failed_requests"] == 0
        assert len(analytics.stats["processing_times"]) == 0
        assert isinstance(analytics.stats["start_time"], datetime)
    
    def test_record_successful_request(self):
        """Test rejestrowania udanego requestu"""
        analytics = MutalyzerAnalytics()
        
        analytics.record_request(
            variant_description="c.123A>T",
            is_successful=True,
            processing_time_ms=45.6,
            variant_type="substitution"
        )
        
        assert analytics.stats["total_requests"] == 1
        assert analytics.stats["successful_requests"] == 1
        assert analytics.stats["failed_requests"] == 0
        assert analytics.stats["processing_times"] == [45.6]
        assert analytics.stats["variant_types"]["substitution"] == 1
    
    def test_record_failed_request(self):
        """Test rejestrowania nieudanego requestu"""
        analytics = MutalyzerAnalytics()
        
        analytics.record_request(
            variant_description="invalid",
            is_successful=False,
            processing_time_ms=12.3,
            error_type="syntax_error"
        )
        
        assert analytics.stats["total_requests"] == 1
        assert analytics.stats["successful_requests"] == 0
        assert analytics.stats["failed_requests"] == 1
        assert analytics.stats["error_types"]["syntax_error"] == 1
    
    def test_analytics_summary(self):
        """Test generowania podsumowania"""
        analytics = MutalyzerAnalytics()
        
        # Dodaj dane testowe
        analytics.record_request("c.123A>T", True, 45.6, "substitution")
        analytics.record_request("c.456C>G", True, 67.8, "substitution")
        analytics.record_request("invalid", False, 23.4, None, "syntax_error")
        
        summary = analytics.get_summary()
        
        assert summary["total_requests"] == 3
        assert summary["successful_requests"] == 2
        assert summary["failed_requests"] == 1
        assert summary["success_rate"] == 2/3
        assert summary["average_processing_time_ms"] == (45.6 + 67.8 + 23.4) / 3
        assert summary["min_processing_time_ms"] == 23.4
        assert summary["max_processing_time_ms"] == 67.8
        assert summary["most_common_variant_types"]["substitution"] == 2
        assert summary["most_common_error_types"]["syntax_error"] == 1
    
    def test_reset_stats(self):
        """Test resetowania statystyk"""
        analytics = MutalyzerAnalytics()
        
        # Dodaj dane
        analytics.record_request("c.123A>T", True, 45.6)
        
        # Reset
        analytics.reset_stats()
        
        assert analytics.stats["total_requests"] == 0
        assert analytics.stats["successful_requests"] == 0
        assert len(analytics.stats["processing_times"]) == 0


class TestMutalyzerService:
    """Testy dla głównego serwisu"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock klienta Mutalyzer"""
        return AsyncMock(spec=MutalyzerClient)
    
    @pytest.fixture
    def service(self, mock_client):
        """Service z mock klientem"""
        return MutalyzerService(
            client=mock_client,
            enable_cache=True,
            enable_analytics=True
        )
    
    @pytest.fixture
    def service_no_cache(self, mock_client):
        """Service bez cache"""
        return MutalyzerService(
            client=mock_client,
            enable_cache=False,
            enable_analytics=False
        )
    
    @pytest.mark.asyncio
    async def test_check_variant_success(self, service, mock_client):
        """Test udanego sprawdzania wariantu"""
        
        # Mock odpowiedzi klienta
        mock_client_response = {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T",
            "reference_found": True,
            "processing_time_ms": 45.6
        }
        
        async def mock_check(*args, **kwargs):
            return mock_client_response
        
        mock_client.check_variant.side_effect = mock_check
        
        # Request without normalization to avoid complexity
        request = VariantCheckRequest(
            variant_description="c.123A>T",
            normalize=False  # Disable normalization to simplify the test
        )
        response = await service.check_variant(request)
        
        # Sprawdź odpowiedź
        assert response.is_valid is True
        assert response.syntax_valid is True
        assert response.semantic_valid is True
        assert response.original_description == "c.123A>T"
        
        # Sprawdź wywołanie klienta
        mock_client.check_variant.assert_called_once()
        
        # Sprawdź analitykę
        assert service.analytics.stats["total_requests"] == 1
        assert service.analytics.stats["successful_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_check_variant_with_cache(self, service, mock_client):
        """Test sprawdzania wariantu z wykorzystaniem cache"""
        
        mock_client_response = {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T",
            "reference_found": True,
            "processing_time_ms": 45.6
        }
        
        async def mock_check(*args, **kwargs):
            return mock_client_response
        
        mock_client.check_variant.side_effect = mock_check
        
        request = VariantCheckRequest(
            variant_description="c.123A>T",
            normalize=False  # Disable normalization to simplify the test
        )
        
        # Pierwsze wywołanie - powinno trafić do klienta
        response1 = await service.check_variant(request)
        assert mock_client.check_variant.call_count == 1
        
        # Drugie wywołanie - powinno trafić z cache
        response2 = await service.check_variant(request)
        assert mock_client.check_variant.call_count == 1  # Nie powinno wzrosnąć
        
        # Sprawdź statystyki cache
        cache_stats = service.get_cache_stats()
        assert cache_stats["hits"] == 1
        assert cache_stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_check_variant_client_error(self, service, mock_client):
        """Test obsługi błędu klienta"""
        
        mock_client.check_variant.side_effect = MutalyzerClientError(
            "Client error", ErrorType.VALIDATION_ERROR
        )
        
        request = VariantCheckRequest(variant_description="c.123A>T")
        response = await service.check_variant(request)
        
        assert response.is_valid is False
        assert len(response.errors) == 1
        assert response.errors[0].error_type == ErrorType.VALIDATION_ERROR
        
        # Sprawdź analitykę
        assert service.analytics.stats["failed_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_normalize_variant_success(self, service, mock_client):
        """Test udanej normalizacji"""
        
        mock_client_response = {
            "is_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T",
            "normalized_dna": "c.123A>T",
            "normalized_protein": "p.Ala41Val",
            "processing_time_ms": 67.8
        }
        mock_client.normalize_variant.return_value = mock_client_response
        
        request = VariantNormalizationRequest(
            variant_description="c.123A>T",
            include_protein_description=True
        )
        response = await service.normalize_variant(request)
        
        assert response.is_valid is True
        assert response.normalized_dna == "c.123A>T"
        assert response.normalized_protein == "p.Ala41Val"
        
        # Sprawdź wywołanie klienta
        mock_client.normalize_variant.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_normalize_variant_with_cache(self, service, mock_client):
        """Test normalizacji z cache"""
        
        mock_client_response = {
            "is_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T",
            "normalized_dna": "c.123A>T",
            "processing_time_ms": 67.8
        }
        mock_client.normalize_variant.return_value = mock_client_response
        
        request = VariantNormalizationRequest(variant_description="c.123A>T")
        
        # Pierwsze wywołanie
        await service.normalize_variant(request)
        assert mock_client.normalize_variant.call_count == 1
        
        # Drugie wywołanie - z cache
        await service.normalize_variant(request)
        assert mock_client.normalize_variant.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self, service, mock_client):
        """Test udanego przetwarzania wsadowego"""
        
        mock_client_response = {
            "total_variants": 2,
            "successful_variants": 2,
            "failed_variants": 0,
            "results": [
                {
                    "is_valid": True,
                    "syntax_valid": True,
                    "semantic_valid": True,
                    "original_description": "c.123A>T",
                    "normalized_description": "c.123A>T",
                    "reference_found": True
                },
                {
                    "is_valid": True,
                    "syntax_valid": True,
                    "semantic_valid": True,
                    "original_description": "c.456C>G",
                    "normalized_description": "c.456C>G",
                    "reference_found": True
                }
            ],
            "processing_time_ms": 123.4
        }
        mock_client.process_batch.return_value = mock_client_response
        
        # Przygotuj request
        variants = [
            {"variant_description": "c.123A>T"},
            {"variant_description": "c.456C>G"}
        ]
        request = BatchVariantRequest(variants=variants)
        
        response = await service.process_batch(request)
        
        assert response.total_variants == 2
        assert response.successful_variants == 2
        assert response.failed_variants == 0
        assert len(response.results) == 2
        
        # Sprawdź analitykę - powinny być 2 wpisy
        assert service.analytics.stats["total_requests"] == 2
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, service, mock_client):
        """Test przetwarzania wsadowego z błędami"""
        
        mock_client.process_batch.side_effect = Exception("Batch error")
        
        variants = [{"variant_description": "c.123A>T"}]
        request = BatchVariantRequest(variants=variants)
        
        response = await service.process_batch(request)
        
        assert response.total_variants == 1
        assert response.successful_variants == 0
        assert response.failed_variants == 1
        assert len(response.results) == 1
        assert response.results[0].is_valid is False
    
    def test_get_cache_stats(self, service):
        """Test pobierania statystyk cache"""
        stats = service.get_cache_stats()
        
        assert stats is not None
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats
    
    def test_get_cache_stats_no_cache(self, service_no_cache):
        """Test pobierania statystyk gdy cache wyłączony"""
        stats = service_no_cache.get_cache_stats()
        assert stats is None
    
    def test_get_analytics_summary(self, service):
        """Test pobierania podsumowania analityki"""
        summary = service.get_analytics_summary()
        
        assert summary is not None
        assert "total_requests" in summary
        assert "success_rate" in summary
    
    def test_get_analytics_summary_no_analytics(self, service_no_cache):
        """Test pobierania analityki gdy wyłączona"""
        summary = service_no_cache.get_analytics_summary()
        assert summary is None
    
    def test_clear_cache(self, service):
        """Test czyszczenia cache"""
        # Dodaj coś do cache
        service.cache.set("test", {"data": "test"})
        assert len(service.cache.cache) == 1
        
        # Wyczyść
        service.clear_cache()
        assert len(service.cache.cache) == 0
    
    def test_reset_analytics(self, service):
        """Test resetowania analityki"""
        # Dodaj dane
        service.analytics.record_request("c.123A>T", True, 45.6)
        assert service.analytics.stats["total_requests"] == 1
        
        # Reset
        service.reset_analytics()
        assert service.analytics.stats["total_requests"] == 0
    
    def test_get_cache_key_generation(self, service):
        """Test generowania kluczy cache"""
        
        key1 = service._get_cache_key(
            "check_variant",
            variant_description="c.123A>T",
            check_syntax_only=False
        )
        
        key2 = service._get_cache_key(
            "check_variant",
            variant_description="c.123A>T",
            check_syntax_only=True
        )
        
        # Różne parametry = różne klucze
        assert key1 != key2
        
        key3 = service._get_cache_key(
            "check_variant",
            variant_description="c.123A>T",
            check_syntax_only=False
        )
        
        # Te same parametry = ten sam klucz
        assert key1 == key3
    
    @pytest.mark.asyncio
    async def test_check_variant_with_normalization(self, service, mock_client):
        """Test sprawdzania wariantu z dodatkową normalizacją"""
        
        # Mock odpowiedzi sprawdzania
        mock_check_response = {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": None,  # Brak normalizacji
            "reference_found": True,
            "processing_time_ms": 45.6
        }
        
        # Mock odpowiedzi normalizacji
        mock_normalize_response = {
            "is_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T"
        }
        
        # Configure async mocks to return actual values
        async def mock_check(*args, **kwargs):
            return mock_check_response
        
        async def mock_normalize(*args, **kwargs):
            return mock_normalize_response
        
        mock_client.check_variant.side_effect = mock_check
        mock_client.normalize_variant.side_effect = mock_normalize
        
        request = VariantCheckRequest(
            variant_description="c.123A>T",
            normalize=True
        )
        
        response = await service.check_variant(request)
        
        # Sprawdź czy oba wywołania zostały wykonane
        mock_client.check_variant.assert_called_once()
        mock_client.normalize_variant.assert_called_once()
        
        # Sprawdź czy normalizacja została dodana
        assert response.normalized_description == "c.123A>T"


class TestMutalyzerServiceEdgeCases:
    """Testy przypadków brzegowych"""
    
    @pytest.fixture
    def service(self):
        mock_client = AsyncMock(spec=MutalyzerClient)
        return MutalyzerService(client=mock_client)
    
    @pytest.mark.asyncio
    async def test_check_variant_normalization_error(self, service):
        """Test błędu podczas dodatkowej normalizacji"""
        
        # Mock sprawdzania - sukces
        mock_check_response = {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": None,
            "reference_found": True,
            "processing_time_ms": 45.6
        }
        
        service.client.check_variant.return_value = mock_check_response
        service.client.normalize_variant.side_effect = Exception("Normalization error")
        
        request = VariantCheckRequest(
            variant_description="c.123A>T",
            normalize=True
        )
        
        # Nie powinno rzucić wyjątku, tylko zalogować warning
        response = await service.check_variant(request)
        
        assert response.is_valid is True
        # Normalizacja nie powinna być dodana ze względu na błąd
        assert response.normalized_description is None
    
    def test_analytics_record_without_optional_params(self):
        """Test rejestrowania analityki bez opcjonalnych parametrów"""
        analytics = MutalyzerAnalytics()
        
        analytics.record_request(
            variant_description="c.123A>T",
            is_successful=True,
            processing_time_ms=45.6
            # Brak variant_type i error_type
        )
        
        assert analytics.stats["total_requests"] == 1
        assert analytics.stats["successful_requests"] == 1
        # Counters powinny pozostać puste
        assert len(analytics.stats["variant_types"]) == 0
        assert len(analytics.stats["error_types"]) == 0
    
    def test_cache_with_zero_max_size(self):
        """Test cache z maksymalnym rozmiarem 0"""
        cache = MutalyzerCache(max_size=0)
        
        cache.set("key", {"data": "value"})
        
        # Wszystko powinno zostać natychmiast usunięte
        assert len(cache.cache) == 0
        assert cache.stats["evictions"] > 0
    
    def test_analytics_summary_empty(self):
        """Test podsumowania analityki bez danych"""
        analytics = MutalyzerAnalytics()
        
        summary = analytics.get_summary()
        
        assert summary["total_requests"] == 0
        assert summary["success_rate"] == 0
        assert summary["average_processing_time_ms"] == 0
        assert summary["min_processing_time_ms"] == 0
        assert summary["max_processing_time_ms"] == 0


class TestMutalyzerServiceIntegration:
    """Testy integracyjne różnych komponentów"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_cache_and_analytics(self):
        """Test pełnego workflow z cache i analityką"""
        
        # Mock klient
        mock_client = AsyncMock(spec=MutalyzerClient)
        mock_response = {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": "c.123A>T",
            "normalized_description": "c.123A>T",
            "reference_found": True,
            "processing_time_ms": 45.6
        }
        
        async def mock_check(*args, **kwargs):
            return mock_response
        
        mock_client.check_variant.side_effect = mock_check
        
        service = MutalyzerService(
            client=mock_client,
            enable_cache=True,
            enable_analytics=True
        )
        
        request = VariantCheckRequest(
            variant_description="c.123A>T",
            normalize=False  # Disable normalization to simplify the test
        )
        
        # Pierwsz wywołanie
        response1 = await service.check_variant(request)
        assert response1.is_valid is True
        
        # Sprawdź statystyki
        cache_stats = service.get_cache_stats()
        analytics_summary = service.get_analytics_summary()
        
        assert cache_stats["misses"] == 1
        assert cache_stats["hits"] == 0
        assert analytics_summary["total_requests"] == 1
        assert analytics_summary["successful_requests"] == 1
        
        # Drugie wywołanie (z cache)
        response2 = await service.check_variant(request)
        assert response2.is_valid is True
        
        # Sprawdź statystyki po drugim wywołaniu
        cache_stats = service.get_cache_stats()
        assert cache_stats["hits"] == 1  # Wzrost o 1
        
        # Klient powinien być wywołany tylko raz
        assert mock_client.check_variant.call_count == 1