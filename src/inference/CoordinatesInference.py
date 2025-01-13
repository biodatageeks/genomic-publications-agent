import logging

from src.flow.PubmedEndpoint import PubmedEndpoint
from src.flow.coordinates_extraction.CoordinatesLLMExtractor import CoordinatesLlmExtractor
from src.flow.ContextRetriever import ContextRetriever
from src.flow.SequenceOntologyMapper import SequenceOntologyMapper
from src.flow.KeyValueMapper import KeyValueMapper


class CoordinatesInference:
    def __init__(self, llm):
        self.logger = logging.getLogger(__name__)
        self.coordinates_extraction_service = CoordinatesLlmExtractor(llm)
        self.context_extraction_service = ContextRetriever(llm)
        self.sequence_ontology_mapping_service = SequenceOntologyMapper(llm)
        self.links_from_query_extraction_service = KeyValueMapper(llm)

    def search_coordinates(self, pmid: str, user_query_dict: dict):
        self.logger.info(f"Searching coordinates for pmid {pmid} with user query {user_query_dict}")
        publication_text = PubmedEndpoint.fetch_full_text_from_pubmed_id(pmid)
        return self.search_coordinates_in_text(publication_text, user_query_dict)

    def search_coordinates_in_text(self, text: str, user_query_dict: dict):
        self.logger.info(f"Searching coordinates in text with user query {user_query_dict}")
        coordinates_list = self.coordinates_extraction_service.extract(text)
        self.logger.info(f"Extracted coordinates: {coordinates_list}")
        results = []
        for coordinate in coordinates_list:
            self.logger.info(f"------------------------------Processing coordinate {coordinate}------------------------------")
            context, so_term, links = self.process_coordinate(coordinate, text, user_query_dict)
            results.append({"coordinate": coordinate, "context": context, "so_term": so_term, "links": links})
        return results

    def extract_coordinates_from_text(self, text: str):
        return self.coordinates_extraction_service.extract(text)

    def process_coordinate(self, coordinate: str, text: str, user_query_dict: dict):
        self.logger.info(f"Processing coordinate {coordinate} in text with user query {user_query_dict}")
        context: str = self.context_extraction_service.extract_context_from_coordinate(text, coordinate)
        self.logger.info(f"Extracted context: {context}")
        so_term = self.sequence_ontology_mapping_service.map_coordinates_to_sequence_ontology(coordinate, context)
        self.logger.info(f"Extracted sequence ontology term: {so_term}")
        links = self.links_from_query_extraction_service.extract_links_from_query(coordinate, context, so_term,
                                                                                  user_query_dict)
        self.logger.info(f"Extracted links: {links}")
        return context, so_term, links
