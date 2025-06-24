from typing import List
import logging

from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from src.utils.config.config import Config

config = Config()
genomic_coordinates_examples = config.load_genomic_coordinates_examples()

logger = logging.getLogger(__name__)


class CoordinatesLlmExtractor:
    

    prompt = """
    SYSTEM:

    Your task is to extract genomic coordinates from the provided text. 
    Focus on the section labeled PUBLICATION and identify all genomic coordinates present. 
    Format the extracted coordinates as a list, with each coordinate on a new line. 
    Ensure that you only return the coordinates found in the text, and nothing else. 
    If no coordinates are detected, respond with "NONE". 
    """

    def __init__(self, llm):
        self.llm = llm

    def extract(self, text):
        model_response = self.query_llm(self.prompt, text)
        logger.info(f'Model response: {model_response}')
        return self.parse_response(model_response, text)

    def query_llm(self, system_prompt: str, publication_text: str):
            prompt = ChatPromptTemplate.from_template("""
                                                      {system}
                                                      PUBLICATION:
                                                      {publication}
                                                      """)
            llm_chain = LLMChain(llm=self.llm, prompt=prompt)
            return llm_chain.run({
                "system": system_prompt,
                "publication": publication_text
            })
    
    def parse_response(self, response, text):
        coordinates_list: List[str] = response.split("\n")
        if len(coordinates_list) > 0 and coordinates_list[0] == "NONE":
            return []
        unique_coordinates = set(a[2:] if a.startswith('- ') else a[3:] if a.startswith(tuple(f"{i}. " for i in range(1, 101))) else a for a in list(filter(lambda x: 'coordinate' not in x.lower() and 'publication' not in x.lower(), coordinates_list)))
        coordinates_without_empty_strings = [a for a in list(unique_coordinates) if a != '']
        only_coordinates_existing_in_text = [a for a in coordinates_without_empty_strings if a in text]
        return only_coordinates_existing_in_text

    
