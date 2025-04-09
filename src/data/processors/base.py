"""
Base data processor implementation.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from ...core.utils.logging import get_logger
from ...core.utils.helpers import load_json, save_json

logger = get_logger(__name__)

class BaseProcessor(ABC):
    """
    Base class for data processors.
    """
    
    def __init__(self, input_path: Union[str, Path], output_path: Union[str, Path]):
        """
        Initialize the processor.
        
        Args:
            input_path: Path to input data
            output_path: Path to save processed data
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
    @abstractmethod
    def process(self) -> None:
        """
        Process the data.
        
        This method should be implemented by subclasses.
        """
        pass
    
    def load_input(self) -> Any:
        """
        Load input data.
        
        Returns:
            Any: Loaded data
            
        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
            
        return load_json(self.input_path)
    
    def save_output(self, data: Any) -> None:
        """
        Save processed data.
        
        Args:
            data: Data to save
        """
        save_json(data, self.output_path)
        logger.info(f"Saved processed data to {self.output_path}") 