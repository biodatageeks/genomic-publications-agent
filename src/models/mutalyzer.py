"""
Modele danych dla API Mutalyzer
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, validator


class VariantType(str, Enum):
    """Typy wariantów DNA"""
    SUBSTITUTION = "substitution"
    DELETION = "deletion"
    INSERTION = "insertion"
    DUPLICATION = "duplication"
    INVERSION = "inversion"
    COMPLEX = "complex"


class MoleculeType(str, Enum):
    """Typy molekuł"""
    DNA = "dna"
    RNA = "rna"
    PROTEIN = "protein"


class ErrorType(str, Enum):
    """Typy błędów Mutalyzer"""
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    REFERENCE_ERROR = "reference_error"
    MAPPING_ERROR = "mapping_error"
    VALIDATION_ERROR = "validation_error"


class MutalyzerError(BaseModel):
    """Model błędu Mutalyzer"""
    error_type: ErrorType
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TranscriptInfo(BaseModel):
    """Informacje o transkrypcji"""
    transcript_id: str
    gene_symbol: Optional[str] = None
    strand: Optional[str] = Field(None, pattern=r"^[+-]$")
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    exon_count: Optional[int] = None


class ProteinInfo(BaseModel):
    """Informacje o białku"""
    protein_id: Optional[str] = None
    sequence: Optional[str] = None
    length: Optional[int] = None
    molecular_weight: Optional[float] = None


class VariantInfo(BaseModel):
    """Szczegółowe informacje o wariancie"""
    variant_type: Optional[VariantType] = None
    reference_sequence: Optional[str] = None
    alternative_sequence: Optional[str] = None
    position: Optional[int] = None
    length: Optional[int] = None
    affected_transcripts: Optional[List[TranscriptInfo]] = None
    protein_changes: Optional[List[ProteinInfo]] = None


class MutalyzerRequest(BaseModel):
    """Bazowy request dla Mutalyzer"""
    variant_description: str = Field(..., description="Opis wariantu w formacie HGVS")
    reference_sequence: Optional[str] = Field(None, description="Sekwencja referencyjna")
    molecule_type: MoleculeType = Field(MoleculeType.DNA, description="Typ molekuły")
    
    @validator('variant_description')
    def validate_variant_description(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Opis wariantu nie może być pusty")
        return v.strip()


class MutalyzerResponse(BaseModel):
    """Bazowa odpowiedź z Mutalyzer"""
    is_valid: bool
    normalized_description: Optional[str] = None
    original_description: str
    errors: Optional[List[MutalyzerError]] = None
    warnings: Optional[List[str]] = None
    variant_info: Optional[VariantInfo] = None
    processing_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class VariantCheckRequest(MutalyzerRequest):
    """Request dla sprawdzania wariantów"""
    check_syntax_only: bool = Field(False, description="Sprawdź tylko składnię")
    normalize: bool = Field(True, description="Znormalizuj opis wariantu")


class VariantCheckResponse(MutalyzerResponse):
    """Odpowiedź dla sprawdzania wariantów"""
    syntax_valid: bool
    semantic_valid: bool
    reference_found: bool = True
    suggestions: Optional[List[str]] = None


class VariantNormalizationRequest(MutalyzerRequest):
    """Request dla normalizacji wariantów"""
    target_format: str = Field("hgvs", description="Docelowy format normalizacji")
    include_protein_description: bool = Field(True, description="Uwzględnij opis białka")
    include_rna_description: bool = Field(False, description="Uwzględnij opis RNA")


class VariantNormalizationResponse(MutalyzerResponse):
    """Odpowiedź dla normalizacji wariantów"""
    normalized_dna: Optional[str] = None
    normalized_rna: Optional[str] = None
    normalized_protein: Optional[str] = None
    genomic_coordinates: Optional[Dict[str, Any]] = None


class BatchVariantRequest(BaseModel):
    """Request dla przetwarzania wsadowego wariantów"""
    variants: List[MutalyzerRequest] = Field(..., min_items=1, max_items=1000)
    fail_fast: bool = Field(False, description="Zatrzymaj na pierwszym błędzie")
    parallel_processing: bool = Field(True, description="Przetwarzanie równoległe")
    
    @validator('variants')
    def validate_variants_limit(cls, v):
        if len(v) > 1000:
            raise ValueError("Maksymalnie 1000 wariantów na batch")
        return v


class BatchVariantResponse(BaseModel):
    """Odpowiedź dla przetwarzania wsadowego"""
    total_variants: int
    successful_variants: int
    failed_variants: int
    results: List[MutalyzerResponse]
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)