"""
LLM Context Analyzer for biomedical publications.

This module provides tools for analyzing the context of biomedical entities 
in scientific publications using language models (LLM).
It utilizes annotations from the PubTator3 API and the Llama 3.1 8B model to identify 
relationships between variants and other biomedical entities.
"""

import csv
import json
import logging
import os
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from collections import defaultdict

import bioc
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from src.pubtator_client.pubtator_client import PubTatorClient
from src.pubtator_client.exceptions import PubTatorError
from src.context_analyzer.context_analyzer import ContextAnalyzer
from src.core.llm.manager import LlmManager
from src.cache.cache import APICache


class LlmContextAnalyzer(ContextAnalyzer):
    """
    Analyzer of contextual relationships between variants and other biomedical entities
    using language models (LLM).
    
    This class identifies relationships between variants and other entities (genes, diseases, tissues)
    in the context of passages from biomedical publications, using the Llama 3.1 8B model
    to analyze text and detect semantic relationships.
    
    Example usage:
        analyzer = LlmContextAnalyzer()
        pmids = ["32735606", "32719766"]
        relationships = analyzer.analyze_publications(pmids)
        analyzer.save_relationships_to_csv(relationships, "variant_relationships.csv")
    """
    
    # Entity types to extract from publications
    ENTITY_TYPES = {
        "variant": ["Mutation", "DNAMutation", "Variant"],
        "gene": ["Gene"],
        "disease": ["Disease"],
        "tissue": ["Tissue"],
        "species": ["Species"],
        "chemical": ["Chemical"]
    }
    
    # System prompt template
    SYSTEM_PROMPT = """You are an expert in biomedical text analysis and recognizing relationships between 
biomedical entities. Your task is to determine whether there are relationships between a genetic 
variant and other biomedical entities in the provided text. Respond only in 
JSON format, containing information about the relationships.
"""
    
    # User prompt template
    USER_PROMPT_TEMPLATE = """Analyze the provided biomedical text fragment and determine whether there are 
relationships between the variant {variant_text} and the following biomedical entities:

{entities_list}

Respond in a strictly defined JSON format, where for each entity you specify whether there is 
a relationship with the variant (true/false) and briefly justify your answer in 1-2 sentences.

Text fragment: "{passage_text}"

Response format:
{{
  "relationships": [
    {{
      "entity_type": "entity type, e.g., gene",
      "entity_text": "entity text",
      "entity_id": "entity identifier",
      "has_relationship": true/false,
      "explanation": "Brief justification of the decision"
    }},
    ...
  ]
}}
"""
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None, 
                 llm_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
                 use_cache: bool = True, cache_ttl: int = 86400,
                 cache_storage_type: str = "memory"):
        """
        Initializes the LLM Context Analyzer.
        
        Args:
            pubtator_client: Optional PubTator client
            llm_model_name: Name of the LLM model to use
            use_cache: Whether to use cache for LLM queries (default True)
            cache_ttl: Time-to-live for cache entries in seconds (default 24h)
            cache_storage_type: Type of cache: "memory" or "disk"
        """
        super().__init__(pubtator_client)
        self.logger = logging.getLogger(__name__)
        self.llm_manager = LlmManager('together', llm_model_name)
        self.llm = self.llm_manager.get_llm()
        self.logger.info(f'Loaded LLM model: {llm_model_name}')
        
        # Initialize cache
        self.use_cache = use_cache
        if use_cache:
            self.cache = APICache.create(storage_type=cache_storage_type, ttl=cache_ttl)
            self.logger.info(f"Cache enabled ({cache_storage_type}), TTL: {cache_ttl}s")
        else:
            self.cache = None
            self.logger.info("Cache disabled")
    
    def analyze_publications(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Analyzes a list of publications to extract contextual relationships.
        
        Args:
            pmids: List of PubMed identifiers to analyze
            
        Returns:
            List of dictionaries containing relationship data
            
        Raises:
            PubTatorError: If an error occurs while fetching or processing publications
        """
        relationships = []
        
        try:
            # Fetch publications from PubTator
            publications = self.pubtator_client.get_publications_by_pmids(pmids)
            
            for publication in publications:
                publication_relationships = self._analyze_publication(publication)
                relationships.extend(publication_relationships)
                
            return relationships
        except Exception as e:
            self.logger.error(f"Error analyzing publications: {str(e)}")
            raise PubTatorError(f"Error analyzing publications: {str(e)}") from e
    
    def analyze_publication(self, pmid: str) -> List[Dict[str, Any]]:
        """
        Analyzes a single publication to extract contextual relationships.
        
        Args:
            pmid: PubMed identifier to analyze
            
        Returns:
            List of dictionaries containing relationship data
            
        Raises:
            PubTatorError: If an error occurs while fetching or processing the publication
        """
        try:
            publication = self.pubtator_client.get_publication_by_pmid(pmid)
            if not publication:
                self.logger.warning(f"Publication not found for PMID: {pmid}")
                return []
                
            return self._analyze_publication(publication)
        except PubTatorError as e:
            self.logger.error(f"Error analyzing publication {pmid}: {str(e)}")
            raise
        
        # Add default return of an empty list in case of unexpected control flow
        return []
    
    def _analyze_publication(self, publication: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extracts contextual relationships from a single publication.
        
        Args:
            publication: BioCDocument object containing the publication with annotations
            
        Returns:
            List of dictionaries containing relationship data
        """
        relationships = []
        pmid = publication.id
        
        # Process each passage in the publication
        for passage in publication.passages:
            passage_relationships = self._analyze_passage(pmid, passage)
            relationships.extend(passage_relationships)
        
        return relationships
    
    def _analyze_passage(self, pmid: str, passage: bioc.BioCPassage) -> List[Dict[str, Any]]:
        """
        Extracts contextual relationships from a single passage using LLM.
        
        Args:
            pmid: PubMed identifier of the publication
            passage: BioCPassage object containing the passage with annotations
            
        Returns:
            List of dictionaries containing relationship data for this passage
        """
        relationships = []
        
        # Group annotations in the passage by type
        entities_by_type = self._group_annotations_by_type(passage)
        
        # If there are no variants in this passage, return an empty list
        if not any(variant_type in entities_by_type for variant_type in self.ENTITY_TYPES["variant"]):
            return []
        
        # Get all variants
        variants = []
        for variant_type in self.ENTITY_TYPES["variant"]:
            if variant_type in entities_by_type:
                variants.extend(entities_by_type[variant_type])
        
        # For each variant, create a relationship with other entities in the passage
        for variant in variants:
            variant_text = variant.text
            variant_offset = variant.locations[0].offset if variant.locations else None
            
            # Create a dictionary with the base relationship data
            relationship = {
                "pmid": pmid,
                "variant_text": variant_text,
                "variant_offset": variant_offset,
                "variant_id": variant.infons.get("identifier", ""),
                "genes": [],
                "diseases": [],
                "tissues": [],
                "species": [],
                "chemicals": [],
                "passage_text": passage.text
            }
            
            # Prepare a list of all entities in the passage (excluding variants)
            all_entities = []
            for entity_type, type_list in self.ENTITY_TYPES.items():
                if entity_type == "variant":
                    continue
                
                for type_name in type_list:
                    if type_name in entities_by_type:
                        for entity in entities_by_type[type_name]:
                            entity_data = {
                                "entity_type": entity_type,
                                "text": entity.text,
                                "id": entity.infons.get("identifier", ""),
                                "offset": entity.locations[0].offset if entity.locations else None
                            }
                            all_entities.append(entity_data)
            
            # If there are no other entities in the passage, skip LLM analysis
            if not all_entities:
                relationships.append(relationship)
                continue
            
            # Analyze relationships between the variant and other entities using LLM
            llm_relationships = self._analyze_relationships_with_llm(
                variant_text=variant_text, 
                entities=all_entities, 
                passage_text=passage.text
            )
            
            # Process results from LLM
            if llm_relationships:
                for rel in llm_relationships:
                    entity_type = rel.get("entity_type", "").lower()
                    if entity_type and entity_type in relationship and rel.get("has_relationship", False):
                        entity_data = {
                            "text": rel.get("entity_text", ""),
                            "id": rel.get("entity_id", ""),
                            "explanation": rel.get("explanation", "")
                        }
                        # Handle special case for "species", which already ends with 's'
                        key = entity_type + "s" if entity_type != "species" else entity_type
                        relationship[key].append(entity_data)
            
            relationships.append(relationship)
        
        return relationships
    
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                      passage_text: str) -> List[Dict[str, Any]]:
        """
        Analyzes relationships between the variant and entities in the passage using LLM.
        
        Args:
            variant_text: Text of the variant
            entities: List of entities in the passage (dictionaries with fields entity_type, text, id, offset)
            passage_text: Text of the passage
            
        Returns:
            List of dictionaries containing relationship data specified by LLM
        """
        if not entities:
            return []
            
        # Prepare the list of entities in the format for the prompt
        entities_list = "\n".join([f"- {e['entity_type']}: {e['text']} (ID: {e['id']})" for e in entities])
        
        # Check cache
        cache_key = f"llm_analysis:{variant_text}:{json.dumps(entities, sort_keys=True)}:{passage_text}"
        if self.use_cache and self.cache and self.cache.has(cache_key):
            self.logger.debug(f"Cache hit for LLM analysis: {variant_text}")
            return self.cache.get(cache_key)
        
        # Prepare messages for LLM
        system_message = SystemMessage(content=self.SYSTEM_PROMPT)
        
        prompt_template = PromptTemplate.from_template(self.USER_PROMPT_TEMPLATE)
        user_message_content = prompt_template.format(
            variant_text=variant_text,
            entities_list=entities_list,
            passage_text=passage_text
        )
        user_message = HumanMessage(content=user_message_content)
        
        # Send request to LLM
        try:
            response = self.llm.invoke([system_message, user_message])
            response_content = response.content
            
            # Parse JSON response
            try:
                # Ensure response_content is of type string
                response_str = str(response_content) if response_content is not None else "{}"
                
                # Remove any special characters and markdown code from JSON
                clean_json = self._clean_json_response(response_str)
                result_data = json.loads(clean_json)
                
                if "relationships" in result_data:
                    # Save to cache
                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, result_data["relationships"])
                    
                    return result_data["relationships"]
                else:
                    self.logger.warning(f"Invalid LLM response structure: missing 'relationships' field")
                    return []
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing LLM response: {str(e)}")
                self.logger.debug(f"LLM response: {response_content}")
                return []
        except Exception as e:
            self.logger.error(f"Error calling LLM: {str(e)}")
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """
        Cleans the LLM response to obtain a valid JSON format.
        
        Args:
            response: Response from LLM
            
        Returns:
            Cleaned JSON string
        """
        # Find the first '{' and the last '}'
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
            # If no valid JSON found, return an empty object
            return "{}"
        
        # Extract JSON from the response
        json_str = response[start_idx:end_idx+1]
        return json_str
    
    def _group_annotations_by_type(self, passage: bioc.BioCPassage) -> Dict[str, List[bioc.BioCAnnotation]]:
        """
        Groups annotations in the passage by type.
        
        Args:
            passage: BioCPassage object containing the passage with annotations
            
        Returns:
            Dictionary mapping annotation types to lists of BioCAnnotation objects
        """
        grouped = defaultdict(list)
        
        for annotation in passage.annotations:
            annotation_type = annotation.infons.get("type", "")
            if annotation_type:
                grouped[annotation_type].append(annotation)
        
        return grouped
    
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str):
        """
        Zapisuje wyniki analizy relacji do pliku CSV.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            output_file: Ścieżka do pliku wyjściowego
        """
        if not relationships:
            self.logger.warning("Brak relacji do zapisania")
            return
            
        # Określ nagłówki dla pliku CSV
        headers = [
            "pmid", "variant_text", "variant_id", "variant_offset",
            "gene", "gene_id", "gene_explanation",
            "disease", "disease_id", "disease_explanation",
            "tissue", "tissue_id", "tissue_explanation",
            "species", "species_id", "species_explanation",
            "chemical", "chemical_id", "chemical_explanation",
            "passage_text"
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for rel in relationships:
                    # Przygotuj bazowy wiersz z informacjami o wariancie i pasażu
                    base_row = {
                        "pmid": rel["pmid"],
                        "variant_text": rel["variant_text"],
                        "variant_id": rel["variant_id"],
                        "variant_offset": rel["variant_offset"],
                        "passage_text": rel["passage_text"]
                    }
                    
                    # Sprawdź, czy istnieją jakiekolwiek relacje
                    has_relationships = any(len(rel[entity_type + "s"]) > 0 
                                           for entity_type in ["gene", "disease", "tissue", "species", "chemical"])
                    
                    if not has_relationships:
                        # Jeśli nie ma relacji, zapisz tylko wiersz bazowy
                        writer.writerow(base_row)
                    else:
                        # Dla każdego typu encji, dodaj informacje o relacjach
                        for entity_type in ["gene", "disease", "tissue", "species", "chemical"]:
                            entities = rel[entity_type + "s"]
                            
                            if not entities:
                                continue
                                
                            for entity in entities:
                                row = base_row.copy()
                                row[entity_type] = entity["text"]
                                row[entity_type + "_id"] = entity["id"]
                                row[entity_type + "_explanation"] = entity["explanation"]
                                writer.writerow(row)
                
            self.logger.info(f"Zapisano relacje do pliku: {output_file}")
        except Exception as e:
            self.logger.error(f"Błąd zapisywania do pliku CSV: {str(e)}")
            raise
    
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Zapisuje dane relacji do pliku JSON.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            output_file: Ścieżka do pliku wyjściowego JSON
        """
        if not relationships:
            self.logger.warning("Brak relacji do zapisania")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(relationships, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Zapisano {len(relationships)} relacji do {output_file}")
        except Exception as e:
            self.logger.error(f"Błąd zapisywania relacji do JSON: {str(e)}")
            raise
    
    def filter_relationships_by_entity(
            self, 
            relationships: List[Dict[str, Any]], 
            entity_type: str, 
            entity_value: str) -> List[Dict[str, Any]]:
        """
        Filtruje relacje według konkretnej wartości bytu.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            entity_type: Typ bytu do filtrowania (gen, choroba, itp.)
            entity_value: Wartość do filtrowania (może być id lub tekst)
            
        Returns:
            Przefiltrowana lista relacji
        """
        filtered = []
        entity_plural = entity_type + "s"
        
        # Obsługa specjalnych przypadków
        if entity_type == "species":
            entity_plural = "species"
        elif entity_type == "chemical":
            entity_plural = "chemicals"
        
        for rel in relationships:
            if entity_plural in rel:
                for entity in rel[entity_plural]:
                    if entity.get("text") == entity_value or entity.get("id") == entity_value:
                        filtered.append(rel)
                        break 
                        
        return filtered 