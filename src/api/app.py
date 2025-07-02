"""
Główna aplikacja FastAPI dla Mutalyzer API
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .endpoints.mutalyzer import router as mutalyzer_router


# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Zarządzanie cyklem życia aplikacji"""
    
    # Startup
    logger.info("Uruchamianie Mutalyzer API...")
    
    # Tutaj można dodać inicjalizację bazy danych, cache, etc.
    
    yield
    
    # Shutdown
    logger.info("Zamykanie Mutalyzer API...")


def create_app() -> FastAPI:
    """Fabryka aplikacji FastAPI"""
    
    app = FastAPI(
        title="Mutalyzer API",
        description="""
        **API dla walidacji i normalizacji wariantów HGVS**
        
        Ten serwis zapewnia kompleksową walidację opisów wariantów genetycznych 
        zgodnie ze standardami Human Genome Variation Society (HGVS).
        
        ## Główne funkcjonalności:
        
        * **Walidacja wariantów** - sprawdzanie poprawności składni i semantyki HGVS
        * **Normalizacja** - konwersja do standardowego formatu
        * **Przetwarzanie wsadowe** - obsługa wielu wariantów jednocześnie
        * **Cache i analityka** - optymalizacja wydajności i monitorowanie
        
        ## Obsługiwane formaty:
        
        * DNA (genomowy): `g.123A>T`
        * cDNA (kodujący): `c.123A>T`
        * RNA: `r.123a>u`
        * Białko: `p.Arg123Cys`
        
        ## Typy wariantów:
        
        * Substytucje: `c.123A>T`
        * Delecje: `c.123_124delAT`
        * Insercje: `c.123_124insATGC`
        * Duplikacje: `c.123_124dupAT`
        * Inwersje: `c.123_456inv`
        * Kompleksowe: `c.[123A>T;456C>G]`
        
        ## Rate Limiting:
        
        * Pojedyncze requesty: bez limitu
        * Batch processing: max 1000 wariantów na request
        * Timeout: 300 sekund
        
        ## Wykorzystanie w badanianiach:
        
        Idealny do:
        * Walidacji danych z plików VCF
        * Sprawdzania wariantów z literatury
        * Standaryzacji opisów w bazach danych
        * Automatyzacji pipeline'ów bioinformatycznych
        """,
        version="1.0.0",
        contact={
            "name": "Bioinformatics Team",
            "email": "bioinformatics@example.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # W produkcji należy ograniczyć
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # W produkcji należy ograniczyć
    )
    
    # Dodaj routery
    app.include_router(mutalyzer_router)
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Globalny handler wyjątków"""
        
        logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred. Please try again later.",
                "request_id": str(id(request))
            }
        )
    
    # Root endpoint
    @app.get("/", summary="API Info")
    async def root() -> Dict[str, Any]:
        """Informacje o API"""
        return {
            "service": "Mutalyzer API",
            "version": "1.0.0",
            "description": "API dla walidacji i normalizacji wariantów HGVS",
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "check_variant": "/mutalyzer/check",
                "normalize_variant": "/mutalyzer/normalize", 
                "batch_processing": "/mutalyzer/batch",
                "statistics": "/mutalyzer/stats",
                "health": "/mutalyzer/health",
                "examples": "/mutalyzer/variants/examples"
            }
        }
    
    return app


# Instancja aplikacji
app = create_app()


if __name__ == "__main__":
    # Uruchomienie serwera dla development
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )