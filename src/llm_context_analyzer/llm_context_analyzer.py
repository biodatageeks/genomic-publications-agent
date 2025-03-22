"""
LLM Context Analyzer dla publikacji biomedycznych.

Ten moduł dostarcza narzędzia do analizy kontekstu bytów biomedycznych 
w publikacjach naukowych przy użyciu modeli językowych (LLM).
Wykorzystuje adnotacje z API PubTator3 i model Llama 3.1 8B do identyfikacji 
relacji między wariantami a innymi bytami biomedycznymi.
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
from src.LlmManager import LlmManager
from src.cache.cache import APICache


class LlmContextAnalyzer(ContextAnalyzer):
    """
    Analizator relacji kontekstowych między wariantami a innymi bytami biomedycznymi
    wykorzystujący modele językowe (LLM).
    
    Ta klasa identyfikuje relacje między wariantami a innymi bytami (genami, chorobami, tkankami)
    w kontekście pasaży publikacji biomedycznych, używając modelu Llama 3.1 8B
    do analizy tekstu i wykrywania relacji semantycznych.
    
    Przykład użycia:
        analyzer = LlmContextAnalyzer()
        pmids = ["32735606", "32719766"]
        relationships = analyzer.analyze_publications(pmids)
        analyzer.save_relationships_to_csv(relationships, "variant_relationships.csv")
    """
    
    # Typy bytów do ekstrakcji z publikacji
    ENTITY_TYPES = {
        "variant": ["Mutation", "DNAMutation", "Variant"],
        "gene": ["Gene"],
        "disease": ["Disease"],
        "tissue": ["Tissue"],
        "species": ["Species"],
        "chemical": ["Chemical"]
    }
    
    # Szablon promptu systemowego
    SYSTEM_PROMPT = """Jesteś ekspertem w analizie tekstu biomedycznego i rozpoznawaniu relacji między 
bytami biomedycznymi. Twoim zadaniem jest określenie, czy istnieją relacje między wariantem 
genetycznym a innymi bytami biomedycznymi w podanym tekście. Odpowiedz tylko i wyłącznie w 
formacie JSON, zawierającym informacje o relacjach.
"""
    
    # Szablon promptu użytkownika
    USER_PROMPT_TEMPLATE = """Przeanalizuj podany fragment tekstu biomedycznego i określ, czy istnieją 
relacje między wariantem {variant_text} a następującymi bytami biomedycznymi:

{entities_list}

Odpowiedź zwróć w ściśle określonym formacie JSON, gdzie dla każdej encji określisz, czy istnieje 
relacja z wariantem (true/false) i krótko uzasadnisz swoją odpowiedź w 1-2 zdaniach.

Tekst fragmentu: "{passage_text}"

Format odpowiedzi:
{{
  "relationships": [
    {{
      "entity_type": "typ encji, np. gene",
      "entity_text": "tekst encji",
      "entity_id": "identyfikator encji",
      "has_relationship": true/false,
      "explanation": "Krótkie uzasadnienie decyzji"
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
        Inicjalizuje LLM Context Analyzer.
        
        Args:
            pubtator_client: Opcjonalny klient PubTator
            llm_model_name: Nazwa modelu LLM do wykorzystania
            use_cache: Czy używać cache'a dla zapytań do LLM (domyślnie True)
            cache_ttl: Czas życia wpisów w cache'u w sekundach (domyślnie 24h)
            cache_storage_type: Typ cache'a: "memory" lub "disk"
        """
        super().__init__(pubtator_client)
        self.logger = logging.getLogger(__name__)
        self.llm_manager = LlmManager('together', llm_model_name)
        self.llm = self.llm_manager.get_llm()
        self.logger.info(f'Załadowano model LLM: {llm_model_name}')
        
        # Inicjalizacja cache'a
        self.use_cache = use_cache
        if use_cache:
            self.cache = APICache(ttl=cache_ttl, storage_type=cache_storage_type)
            self.logger.info(f"Cache włączony ({cache_storage_type}), TTL: {cache_ttl}s")
        else:
            self.cache = None
            self.logger.info("Cache wyłączony")
    
    def analyze_publications(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Analizuje listę publikacji, aby wydobyć relacje kontekstowe.
        
        Args:
            pmids: Lista identyfikatorów PubMed do analizy
            
        Returns:
            Lista słowników zawierających dane relacji
            
        Raises:
            PubTatorError: Jeśli wystąpi błąd pobierania lub przetwarzania publikacji
        """
        relationships = []
        
        try:
            # Pobierz publikacje z PubTator
            publications = self.pubtator_client.get_publications_by_pmids(pmids)
            
            for publication in publications:
                publication_relationships = self._analyze_publication(publication)
                relationships.extend(publication_relationships)
                
            return relationships
        except Exception as e:
            self.logger.error(f"Błąd analizy publikacji: {str(e)}")
            raise PubTatorError(f"Błąd analizy publikacji: {str(e)}") from e
    
    def analyze_publication(self, pmid: str) -> List[Dict[str, Any]]:
        """
        Analizuje pojedynczą publikację, aby wydobyć relacje kontekstowe.
        
        Args:
            pmid: Identyfikator PubMed do analizy
            
        Returns:
            Lista słowników zawierających dane relacji
            
        Raises:
            PubTatorError: Jeśli wystąpi błąd pobierania lub przetwarzania publikacji
        """
        try:
            publication = self.pubtator_client.get_publication_by_pmid(pmid)
            if not publication:
                self.logger.warning(f"Nie znaleziono publikacji dla PMID: {pmid}")
                return []
                
            return self._analyze_publication(publication)
        except PubTatorError as e:
            self.logger.error(f"Błąd analizy publikacji {pmid}: {str(e)}")
            raise
        
        # Dodajemy domyślny zwrot pustej listy w przypadku nieprzewidzianego przepływu kontroli
        return []
    
    def _analyze_publication(self, publication: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Wydobywa relacje kontekstowe z pojedynczej publikacji.
        
        Args:
            publication: Obiekt BioCDocument zawierający publikację z adnotacjami
            
        Returns:
            Lista słowników zawierających dane relacji
        """
        relationships = []
        pmid = publication.id
        
        # Przetwórz każdy pasaż w publikacji
        for passage in publication.passages:
            passage_relationships = self._analyze_passage(pmid, passage)
            relationships.extend(passage_relationships)
        
        return relationships
    
    def _analyze_passage(self, pmid: str, passage: bioc.BioCPassage) -> List[Dict[str, Any]]:
        """
        Wydobywa relacje kontekstowe z pojedynczego pasażu przy użyciu LLM.
        
        Args:
            pmid: Identyfikator PubMed publikacji
            passage: Obiekt BioCPassage zawierający pasaż z adnotacjami
            
        Returns:
            Lista słowników zawierających dane relacji dla tego pasażu
        """
        relationships = []
        
        # Grupuj adnotacje w pasażu według typu
        entities_by_type = self._group_annotations_by_type(passage)
        
        # Jeśli brak wariantów w tym pasażu, zwróć pustą listę
        if not any(variant_type in entities_by_type for variant_type in self.ENTITY_TYPES["variant"]):
            return []
        
        # Pobierz wszystkie warianty
        variants = []
        for variant_type in self.ENTITY_TYPES["variant"]:
            if variant_type in entities_by_type:
                variants.extend(entities_by_type[variant_type])
        
        # Dla każdego wariantu, utwórz relację z innymi bytami w pasażu
        for variant in variants:
            variant_text = variant.text
            variant_offset = variant.locations[0].offset if variant.locations else None
            
            # Utwórz słownik z danymi bazowymi relacji
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
            
            # Przygotuj listę wszystkich bytów w pasażu (poza wariantami)
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
            
            # Jeśli nie ma innych bytów w pasażu, pomiń analizę LLM
            if not all_entities:
                relationships.append(relationship)
                continue
            
            # Analizuj relacje między wariantem a innymi bytami za pomocą LLM
            llm_relationships = self._analyze_relationships_with_llm(
                variant_text=variant_text, 
                entities=all_entities, 
                passage_text=passage.text
            )
            
            # Przetwórz wyniki z LLM
            if llm_relationships:
                for rel in llm_relationships:
                    entity_type = rel.get("entity_type", "").lower()
                    if entity_type and entity_type in relationship and rel.get("has_relationship", False):
                        entity_data = {
                            "text": rel.get("entity_text", ""),
                            "id": rel.get("entity_id", ""),
                            "explanation": rel.get("explanation", "")
                        }
                        relationship[entity_type + "s"].append(entity_data)
            
            relationships.append(relationship)
        
        return relationships
    
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                      passage_text: str) -> List[Dict[str, Any]]:
        """
        Analizuje relacje między wariantem a bytami w pasażu za pomocą LLM.
        
        Args:
            variant_text: Tekst wariantu
            entities: Lista bytów w pasażu (słowniki z polami entity_type, text, id, offset)
            passage_text: Tekst pasażu
            
        Returns:
            Lista słowników zawierających dane relacji określone przez LLM
        """
        if not entities:
            return []
            
        # Przygotuj listę bytów w formacie dla promptu
        entities_list = "\n".join([f"- {e['entity_type']}: {e['text']} (ID: {e['id']})" for e in entities])
        
        # Sprawdź cache
        if self.use_cache and self.cache:
            cache_key = f"llm_analysis:{variant_text}:{json.dumps(entities, sort_keys=True)}:{passage_text}"
            if self.cache.has(cache_key):
                self.logger.debug(f"Cache hit dla analizy LLM: {variant_text}")
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
                
                # Usuń ewentualne znaki specjalne i kod markdown z JSON
                clean_json = self._clean_json_response(response_str)
                result_data = json.loads(clean_json)
                
                if "relationships" in result_data:
                    # Zapisz do cache'a
                    if self.use_cache and self.cache:
                        self.cache.set(f"llm_analysis:{variant_text}:{json.dumps(entities, sort_keys=True)}:{passage_text}", 
                                      result_data["relationships"])
                    
                    return result_data["relationships"]
                else:
                    self.logger.warning(f"Nieprawidłowa struktura odpowiedzi LLM: brak pola 'relationships'")
                    return []
            except json.JSONDecodeError as e:
                self.logger.error(f"Błąd parsowania odpowiedzi LLM: {str(e)}")
                self.logger.debug(f"Odpowiedź LLM: {response_content}")
                return []
        except Exception as e:
            self.logger.error(f"Błąd wywołania LLM: {str(e)}")
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """
        Czyści odpowiedź LLM, aby uzyskać poprawny format JSON.
        
        Args:
            response: Odpowiedź od LLM
            
        Returns:
            Oczyszczony string JSON
        """
        # Znajdź pierwszy znak '{' i ostatni znak '}'
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
            # Jeśli nie znaleziono poprawnego JSON, zwróć pusty obiekt
            return "{}"
        
        # Wytnij JSON z odpowiedzi
        json_str = response[start_idx:end_idx+1]
        return json_str
    
    def _group_annotations_by_type(self, passage: bioc.BioCPassage) -> Dict[str, List[bioc.BioCAnnotation]]:
        """
        Grupuje adnotacje w pasażu według typu.
        
        Args:
            passage: Obiekt BioCPassage zawierający pasaż z adnotacjami
            
        Returns:
            Słownik mapujący typy adnotacji na listy obiektów BioCAnnotation
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