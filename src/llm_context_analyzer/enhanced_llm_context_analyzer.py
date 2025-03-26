"""
Ulepszona wersja analizatora kontekstu LLM z dodatkowymi możliwościami 
debugowania i obsługi błędów.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from src.pubtator_client.pubtator_client import PubTatorClient
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer


class EnhancedLlmContextAnalyzer(LlmContextAnalyzer):
    """
    Rozszerzona wersja analizatora kontekstowego LLM z ulepszoną obsługą błędów JSON.
    
    Ta klasa dziedziczy z podstawowej klasy LlmContextAnalyzer, dodając:
    1. Zaawansowane metody naprawy niepoprawnego JSON
    2. Lepszą obsługę błędów i logowanie
    3. Dodatkowe opcje debugowania
    """
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None, 
                 llm_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
                 use_cache: bool = True, cache_ttl: int = 86400,
                 cache_storage_type: str = "memory",
                 debug_mode: bool = False):
        """
        Inicjalizuje rozszerzony analizator kontekstowy LLM.
        
        Args:
            pubtator_client: Opcjonalny klient PubTator
            llm_model_name: Nazwa modelu LLM do użycia
            use_cache: Czy używać cache dla zapytań LLM (domyślnie True)
            cache_ttl: Czas życia wpisów w cache w sekundach (domyślnie 24h)
            cache_storage_type: Typ cache: "memory" lub "disk"
            debug_mode: Czy włączyć tryb debugowania (więcej logów)
        """
        super().__init__(pubtator_client, llm_model_name, use_cache, cache_ttl, cache_storage_type)
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)
        
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info("Tryb debugowania włączony")
    
    def _clean_json_response(self, response: str) -> str:
        """
        Czyści odpowiedź LLM, aby uzyskać poprawny format JSON.
        
        Args:
            response: Odpowiedź z LLM
            
        Returns:
            Oczyszczony ciąg JSON
        """
        # Najpierw użyj metody z klasy bazowej
        json_str = super()._clean_json_response(response)
        
        # Jeśli tryb debugowania jest włączony, zapisz oryginalną odpowiedź
        if self.debug_mode:
            self.logger.debug(f"Oryginalna odpowiedź JSON: {json_str}")
        
        # Sprawdź, czy JSON jest już poprawny
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # Jeśli nie, spróbuj naprawić błędy
            return self._attempt_json_fix(json_str)
    
    def _fix_trailing_commas(self, json_str: str) -> str:
        """
        Naprawia błędy związane z przecinkami końcowymi w JSON.
        
        Args:
            json_str: Ciąg JSON do naprawy
            
        Returns:
            Naprawiony ciąg JSON
        """
        # Usuń przecinki po ostatnim elemencie w obiektach
        json_str = re.sub(r',(\s*})', r'\1', json_str)
        
        # Usuń przecinki po ostatnim elemencie w tablicach
        json_str = re.sub(r',(\s*])', r'\1', json_str)
        
        return json_str
    
    def _fix_missing_commas(self, json_str: str) -> str:
        """
        Dodaje brakujące przecinki między elementami.
        
        Args:
            json_str: Ciąg JSON do naprawy
            
        Returns:
            Naprawiony ciąg JSON
        """
        # Wzór dodający przecinek po właściwości przed następną właściwością
        # Rozpoznaje sytuacje, gdy po zamknięciu wartości (cudzysłów, nawias, liczba) następuje bezpośrednio nowy klucz
        json_str = re.sub(r'(["}\d])\s+(")', r'\1, \2', json_str)
        
        return json_str
    
    def _fix_missing_quotes(self, json_str: str) -> str:
        """
        Próbuje naprawić brakujące cudzysłowy w kluczach i wartościach.
        
        Args:
            json_str: Ciąg JSON do naprawy
            
        Returns:
            Naprawiony ciąg JSON
        """
        # Napraw klucze bez cudzysłowów
        json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', json_str)
        
        return json_str
    
    def _fix_inconsistent_quotes(self, json_str: str) -> str:
        """
        Naprawia niekonsekwentne cudzysłowy (miesza ' i ").
        
        Args:
            json_str: Ciąg JSON do naprawy
            
        Returns:
            Naprawiony ciąg JSON
        """
        # Zamień wszystkie pojedyncze cudzysłowy na podwójne
        in_string = False
        result = []
        
        i = 0
        while i < len(json_str):
            char = json_str[i]
            
            if char == '"':
                # Rozpocznij lub zakończ ciąg znaków z podwójnymi cudzysłowami
                in_string = not in_string
                result.append(char)
            elif char == "'" and not in_string:
                # Zamień pojedyncze cudzysłowy na podwójne poza ciągami znaków
                result.append('"')
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _attempt_json_fix(self, json_str: str) -> str:
        """
        Próbuje naprawić niepoprawny JSON, stosując różne metody naprawcze.
        
        Args:
            json_str: Potencjalnie niepoprawny ciąg JSON
            
        Returns:
            Naprawiony ciąg JSON (lub oryginalny, jeśli naprawa się nie powiodła)
        """
        try:
            # Najpierw sprawdź, czy JSON jest już poprawny
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            self.logger.info(f"Wykryto błąd JSON: {str(e)}")
            if self.debug_mode:
                self.logger.debug(f"Problematyczny JSON (wycinek 100 znaków przed i po miejscu błędu):")
                error_pos = e.pos
                start = max(0, error_pos - 100)
                end = min(len(json_str), error_pos + 100)
                self.logger.debug(json_str[start:end])
                if error_pos < len(json_str):
                    self.logger.debug(f"Znak w miejscu błędu: '{json_str[error_pos]}' (kod: {ord(json_str[error_pos])})")
            
            # Zastosuj różne metody naprawcze
            fixed_json = json_str
            
            # Krok 1: Napraw przecinki końcowe
            fixed_json = self._fix_trailing_commas(fixed_json)
            
            # Krok 2: Napraw brakujące przecinki
            fixed_json = self._fix_missing_commas(fixed_json)
            
            # Krok 3: Napraw brakujące cudzysłowy
            fixed_json = self._fix_missing_quotes(fixed_json)
            
            # Krok 4: Napraw niekonsekwentne cudzysłowy
            fixed_json = self._fix_inconsistent_quotes(fixed_json)
            
            try:
                # Sprawdź, czy naprawiony JSON jest poprawny
                json.loads(fixed_json)
                self.logger.info("Naprawiono JSON")
                if self.debug_mode:
                    self.logger.debug(f"Naprawiony JSON: {fixed_json[:100]}...")
                return fixed_json
            except json.JSONDecodeError as e:
                self.logger.warning("Nie udało się naprawić JSON")
                if self.debug_mode:
                    self.logger.debug(f"Błąd po naprawie: {str(e)}")
                    self.logger.debug(f"Niepoprawiony JSON (wycinek): {fixed_json[:100]}...")
                return json_str
    
    def analyze_publications(self, pmids: List[str], save_debug_info: bool = False) -> List[Dict[str, Any]]:
        """
        Analizuje listę publikacji, aby wyodrębnić kontekstowe relacje.
        
        Args:
            pmids: Lista identyfikatorów PubMed do analizy
            save_debug_info: Czy zapisać informacje debugowania
            
        Returns:
            Lista słowników zawierających dane relacji
            
        Raises:
            PubTatorError: Jeśli wystąpi błąd podczas pobierania lub przetwarzania publikacji
        """
        results = super().analyze_publications(pmids)
        
        # Jeśli tryb debugowania jest włączony, zapisz informacje o błędach
        if save_debug_info and self.debug_mode:
            debug_info = {
                "pmids": pmids,
                "successful_count": len(results),
                "unsuccessful_pmids": [pmid for pmid in pmids if not any(rel["pmid"] == pmid for rel in results)]
            }
            
            with open("debug_analyze_publications.json", "w", encoding="utf-8") as f:
                json.dump(debug_info, f, indent=2)
            
            self.logger.info(f"Zapisano informacje debugowania do debug_analyze_publications.json")
        
        return results
        
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                      passage_text: str) -> List[Dict[str, Any]]:
        """
        Analizuje relacje między wariantem a encjami w pasażu, używając LLM.
        Wykorzystuje ulepszone mechanizmy naprawiania JSON.
        
        Args:
            variant_text: Tekst wariantu
            entities: Lista encji w pasażu (słowniki z polami entity_type, text, id, offset)
            passage_text: Tekst pasażu
            
        Returns:
            Lista słowników zawierających dane relacji określone przez LLM
        """
        if not entities:
            return []
            
        # Przygotuj listę encji w formacie do promptu
        entities_list = "\n".join([f"- {e['entity_type']}: {e['text']} (ID: {e['id']})" for e in entities])
        
        # Sprawdź cache
        cache_key = f"llm_analysis:{variant_text}:{json.dumps(entities, sort_keys=True)}:{passage_text}"
        if self.use_cache and self.cache and self.cache.has(cache_key):
            self.logger.debug(f"Cache hit for LLM analysis: {variant_text}")
            return self.cache.get(cache_key)
        
        # Przygotuj wiadomości dla LLM
        system_message = SystemMessage(content=self.SYSTEM_PROMPT)
        
        prompt_template = PromptTemplate.from_template(self.USER_PROMPT_TEMPLATE)
        user_message_content = prompt_template.format(
            variant_text=variant_text,
            entities_list=entities_list,
            passage_text=passage_text
        )
        user_message = HumanMessage(content=user_message_content)
        
        # Wyślij zapytanie do LLM
        try:
            response = self.llm.invoke([system_message, user_message])
            response_content = response.content
            
            # Parsuj odpowiedź JSON
            try:
                # Upewnij się, że response_content jest typu string
                response_str = str(response_content) if response_content is not None else "{}"
                
                # Najpierw wyczyść odpowiedź z tekstu otaczającego JSON
                response_str = self._clean_json_response(response_str)
                
                # Następnie napraw błędy w samym JSON
                fixed_json = self._attempt_json_fix(response_str)
                
                # Spróbuj sparsować naprawiony JSON
                result_data = json.loads(fixed_json)
                
                if "relationships" in result_data:
                    # Zapisz do cache
                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, result_data["relationships"])
                    
                    return result_data["relationships"]
                else:
                    self.logger.warning(f"Nieprawidłowa struktura odpowiedzi LLM: brak pola 'relationships'")
                    return []
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing LLM response: {str(e)}")
                self.logger.debug(f"LLM response: {response_content}")
                return []
        except Exception as e:
            self.logger.error(f"Error calling LLM: {str(e)}")
            return [] 