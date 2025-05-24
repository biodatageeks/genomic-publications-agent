"""
Validation report class for ClinvarRelationshipValidator.

This module provides the ValidationReport class that stores the results of validating
relationships between genetic variants, genes, and diseases against clinical data.
"""

import csv
import json
import logging
from typing import Dict, List, Any, Optional


class ValidationReport:
    """
    Validation report for genetic relationship verification results.
    
    Stores information about relationships verified as correct, incorrect,
    and those for which an error occurred during verification.
    """
    
    def __init__(self):
        """
        Initialize a new validation report.
        """
        self.valid_relationships = []
        self.invalid_relationships = []
        self.error_relationships = []
        self.total_relationships = 0
        self.logger = logging.getLogger(__name__)
    
    def add_valid_relationship(self, relationship: Dict[str, Any], reason: str) -> None:
        """
        Adds a relationship verified as correct.
        
        Args:
            relationship: Dictionary with relationship data
            reason: Reason for considering the relationship as correct
        """
        relationship_with_reason = relationship.copy()
        relationship_with_reason["validation_result"] = "valid"
        relationship_with_reason["validation_reason"] = reason
        
        self.valid_relationships.append(relationship_with_reason)
        self.total_relationships += 1
    
    def add_invalid_relationship(self, relationship: Dict[str, Any], reason: str) -> None:
        """
        Adds a relationship verified as incorrect.
        
        Args:
            relationship: Dictionary with relationship data
            reason: Reason for considering the relationship as incorrect
        """
        relationship_with_reason = relationship.copy()
        relationship_with_reason["validation_result"] = "invalid"
        relationship_with_reason["validation_reason"] = reason
        
        self.invalid_relationships.append(relationship_with_reason)
        self.total_relationships += 1
    
    def add_error_relationship(self, relationship: Dict[str, Any], error_message: str) -> None:
        """
        Adds a relationship for which an error occurred during verification.
        
        Args:
            relationship: Dictionary with relationship data
            error_message: Error message
        """
        relationship_with_error = relationship.copy()
        relationship_with_error["validation_result"] = "error"
        relationship_with_error["validation_reason"] = error_message
        
        self.error_relationships.append(relationship_with_error)
        self.total_relationships += 1
    
    def get_all_relationships(self) -> List[Dict[str, Any]]:
        """
        Returns all verified relationships.
        
        Returns:
            List of all relationships with validation results
        """
        return self.valid_relationships + self.invalid_relationships + self.error_relationships
    
    def get_valid_count(self) -> int:
        """
        Returns the number of correct relationships.
        
        Returns:
            Number of correct relationships
        """
        return len(self.valid_relationships)
    
    def get_invalid_count(self) -> int:
        """
        Returns the number of incorrect relationships.
        
        Returns:
            Number of incorrect relationships
        """
        return len(self.invalid_relationships)
    
    def get_error_count(self) -> int:
        """
        Returns the number of relationships with errors.
        
        Returns:
            Number of relationships with errors
        """
        return len(self.error_relationships)
    
    def get_percentage_valid(self) -> float:
        """
        Returns the percentage of correct relationships.
        
        Returns:
            Percentage of correct relationships (0-100)
        """
        if self.total_relationships == 0:
            return 0.0
        
        return (len(self.valid_relationships) / self.total_relationships) * 100
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Returns validation statistics.
        
        Returns:
            Dictionary with validation statistics
        """
        return {
            "total": self.total_relationships,
            "valid": len(self.valid_relationships),
            "invalid": len(self.invalid_relationships),
            "errors": len(self.error_relationships),
            "percent_valid": self.get_percentage_valid()
        }
    
    def save_to_json(self, output_file: str) -> None:
        """
        Saves the validation report to a JSON file.
        
        Args:
            output_file: Path to the output file
        """
        data = {
            "statistics": self.get_statistics(),
            "relationships": self.get_all_relationships()
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Saved validation report to JSON file: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error while saving to JSON file: {str(e)}")
            raise
    
    def save_to_csv(self, output_file: str) -> None:
        """
        Saves the validation report to a CSV file.
        
        Args:
            output_file: Path to the output file
        """
        relationships = self.get_all_relationships()
        
        if not relationships:
            self.logger.warning("No relationships to save")
            return
        
        try:
            # Determine columns based on the first relationship
            first_rel = relationships[0]
            columns = list(first_rel.keys())
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(relationships)
                
            self.logger.info(f"Saved validation report to CSV file: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error while saving to CSV file: {str(e)}")
            raise 