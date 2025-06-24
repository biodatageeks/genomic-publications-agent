"""
UnifiedLlmContextAnalyzer combines the functionality of LlmContextAnalyzer and EnhancedLlmContextAnalyzer
into a single class with improved caching, error handling, and relationship scoring.
"""

import csv
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from collections import defaultdict

import bioc
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from src.api.clients.pubtator_client import PubTatorClient
from src.api.clients.exceptions import PubTatorError
from src.analysis.context.context_analyzer import ContextAnalyzer
from src.utils.llm.manager import LlmManager
from src.api.cache.cache import APICache


class UnifiedLlmContextAnalyzer(ContextAnalyzer):
    """
    Analyzer of contextual relationships between variants and other biomedical entities
    using language models (LLM).
    
    This class identifies relationships between variants and other entities (genes, diseases, tissues)
    in the context of passages from biomedical publications, using LLM models to analyze text 
    and detect semantic relationships with a strength score from 0 to 10.
    
    Features:
    - Advanced JSON error handling
    - Optimized caching with model name tracking
    - Relationship strength scoring (0-10)
    - Debugging options
    
    Example usage:
        analyzer = UnifiedLlmContextAnalyzer()
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
biomedical entities. Your task is to determine whether there are semantic relationships between a genetic 
variant and other biomedical entities in the provided text. 

Important: Only identify semantic relationships where the variant and entity are directly connected in the text.
Do not infer relationships that are not explicitly or implicitly stated in the passage.

Score the strength of each relationship from 0 to 10:
- 0: No relationship at all
- 1-3: Weak relationship (mentioned together but connection unclear)
- 4-7: Moderate relationship (some explicit connection)
- 8-10: Strong relationship (clear causal or direct relationship)

Respond only in JSON format containing information about the relationships.
"""
    
    # User prompt template
    USER_PROMPT_TEMPLATE = """Analyze the provided biomedical text fragment and determine whether there are 
semantic relationships between the variant {variant_text} and the following biomedical entities:

{entities_list}

Respond in a strictly defined JSON format, where for each entity you specify:
1. Whether there is a relationship with the variant (true/false)
2. The strength of the relationship on a scale from 0 to 10 (0 = no relationship, 10 = strongest relationship)
3. Brief justification of your decision (1-2 sentences)

Text fragment: "{passage_text}"

Response format:
{{
  "relationships": [
    {{
      "entity_type": "entity type, e.g., gene",
      "entity_text": "entity text",
      "entity_id": "entity identifier",
      "has_relationship": true/false,
      "relationship_score": 0-10,
      "explanation": "Brief justification of the decision"
    }},
    ...
  ]
}}
"""
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None, 
                 llm_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
                 use_cache: bool = True, cache_ttl: int = 86400,
                 cache_storage_type: str = "memory",
                 debug_mode: bool = False):
        """
        Initializes the Unified LLM Context Analyzer.
        
        Args:
            pubtator_client: Optional PubTator client
            llm_model_name: Name of the LLM model to use
            use_cache: Whether to use cache for LLM queries (default True)
            cache_ttl: Time-to-live for cache entries in seconds (default 24h)
            cache_storage_type: Type of cache: "memory" or "disk"
            debug_mode: Whether to enable debugging mode (more logs)
        """
        super().__init__(pubtator_client)
        self.logger = logging.getLogger(__name__)
        self.llm_model_name = llm_model_name
        self.llm_manager = LlmManager('together', llm_model_name)
        self.llm = self.llm_manager.get_llm()
        self.logger.info(f'Loaded LLM model: {llm_model_name}')
        
        # Initialize cache
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.cache_storage_type = cache_storage_type
        
        if use_cache:
            self.cache = APICache.create(storage_type=cache_storage_type, ttl=cache_ttl)
            self.logger.info(f"Cache enabled ({cache_storage_type}), TTL: {cache_ttl}s")
        else:
            self.cache = None
            self.logger.info("Cache disabled")
            
        # Debug settings
        self.debug_mode = debug_mode
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info("Debug mode enabled")
    
    def analyze_publications(self, pmids: List[str], save_debug_info: bool = False) -> List[Dict[str, Any]]:
        """
        Analyzes a list of publications to extract contextual relationships.
        
        Args:
            pmids: List of PubMed identifiers to analyze
            save_debug_info: Whether to save debugging information
            
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
            
            # If debug mode is enabled, save error information
            if save_debug_info and self.debug_mode:
                debug_info = {
                    "pmids": pmids,
                    "successful_count": len(relationships),
                    "unsuccessful_pmids": [pmid for pmid in pmids if not any(rel["pmid"] == pmid for rel in relationships)]
                }
                
                with open("debug_analyze_publications.json", "w", encoding="utf-8") as f:
                    json.dump(debug_info, f, indent=2)
                
                self.logger.info(f"Saved debugging information to debug_analyze_publications.json")
                
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
                    if entity_type and entity_type in self.ENTITY_TYPES:
                        # Only add if has_relationship is True
                        if rel.get("has_relationship", False):
                            entity_data = {
                                "text": rel.get("entity_text", ""),
                                "id": rel.get("entity_id", ""),
                                "explanation": rel.get("explanation", ""),
                                "relationship_score": rel.get("relationship_score", 0)
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
        Includes relationship score and enhanced error handling.
        
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
        
        # Check cache (use model name in the cache key)
        cache_key = f"llm_analysis:{self.llm_model_name}:{variant_text}:{json.dumps(entities, sort_keys=True)}:{passage_text}"
        if self.use_cache and self.cache and self.cache.has(cache_key):
            self.logger.debug(f"Cache hit for LLM analysis: {variant_text} (model: {self.llm_model_name})")
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
                
                # First, clean the response from surrounding text
                clean_json = self._clean_json_response(response_str)
                
                # Then fix any JSON errors
                fixed_json = self._attempt_json_fix(clean_json)
                
                result_data = json.loads(fixed_json)
                
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
        
        # If debug mode is enabled, log the original response
        if self.debug_mode:
            self.logger.debug(f"Original JSON response: {json_str}")
            
        return json_str
    
    def _fix_trailing_commas(self, json_str: str) -> str:
        """
        Fixes issues related to trailing commas in JSON.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Remove commas after the last element in objects
        json_str = re.sub(r',(\s*})', r'\1', json_str)
        
        # Remove commas after the last element in arrays
        json_str = re.sub(r',(\s*])', r'\1', json_str)
        
        return json_str
    
    def _fix_missing_commas(self, json_str: str) -> str:
        """
        Adds missing commas between elements.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Pattern to add a comma after a property before the next property
        # Recognizes situations where a new key follows immediately after closing a value (quote, brace, number)
        json_str = re.sub(r'(["}\d])\s+(")', r'\1, \2', json_str)
        
        return json_str
    
    def _fix_missing_quotes(self, json_str: str) -> str:
        """
        Attempts to fix missing quotes in keys and values.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Fix keys without quotes
        json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', json_str)
        
        return json_str
    
    def _fix_inconsistent_quotes(self, json_str: str) -> str:
        """
        Fixes inconsistent quotes (mixing ' and ").
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Replace all single quotes with double quotes
        in_string = False
        result = []
        
        i = 0
        while i < len(json_str):
            char = json_str[i]
            
            if char == '"':
                # Start or end a string with double quotes
                in_string = not in_string
                result.append(char)
            elif char == "'" and not in_string:
                # Replace single quotes with double quotes outside of strings
                result.append('"')
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _attempt_json_fix(self, json_str: str) -> str:
        """
        Attempts to fix invalid JSON by applying various repair methods.
        
        Args:
            json_str: Potentially invalid JSON string
            
        Returns:
            Fixed JSON string (or original if repair fails)
        """
        try:
            # First, check if the JSON is already valid
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            self.logger.info(f"Detected JSON error: {str(e)}")
            if self.debug_mode:
                self.logger.debug(f"Problematic JSON (snippet 100 characters before and after error position):")
                error_pos = e.pos
                start = max(0, error_pos - 100)
                end = min(len(json_str), error_pos + 100)
                self.logger.debug(json_str[start:end])
                if error_pos < len(json_str):
                    self.logger.debug(f"Character at error position: '{json_str[error_pos]}' (code: {ord(json_str[error_pos])})")
            
            # Apply various repair methods
            fixed_json = json_str
            
            # Step 1: Fix trailing commas
            fixed_json = self._fix_trailing_commas(fixed_json)
            
            # Step 2: Fix missing commas
            fixed_json = self._fix_missing_commas(fixed_json)
            
            # Step 3: Fix missing quotes
            fixed_json = self._fix_missing_quotes(fixed_json)
            
            # Step 4: Fix inconsistent quotes
            fixed_json = self._fix_inconsistent_quotes(fixed_json)
            
            try:
                # Check if the fixed JSON is valid
                json.loads(fixed_json)
                self.logger.info("JSON fixed")
                if self.debug_mode:
                    self.logger.debug(f"Fixed JSON: {fixed_json[:100]}...")
                return fixed_json
            except json.JSONDecodeError as e:
                self.logger.warning("Failed to fix JSON")
                if self.debug_mode:
                    self.logger.debug(f"Error after fixing: {str(e)}")
                    self.logger.debug(f"Invalid JSON (snippet): {fixed_json[:100]}...")
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
        Saves relationship analysis results to a CSV file.
        
        Args:
            relationships: List of dictionaries containing relationship data
            output_file: Path to the output file
        """
        if not relationships:
            self.logger.warning("No relationships to save")
            return
            
        # Define headers for the CSV file
        headers = [
            "pmid", "variant_text", "variant_id", "variant_offset",
            "gene", "gene_id", "gene_explanation", "gene_score",
            "disease", "disease_id", "disease_explanation", "disease_score",
            "tissue", "tissue_id", "tissue_explanation", "tissue_score",
            "species", "species_id", "species_explanation", "species_score",
            "chemical", "chemical_id", "chemical_explanation", "chemical_score",
            "passage_text"
        ]
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for rel in relationships:
                    # Prepare base row with variant and passage information
                    base_row = {
                        "pmid": rel["pmid"],
                        "variant_text": rel["variant_text"],
                        "variant_id": rel["variant_id"],
                        "variant_offset": rel["variant_offset"],
                        "passage_text": rel["passage_text"]
                    }
                    
                    # Check if there are any relationships
                    entity_types = ["gene", "disease", "tissue", "chemical"]
                    has_relationships = any(len(rel[entity_type + "s"]) > 0 
                                           for entity_type in entity_types) or len(rel["species"]) > 0
                    
                    if not has_relationships:
                        # If no relationships, just write the base row
                        writer.writerow(base_row)
                    else:
                        # For each entity type, add relationship information
                        for entity_type in ["gene", "disease", "tissue", "chemical"]:
                            entities = rel[entity_type + "s"]
                            
                            if not entities:
                                continue
                                
                            for entity in entities:
                                row = base_row.copy()
                                row[entity_type] = entity["text"]
                                row[entity_type + "_id"] = entity["id"]
                                row[entity_type + "_explanation"] = entity["explanation"]
                                row[entity_type + "_score"] = entity.get("relationship_score", 0)
                                writer.writerow(row)
                        
                        # Handle species separately since it doesn't follow the same pattern
                        species_entities = rel["species"]
                        for entity in species_entities:
                            row = base_row.copy()
                            row["species"] = entity["text"]
                            row["species_id"] = entity["id"]
                            row["species_explanation"] = entity["explanation"]
                            row["species_score"] = entity.get("relationship_score", 0)
                            writer.writerow(row)
                
            self.logger.info(f"Saved relationships to file: {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving to CSV file: {str(e)}")
            raise
    
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Saves relationship data to a JSON file.
        
        Args:
            relationships: List of dictionaries containing relationship data
            output_file: Path to the output JSON file
        """
        if not relationships:
            self.logger.warning("No relationships to save")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(relationships, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(relationships)} relationships to {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving relationships to JSON: {str(e)}")
            raise
    
    def filter_relationships_by_entity(
            self, 
            relationships: List[Dict[str, Any]], 
            entity_type: str, 
            entity_value: str) -> List[Dict[str, Any]]:
        """
        Filters relationships by a specific entity value.
        
        Args:
            relationships: List of dictionaries containing relationship data
            entity_type: Type of entity to filter by (gene, disease, etc.)
            entity_value: Value to filter by (can be id or text)
            
        Returns:
            Filtered list of relationships
        """
        filtered = []
        entity_plural = entity_type + "s"
        
        # Handle special cases
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