#!/usr/bin/env python3
"""
Testy dla ulepszonej klasy EnhancedLlmContextAnalyzer.
"""

import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock, Mock

from src.llm_context_analyzer.enhanced_llm_context_analyzer import EnhancedLlmContextAnalyzer
from src.pubtator_client.pubtator_client import PubTatorClient


class TestEnhancedLlmContextAnalyzer(unittest.TestCase):
    """
    Testy dla EnhancedLlmContextAnalyzer weryfikujące poprawność działania funkcji naprawiających JSON.
    """
    
    def setUp(self):
        """Przygotowanie do testów."""
        # Mock PubTator client
        self.pubtator_mock = MagicMock(spec=PubTatorClient)
        
        # Patch klasy LlmManager aby testy były izolowane
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as self.mock_llm_manager:
            self.mock_llm = MagicMock()
            self.mock_llm_manager_instance = MagicMock()
            self.mock_llm_manager_instance.get_llm.return_value = self.mock_llm
            self.mock_llm_manager.return_value = self.mock_llm_manager_instance
            
            # Create the analyzer with the mock
            self.analyzer = EnhancedLlmContextAnalyzer(
                pubtator_client=self.pubtator_mock,
                llm_model_name="test-model",
                use_cache=False,
                debug_mode=True
            )
    
    def test_clean_json_response_basic(self):
        """Test podstawowej funkcjonalności czyszczenia JSON."""
        response = "Jakiś tekst przed JSON {\"key\": \"value\"} jakiś tekst po JSON"
        cleaned = self.analyzer._clean_json_response(response)
        self.assertEqual(cleaned, "{\"key\": \"value\"}")
        
        # Sprawdź, czy można go sparsować
        parsed = json.loads(cleaned)
        self.assertEqual(parsed["key"], "value")
    
    def test_fix_trailing_commas(self):
        """Test naprawy końcowych przecinków w JSON."""
        # JSON z przecinkiem na końcu obiektu
        invalid_json = '{"key1": "value1", "key2": "value2", }'
        fixed = self.analyzer._fix_trailing_commas(invalid_json)
        
        # Sprawdź, czy przecinek został usunięty
        self.assertEqual(fixed, '{"key1": "value1", "key2": "value2" }')
        
        # JSON z przecinkiem na końcu tablicy
        invalid_json_array = '{"items": ["item1", "item2", ]}'
        fixed_array = self.analyzer._fix_trailing_commas(invalid_json_array)
        
        # Sprawdź, czy przecinek został usunięty
        self.assertEqual(fixed_array, '{"items": ["item1", "item2" ]}')
    
    def test_fix_missing_quotes(self):
        """Test naprawy brakujących cudzysłowów w kluczach JSON."""
        # JSON z kluczami bez cudzysłowów
        invalid_json = '{key1: "value1", key2: "value2"}'
        fixed = self.analyzer._fix_missing_quotes(invalid_json)
        
        # Sprawdź, czy cudzysłowy zostały dodane
        self.assertEqual(fixed, '{ "key1": "value1", "key2": "value2"}')
    
    def test_fix_inconsistent_quotes(self):
        """Test naprawy niekonsekwentnych cudzysłowów w JSON."""
        # JSON z mieszanymi typami cudzysłowów
        invalid_json = "{'key1': \"value1\", 'key2': 'value2'}"
        fixed = self.analyzer._fix_inconsistent_quotes(invalid_json)
        
        # Sprawdź, czy wszystkie cudzysłowy zostały ujednolicone
        self.assertEqual(fixed, "{\"key1\": \"value1\", \"key2\": \"value2\"}")
    
    def test_attempt_json_fix_end_delimiter(self):
        """Test naprawy typowego błędu JSON z błędnym formatowaniem końcowych znaków."""
        # Typowy błąd ze źle sformatowanym JSON z modelu LLM
        invalid_json = """
{
  "relationships": [
    {
      "entity_type": "gene",
      "entity_text": "BRAF",
      "entity_id": "673",
      "has_relationship": true,
      "explanation": "BRAF jest bezpośrednio powiązany z wariantem V600E."
    },
    {
      "entity_type": "disease",
      "entity_text": "melanoma",
      "entity_id": "D008545",
      "has_relationship": true,
      "explanation": "Wariant V600E jest silnie związany z czerniakiem."
    }
  ]
}
"""
        # To jest poprawny JSON, ale przetestujmy czy metoda działa
        fixed = self.analyzer._attempt_json_fix(invalid_json)
        parsed = json.loads(fixed)
        self.assertEqual(len(parsed["relationships"]), 2)
    
    def test_attempt_json_fix_trailing_comma(self):
        """Test naprawy JSON z końcowymi przecinkami."""
        invalid_json = """
{
  "relationships": [
    {
      "entity_type": "gene",
      "entity_text": "BRAF",
      "entity_id": "673",
      "has_relationship": true,
      "explanation": "BRAF jest bezpośrednio powiązany z wariantem V600E."
    },
    {
      "entity_type": "disease",
      "entity_text": "melanoma",
      "entity_id": "D008545",
      "has_relationship": true,
      "explanation": "Wariant V600E jest silnie związany z czerniakiem."
    },
  ]
}
"""
        fixed = self.analyzer._attempt_json_fix(invalid_json)
        
        # Powinna być poprawna struktura JSON
        parsed = json.loads(fixed)
        self.assertEqual(len(parsed["relationships"]), 2)
    
    def test_complex_json_fix(self):
        """Test naprawy złożonego błędu JSON z wieloma problemami."""
        # JSON z wieloma problemami: końcowe przecinki, niekonsekwentne cudzysłowy, brakujące cudzysłowy
        invalid_json = """
{
  relationships: [
    {
      "entity_type": "gene",
      "entity_text": "BRAF",
      "entity_id": "673",
      'has_relationship': true,
      'explanation': "BRAF jest powiązany z V600E.",
    },
    {
      entity_type: "disease",
      entity_text: "melanoma",
      entity_id: "D008545",
      has_relationship: true,
      explanation: "V600E jest związany z czerniakiem.",
    },
  ]
}
"""
        fixed = self.analyzer._attempt_json_fix(invalid_json)
        
        # Sprawdź, czy udało się naprawić i sparsować
        try:
            parsed = json.loads(fixed)
            self.assertEqual(len(parsed["relationships"]), 2)
            self.assertEqual(parsed["relationships"][0]["entity_text"], "BRAF")
            self.assertEqual(parsed["relationships"][1]["entity_text"], "melanoma")
        except json.JSONDecodeError as e:
            self.fail(f"Nie udało się sparsować naprawionego JSON: {e}")
    
    def test_real_word_llm_response(self):
        """Test naprawy rzeczywistej odpowiedzi z modelu LLM."""
        # Przykładowa odpowiedź z modelu, która generuje błędy parsowania
        llm_response = """
Analizując podany fragment tekstu biomedycznego, mogę określić, czy istnieją relacje między wariantem V600E a wymienionymi bytami biomedycznymi:

```json
{
  "relationships": [
    {
      "entity_type": "gene",
      "entity_text": "BRAF",
      "entity_id": "673",
      "has_relationship": true,
      "explanation": "Wariant V600E jest mutacją w genie BRAF. Tekst wyraźnie wskazuje na bezpośrednią relację."
    },
    {
      "entity_type": "disease",
      "entity_text": "melanoma",
      "entity_id": "D008545",
      "has_relationship": true,
      "explanation": "Tekst jasno stwierdza, że mutacja V600E w BRAF jest związana z czerniakiem (melanoma)."
    }
  ]
}
```
"""
        # Sprawdź, czy podstawowa metoda _clean_json_response wyodrębni poprawnie JSON
        cleaned = self.analyzer._clean_json_response(llm_response)
        
        # Sprawdź, czy można sparsować wyniki
        try:
            parsed = json.loads(cleaned)
            self.assertEqual(len(parsed["relationships"]), 2)
            self.assertEqual(parsed["relationships"][0]["entity_text"], "BRAF")
            self.assertEqual(parsed["relationships"][1]["entity_text"], "melanoma")
        except json.JSONDecodeError as e:
            self.fail(f"Nie udało się sparsować wyczyszczonego JSON: {e}")
    
    @patch('src.LlmManager.LlmManager')
    def test_analyze_relationships_with_llm_trailing_commas(self, mock_llm_manager):
        # Mock response from LLM with trailing commas in JSON
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '''
        Here's the analysis:
        {
          "relationships": [
            {
              "entity_type": "species",
              "entity_text": "human",
              "entity_id": "9606",
              "has_relationship": true,
              "explanation": "The variant affects human genes.",
            }
          ]
        }
        '''
        mock_llm.invoke.return_value = mock_response
        mock_llm_manager_instance = MagicMock()
        mock_llm_manager_instance.get_llm.return_value = mock_llm
        mock_llm_manager.return_value = mock_llm_manager_instance
        
        # Przekazujemy patchowany LlmManager do analizatora
        self.analyzer.llm = mock_llm
        
        # Run the method
        entities = [
            {"entity_type": "species", "text": "human", "id": "9606", "offset": 0}
        ]
        result = self.analyzer._analyze_relationships_with_llm("rs123", entities, "Test passage")
        
        # Check that the JSON was properly fixed and parsed
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_type"], "species")
        self.assertEqual(result[0]["entity_id"], "9606")
        self.assertTrue(result[0]["has_relationship"])

    def test_fix_missing_commas(self):
        # Test adding missing commas between properties
        json_without_comma = '{"key1": "value1" "key2": "value2"}'
        result = self.analyzer._fix_missing_commas(json_without_comma)
        self.assertEqual(result, '{"key1": "value1", "key2": "value2"}')
        
        # Test more complex case
        complex_json = '{"key1": "value1" "key2": 123 "key3": {"nested": "value"}}'
        result = self.analyzer._fix_missing_commas(complex_json)
        self.assertEqual(result, '{"key1": "value1", "key2": 123, "key3": {"nested": "value"}}')
        
        # Test with a JSON where commas already exist
        json_with_commas = '{"key1": "value1", "key2": "value2"}'
        result = self.analyzer._fix_missing_commas(json_with_commas)
        self.assertEqual(result, json_with_commas)


if __name__ == "__main__":
    unittest.main() 