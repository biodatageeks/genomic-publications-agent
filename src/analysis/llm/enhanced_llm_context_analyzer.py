"""
Enhanced version of the LLM context analyzer with additional debugging 
and error handling capabilities.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from src.api.clients.pubtator_client import PubTatorClient
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer


class EnhancedLlmContextAnalyzer(LlmContextAnalyzer):
    """
    Extended version of the LLM context analyzer with improved JSON error handling.
    
    This class inherits from the base class LlmContextAnalyzer, adding:
    1. Advanced methods for fixing invalid JSON
    2. Better error handling and logging
    3. Additional debugging options
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None, 
                 llm_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
                 use_cache: bool = True, cache_ttl: int = 86400,
                 cache_storage_type: str = "memory",
                 debug_mode: bool = False):
        """
        Initializes the enhanced LLM context analyzer.
        
        Args:
            pubtator_client: Optional PubTator client
            llm_model_name: Name of the LLM model to use
            use_cache: Whether to use cache for LLM queries (default True)
            cache_ttl: Time to live for cache entries in seconds (default 24h)
            cache_storage_type: Cache type: "memory" or "disk"
            debug_mode: Whether to enable debugging mode (more logs)
        """
        super().__init__(pubtator_client, llm_model_name, use_cache, cache_ttl, cache_storage_type)
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)
        
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info("Debug mode enabled")
    
    def _clean_json_response(self, response: str) -> str:
        """
        Cleans the LLM response to obtain a valid JSON format.
        
        Args:
            response: Response from the LLM
            
        Returns:
            Cleaned JSON string
        """
        # First, use the method from the base class
        json_str = super()._clean_json_response(response)
        
        # If debug mode is enabled, log the original response
        if self.debug_mode:
            self.logger.debug(f"Original JSON response: {json_str}")
        
        # Check if the JSON is already valid
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # If not, try to fix the errors
            return self._attempt_json_fix(json_str)
    
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
        results = super().analyze_publications(pmids)
        
        # If debug mode is enabled, save error information
        if save_debug_info and self.debug_mode:
            debug_info = {
                "pmids": pmids,
                "successful_count": len(results),
                "unsuccessful_pmids": [pmid for pmid in pmids if not any(rel["pmid"] == pmid for rel in results)]
            }
            
            with open("debug_analyze_publications.json", "w", encoding="utf-8") as f:
                json.dump(debug_info, f, indent=2)
            
            self.logger.info(f"Saved debugging information to debug_analyze_publications.json")
        
        return results
        
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                      passage_text: str) -> List[Dict[str, Any]]:
        """
        Analyzes relationships between the variant and entities in the passage using LLM.
        Utilizes enhanced JSON fixing mechanisms.
        
        Args:
            variant_text: Variant text
            entities: List of entities in the passage (dictionaries with fields entity_type, text, id, offset)
            passage_text: Passage text
            
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
                
                # First, clean the response from surrounding text
                response_str = self._clean_json_response(response_str)
                
                # Then fix errors in the JSON itself
                fixed_json = self._attempt_json_fix(response_str)
                
                # Try to parse the fixed JSON
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