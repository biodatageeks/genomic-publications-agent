"""
Klient HTTP dla API Mutalyzer
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import logging

import aiohttp
import httpx
from mutalyzer.normalizer import normalize

from ...models.mutalyzer import (
    MutalyzerError,
    ErrorType,
    VariantInfo,
    TranscriptInfo,
    ProteinInfo,
    VariantType
)


logger = logging.getLogger(__name__)


class MutalyzerClientError(Exception):
    """Wyjątek klienta Mutalyzer"""
    def __init__(self, message: str, error_type: ErrorType = ErrorType.VALIDATION_ERROR):
        super().__init__(message)
        self.error_type = error_type


class MutalyzerClient:
    """
    Klient HTTP dla komunikacji z API Mutalyzer
    Wspiera zarówno lokalne mutalyzer jak i zdalny serwis
    """
    
    def __init__(
        self,
        base_url: str = "https://mutalyzer.nl/api/v1",
        timeout: int = 30,
        max_retries: int = 3,
        use_local: bool = True
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_local = use_local
        
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
    
    async def check_variant(
        self,
        variant_description: str,
        reference_sequence: Optional[str] = None,
        check_syntax_only: bool = False
    ) -> Dict[str, Any]:
        """
        Sprawdza poprawność opisu wariantu
        """
        start_time = time.time()
        
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
            
            processing_time = (time.time() - start_time) * 1000
            result["processing_time_ms"] = processing_time
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wariantu {variant_description}: {e}")
            raise MutalyzerClientError(
                f"Błąd sprawdzania wariantu: {str(e)}",
                ErrorType.VALIDATION_ERROR
            )
    
    async def _check_variant_local(
        self,
        variant_description: str,
        reference_sequence: Optional[str],
        check_syntax_only: bool
    ) -> Dict[str, Any]:
        """Sprawdzenie wariantu używając lokalnego normalizatora"""
        
        try:
            # Sprawdzenie składni
            syntax_valid = self._validate_hgvs_syntax(variant_description)
            
            if check_syntax_only:
                return {
                    "is_valid": syntax_valid,
                    "syntax_valid": syntax_valid,
                    "semantic_valid": False,
                    "original_description": variant_description,
                    "normalized_description": None,
                    "errors": [] if syntax_valid else [
                        MutalyzerError(
                            error_type=ErrorType.SYNTAX_ERROR,
                            message="Nieprawidłowa składnia HGVS"
                        ).dict()
                    ]
                }
            
            # Pełna walidacja
            try:
                if not self.normalizer_available:
                    raise Exception("Normalizer nie jest dostępny")
                    
                normalized = normalize(variant_description)
                
                return {
                    "is_valid": True,
                    "syntax_valid": True,
                    "semantic_valid": True,
                    "original_description": variant_description,
                    "normalized_description": normalized.get("description") if normalized else None,
                    "errors": [],
                    "variant_info": self._extract_variant_info(normalized),
                    "reference_found": True
                }
                
            except Exception as e:
                return {
                    "is_valid": False,
                    "syntax_valid": syntax_valid,
                    "semantic_valid": False,
                    "original_description": variant_description,
                    "normalized_description": None,
                    "errors": [
                        MutalyzerError(
                            error_type=ErrorType.SEMANTIC_ERROR,
                            message=str(e)
                        ).dict()
                    ],
                    "reference_found": False
                }
                
        except Exception as e:
            logger.error(f"Błąd lokalnego sprawdzania: {e}")
            raise MutalyzerClientError(
                f"Błąd lokalnego sprawdzania: {str(e)}",
                ErrorType.VALIDATION_ERROR
            )
    
    async def _check_variant_remote(
        self,
        variant_description: str,
        reference_sequence: Optional[str],
        check_syntax_only: bool
    ) -> Dict[str, Any]:
        """Sprawdzenie wariantu używając zdalnego API"""
        
        endpoint = f"{self.base_url}/check"
        payload = {
            "variant": variant_description,
            "reference": reference_sequence,
            "syntax_only": check_syntax_only
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    
                    data = response.json()
                    return self._process_remote_response(data, variant_description)
                    
                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise MutalyzerClientError(
                        "Timeout podczas komunikacji z Mutalyzer API",
                        ErrorType.VALIDATION_ERROR
                    )
                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise MutalyzerClientError(
                        f"HTTP Error {e.response.status_code}: {e.response.text}",
                        ErrorType.VALIDATION_ERROR
                    )
        
        # Jeśli dotarliśmy tutaj, wszystkie próby się nie powiodły
        raise MutalyzerClientError(
            "Wszystkie próby komunikacji z Mutalyzer API się nie powiodły",
            ErrorType.VALIDATION_ERROR
        )
    
    async def normalize_variant(
        self,
        variant_description: str,
        target_format: str = "hgvs",
        include_protein: bool = True,
        include_rna: bool = False
    ) -> Dict[str, Any]:
        """
        Normalizuje opis wariantu
        """
        start_time = time.time()
        
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
            
            processing_time = (time.time() - start_time) * 1000
            result["processing_time_ms"] = processing_time
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas normalizacji wariantu {variant_description}: {e}")
            raise MutalyzerClientError(
                f"Błąd normalizacji wariantu: {str(e)}",
                ErrorType.VALIDATION_ERROR
            )
    
    async def _normalize_variant_local(
        self,
        variant_description: str,
        target_format: str,
        include_protein: bool,
        include_rna: bool
    ) -> Dict[str, Any]:
        """Normalizacja wariantu używając lokalnego normalizatora"""
        
        try:
            if not self.normalizer_available:
                raise Exception("Normalizer nie jest dostępny")
                
            normalized = normalize(variant_description)
            
            result = {
                "is_valid": True,
                "original_description": variant_description,
                "normalized_description": normalized.get("description") if normalized else None,
                "normalized_dna": normalized.get("description") if normalized else None,
                "errors": []
            }
            
            if include_protein and "protein" in normalized:
                result["normalized_protein"] = normalized["protein"].get("description")
            
            if include_rna and "rna" in normalized:
                result["normalized_rna"] = normalized["rna"].get("description")
            
            if "coordinates" in normalized:
                result["genomic_coordinates"] = normalized["coordinates"]
            
            return result
            
        except Exception as e:
            return {
                "is_valid": False,
                "original_description": variant_description,
                "normalized_description": None,
                "errors": [
                    MutalyzerError(
                        error_type=ErrorType.SEMANTIC_ERROR,
                        message=str(e)
                    ).dict()
                ]
            }
    
    async def _normalize_variant_remote(
        self,
        variant_description: str,
        target_format: str,
        include_protein: bool,
        include_rna: bool
    ) -> Dict[str, Any]:
        """Normalizacja wariantu używając zdalnego API"""
        
        endpoint = f"{self.base_url}/normalize"
        payload = {
            "variant": variant_description,
            "format": target_format,
            "include_protein": include_protein,
            "include_rna": include_rna
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return self._process_remote_response(data, variant_description)
    
    async def process_batch(
        self,
        variants: List[str],
        parallel: bool = True,
        fail_fast: bool = False
    ) -> Dict[str, Any]:
        """
        Przetwarza wiele wariantów naraz
        """
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        
        if parallel:
            tasks = [
                self.check_variant(variant)
                for variant in variants
            ]
            
            if fail_fast:
                batch_results = await asyncio.gather(*tasks)
            else:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "is_valid": False,
                        "original_description": variants[i],
                        "errors": [
                            MutalyzerError(
                                error_type=ErrorType.VALIDATION_ERROR,
                                message=str(result)
                            ).dict()
                        ]
                    })
                    failed += 1
                else:
                    results.append(result)
                    if isinstance(result, dict) and result.get("is_valid", False):
                        successful += 1
                    else:
                        failed += 1
        else:
            # Sekwencyjne przetwarzanie
            for variant in variants:
                try:
                    result = await self.check_variant(variant)
                    results.append(result)
                    if isinstance(result, dict) and result.get("is_valid", False):
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    if fail_fast:
                        raise
                    
                    results.append({
                        "is_valid": False,
                        "original_description": variant,
                        "errors": [
                            MutalyzerError(
                                error_type=ErrorType.VALIDATION_ERROR,
                                message=str(e)
                            ).dict()
                        ]
                    })
                    failed += 1
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "total_variants": len(variants),
            "successful_variants": successful,
            "failed_variants": failed,
            "results": results,
            "processing_time_ms": processing_time
        }
    
    def _validate_hgvs_syntax(self, variant_description: str) -> bool:
        """Podstawowa walidacja składni HGVS"""
        
        # Proste sprawdzenia składni HGVS
        if not variant_description:
            return False
        
        # Sprawdź czy zawiera podstawowe elementy HGVS
        hgvs_patterns = [
            r"[gcnrp]\.",  # prefiksy HGVS
            r">\w+",       # substytucje
            r"del",        # delecje
            r"ins",        # insercje
            r"dup",        # duplikacje
            r"inv"         # inwersje
        ]
        
        import re
        for pattern in hgvs_patterns:
            if re.search(pattern, variant_description, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_variant_info(self, normalized_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Wyciąga informacje o wariancie z znormalizowanych danych"""
        
        if not normalized_data:
            return None
        
        variant_info = {
            "variant_type": self._determine_variant_type(normalized_data.get("description", "")),
            "position": normalized_data.get("position"),
            "reference_sequence": normalized_data.get("reference"),
            "alternative_sequence": normalized_data.get("alternative")
        }
        
        # Dodaj informacje o transkryptach jeśli dostępne
        if "transcripts" in normalized_data:
            variant_info["affected_transcripts"] = [
                {
                    "transcript_id": t.get("id"),
                    "gene_symbol": t.get("gene"),
                    "strand": t.get("strand")
                }
                for t in normalized_data["transcripts"]
            ]
        
        return variant_info
    
    def _determine_variant_type(self, description: str) -> Optional[str]:
        """Określa typ wariantu na podstawie opisu"""
        
        description_lower = description.lower()
        
        if "del" in description_lower:
            return VariantType.DELETION.value
        elif "ins" in description_lower:
            return VariantType.INSERTION.value
        elif "dup" in description_lower:
            return VariantType.DUPLICATION.value
        elif "inv" in description_lower:
            return VariantType.INVERSION.value
        elif ">" in description_lower:
            return VariantType.SUBSTITUTION.value
        else:
            return VariantType.COMPLEX.value
    
    def _process_remote_response(
        self, 
        data: Dict[str, Any], 
        original_description: str
    ) -> Dict[str, Any]:
        """Przetwarza odpowiedź ze zdalnego API"""
        
        return {
            "is_valid": data.get("valid", False),
            "syntax_valid": data.get("syntax_valid", False),
            "semantic_valid": data.get("semantic_valid", False),
            "original_description": original_description,
            "normalized_description": data.get("normalized"),
            "errors": [
                MutalyzerError(
                    error_type=ErrorType.VALIDATION_ERROR,
                    message=error
                ).dict()
                for error in data.get("errors", [])
            ],
            "warnings": data.get("warnings", []),
            "reference_found": data.get("reference_found", True)
        }