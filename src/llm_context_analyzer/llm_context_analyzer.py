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
                 llm_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"):
        """
        Inicjalizuje LLM Context Analyzer.
        
        Args:
            pubtator_client: Opcjonalny klient PubTator
            llm_model_name: Nazwa modelu LLM do wykorzystania
        """
        super().__init__(pubtator_client)
        self.logger = logging.getLogger(__name__)
        self.llm_manager = LlmManager('together', llm_model_name)
        self.llm = self.llm_manager.get_llm()
        self.logger.info(f'Załadowano model LLM: {llm_model_name}')
    
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
                self._process_llm_results(relationship, llm_relationships)
            
            relationships.append(relationship)
        
        return relationships
    
    def _analyze_relationships_with_llm(self, variant_text: str, entities: List[Dict[str, Any]], 
                                        passage_text: str) -> Dict[str, Any]:
        """
        Analizuje relacje między wariantem a innymi bytami przy użyciu LLM.
        
        Args:
            variant_text: Tekst wariantu
            entities: Lista bytów do analizy relacji
            passage_text: Tekst pasażu
            
        Returns:
            Słownik zawierający odpowiedź LLM z analizą relacji
        """
        try:
            # Przygotuj listę bytów dla promptu
            entities_list = "\n".join([
                f"- {entity['entity_type'].capitalize()}: {entity['text']} (ID: {entity['id']})"
                for entity in entities
            ])
            
            # Przygotuj prompt dla LLM
            prompt = PromptTemplate(
                template=self.USER_PROMPT_TEMPLATE,
                input_variables=["variant_text", "entities_list", "passage_text"]
            ).format(
                variant_text=variant_text,
                entities_list=entities_list,
                passage_text=passage_text
            )
            
            # Przygotuj wiadomości dla modelu
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            # Wywołaj model LLM
            response = self.llm.invoke(messages)
            
            # Przetwórz odpowiedź do formatu JSON
            response_content = response.content
            
            if isinstance(response_content, str):
                try:
                    # Próbuj przetworzyć odpowiedź jako JSON
                    response_json = json.loads(response_content)
                    return response_json
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Nie udało się przetworzyć odpowiedzi LLM jako JSON: {str(e)}. " 
                        f"Odpowiedź: {response_content[:100]}..."
                    )
            else:
                self.logger.warning(f"Nieoczekiwany typ odpowiedzi LLM: {type(response_content)}")
            
            return {"relationships": []}
                
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy LLM: {str(e)}")
            return {"relationships": []}
    
    def _process_llm_results(self, relationship: Dict[str, Any], llm_results: Dict[str, Any]) -> None:
        """
        Przetwarza wyniki analizy LLM i aktualizuje dane relacji.
        
        Args:
            relationship: Słownik z danymi relacji do aktualizacji
            llm_results: Wyniki analizy z LLM
        """
        if "relationships" not in llm_results:
            return
        
        for entity_rel in llm_results["relationships"]:
            if not entity_rel.get("has_relationship", False):
                continue
                
            entity_type = entity_rel.get("entity_type", "")
            if not entity_type:
                continue
                
            # Normalizuj typ bytu
            if entity_type.lower() in ["gen", "gene"]:
                entity_type = "gene"
            elif entity_type.lower() in ["choroba", "disease"]:
                entity_type = "disease"
            elif entity_type.lower() in ["tkanka", "tissue"]:
                entity_type = "tissue"
            elif entity_type.lower() in ["gatunek", "species"]:
                entity_type = "species"
            elif entity_type.lower() in ["związek chemiczny", "chemical"]:
                entity_type = "chemical"
            
            # Obsługa specjalnych przypadków, żeby uniknąć "speciess" i "chemicalss"
            if entity_type == "species":
                entity_list = "species"
            elif entity_type == "chemical":
                entity_list = "chemicals"
            else:
                entity_list = entity_type + "s"
            
            if entity_list in relationship:
                relationship[entity_list].append({
                    "text": entity_rel.get("entity_text", ""),
                    "id": entity_rel.get("entity_id", ""),
                    "explanation": entity_rel.get("explanation", "")
                })
    
    def _group_annotations_by_type(self, passage: bioc.BioCPassage) -> Dict[str, List[bioc.BioCAnnotation]]:
        """
        Grupuje adnotacje w pasażu według ich typu.
        
        Args:
            passage: Obiekt BioCPassage zawierający adnotacje
            
        Returns:
            Słownik z typami adnotacji jako kluczami i listami adnotacji jako wartościami
        """
        annotations_by_type = defaultdict(list)
        
        for annotation in passage.annotations:
            anno_type = annotation.infons.get("type")
            if anno_type:
                annotations_by_type[anno_type].append(annotation)
        
        return annotations_by_type
    
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str) -> None:
        """
        Zapisuje dane relacji do pliku CSV.
        
        Args:
            relationships: Lista słowników zawierających dane relacji
            output_file: Ścieżka do pliku wyjściowego CSV
        """
        if not relationships:
            self.logger.warning("Brak relacji do zapisania")
            return
        
        # Zdefiniuj kolumny CSV
        columns = ["pmid", "variant_text", "variant_offset", "variant_id", 
                   "gene_text", "gene_id", "disease_text", "disease_id", 
                   "tissue_text", "tissue_id", "explanation", "passage_text"]
        
        # Spłaszcz relacje do formatu CSV
        flattened_data = []
        for rel in relationships:
            # Podstawowy wpis z informacjami o wariancie
            base_entry = {
                "pmid": rel["pmid"],
                "variant_text": rel["variant_text"],
                "variant_offset": rel["variant_offset"],
                "variant_id": rel["variant_id"],
                "passage_text": rel["passage_text"]
            }
            
            # Utwórz wpisy dla każdej kombinacji bytów
            genes = rel["genes"] if rel["genes"] else [{"text": "", "id": "", "explanation": ""}]
            diseases = rel["diseases"] if rel["diseases"] else [{"text": "", "id": "", "explanation": ""}]
            tissues = rel["tissues"] if rel["tissues"] else [{"text": "", "id": "", "explanation": ""}]
            
            for gene in genes:
                for disease in diseases:
                    for tissue in tissues:
                        entry = base_entry.copy()
                        entry["gene_text"] = gene.get("text", "")
                        entry["gene_id"] = gene.get("id", "")
                        entry["disease_text"] = disease.get("text", "")
                        entry["disease_id"] = disease.get("id", "")
                        entry["tissue_text"] = tissue.get("text", "")
                        entry["tissue_id"] = tissue.get("id", "")
                        
                        # Dodaj objaśnienia z LLM
                        explanations = []
                        if gene.get("explanation"):
                            explanations.append(f"Gen: {gene.get('explanation')}")
                        if disease.get("explanation"):
                            explanations.append(f"Choroba: {disease.get('explanation')}")
                        if tissue.get("explanation"):
                            explanations.append(f"Tkanka: {tissue.get('explanation')}")
                        
                        entry["explanation"] = " | ".join(explanations)
                        flattened_data.append(entry)
        
        # Zapisz do CSV
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()
                writer.writerows(flattened_data)
            
            self.logger.info(f"Zapisano {len(flattened_data)} wpisów relacji do {output_file}")
        except Exception as e:
            self.logger.error(f"Błąd zapisywania relacji do CSV: {str(e)}")
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