"""
Analyzer for contextual relationships between variants and other biomedical entities
using language models (LLM).

This module contains the UnifiedLlmContextAnalyzer class which identifies 
relationships between variants and other entities (genes, diseases, tissues)
in biomedical publications using LLM analysis.
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

from src.models.data.clients.pubtator import PubTatorClient
from src.models.data.clients.exceptions import PubTatorError
from src.analysis.base.analyzer import BaseAnalyzer
from src.utils.llm.manager import LlmManager
from src.api.cache.cache import CacheManager


class UnifiedLlmContextAnalyzer(BaseAnalyzer):
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
            self.cache = CacheManager.create(storage_type=cache_storage_type, ttl=cache_ttl)
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
                
                debug_dir = os.path.join("data", "debug")
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, "debug_analyze_publications.json")
                
                with open(debug_path, "w", encoding="utf-8") as f:
                    json.dump(debug_info, f, indent=2)
                
                self.logger.info(f"Saved debugging information to {debug_path}")
                
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
            return self._analyze_publication(publication)
        except Exception as e:
            self.logger.error(f"Error analyzing publication {pmid}: {str(e)}")
            raise PubTatorError(f"Error analyzing publication {pmid}: {str(e)}") from e
    
    def _analyze_publication(self, publication: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Analyzes a publication to extract contextual relationships.
        
        Args:
            publication: BioCDocument to analyze
            
        Returns:
            List of dictionaries containing relationship data
        """
        publication_relationships = []
        pmid = publication.id
        
        for passage in publication.passages:
            passage_relationships = self._analyze_passage(pmid, passage)
            publication_relationships.extend(passage_relationships)
        
        return publication_relationships
    
    def _analyze_passage(self, pmid: str, passage: bioc.BioCPassage) -> List[Dict[str, Any]]:
        """
        Analyzes a passage to extract contextual relationships between variants and other entities.
        
        Args:
            pmid: PubMed identifier
            passage: BioCPassage to analyze
            
        Returns:
            List of dictionaries containing relationship data
        """
        passage_relationships = []
        passage_text = passage.text
        
        # Group annotations by entity type
        grouped_annotations = self._group_annotations_by_type(passage)
        
        # Find variant annotations
        variant_annotations = []
        for entity_type in self.ENTITY_TYPES["variant"]:
            if entity_type in grouped_annotations:
                variant_annotations.extend(grouped_annotations[entity_type])
        
        # For each variant, analyze relationships with other entities
        for variant_annotation in variant_annotations:
            variant_text = variant_annotation.text
            variant_id = variant_annotation.id
            
            # Create a list of entities to check for relationships
            entities = []
            
            # Add all entities except variants to the list
            for entity_category, entity_types in self.ENTITY_TYPES.items():
                if entity_category == "variant":
                    continue
                
                for entity_type in entity_types:
                    if entity_type in grouped_annotations:
                        for annotation in grouped_annotations[entity_type]:
                            entities.append({
                                "entity_category": entity_category,
                                "entity_type": entity_type,
                                "entity_text": annotation.text,
                                "entity_id": annotation.id
                            })
            
            # Skip if no other entities in the passage
            if not entities:
                continue
            
            # Use LLM to determine relationships
            relationships = self._analyze_relationships_with_llm(variant_text, entities, passage_text)
            
            # Add metadata to relationships
            for relationship in relationships:
                relationship["pmid"] = pmid
                relationship["passage_text"] = passage_text
                relationship["variant_text"] = variant_text
                relationship["variant_id"] = variant_id
                
                passage_relationships.append(relationship)
        
        return passage_relationships
    
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                      passage_text: str) -> List[Dict[str, Any]]:
        """
        Analyzes relationships between a variant and other entities using LLM.
        
        Args:
            variant_text: Text of the variant
            entities: List of entities to check for relationships
            passage_text: Text of the passage
            
        Returns:
            List of dictionaries containing relationship data
        """
        # Generate cache key based on inputs and model name
        if self.use_cache:
            cache_key = f"relationship_{variant_text}_{hash(str(entities))}_{hash(passage_text)}_{self.llm_model_name}"
            cached_result = self.cache.get(cache_key)
            
            if cached_result:
                self.logger.debug(f"Using cached LLM result for variant {variant_text}")
                return cached_result
        
        # Prepare entities list for prompt
        entities_list = "\n".join([
            f"- {entity['entity_category']} '{entity['entity_text']}' (ID: {entity['entity_id']})"
            for entity in entities
        ])
        
        # Prepare the user prompt
        prompt = self.USER_PROMPT_TEMPLATE.format(
            variant_text=variant_text,
            entities_list=entities_list,
            passage_text=passage_text
        )
        
        # Create messages for LLM
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        try:
            # Get response from LLM
            self.logger.debug(f"Querying LLM for variant {variant_text}")
            response = self.llm.invoke(messages)
            response_text = response.content
            
            # Attempt to fix and parse JSON
            clean_json = self._attempt_json_fix(response_text)
            result = json.loads(clean_json)
            
            # Extract relationship data
            relationships = result.get("relationships", [])
            
            # Cache the result if caching is enabled
            if self.use_cache:
                self.cache.set(cache_key, relationships)
            
            return relationships
        except Exception as e:
            self.logger.error(f"Error querying LLM for variant {variant_text}: {str(e)}")
            self.logger.debug(f"Error details: {str(e)}, response: {response_text if 'response_text' in locals() else 'N/A'}")
            
            if self.debug_mode:
                debug_dir = os.path.join("data", "debug")
                os.makedirs(debug_dir, exist_ok=True)
                error_file = os.path.join(debug_dir, f"llm_error_{hash(variant_text)}.txt")
                
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(f"Variant: {variant_text}\n")
                    f.write(f"Passage: {passage_text}\n")
                    f.write(f"Entities: {entities}\n")
                    f.write(f"Error: {str(e)}\n")
                    if 'response_text' in locals():
                        f.write(f"Response: {response_text}\n")
                
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """
        Attempts to extract JSON from the LLM response.
        
        Args:
            response: Response from LLM
            
        Returns:
            Cleaned JSON string
        """
        # Try to find JSON block in markdown code blocks
        if "```" in response:
            json_blocks = re.findall(r"```(?:json)?(.*?)```", response, re.DOTALL)
            if json_blocks:
                return json_blocks[0].strip()
        
        # Try to find JSON block with curly braces
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Return original if no JSON found
        return response
    
    def _fix_trailing_commas(self, json_str: str) -> str:
        """
        Fixes trailing commas in JSON strings.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Fix trailing commas in arrays
        json_str = re.sub(r",\s*]", "]", json_str)
        # Fix trailing commas in objects
        json_str = re.sub(r",\s*}", "}", json_str)
        return json_str
    
    def _fix_missing_commas(self, json_str: str) -> str:
        """
        Fixes missing commas in JSON strings.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Fix missing commas between array elements (simplified)
        json_str = re.sub(r"}\s*{", "},{", json_str)
        # Fix missing commas between object properties (simplified)
        json_str = re.sub(r'"\s*"', '","', json_str)
        return json_str
    
    def _fix_missing_quotes(self, json_str: str) -> str:
        """
        Fixes missing quotes around property names.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Add quotes around unquoted property names (simplified approach)
        json_str = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        return json_str
    
    def _fix_inconsistent_quotes(self, json_str: str) -> str:
        """
        Fixes inconsistent quotes in JSON strings.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # Replace single quotes with double quotes
        # This is a simplified approach and may not handle nested quotes correctly
        in_string = False
        in_single_quote_string = False
        result = []
        
        for i, char in enumerate(json_str):
            if char == '"' and (i == 0 or json_str[i-1] != '\\'):
                in_string = not in_string
                result.append(char)
            elif char == "'" and (i == 0 or json_str[i-1] != '\\'):
                if not in_string:
                    # Replace ' with " when not inside a double-quoted string
                    result.append('"')
                    in_single_quote_string = not in_single_quote_string
                else:
                    # Keep ' when inside a double-quoted string
                    result.append(char)
            else:
                result.append(char)
                
        return ''.join(result)
    
    def _attempt_json_fix(self, json_str: str) -> str:
        """
        Attempts to fix common JSON formatting issues.
        
        Args:
            json_str: JSON string to fix
            
        Returns:
            Fixed JSON string
        """
        # First extract the JSON part if it's embedded in other text
        json_str = self._clean_json_response(json_str)
        
        # Apply a series of fixes
        fixes = [
            self._fix_inconsistent_quotes,
            self._fix_trailing_commas,
            self._fix_missing_commas,
            self._fix_missing_quotes
        ]
        
        # Try parsing after each fix
        for fix_func in fixes:
            try:
                fixed = fix_func(json_str)
                json.loads(fixed)  # Test if valid JSON
                return fixed
            except json.JSONDecodeError:
                # If still invalid, apply the fix and continue to the next
                json_str = fix_func(json_str)
        
        # If we reach here, all automated fixes have been applied
        # But JSON might still be invalid
        try:
            # One last validation
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            # Last resort: try to create a minimal valid JSON with relationships array
            if self.debug_mode:
                self.logger.debug(f"JSON repair failed: {str(e)}\nAttempting minimal JSON structure")
                
            # Create minimal JSON structure
            return '{"relationships": []}'
    
    def _group_annotations_by_type(self, passage: bioc.BioCPassage) -> Dict[str, List[bioc.BioCAnnotation]]:
        """
        Groups annotations in a passage by entity type.
        
        Args:
            passage: BioCPassage to analyze
            
        Returns:
            Dictionary mapping entity types to annotations
        """
        grouped = defaultdict(list)
        
        for annotation in passage.annotations:
            entity_type = annotation.infons.get("type")
            if entity_type:
                grouped[entity_type].append(annotation)
        
        return grouped
    
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str):
        """
        Saves relationships to a CSV file.
        
        Args:
            relationships: List of relationship dictionaries
            output_file: Path to the output CSV file
        """
        if not relationships:
            self.logger.warning("No relationships to save to CSV")
            return
        
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            # Determine all possible fields
            all_fields = set()
            for rel in relationships:
                all_fields.update(rel.keys())
            
            # Define fields order for CSV (ensure key fields come first)
            key_fields = [
                "pmid", "variant_id", "variant_text", 
                "entity_id", "entity_text", "entity_type", "entity_category",
                "has_relationship", "relationship_score", "explanation"
            ]
            
            # Include remaining fields after key fields
            other_fields = [f for f in sorted(all_fields) if f not in key_fields]
            fields = key_fields + other_fields
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                
                # Write rows, handling missing fields
                for relationship in relationships:
                    # Create a row with all fields (empty values for missing fields)
                    row = {field: relationship.get(field, "") for field in fields}
                    writer.writerow(row)
                    
            self.logger.info(f"Saved {len(relationships)} relationships to CSV: {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save relationships to CSV: {str(e)}")
            raise
    
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Saves relationships to a JSON file.
        
        Args:
            relationships: List of relationship dictionaries
            output_file: Path to the output JSON file
        """
        if not relationships:
            self.logger.warning("No relationships to save to JSON")
            return
        
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(relationships, f, indent=2)
                
            self.logger.info(f"Saved {len(relationships)} relationships to JSON: {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save relationships to JSON: {str(e)}")
            raise
    
    def filter_relationships_by_entity(
            self, 
            relationships: List[Dict[str, Any]], 
            entity_type: str, 
            entity_value: str) -> List[Dict[str, Any]]:
        """
        Filters relationships by entity type and value.
        
        Args:
            relationships: List of relationship dictionaries
            entity_type: Type of entity to filter by (e.g., 'gene', 'disease')
            entity_value: Value to filter by (e.g., 'BRCA1', 'breast cancer')
            
        Returns:
            List of filtered relationships
        """
        filtered = []
        
        for rel in relationships:
            # Filter by entity category and text
            if rel.get("entity_category") == entity_type and rel.get("entity_text") == entity_value:
                filtered.append(rel)
        
        return filtered 