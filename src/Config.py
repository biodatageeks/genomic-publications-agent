"""
Configuration module for the application.

This module provides both the Config class and a load_config function
for backward compatibility with existing imports.
"""

from src.utils.config.config import Config as _Config
from typing import Dict, Any, Optional

# Create a global config instance for the load_config function
_global_config_instance: Optional[_Config] = None

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path (str, optional): Path to the configuration file.
            If not provided, defaults to config/development.yaml
            
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    global _global_config_instance
    
    if _global_config_instance is None:
        _global_config_instance = _Config(config_path)
    
    return _global_config_instance.config

# Re-export Config class for direct usage
Config = _Config 