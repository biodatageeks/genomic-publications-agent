import logging
from typing import Dict, List, Union, Tuple, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.inference.CoordinatesInference import CoordinatesInference
from src.LlmManager import LlmManager
from src.flow.PubmedEndpoint import PubmedEndpoint


class BenchmarkTestService:
    def __init__(self, endpoint_type: str, model_name: str, max_num_tokens: int):
        self.llm_manager = LlmManager(endpoint_type, model_name)
        self.max_num_tokens = max_num_tokens
        logging.basicConfig(filename='../log/debug.log', level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.basicConfig(filename='../log/info.log', level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def perform_benchmark_inference(self, benchmark_tests: List[Dict[str, Union[str, Dict[str, str], List[str]]]]):
        coordinates_search_service = CoordinatesInference(self.llm_manager.llm)

        full_results = []
        for test in benchmark_tests:
            pmids: List[str] = test['pmids']
            user_query_dict: Dict[str, str] = test['user_query_dict']
            hgvs_coordinate: str = test["hgvs_coordinate"]
            results = []
            for text in self.prepare_texts_from_pmids(pmids):
                partial_results = coordinates_search_service.search_coordinates_in_text(text, user_query_dict)
                results.extend(partial_results)
            full_results.append(results)
        return full_results

    def manual_test_coordinate_search(self, pmids: List[str]):
        coordinates_list = []
        coordinates_search_service = CoordinatesInference(self.llm_manager.llm)
        for text in self.prepare_texts_from_pmids(pmids):
            coordinates_list.extend(coordinates_search_service.extract_coordinates_from_text(text))
        return coordinates_list


    def perform_simple_benchmark_test(self, benchmark_test: Dict[str, Union[str, Dict[str, str], List[str]]]) -> Tuple[bool, Optional[bool]]:
        coordinates_search_service = CoordinatesInference(self.llm_manager.llm)

        pmids: List[str] = benchmark_test['pmids']
        user_query_dict: Dict[str, str] = benchmark_test['user_query_dict']
        hgvs_coordinate: str = benchmark_test["hgvs_coordinate"]
        for text in self.prepare_texts_from_pmids(pmids):
            coordinates_list = coordinates_search_service.extract_coordinates_from_text(text)
            if hgvs_coordinate in coordinates_list:
                context, so_term, links = coordinates_search_service.process_coordinate(hgvs_coordinate, text, user_query_dict)
                return True, all(links.values())
        return False, None

    def prepare_texts_from_pmids(self, pmids):
        logging.getLogger(__name__).info(f"Fetching full texts for pmids: {pmids}")
        texts = []
        for pmid in pmids:
            full_text = PubmedEndpoint.fetch_full_text_from_pubmed_id(pmid)
            overlap = 50
            expected_system_prompt_num_tokens = 3000
            expected_answer_num_tokens = 3000
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.max_num_tokens - overlap - expected_system_prompt_num_tokens - expected_answer_num_tokens,
                chunk_overlap=overlap,
                length_function=self.llm_manager.llm.get_num_tokens
            )
            chunks = splitter.create_documents([full_text])
            texts.extend([c.page_content for c in chunks])
        return texts
