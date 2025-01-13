from typing import List
import logging

from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from src.Config import Config

config = Config()
genomic_coordinates_examples = config.load_genomic_coordinates_examples()

logger = logging.getLogger(__name__)


class CoordinatesLlmExtractor:
    

    prompt = f"""
    SYSTEM:

    You are a coordinates extractor. Your task is to extract genomic coordinates from a text.
    Given a text in section PUBLICATION, please extract all genomic coordinates from it
    and format them in a newline separated list.
    Do not return any other coordinates than the ones in the text.
    Return only the list of coordinates, separated by newlines.
    If no coordinates are found, return a word "NONE".
    Examples of genomic coordinates are:
    {genomic_coordinates_examples}
    """

    def __init__(self, llm):
        self.llm = llm

    def extract(self, text):
        model_response = self.query_llm(self.prompt, text)
        logger.info(f'Model response: {model_response}')
        return self.parse_response(model_response)

    def query_llm(self, system_prompt: str, publication_text: str):
            prompt = ChatPromptTemplate.from_template("{system} PUBLICATION: {publication}")
            llm_chain = LLMChain(llm=self.llm, prompt=prompt)
            return llm_chain.run({
                "system": system_prompt,
                "publication": publication_text
            })
    
    def parse_response(self, response):
        coordinates_list: List[str] = response.split("\n")
        if len(coordinates_list) > 0 and coordinates_list[0] == "NONE":
            return []
        return coordinates_list

    
