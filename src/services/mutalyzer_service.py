"""
Service layer dla API Mutalyzer z logiką biznesową
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, Counter

from ..api.clients.mutalyzer_client import MutalyzerClient, MutalyzerClientError
from ..models.mutalyzer import (
    VariantCheckRequest,
    VariantCheckResponse,
    VariantNormalizationRequest,
    VariantNormalizationResponse,
    BatchVariantRequest,
    BatchVariantResponse,
    MutalyzerError,
    ErrorType,
    VariantType
)


logger = logging.getLogger(__name__)


class MutalyzerCache:
    """Prosty cache w pamięci dla wyników Mutalyzer"""
    
    def __init__(self, max_size: int = 10000, ttl_hours: int = 24):
        self.cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _is_expired(self, timestamp: datetime) -> bool:
        return datetime.now() - timestamp > self.ttl
    
    def _cleanup_expired(self):
        """Usuwa wygasłe wpisy z cache"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.stats["evictions"] += 1
    
    def _evict_oldest(self):
        """Usuwa najstarsze wpisy jeśli cache jest pełen"""
        if self.max_size <= 0:
            # Jeśli max_size = 0, usuń wszystko
            evicted_count = len(self.cache)
            self.cache.clear()
            self.stats["evictions"] += evicted_count
            return
            
        if len(self.cache) >= self.max_size:
            # Usuń 20% najstarszych wpisów
            entries_to_remove = max(1, len(self.cache) // 5)
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1][1]  # sortuj po timestamp
            )
            
            for i in range(min(entries_to_remove, len(sorted_items))):
                key = sorted_items[i][0]
                del self.cache[key]
                self.stats["evictions"] += 1
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Pobiera wartość z cache"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                self.stats["hits"] += 1
                return value
            else:
                del self.cache[key]
        
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Dict[str, Any]):
        """Zapisuje wartość do cache"""
        self._cleanup_expired()
        
        # Jeśli max_size = 0, nie dodawaj nic do cache
        if self.max_size <= 0:
            self.stats["evictions"] += 1
            return
            
        self._evict_oldest()
        
        self.cache[key] = (value, datetime.now())
    
    def get_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki cache"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"]
        }


class MutalyzerAnalytics:
    """Analityka i statystyki dla Mutalyzer"""
    
    def __init__(self):
        self.reset_stats()
    
    def reset_stats(self):
        """Resetuje statystyki"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "processing_times": [],
            "variant_types": Counter(),
            "error_types": Counter(),
            "hourly_requests": defaultdict(int),
            "daily_requests": defaultdict(int),
            "start_time": datetime.now()
        }
    
    def record_request(
        self,
        variant_description: str,
        is_successful: bool,
        processing_time_ms: float,
        variant_type: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """Rejestruje statystyki requestu"""
        
        self.stats["total_requests"] += 1
        
        if is_successful:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        self.stats["processing_times"].append(processing_time_ms)
        
        if variant_type:
            self.stats["variant_types"][variant_type] += 1
        
        if error_type:
            self.stats["error_types"][error_type] += 1
        
        # Statystyki czasowe
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d %H:00")
        day_key = now.strftime("%Y-%m-%d")
        
        self.stats["hourly_requests"][hour_key] += 1
        self.stats["daily_requests"][day_key] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Zwraca podsumowanie statystyk"""
        
        processing_times = self.stats["processing_times"]
        
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            min_processing_time = min(processing_times)
            max_processing_time = max(processing_times)
        else:
            avg_processing_time = min_processing_time = max_processing_time = 0
        
        total = self.stats["total_requests"]
        success_rate = (
            self.stats["successful_requests"] / total if total > 0 else 0
        )
        
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            "total_requests": total,
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": success_rate,
            "average_processing_time_ms": avg_processing_time,
            "min_processing_time_ms": min_processing_time,
            "max_processing_time_ms": max_processing_time,
            "most_common_variant_types": dict(self.stats["variant_types"].most_common(5)),
            "most_common_error_types": dict(self.stats["error_types"].most_common(5)),
            "uptime_hours": uptime.total_seconds() / 3600,
            "requests_per_hour": total / (uptime.total_seconds() / 3600) if uptime.total_seconds() > 0 else 0
        }


class MutalyzerService:
    """
    Service layer dla Mutalyzer API
    Zawiera logikę biznesową, cache i analitykę
    """
    
    def __init__(
        self,
        client: Optional[MutalyzerClient] = None,
        enable_cache: bool = True,
        enable_analytics: bool = True
    ):
        self.client = client or MutalyzerClient()
        self.cache = MutalyzerCache() if enable_cache else None
        self.analytics = MutalyzerAnalytics() if enable_analytics else None
        
        logger.info("Inicjalizowano MutalyzerService")
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generuje klucz cache na podstawie metody i parametrów"""
        key_data = {"method": method, **kwargs}
        return json.dumps(key_data, sort_keys=True)
    
    def _record_analytics(
        self,
        variant_description: str,
        is_successful: bool,
        processing_time_ms: float,
        result: Optional[Dict[str, Any]] = None
    ):
        """Rejestruje statystyki analityczne"""
        
        if not self.analytics:
            return
        
        variant_type = None
        error_type = None
        
        if result:
            variant_info = result.get("variant_info", {})
            if variant_info:
                variant_type = variant_info.get("variant_type")
            
            errors = result.get("errors", [])
            if errors and len(errors) > 0:
                error_type = errors[0].get("error_type")
        
        self.analytics.record_request(
            variant_description,
            is_successful,
            processing_time_ms,
            variant_type,
            error_type
        )
    
    async def check_variant(self, request: VariantCheckRequest) -> VariantCheckResponse:
        """
        Sprawdza poprawność wariantu z wykorzystaniem cache i analityki
        """
        
        # Sprawdź cache
        cache_key = self._get_cache_key(
            "check_variant",
            variant_description=request.variant_description,
            reference_sequence=request.reference_sequence,
            check_syntax_only=request.check_syntax_only,
            normalize=request.normalize
        )
        
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit dla wariantu: {request.variant_description}")
                return VariantCheckResponse(**cached_result)
        
        # Wykonaj sprawdzenie
        try:
            result = await self.client.check_variant(
                variant_description=request.variant_description,
                reference_sequence=request.reference_sequence,
                check_syntax_only=request.check_syntax_only
            )
            
            # Dodaj dodatkowe przetwarzanie
            if request.normalize and result.get("is_valid"):
                try:
                    normalize_result = await self.client.normalize_variant(
                        request.variant_description
                    )
                    if normalize_result.get("is_valid"):
                        result["normalized_description"] = normalize_result.get("normalized_description")
                except Exception as e:
                    logger.warning(f"Błąd normalizacji: {e}")
            
            # Konwertuj na response model
            response_data = {
                **result,
                "syntax_valid": result.get("syntax_valid", result.get("is_valid", False)),
                "semantic_valid": result.get("semantic_valid", result.get("is_valid", False)),
                "reference_found": result.get("reference_found", True)
            }
            
            response = VariantCheckResponse(**response_data)
            
            # Zapisz do cache
            if self.cache:
                self.cache.set(cache_key, response_data)
            
            # Rejestruj analitykę
            self._record_analytics(
                request.variant_description,
                result.get("is_valid", False),
                result.get("processing_time_ms", 0),
                result
            )
            
            return response
            
        except MutalyzerClientError as e:
            logger.error(f"Błąd klienta Mutalyzer: {e}")
            
            error_response = VariantCheckResponse(
                is_valid=False,
                syntax_valid=False,
                semantic_valid=False,
                original_description=request.variant_description,
                errors=[
                    MutalyzerError(
                        error_type=e.error_type,
                        message=str(e)
                    )
                ]
            )
            
            # Rejestruj błąd w analityce
            self._record_analytics(
                request.variant_description,
                False,
                0,
                {"errors": [{"error_type": e.error_type.value}]}
            )
            
            return error_response
    
    async def normalize_variant(
        self, 
        request: VariantNormalizationRequest
    ) -> VariantNormalizationResponse:
        """
        Normalizuje wariant z wykorzystaniem cache i analityki
        """
        
        # Sprawdź cache
        cache_key = self._get_cache_key(
            "normalize_variant",
            variant_description=request.variant_description,
            target_format=request.target_format,
            include_protein_description=request.include_protein_description,
            include_rna_description=request.include_rna_description
        )
        
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit dla normalizacji: {request.variant_description}")
                return VariantNormalizationResponse(**cached_result)
        
        # Wykonaj normalizację
        try:
            result = await self.client.normalize_variant(
                variant_description=request.variant_description,
                target_format=request.target_format,
                include_protein=request.include_protein_description,
                include_rna=request.include_rna_description
            )
            
            response_data = {
                **result,
                "normalized_dna": result.get("normalized_dna") or result.get("normalized_description"),
                "normalized_rna": result.get("normalized_rna"),
                "normalized_protein": result.get("normalized_protein"),
                "genomic_coordinates": result.get("genomic_coordinates")
            }
            
            response = VariantNormalizationResponse(**response_data)
            
            # Zapisz do cache
            if self.cache:
                self.cache.set(cache_key, response_data)
            
            # Rejestruj analitykę
            self._record_analytics(
                request.variant_description,
                result.get("is_valid", False),
                result.get("processing_time_ms", 0),
                result
            )
            
            return response
            
        except MutalyzerClientError as e:
            logger.error(f"Błąd normalizacji Mutalyzer: {e}")
            
            error_response = VariantNormalizationResponse(
                is_valid=False,
                original_description=request.variant_description,
                errors=[
                    MutalyzerError(
                        error_type=e.error_type,
                        message=str(e)
                    )
                ]
            )
            
            return error_response
    
    async def process_batch(self, request: BatchVariantRequest) -> BatchVariantResponse:
        """
        Przetwarza wsadowo wiele wariantów
        """
        
        # Konwertuj na listę stringów
        variant_descriptions = [v.variant_description for v in request.variants]
        
        try:
            batch_result = await self.client.process_batch(
                variants=variant_descriptions,
                parallel=request.parallel_processing,
                fail_fast=request.fail_fast
            )
            
            # Konwertuj wyniki na response modele
            response_results = []
            for i, result in enumerate(batch_result["results"]):
                try:
                    response_data = {
                        **result,
                        "syntax_valid": result.get("syntax_valid", result.get("is_valid", False)),
                        "semantic_valid": result.get("semantic_valid", result.get("is_valid", False)),
                        "reference_found": result.get("reference_found", True)
                    }
                    response_results.append(VariantCheckResponse(**response_data))
                except Exception as e:
                    logger.warning(f"Błąd konwersji wyniku {i}: {e}")
                    response_results.append(
                        VariantCheckResponse(
                            is_valid=False,
                            syntax_valid=False,
                            semantic_valid=False,
                            original_description=variant_descriptions[i] if i < len(variant_descriptions) else "unknown",
                            errors=[
                                MutalyzerError(
                                    error_type=ErrorType.VALIDATION_ERROR,
                                    message=f"Błąd konwersji wyniku: {str(e)}"
                                )
                            ]
                        )
                    )
            
            response = BatchVariantResponse(
                total_variants=batch_result["total_variants"],
                successful_variants=batch_result["successful_variants"],
                failed_variants=batch_result["failed_variants"],
                results=response_results,
                processing_time_ms=batch_result["processing_time_ms"]
            )
            
            # Rejestruj analitykę dla każdego wariantu
            for i, result in enumerate(batch_result["results"]):
                if i < len(variant_descriptions):
                    self._record_analytics(
                        variant_descriptions[i],
                        isinstance(result, dict) and result.get("is_valid", False),
                        result.get("processing_time_ms", 0) if isinstance(result, dict) else 0,
                        result if isinstance(result, dict) else None
                    )
            
            return response
            
        except Exception as e:
            logger.error(f"Błąd przetwarzania wsadowego: {e}")
            
            # Zwróć błąd dla wszystkich wariantów
            failed_results = []
            for variant in request.variants:
                failed_results.append(
                    VariantCheckResponse(
                        is_valid=False,
                        syntax_valid=False,
                        semantic_valid=False,
                        original_description=variant.variant_description,
                        errors=[
                            MutalyzerError(
                                error_type=ErrorType.VALIDATION_ERROR,
                                message=str(e)
                            )
                        ]
                    )
                )
            
            return BatchVariantResponse(
                total_variants=len(request.variants),
                successful_variants=0,
                failed_variants=len(request.variants),
                results=failed_results,
                processing_time_ms=0
            )
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Zwraca statystyki cache"""
        return self.cache.get_stats() if self.cache else None
    
    def get_analytics_summary(self) -> Optional[Dict[str, Any]]:
        """Zwraca podsumowanie analityki"""
        return self.analytics.get_summary() if self.analytics else None
    
    def clear_cache(self):
        """Czyści cache"""
        if self.cache:
            self.cache.cache.clear()
            logger.info("Cache został wyczyszczony")
    
    def reset_analytics(self):
        """Resetuje analitykę"""
        if self.analytics:
            self.analytics.reset_stats()
            logger.info("Analityka została zresetowana")