"""
Configuration settings for the application.
"""
import os
from pathlib import Path
from typing import Dict, Any

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"

# API settings
API_TIMEOUT = 30
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 1

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Cache settings
CACHE_ENABLED = True
CACHE_EXPIRY = 3600  # 1 hour

def get_config() -> Dict[str, Any]:
    """
    Get the current configuration settings.
    
    Returns:
        Dict[str, Any]: Configuration settings
    """
    return {
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "raw_data_dir": str(RAW_DATA_DIR),
        "processed_data_dir": str(PROCESSED_DATA_DIR),
        "cache_dir": str(CACHE_DIR),
        "api_timeout": API_TIMEOUT,
        "api_retry_attempts": API_RETRY_ATTEMPTS,
        "api_retry_delay": API_RETRY_DELAY,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        "cache_enabled": CACHE_ENABLED,
        "cache_expiry": CACHE_EXPIRY,
    } 