import logging
import os
from getpass import getpass
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from src.Config import Config


class LlmManager:

    def __init__(self, endpoint: str, llm_model_name: Optional[str] = None, temperature=0.7):
        logger = logging.getLogger(__name__)
        config = Config()
        
        # Use model name from config if not specified
        if llm_model_name is None:
            llm_model_name = config.get_llm_model_name()
            
        # At this point, llm_model_name should be a string (not None)
        assert llm_model_name is not None, "Model name must be specified either directly or in config"
        
        if endpoint == 'gpt':
            # Try to get API key from config
            api_key = config.get_openai_api_key()
            
            if not api_key and "OPENAI_API_KEY" not in os.environ:
                # If no API key in config or environment, prompt user
                api_key = getpass("Enter your OpenAI API key: ")
            
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                
            self.llm = ChatOpenAI(temperature=temperature)
            self.llm_model_name = llm_model_name
            logger.info('Loaded OpenAI model')
        elif endpoint == 'together':
            # Try to get API key from config
            api_key = config.get_together_api_key()
            
            if not api_key and "TOGETHER_API_KEY" not in os.environ:
                # If no API key in config or environment, prompt user
                api_key = getpass("Enter your Together API key: ")
            
            if api_key:
                os.environ["TOGETHER_API_KEY"] = api_key
                
            self.llm = ChatTogether(
                model=llm_model_name,  # Type checker will know llm_model_name is str due to assert above
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )
            self.llm_model_name = llm_model_name
            logger.info(f'Loaded TogetherAI model: {llm_model_name}')
        else:
            logger.error(f'Invalid endpoint: {endpoint}')
            raise ValueError(f"Invalid LLM endpoint: {endpoint}")

    def get_llm(self):
        return self.llm
    
    def get_llm_model_name(self):
        return self.llm_model_name
