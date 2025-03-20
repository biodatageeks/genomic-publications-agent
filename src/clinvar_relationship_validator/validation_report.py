"""
Klasa raportu walidacji dla ClinvarRelationshipValidator.

Ten moduł zapewnia klasę ValidationReport, która przechowuje wyniki walidacji relacji
między wariantami genetycznymi, genami i chorobami w odniesieniu do danych klinicznych.
"""

import csv
import json
import logging
from typing import Dict, List, Any, Optional


class ValidationReport:
    """
    Raport walidacji dla wyników weryfikacji relacji genetycznych.
    
    Przechowuje informacje o relacjach zweryfikowanych jako poprawne, niepoprawne
    oraz tych, dla których wystąpił błąd podczas weryfikacji.
    """
    
    def __init__(self):
        """
        Inicjalizacja nowego raportu walidacji.
        """
        self.valid_relationships = []
        self.invalid_relationships = []
        self.error_relationships = []
        self.total_relationships = 0
        self.logger = logging.getLogger(__name__)
    
    def add_valid_relationship(self, relationship: Dict[str, Any], reason: str) -> None:
        """
        Dodaje relację zweryfikowaną jako poprawną.
        
        Args:
            relationship: Słownik z danymi relacji
            reason: Powód uznania relacji za poprawną
        """
        relationship_with_reason = relationship.copy()
        relationship_with_reason["validation_result"] = "valid"
        relationship_with_reason["validation_reason"] = reason
        
        self.valid_relationships.append(relationship_with_reason)
        self.total_relationships += 1
    
    def add_invalid_relationship(self, relationship: Dict[str, Any], reason: str) -> None:
        """
        Dodaje relację zweryfikowaną jako niepoprawną.
        
        Args:
            relationship: Słownik z danymi relacji
            reason: Powód uznania relacji za niepoprawną
        """
        relationship_with_reason = relationship.copy()
        relationship_with_reason["validation_result"] = "invalid"
        relationship_with_reason["validation_reason"] = reason
        
        self.invalid_relationships.append(relationship_with_reason)
        self.total_relationships += 1
    
    def add_error_relationship(self, relationship: Dict[str, Any], error_message: str) -> None:
        """
        Dodaje relację, dla której wystąpił błąd podczas weryfikacji.
        
        Args:
            relationship: Słownik z danymi relacji
            error_message: Komunikat błędu
        """
        relationship_with_error = relationship.copy()
        relationship_with_error["validation_result"] = "error"
        relationship_with_error["validation_reason"] = error_message
        
        self.error_relationships.append(relationship_with_error)
        self.total_relationships += 1
    
    def get_all_relationships(self) -> List[Dict[str, Any]]:
        """
        Zwraca wszystkie zweryfikowane relacje.
        
        Returns:
            Lista wszystkich relacji z wynikami walidacji
        """
        return self.valid_relationships + self.invalid_relationships + self.error_relationships
    
    def get_valid_count(self) -> int:
        """
        Zwraca liczbę poprawnych relacji.
        
        Returns:
            Liczba poprawnych relacji
        """
        return len(self.valid_relationships)
    
    def get_invalid_count(self) -> int:
        """
        Zwraca liczbę niepoprawnych relacji.
        
        Returns:
            Liczba niepoprawnych relacji
        """
        return len(self.invalid_relationships)
    
    def get_error_count(self) -> int:
        """
        Zwraca liczbę relacji z błędami.
        
        Returns:
            Liczba relacji z błędami
        """
        return len(self.error_relationships)
    
    def get_percentage_valid(self) -> float:
        """
        Zwraca procent poprawnych relacji.
        
        Returns:
            Procent poprawnych relacji (0-100)
        """
        if self.total_relationships == 0:
            return 0.0
        
        return (len(self.valid_relationships) / self.total_relationships) * 100
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Zwraca statystyki walidacji.
        
        Returns:
            Słownik ze statystykami walidacji
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
        Zapisuje raport walidacji do pliku JSON.
        
        Args:
            output_file: Ścieżka do pliku wyjściowego
        """
        data = {
            "statistics": self.get_statistics(),
            "relationships": self.get_all_relationships()
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Zapisano raport walidacji do pliku JSON: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania do pliku JSON: {str(e)}")
            raise
    
    def save_to_csv(self, output_file: str) -> None:
        """
        Zapisuje raport walidacji do pliku CSV.
        
        Args:
            output_file: Ścieżka do pliku wyjściowego
        """
        relationships = self.get_all_relationships()
        
        if not relationships:
            self.logger.warning("Brak relacji do zapisania")
            return
        
        try:
            # Określenie kolumn na podstawie pierwszej relacji
            first_rel = relationships[0]
            columns = list(first_rel.keys())
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(relationships)
                
            self.logger.info(f"Zapisano raport walidacji do pliku CSV: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania do pliku CSV: {str(e)}")
            raise 