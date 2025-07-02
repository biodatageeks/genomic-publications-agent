"""
FastAPI endpoints dla Mutalyzer API
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ...models.mutalyzer import (
    VariantCheckRequest,
    VariantCheckResponse, 
    VariantNormalizationRequest,
    VariantNormalizationResponse,
    BatchVariantRequest,
    BatchVariantResponse,
    MutalyzerError,
    ErrorType
)
from ...services.mutalyzer_service import MutalyzerService


logger = logging.getLogger(__name__)

# Router dla endpoints Mutalyzer
router = APIRouter(prefix="/mutalyzer", tags=["mutalyzer"])

# Singleton service instance
_mutalyzer_service: Optional[MutalyzerService] = None


def get_mutalyzer_service() -> MutalyzerService:
    """Dependency provider dla MutalyzerService"""
    global _mutalyzer_service
    if _mutalyzer_service is None:
        _mutalyzer_service = MutalyzerService()
    return _mutalyzer_service


@router.post(
    "/check", 
    response_model=VariantCheckResponse,
    summary="Sprawdź poprawność wariantu HGVS",
    description="""
    Sprawdza poprawność opisu wariantu według standardów HGVS.
    
    Endpoint obsługuje:
    - Walidację składni HGVS
    - Walidację semantyczną
    - Sprawdzenie dostępności sekwencji referencyjnej
    - Opcjonalną normalizację wariantu
    
    **Przykładowe warianty:**
    - `c.123A>T` - substytucja punktowa
    - `c.123_124delAT` - delecja
    - `c.123_124insATGC` - insercja
    - `g.12345C>T` - wariant genomowy
    """
)
async def check_variant(
    request: VariantCheckRequest,
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> VariantCheckResponse:
    """Sprawdza poprawność wariantu HGVS"""
    
    try:
        logger.info(f"Sprawdzanie wariantu: {request.variant_description}")
        
        response = await service.check_variant(request)
        
        logger.info(
            f"Wynik sprawdzenia {request.variant_description}: "
            f"valid={response.is_valid}, "
            f"syntax_valid={response.syntax_valid}, "
            f"semantic_valid={response.semantic_valid}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania wariantu {request.variant_description}: {e}")
        
        # Zwróć structured error response
        error_response = VariantCheckResponse(
            is_valid=False,
            syntax_valid=False,
            semantic_valid=False,
            original_description=request.variant_description,
            errors=[
                MutalyzerError(
                    error_type=ErrorType.VALIDATION_ERROR,
                    message=f"Unexpected error: {str(e)}"
                )
            ]
        )
        
        return error_response


@router.post(
    "/normalize",
    response_model=VariantNormalizationResponse,
    summary="Znormalizuj opis wariantu",
    description="""
    Normalizuje opis wariantu do standardowego formatu HGVS.
    
    Endpoint może zwrócić:
    - Znormalizowany opis DNA
    - Opis RNA (jeśli dostępny)
    - Opis białka (jeśli dostępny)
    - Koordynaty genomowe
    
    **Opcje normalizacji:**
    - `target_format`: docelowy format (domyślnie 'hgvs')
    - `include_protein_description`: czy uwzględnić opis białka
    - `include_rna_description`: czy uwzględnić opis RNA
    """
)
async def normalize_variant(
    request: VariantNormalizationRequest,
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> VariantNormalizationResponse:
    """Normalizuje wariant do standardowego formatu HGVS"""
    
    try:
        logger.info(f"Normalizacja wariantu: {request.variant_description}")
        
        response = await service.normalize_variant(request)
        
        logger.info(
            f"Wynik normalizacji {request.variant_description}: "
            f"valid={response.is_valid}, "
            f"normalized={response.normalized_description}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Błąd podczas normalizacji wariantu {request.variant_description}: {e}")
        
        error_response = VariantNormalizationResponse(
            is_valid=False,
            original_description=request.variant_description,
            errors=[
                MutalyzerError(
                    error_type=ErrorType.VALIDATION_ERROR,
                    message=f"Unexpected error: {str(e)}"
                )
            ]
        )
        
        return error_response


@router.post(
    "/batch",
    response_model=BatchVariantResponse,
    summary="Przetwarzaj wiele wariantów jednocześnie",
    description="""
    Przetwarza wiele wariantów jednocześnie w trybie wsadowym.
    
    **Opcje przetwarzania:**
    - `parallel_processing`: przetwarzanie równoległe (szybsze)
    - `fail_fast`: zatrzymanie na pierwszym błędzie
    
    **Limity:**
    - Maksymalnie 1000 wariantów na request
    - Timeout: 300 sekund
    
    **Przykład użycia:**
    Idealny do walidacji większych zbiorów wariantów z plików VCF lub list wariantów.
    """
)
async def process_batch(
    request: BatchVariantRequest,
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> BatchVariantResponse:
    """Przetwarza wiele wariantów jednocześnie"""
    
    try:
        logger.info(f"Przetwarzanie wsadowe {len(request.variants)} wariantów")
        
        response = await service.process_batch(request)
        
        logger.info(
            f"Wynik przetwarzania wsadowego: "
            f"total={response.total_variants}, "
            f"successful={response.successful_variants}, "
            f"failed={response.failed_variants}, "
            f"time={response.processing_time_ms:.2f}ms"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wsadowego: {e}")
        
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
                            message=f"Batch processing error: {str(e)}"
                        )
                    ]
                )
            )
        
        error_response = BatchVariantResponse(
            total_variants=len(request.variants),
            successful_variants=0,
            failed_variants=len(request.variants),
            results=failed_results,
            processing_time_ms=0
        )
        
        return error_response


@router.get(
    "/stats",
    summary="Statystyki serwisu Mutalyzer",
    description="""
    Zwraca statystyki działania serwisu Mutalyzer.
    
    **Zawiera:**
    - Statystyki cache (współczynnik trafień, rozmiar)
    - Analitykę requestów (liczba, czas przetwarzania, typy błędów)
    - Najpopularniejsze typy wariantów
    - Wydajność systemu
    """
)
async def get_stats(
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> Dict[str, Any]:
    """Zwraca statystyki serwisu"""
    
    try:
        cache_stats = service.get_cache_stats()
        analytics_stats = service.get_analytics_summary()
        
        stats = {
            "service": "Mutalyzer API",
            "status": "running",
            "cache": cache_stats,
            "analytics": analytics_stats
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statystyk: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stats: {str(e)}"
        )


@router.post(
    "/admin/clear-cache",
    summary="Wyczyść cache (admin)",
    description="Czyści cache serwisu. Operacja administracyjna."
)
async def clear_cache(
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> Dict[str, str]:
    """Czyści cache serwisu"""
    
    try:
        service.clear_cache()
        logger.info("Cache został wyczyszczony przez administratora")
        
        return {"status": "success", "message": "Cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )


@router.post(
    "/admin/reset-analytics",
    summary="Resetuj analitykę (admin)",
    description="Resetuje statystyki analityczne. Operacja administracyjna."
)
async def reset_analytics(
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> Dict[str, str]:
    """Resetuje analitykę serwisu"""
    
    try:
        service.reset_analytics()
        logger.info("Analityka została zresetowana przez administratora")
        
        return {"status": "success", "message": "Analytics reset successfully"}
        
    except Exception as e:
        logger.error(f"Błąd podczas resetowania analityki: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting analytics: {str(e)}"
        )


@router.get(
    "/health",
    summary="Sprawdzenie stanu serwisu",
    description="Endpoint do sprawdzania stanu zdrowia serwisu Mutalyzer."
)
async def health_check(
    service: MutalyzerService = Depends(get_mutalyzer_service)
) -> Dict[str, Any]:
    """Sprawdzenie stanu zdrowia serwisu"""
    
    try:
        # Prosta walidacja działania serwisu
        test_request = VariantCheckRequest(
            variant_description="c.123A>T",
            check_syntax_only=True
        )
        
        test_response = await service.check_variant(test_request)
        
        # Sprawdź czy podstawowe funkcje działają
        health_status = {
            "status": "healthy" if test_response.syntax_valid else "degraded",
            "service": "Mutalyzer API",
            "version": "1.0.0",
            "timestamp": test_response.timestamp.isoformat(),
            "checks": {
                "syntax_validation": test_response.syntax_valid,
                "service_reachable": True
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        return {
            "status": "unhealthy",
            "service": "Mutalyzer API", 
            "version": "1.0.0",
            "error": str(e),
            "checks": {
                "syntax_validation": False,
                "service_reachable": False
            }
        }


@router.get(
    "/variants/examples",
    summary="Przykładowe warianty HGVS",
    description="""
    Zwraca przykładowe warianty HGVS do testowania.
    
    **Kategorie:**
    - `valid`: poprawne warianty do testowania pozytywnego
    - `invalid_syntax`: niepoprawna składnia do testowania negatywnego
    - `invalid_semantic`: błędy semantyczne
    - `complex`: złożone przypadki
    """
)
async def get_variant_examples(
    category: Optional[str] = Query(
        None, 
        description="Kategoria przykładów: valid, invalid_syntax, invalid_semantic, complex"
    )
) -> Dict[str, List[Dict[str, str]]]:
    """Zwraca przykładowe warianty HGVS"""
    
    examples = {
        "valid": [
            {
                "variant": "c.123A>T",
                "description": "Substytucja punktowa w cDNA",
                "type": "substitution"
            },
            {
                "variant": "c.123_124delAT",
                "description": "Delecja dwóch nukleotydów",
                "type": "deletion"
            },
            {
                "variant": "c.123_124insATGC",
                "description": "Insercja czterech nukleotydów",
                "type": "insertion"
            },
            {
                "variant": "g.12345C>T",
                "description": "Wariant genomowy",
                "type": "substitution"
            },
            {
                "variant": "p.Arg123Cys",
                "description": "Zmiana aminokwasu w białku",
                "type": "protein_substitution"
            }
        ],
        "invalid_syntax": [
            {
                "variant": "c123A>T",
                "description": "Brak kropki po prefiksie",
                "error": "Missing dot after prefix"
            },
            {
                "variant": "c.123A>>T",
                "description": "Podwójny znak substytucji",
                "error": "Invalid substitution syntax"
            },
            {
                "variant": "c.123_124del",
                "description": "Brak informacji o deletowanych nukleotydach",
                "error": "Missing deleted sequence"
            }
        ],
        "invalid_semantic": [
            {
                "variant": "c.999999A>T",
                "description": "Pozycja poza zakresem sekwencji",
                "error": "Position out of range"
            },
            {
                "variant": "c.123X>T",
                "description": "Nieprawidłowy nukleotyd referencyjny",
                "error": "Invalid reference nucleotide"
            }
        ],
        "complex": [
            {
                "variant": "c.[123A>T;456C>G]",
                "description": "Wiele wariantów w allelu",
                "type": "complex_allele"
            },
            {
                "variant": "c.123_456del234insATGC",
                "description": "Delecja z insercją (delins)",
                "type": "delins"
            },
            {
                "variant": "c.123+1G>T",
                "description": "Wariant w intronie",
                "type": "intronic"
            }
        ]
    }
    
    if category:
        if category in examples:
            return {category: examples[category]}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown category: {category}. Available: {list(examples.keys())}"
            )
    
    return examples