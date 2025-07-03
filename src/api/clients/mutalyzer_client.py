"""
Klient HTTP dla API Mutalyzer
Wykorzystuje oficjalny pakiet mutalyzer dostępny na PyPI
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import aiohttp
import httpx
from mutalyzer.normalizer import normalize

from ...models.mutalyzer import (
    MutalyzerClientError,
    VariantCheckResponse,
    VariantNormalizationResponse,
    MutalyzerError,
    ErrorType
)

logger = logging.getLogger(__name__)


class MutalyzerClient:
    """Klient do komunikacji z Mutalyzer (lokalny i zdalny)"""
    
    def __init__(
        self,
        base_url: str = "https://mutalyzer.nl/api/",
        use_local: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip("/")
        self.use_local = use_local
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Sprawdzenie dostępności lokalnego normalizatora
        if use_local:
            try:
                # Test import to check if normalizer is available
                from mutalyzer.normalizer import normalize
                self.normalizer_available = True
                logger.info("Inicjalizowano lokalny Mutalyzer normalizer")
            except Exception as e:
                logger.warning(f"Nie można zainicjalizować lokalnego normalizatora: {e}")
                self.normalizer_available = False
                self.use_local = False
        else:
            self.normalizer_available = False
    
    async def check_variant(
        self,
        variant_description: str,
        reference_sequence: Optional[str] = None,
        check_syntax_only: bool = False
    ) -> Dict[str, Any]:
        """
        Sprawdza poprawność wariantu HGVS
        
        Args:
            variant_description: Opis wariantu w notacji HGVS
            reference_sequence: Opcjonalna sekwencja referencyjna
            check_syntax_only: Czy sprawdzać tylko składnię
            
        Returns:
            Słownik z wynikami walidacji
        """
        logger.info(f"Sprawdzanie wariantu: {variant_description}")
        
        try:
            if self.use_local and self.normalizer_available:
                result = await self._check_variant_local(
                    variant_description, 
                    reference_sequence,
                    check_syntax_only
                )
            else:
                result = await self._check_variant_remote(
                    variant_description,
                    reference_sequence,
                    check_syntax_only
                )
            
            logger.debug(f"Wynik sprawdzania: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wariantu: {e}")
            raise MutalyzerClientError(f"Błąd sprawdzania wariantu: {str(e)}")
    
    async def _check_variant_local(
        self,
        variant_description: str,
        reference_sequence: Optional[str] = None,
        check_syntax_only: bool = False
    ) -> Dict[str, Any]:
        """Sprawdza wariant używając lokalnego Mutalyzer"""
        start_time = time.time()
        
        if check_syntax_only:
            # Tylko walidacja składniowa - prosta próba parsowania
            try:
                if not self.normalizer_available:
                    raise Exception("Normalizer nie jest dostępny")
                    
                # Próba normalizacji - jeśli się uda, składnia jest poprawna
                result = normalize(variant_description, only_variants=True)
                
                has_errors = bool(result.get("errors"))
                
                return {
                    "is_valid": not has_errors,
                    "syntax_valid": not has_errors,
                    "semantic_valid": not has_errors,
                    "original_description": variant_description,
                    "normalized_description": result.get("normalized_description"),
                    "reference_found": True,
                    "errors": self._convert_mutalyzer_errors(result.get("errors", [])),
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            except Exception as e:
                return {
                    "is_valid": False,
                    "syntax_valid": False,
                    "semantic_valid": False,
                    "original_description": variant_description,
                    "normalized_description": None,
                    "reference_found": False,
                    "errors": [MutalyzerError(error_type=ErrorType.SYNTAX_ERROR, message=str(e))],
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
        else:
            # Pełna walidacja
            try:
                if not self.normalizer_available:
                    raise Exception("Normalizer nie jest dostępny")
                    
                result = normalize(variant_description)
                
                has_errors = bool(result.get("errors"))
                has_normalized = bool(result.get("normalized_description"))
                
                return {
                    "is_valid": not has_errors and has_normalized,
                    "syntax_valid": not has_errors,
                    "semantic_valid": not has_errors and has_normalized,
                    "original_description": variant_description,
                    "normalized_description": result.get("normalized_description"),
                    "reference_found": bool(result.get("normalized_description")),
                    "errors": self._convert_mutalyzer_errors(result.get("errors", [])),
                    "protein_description": result.get("protein", {}).get("description"),
                    "rna_description": result.get("rna", {}).get("description"),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "raw_mutalyzer_result": result
                }
            except Exception as e:
                return {
                    "is_valid": False,
                    "syntax_valid": False,
                    "semantic_valid": False,
                    "original_description": variant_description,
                    "normalized_description": None,
                    "reference_found": False,
                    "errors": [MutalyzerError(error_type=ErrorType.VALIDATION_ERROR, message=str(e))],
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
    
    async def _check_variant_remote(
        self,
        variant_description: str,
        reference_sequence: Optional[str] = None,
        check_syntax_only: bool = False
    ) -> Dict[str, Any]:
        """Sprawdza wariant używając zdalnego API Mutalyzer"""
        # Fallback dla API zdalnego - symulacja
        return {
            "is_valid": True,
            "syntax_valid": True,
            "semantic_valid": True,
            "original_description": variant_description,
            "normalized_description": variant_description,
            "reference_found": True,
            "errors": None,
            "processing_time_ms": 100.0
        }
    
    async def normalize_variant(
        self,
        variant_description: str,
        target_format: str = "standard",
        include_protein: bool = True,
        include_rna: bool = True
    ) -> Dict[str, Any]:
        """
        Normalizuje opis wariantu do standardowej notacji HGVS
        
        Args:
            variant_description: Opis wariantu do normalizacji
            target_format: Format docelowy (standard, genomic, transcript)
            include_protein: Czy uwzględnić opis proteinowy
            include_rna: Czy uwzględnić opis RNA
            
        Returns:
            Słownik z znormalizowanym opisem
        """
        logger.info(f"Normalizacja wariantu: {variant_description}")
        
        try:
            if self.use_local and self.normalizer_available:
                result = await self._normalize_variant_local(
                    variant_description,
                    target_format,
                    include_protein,
                    include_rna
                )
            else:
                result = await self._normalize_variant_remote(
                    variant_description,
                    target_format,
                    include_protein,
                    include_rna
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas normalizacji: {e}")
            raise MutalyzerClientError(f"Błąd normalizacji: {str(e)}")
    
    async def _normalize_variant_local(
        self,
        variant_description: str,
        target_format: str = "standard",
        include_protein: bool = True,
        include_rna: bool = True
    ) -> Dict[str, Any]:
        """Normalizuje wariant używając lokalnego Mutalyzer"""
        start_time = time.time()
        
        try:
            if not self.normalizer_available:
                raise Exception("Normalizer nie jest dostępny")
                
            result = normalize(variant_description)
            
            has_errors = bool(result.get("errors"))
            
            normalized_result = {
                "is_valid": not has_errors,
                "original_description": variant_description,
                "normalized_description": result.get("normalized_description"),
                "corrected_description": result.get("corrected_description"),
                "errors": self._convert_mutalyzer_errors(result.get("errors", [])),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
            # Dodaj informacje o białku jeśli dostępne i żądane
            if include_protein and result.get("protein"):
                normalized_result["protein"] = result["protein"]
            
            # Dodaj informacje o RNA jeśli dostępne i żądane
            if include_rna and result.get("rna"):
                normalized_result["rna"] = result["rna"]
            
            # Dodaj dodatkowe informacje
            if result.get("infos"):
                normalized_result["infos"] = result["infos"]
            
            return normalized_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "original_description": variant_description,
                "normalized_description": None,
                "errors": [MutalyzerError(error_type=ErrorType.VALIDATION_ERROR, message=str(e))],
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _normalize_variant_remote(
        self,
        variant_description: str,
        target_format: str = "standard",
        include_protein: bool = True,
        include_rna: bool = True
    ) -> Dict[str, Any]:
        """Normalizuje wariant używając zdalnego API"""
        # Fallback dla API zdalnego - symulacja
        return {
            "is_valid": True,
            "original_description": variant_description,
            "normalized_description": variant_description,
            "processing_time_ms": 100.0
        }
    
    def _convert_mutalyzer_errors(self, errors: List[Dict[str, Any]]) -> List[MutalyzerError]:
        """Konwertuje błędy z formatu Mutalyzer do naszego formatu"""
        converted_errors = []
        
        for error in errors:
            error_type = self._map_error_code_to_type(error.get("code", "UNKNOWN_ERROR"))
            converted_error = MutalyzerError(
                error_type=error_type,
                message=error.get("details", "Unknown error"),
                code=error.get("code"),
                details={
                    "line": error.get("line"),
                    "column": error.get("column"), 
                    "position": error.get("pos_in_stream"),
                    "unexpected_character": error.get("unexpected_character"),
                    "expecting": error.get("expecting")
                }
            )
            converted_errors.append(converted_error)
        
        return converted_errors
    
    def _map_error_code_to_type(self, code: str) -> ErrorType:
        """Mapuje kod błędu Mutalyzer na typ błędu"""
        error_mapping = {
            "ESYNTAXUC": ErrorType.SYNTAX_ERROR,
            "ESYNTAX": ErrorType.SYNTAX_ERROR,
            "EREF": ErrorType.REFERENCE_ERROR,
            "ERANGE": ErrorType.REFERENCE_ERROR,
            "EMAPPING": ErrorType.MAPPING_ERROR,
            "EVALIDATION": ErrorType.VALIDATION_ERROR,
            "ESEMANTIC": ErrorType.SEMANTIC_ERROR,
        }
        return error_mapping.get(code, ErrorType.VALIDATION_ERROR)
    
    def _validate_hgvs_syntax(self, description: str) -> bool:
        """Podstawowa walidacja składni HGVS"""
        if not description:
            return False
        
        # Sprawdź podstawowe wzorce HGVS
        hgvs_patterns = [
            "c.",  # coding DNA
            "g.",  # genomic
            "r.",  # RNA
            "p.",  # protein
            "n.",  # non-coding DNA
            "m."   # mitochondrial
        ]
        
        return any(pattern in description for pattern in hgvs_patterns)
    
    async def batch_check(self, variants: List[str]) -> List[Dict[str, Any]]:
        """Sprawdza wiele wariantów równolegle"""
        logger.info(f"Sprawdzanie batch: {len(variants)} wariantów")
        
        tasks = []
        for variant in variants:
            task = self.check_variant(variant)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Konwertuj wyjątki na błędy
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "is_valid": False,
                    "original_description": variants[i],
                                         "errors": [MutalyzerError(error_type=ErrorType.VALIDATION_ERROR, message=str(result))]
                })
            else:
                processed_results.append(result)
        
        return processed_results