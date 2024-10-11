from enum import Enum
from typing import List

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from getpass import getpass
import re
import yaml
import os


class NomenclatureType(Enum):
    HGVS = 1
    BED = 2
    GFF_GTF = 3


# Load the YAML file
with open("/home/wojtek/Documents/Badawcze/cooordinates-lit/config/config.yaml", "r") as file:
    config = yaml.safe_load(file)

with open(os.path.join(config['base_dir'], config['paths']['coordinates_extraction_examples']), 'r') as file:
    genomic_coordinates_examples = file.read()


class CoordinatesExtractionService:
    hgvs_regex: str = (r'^(g\.|c\.|m\.|r\.|p\.)?(\d+|[+-]\d+|[A-Z]+\d+)?(?:_(\d+|[+-]\d+|[A-Z]+\d+))?(delins['
                       r'ATCG]+|del|ins[ATCG]*|dup|inv|fs|[A-Z][a-z]{2}|\*)?(>?[A-Z][a-z]{2}|>?[ATCG]|\*|\([A-Z]{'
                       r'3}\d{1,3}[A-Z]{3}\))?(?:\*?\d+)?(?:[+*/-]\d+)?$')
    bed_regex: str = (r'^(chr([1-9]|[1-2][0-9]|X|Y|M|Un(_[a-zA-Z0-9]+)?)|[a-zA-Z]+)\t([0-9]+)\t([0-9]+)\t([^\t]*)?\t(['
                      r'0-9]+(\.[0-9]+)?)?\t([+-]?)\t([0-9]+)\t([0-9]+)\t(0|[0-9]{1,3},[0-9]{1,3},[0-9]{1,'
                      r'3})\t([0-9]+)\t(([0-9]+,)+)\t(([0-9]+,)+)$')
    gff_gtf_regex: str = r'^([\w.\-]+)\t([\w.\-]*)\t([\w.\-]+)\t(\d+)\t(\d+)\t([\d.]+|\.)\t([+-])\t([012]|\.)\t(.+)$'
    # TODO FINISH ACCORDINGLY

    prompt = f"""
    SYSTEM:
    
    You are a coordinates retriever. Your task is to extract genomic coordinates from a text.
    Given a text in section PUBLICATION, please extract all genomic coordinates from it
    and format them in a newline separated list.
    Return only the list of coordinates.
    If no coordinates are found, return a word "NONE".
    1. Examples of genomic coordinates are:
    {genomic_coordinates_examples}
    2. These are examples of regex patterns that you can use to extract the coordinates:
    - HGVS: {hgvs_regex}
    - BED: {bed_regex}
    - GFF/GTF: {gff_gtf_regex}
    3. The coordinates can be in the format like here or similar. They do not have to comply the exact regex pattern. There can be literals, spaces, other delimiters used, or other characters around and inside them.    
    """

    def __init__(self, llm):
        self.llm = llm

    def extract_coordinates_from_text(self, text):
        model_response = self.ask_model(self.prompt, text)
        return self.preprocess_model_response(model_response)

    def preprocess_model_response(self, response):
        coordinates_list: List[str] = response.split("\n")
        if len(coordinates_list) > 0 and coordinates_list[0] == "NONE":
            return []
        regex_match_score = [match is not None for match in
                             [self.match_coordinate_with_regex(coordinate) for coordinate in coordinates_list]]
        print(f"Regex match score: {regex_match_score}")
        return coordinates_list

    def match_coordinate_with_regex(self, coordinate: str):
        if re.fullmatch(self.hgvs_regex, coordinate):
            return NomenclatureType.HGVS
        elif re.fullmatch(self.bed_regex, coordinate):
            return NomenclatureType.BED
        elif re.fullmatch(self.gff_gtf_regex, coordinate):
            return NomenclatureType.GFF_GTF
        else:
            return None

    def ask_model(self, system_prompt: str, publication_text: str):
        prompt = ChatPromptTemplate.from_template("{system} PUBLICATION: {publication}")
        llm_chain = LLMChain(llm=self.llm, prompt=prompt)
        return llm_chain.run({
            "system": system_prompt,
            "publication": publication_text
        })
