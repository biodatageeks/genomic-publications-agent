import json

from langchain.chat_models import ChatOpenAI
from getpass import getpass
import yaml
from langchain.prompts import ChatPromptTemplate
import getpass
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_together import ChatTogether

from src.RAG.RAGService import RAGService
import logging


# Load the YAML file
with open("/home/wojtek/Documents/Badawcze/cooordinates-lit/config/config.yaml", "r") as file:
    config = yaml.safe_load(file)

with open(os.path.join(config['base_dir'], config['paths']['coordinates_extraction_examples']), 'r') as file:
    genomic_coordinates_examples = file.read()


class SequenceOntologyMappingService:
    prompt = f"""
    SYSTEM:

    You are a sequence ontology mapper. Your task is to map text and genomic coordinates into specific sequence ontology term.
    Please give the sequence ontology term name that is the most relevant to the text in section CONTEXT and to the genomic coordinates in section COORDINATES.
    Take into consideration the semantic meaning of the genomic coordinates format and the context of the text together.
    In the section SEQUENCE_ONTOLOGY_JSON there are potential terms. Please choose one of them, basing on the distance and relevance to the context and coordinate.
    Output format should be only the exact JSON of the chosen sequence ontology term.
    """

    def __init__(self, llm):
        self.logger = logging.getLogger(__name__)
        self.llm = llm

    def map_coordinates_to_sequence_ontology(self, coordinates: str, context: str):
        self.logger.info(f"Mapping coordinates {coordinates} to sequence ontology term based on context {context}")
        model_response = self.ask_model(self.prompt, coordinates, context)
        return self.preprocess_model_response(model_response)

    def preprocess_model_response(self, response):
        return response

    def ask_retriever(self, query, limit):
        rag_service = RAGService(setup=False)
        return rag_service.vector_search(query, limit)

    def ask_model(self, system_prompt: str, coordinates: str, context: str):
        results = self.ask_retriever(context, limit=5)
        prompt = ChatPromptTemplate.from_template("""
                {system}
            CONTEXT:
                {context}
            COORDINATES:
                {coordinates}
            SEQUENCE_ONTOLOGY_JSON:
                {results}
        """)

        output_parser = StrOutputParser()

        chain = prompt | self.llm | output_parser

        return chain.invoke({
            "system": system_prompt,
            "context": context,
            "coordinates": coordinates,
            "results": results
        })
