import logging
from typing import Dict, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from src.Config import load_config

config = load_config()

class KeyValueMapper:
    prompt = """
        SYSTEM:

    You are a relevance assessment tool. 
    Your task is to assess whether the coordinates (from section COORDINATES)
    enriched by the context (from section CONTEXT)
    and by the term from the Sequence Ontology (from section SEQUENCE_ONTOLOGY_JSON)
    are linked to the value (from section USER_VALUE) of type key (from section USER_KEY).
    Value and key are given by the end user.
    Please give the answer (YES/NO) and
    in the new line the type of the relation between the genomic coordinate and the user-given value.
    Provide the reasoning for your answer in the last line.
    Format of answer: YES/NO\nRELATION_TYPE\nREASONING
    """

    def __init__(self, llm):
        self.llm = llm
        self.logger = logging.getLogger(__name__)

    def extract_links_from_query(self, coordinates: str, context: str, sequence_ontology_term: str, user_query_dict: Dict[str, str]):
        self.logger.debug(f"Extracting links from query {user_query_dict} for coordinates {coordinates} and context {context}")
        links_dict: Dict[str, bool] = {}
        for key, value in user_query_dict.items():
            has_link: bool = self.extract_link(coordinates, context, sequence_ontology_term, key, value)
            links_dict[key] = has_link
        return links_dict

    def extract_link(self, coordinates: str, context: str, sequence_ontology_term: str, key: str, value: str) -> bool:
        self.logger.info(f"Extracting link between {key} and {value} for coordinates {coordinates} and context {context}")
        response: str = self.ask_model(key, value, coordinates, context, sequence_ontology_term)
        has_link, relation_type, reasoning = KeyValueMapper.preprocess_model_response(response)
        self.logger.info(
            f"Link between ({key}: {value}) and the context: {has_link}. Type of relation is {relation_type}. Reasoning: {reasoning}")
        return has_link

    def ask_model(self, key: str, value: str, coordinates: str, context: str,
                  sequence_ontology_term: str) -> str:
        prompt = ChatPromptTemplate.from_template("""
                        {system}
                    CONTEXT:
                        {context}
                    COORDINATES:
                        {coordinates}
                    SEQUENCE_ONTOLOGY_JSON:
                        {sequence_ontology_term}
                    USER_KEY:
                        {key}
                    USER_VALUE:
                        {value}
                """)

        output_parser = StrOutputParser()

        chain = prompt | self.llm | output_parser

        return chain.invoke({
            "system": self.prompt,
            "context": context,
            "coordinates": coordinates,
            "sequence_ontology_term": sequence_ontology_term,
            "key": key,
            "value": value,
        })

    @staticmethod
    def preprocess_model_response(response: str) -> Tuple[bool, str, str]:
        lines = response.split("\n")
        if len(lines) < 3:
            print("Invalid response format in LinksFromQueryExtractionService. Expected 3 lines.")
            return False, "", ""
        return lines[0].startswith("YES"), lines[1], lines[2]
