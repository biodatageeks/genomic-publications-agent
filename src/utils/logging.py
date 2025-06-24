"""
Logging module.
"""
import logging
import os
from typing import Optional

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name
        level: Optional logging level
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if level is None:
        level = logging.INFO
        
    logger.setLevel(level)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if logs directory exists
    logs_dir = 'logs'
    if os.path.exists(logs_dir):
        file_handler = logging.FileHandler(
            os.path.join(logs_dir, f'{name}.log')
        )
        file_handler.setFormatter(console_formatter)
        logger.addHandler(file_handler)
        
    return logger 