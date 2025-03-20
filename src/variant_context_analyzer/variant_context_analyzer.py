"""
Variant Context Analyzer for biomedical publications.

This module provides tools for analyzing the context of genetic variants
in biomedical publications by utilizing the PubTator3 API annotations.
It identifies relationships between variants and other biomedical entities
like genes, diseases, and tissues that appear within the same passage context.
"""

import csv
import json
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from collections import defaultdict

import bioc
from src.pubtator_client.pubtator_client import PubTatorClient
from src.pubtator_client.exceptions import PubTatorError

class VariantContextAnalyzer:
    """
    Analyzer for context relationships between variants and other biomedical entities.
    
    This class extracts relationships between variants and other entities (genes, diseases, tissues)
    that appear in the same passage context within biomedical publications.
    
    Example usage:
        analyzer = VariantContextAnalyzer()
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
    
    def __init__(self, pubtator_client: Optional[PubTatorClient] = None):
        """
        Initialize the Variant Context Analyzer.
        
        Args:
            pubtator_client: Custom PubTator client instance (optional)
        """
        self.pubtator_client = pubtator_client if pubtator_client else PubTatorClient()
        self.logger = logging.getLogger(__name__)
    
    def analyze_publications(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze a list of publications to extract variant context relationships.
        
        Args:
            pmids: List of PubMed IDs to analyze
            
        Returns:
            List of dictionaries containing variant relationship data
            
        Raises:
            PubTatorError: If there's an error retrieving or processing publications
        """
        relationships = []
        
        try:
            # Retrieve publications from PubTator
            publications = self.pubtator_client.get_publications_by_pmids(pmids)
            
            for publication in publications:
                publication_relationships = self._analyze_publication(publication)
                relationships.extend(publication_relationships)
                
            return relationships
        except PubTatorError as e:
            self.logger.error(f"Error analyzing publications: {str(e)}")
            raise
    
    def analyze_publication(self, pmid: str) -> List[Dict[str, Any]]:
        """
        Analyze a single publication to extract variant context relationships.
        
        Args:
            pmid: PubMed ID to analyze
            
        Returns:
            List of dictionaries containing variant relationship data
            
        Raises:
            PubTatorError: If there's an error retrieving or processing the publication
        """
        try:
            publication = self.pubtator_client.get_publication_by_pmid(pmid)
            if not publication:
                self.logger.warning(f"No publication found for PMID: {pmid}")
                return []
                
            return self._analyze_publication(publication)
        except PubTatorError as e:
            self.logger.error(f"Error analyzing publication {pmid}: {str(e)}")
            raise
    
    def _analyze_publication(self, publication: bioc.BioCDocument) -> List[Dict[str, Any]]:
        """
        Extract variant context relationships from a single publication.
        
        Args:
            publication: BioCDocument object containing the publication with annotations
            
        Returns:
            List of dictionaries containing variant relationship data
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
        Extract variant context relationships from a single passage.
        
        Args:
            pmid: PubMed ID of the publication
            passage: BioCPassage object containing the passage with annotations
            
        Returns:
            List of dictionaries containing variant relationship data for this passage
        """
        relationships = []
        
        # Group annotations in the passage by entity type
        entities_by_type = self._group_annotations_by_type(passage)
        
        # If no variants in this passage, return empty list
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
            
            # Find other entities in the same passage
            for entity_type, type_list in self.ENTITY_TYPES.items():
                if entity_type == "variant":
                    continue
                
                entity_data = []
                for type_name in type_list:
                    if type_name in entities_by_type:
                        for entity in entities_by_type[type_name]:
                            entity_data.append({
                                "text": entity.text,
                                "id": entity.infons.get("identifier", ""),
                                "offset": entity.locations[0].offset if entity.locations else None
                            })
                
                if entity_data:
                    relationship[entity_type + "s"] = entity_data
            
            relationships.append(relationship)
        
        return relationships
    
    def _group_annotations_by_type(self, passage: bioc.BioCPassage) -> Dict[str, List[bioc.BioCAnnotation]]:
        """
        Group annotations in a passage by their type.
        
        Args:
            passage: BioCPassage object containing annotations
            
        Returns:
            Dictionary with annotation types as keys and lists of annotations as values
        """
        annotations_by_type = defaultdict(list)
        
        for annotation in passage.annotations:
            anno_type = annotation.infons.get("type")
            if anno_type:
                annotations_by_type[anno_type].append(annotation)
        
        return annotations_by_type
    
    def save_relationships_to_csv(self, relationships: List[Dict[str, Any]], output_file: str):
        """
        Save variant relationship data to a CSV file.
        
        Args:
            relationships: List of variant relationship dictionaries
            output_file: Path to the output CSV file
        """
        if not relationships:
            self.logger.warning("No relationships to save")
            return
        
        # Define CSV columns
        columns = ["pmid", "variant_text", "variant_offset", "variant_id", 
                   "gene_text", "gene_id", "disease_text", "disease_id", 
                   "tissue_text", "tissue_id", "passage_text"]
        
        # Flatten the relationships for CSV format
        flattened_data = []
        for rel in relationships:
            # Base entry with variant information
            base_entry = {
                "pmid": rel["pmid"],
                "variant_text": rel["variant_text"],
                "variant_offset": rel["variant_offset"],
                "variant_id": rel["variant_id"],
                "passage_text": rel["passage_text"]
            }
            
            # Create entries for each combination of entities
            genes = rel["genes"] if rel["genes"] else [{"text": "", "id": ""}]
            diseases = rel["diseases"] if rel["diseases"] else [{"text": "", "id": ""}]
            tissues = rel["tissues"] if rel["tissues"] else [{"text": "", "id": ""}]
            
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
                        flattened_data.append(entry)
        
        # Write to CSV
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()
                writer.writerows(flattened_data)
            
            self.logger.info(f"Saved {len(flattened_data)} relationship entries to {output_file}")
        except Exception as e:
            self.logger.error(f"Error saving relationships to CSV: {str(e)}")
            raise
    
    def save_relationships_to_json(self, relationships: List[Dict[str, Any]], output_file: str):
        """
        Save variant relationship data to a JSON file.
        
        Args:
            relationships: List of variant relationship dictionaries
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
        Filter relationships by a specific entity value.
        
        Args:
            relationships: List of variant relationship dictionaries
            entity_type: Type of entity to filter by (gene, disease, etc.)
            entity_value: Value to filter by (can be id or text)
            
        Returns:
            Filtered list of relationships
        """
        filtered = []
        entity_plural = entity_type + "s"
        
        for rel in relationships:
            if entity_plural in rel:
                for entity in rel[entity_plural]:
                    if entity.get("text") == entity_value or entity.get("id") == entity_value:
                        filtered.append(rel)
                        break
        
        return filtered 