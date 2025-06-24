"""
Main application module.
"""
import os
from dotenv import load_dotenv
from src.utils.config.config import Config
from src.utils.llm.manager import LlmManager
from src.utils.logging import get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

def main():
    """
    Main application entry point.
    """
    try:
        # Load configuration
        config = Config()
        logger.info('Configuration loaded successfully')
        
        # Initialize LLM manager
        llm_manager = LlmManager(
            provider='openai',
            temperature=0.7
        )
        logger.info('LLM manager initialized successfully')
        
        # TODO: Add your application logic here
        
    except Exception as e:
        logger.error(f'Application error: {str(e)}')
        raise

if __name__ == '__main__':
    main() 