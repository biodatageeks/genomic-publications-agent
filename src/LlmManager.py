import logging
import os
from getpass import getpass

from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether


class LlmManager:

    def __init__(self, endpoint: str, llm_model_name: str, temperature=0.7):
        logger = logging.getLogger(__name__)
        if endpoint == 'gpt':
            if "OPENAI_API_KEY" not in os.environ:
                os.environ["OPENAI_API_KEY"] = getpass("Enter your OpenAI API key: ")
            self.llm = ChatOpenAI(temperature=temperature)
            logger.info('Loaded OpenAI model')
        elif endpoint == 'together':
            if "TOGETHER_API_KEY" not in os.environ:
                os.environ["TOGETHER_API_KEY"] = getpass("Enter your Together API key: ")
            self.llm = ChatTogether(
                model=llm_model_name,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2
            )
            logger.info('Loaded TogetherAI model')
        else:
            logger.error('Invalid endpoint')
