"""
Tests for the LlmContextAnalyzer class from llm_context_analyzer module.
"""
import os
import pytest
import json
from unittest.mock import patch, MagicMock, mock_open, Mock

from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer


class TestLlmContextAnalyzer:
    """
    Test suite for the LlmContextAnalyzer class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_manager = MagicMock()
            mock_llm_manager.return_value = mock_manager
            
            analyzer = LlmContextAnalyzer()
            
            mock_llm_manager.assert_called_once()
            assert analyzer.llm_manager == mock_manager
            assert analyzer.snippets == []
            assert analyzer.snippets_file_path is None
            assert analyzer.model_name == "gpt-3.5-turbo"
            assert analyzer.temperature == 0.0
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_manager = MagicMock()
            mock_llm_manager.return_value = mock_manager
            
            snippets = [{"variant": "c.123A>G", "text": "Sample text"}]
            analyzer = LlmContextAnalyzer(
                snippets=snippets,
                snippets_file_path="test_snippets.json",
                model_name="gpt-4",
                temperature=0.7
            )
            
            assert analyzer.llm_manager == mock_manager
            assert analyzer.snippets == snippets
            assert analyzer.snippets_file_path == "test_snippets.json"
            assert analyzer.model_name == "gpt-4"
            assert analyzer.temperature == 0.7
    
    @patch('builtins.open', new_callable=mock_open, read_data='[{"variant": "c.123A>G", "text": "Sample text"}]')
    def test_load_snippets(self, mock_file):
        """Test loading snippets from a file."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            snippets = analyzer.load_snippets("test_snippets.json")
            
            mock_file.assert_called_once_with("test_snippets.json", "r", encoding="utf-8")
            assert len(snippets) == 1
            assert snippets[0]["variant"] == "c.123A>G"
            assert analyzer.snippets == snippets
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_load_snippets_file_error(self, mock_file):
        """Test handling file error when loading snippets."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            with pytest.raises(IOError):
                analyzer.load_snippets("nonexistent.json")
    
    def test_generate_prompt_for_variant_analysis(self):
        """Test generating a prompt for variant analysis."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            snippets = [
                {"variant": "c.123A>G", "text": "This variant is associated with breast cancer."},
                {"variant": "c.123A>G", "text": "c.123A>G is a pathogenic variant in BRCA1."}
            ]
            
            prompt = analyzer.generate_prompt_for_variant_analysis("c.123A>G", snippets)
            
            assert "c.123A>G" in prompt
            assert "breast cancer" in prompt
            assert "pathogenic variant" in prompt
            assert "BRCA1" in prompt
    
    def test_generate_prompt_for_gene_analysis(self):
        """Test generating a prompt for gene analysis."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            snippets = [
                {"gene": "BRCA1", "variant": "c.123A>G", "text": "This variant in BRCA1 is pathogenic."},
                {"gene": "BRCA1", "variant": "c.456G>T", "text": "BRCA1 mutations are linked to breast cancer."}
            ]
            
            prompt = analyzer.generate_prompt_for_gene_analysis("BRCA1", snippets)
            
            assert "BRCA1" in prompt
            assert "c.123A>G" in prompt
            assert "c.456G>T" in prompt
            assert "pathogenic" in prompt
            assert "breast cancer" in prompt
    
    def test_analyze_variant_with_llm(self):
        """Test analyzing a variant with the LLM."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "This variant is pathogenic and associated with breast cancer."
            
            analyzer = LlmContextAnalyzer()
            snippets = [
                {"variant": "c.123A>G", "text": "This variant is associated with breast cancer."},
                {"variant": "c.123A>G", "text": "c.123A>G is a pathogenic variant in BRCA1."}
            ]
            
            result = analyzer.analyze_variant_with_llm("c.123A>G", snippets)
            
            assert mock_llm.generate.called
            assert "pathogenic" in result
            assert "breast cancer" in result
    
    def test_analyze_gene_with_llm(self):
        """Test analyzing a gene with the LLM."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "BRCA1 is associated with hereditary breast and ovarian cancer syndrome."
            
            analyzer = LlmContextAnalyzer()
            snippets = [
                {"gene": "BRCA1", "variant": "c.123A>G", "text": "This variant in BRCA1 is pathogenic."},
                {"gene": "BRCA1", "variant": "c.456G>T", "text": "BRCA1 mutations are linked to breast cancer."}
            ]
            
            result = analyzer.analyze_gene_with_llm("BRCA1", snippets)
            
            assert mock_llm.generate.called
            assert "BRCA1" in result
            assert "breast" in result
    
    def test_extract_variant_insights(self):
        """Test extracting insights for a specific variant."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "This variant is pathogenic and associated with breast cancer."
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"variant": "c.123A>G", "text": "This variant is associated with breast cancer."},
                {"variant": "c.123A>G", "text": "c.123A>G is a pathogenic variant in BRCA1."},
                {"variant": "p.V600E", "text": "The p.V600E variant in BRAF is common in melanoma."}
            ]
            
            insights = analyzer.extract_variant_insights("c.123A>G")
            
            assert mock_llm.generate.called
            assert insights["variant"] == "c.123A>G"
            assert "pathogenic" in insights["analysis"]
            assert "breast cancer" in insights["analysis"]
    
    def test_extract_gene_insights(self):
        """Test extracting insights for a specific gene."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "BRCA1 is associated with hereditary breast and ovarian cancer syndrome."
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"gene": "BRCA1", "variant": "c.123A>G", "text": "This variant in BRCA1 is pathogenic."},
                {"gene": "BRCA1", "variant": "c.456G>T", "text": "BRCA1 mutations are linked to breast cancer."},
                {"gene": "BRAF", "variant": "p.V600E", "text": "BRAF mutations are common in melanoma."}
            ]
            
            insights = analyzer.extract_gene_insights("BRCA1")
            
            assert mock_llm.generate.called
            assert insights["gene"] == "BRCA1"
            assert "breast" in insights["analysis"]
            assert len(insights["variants"]) == 2
            assert "c.123A>G" in insights["variants"]
            assert "c.456G>T" in insights["variants"]
    
    def test_generate_disease_summary(self):
        """Test generating a disease summary for a variant."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "This variant is associated with breast and ovarian cancer."
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"variant": "c.123A>G", "text": "This variant is associated with breast cancer."},
                {"variant": "c.123A>G", "text": "Also linked to ovarian cancer."}
            ]
            
            summary = analyzer.generate_disease_summary("c.123A>G")
            
            assert mock_llm.generate.called
            assert "breast" in summary
            assert "ovarian" in summary
    
    def test_generate_clinical_significance_summary(self):
        """Test generating a clinical significance summary for a variant."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            mock_llm.generate.return_value = "This variant is classified as pathogenic according to ACMG guidelines."
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"variant": "c.123A>G", "text": "This variant is classified as pathogenic."},
                {"variant": "c.123A>G", "text": "Following ACMG guidelines, this is a class 5 variant."}
            ]
            
            summary = analyzer.generate_clinical_significance_summary("c.123A>G")
            
            assert mock_llm.generate.called
            assert "pathogenic" in summary
            assert "ACMG" in summary
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_analysis_results(self, mock_file):
        """Test saving analysis results to a file."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            
            analysis_results = [
                {
                    "variant": "c.123A>G",
                    "gene": "BRCA1",
                    "analysis": "This variant is pathogenic and associated with breast cancer."
                },
                {
                    "variant": "p.V600E",
                    "gene": "BRAF",
                    "analysis": "This variant is pathogenic and common in melanoma."
                }
            ]
            
            analyzer.save_analysis_results(analysis_results, "analysis_results.json")
            
            mock_file.assert_called_once_with("analysis_results.json", "w", encoding="utf-8")
            mock_handle = mock_file()
            
            # Verify JSON was written correctly
            json_str = mock_handle.write.call_args[0][0]
            saved_data = json.loads(json_str)
            assert len(saved_data) == 2
            assert saved_data[0]["variant"] == "c.123A>G"
            assert saved_data[1]["variant"] == "p.V600E"
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_analysis_results_file_error(self, mock_file):
        """Test handling file error when saving analysis results."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager"):
            analyzer = LlmContextAnalyzer()
            
            analysis_results = [{"variant": "c.123A>G", "analysis": "Test analysis"}]
            
            with pytest.raises(IOError):
                analyzer.save_analysis_results(analysis_results, "invalid/path.json")
    
    def test_analyze_all_variants(self):
        """Test analyzing all variants in the snippets."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            # Set up different responses for different variants
            def generate_side_effect(prompt):
                if "c.123A>G" in prompt:
                    return "This variant is pathogenic and associated with breast cancer."
                elif "p.V600E" in prompt:
                    return "This variant is pathogenic and common in melanoma."
                return ""
            
            mock_llm.generate.side_effect = generate_side_effect
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"variant": "c.123A>G", "text": "Text about c.123A>G", "gene": "BRCA1"},
                {"variant": "p.V600E", "text": "Text about p.V600E", "gene": "BRAF"},
                {"variant": "c.123A>G", "text": "More text about c.123A>G", "gene": "BRCA1"}
            ]
            
            results = analyzer.analyze_all_variants()
            
            # Should be called twice (once for each unique variant)
            assert mock_llm.generate.call_count == 2
            assert len(results) == 2
            
            # Check first variant results
            c123_result = next(r for r in results if r["variant"] == "c.123A>G")
            assert c123_result["gene"] == "BRCA1"
            assert "pathogenic" in c123_result["analysis"]
            assert "breast cancer" in c123_result["analysis"]
            
            # Check second variant results
            v600e_result = next(r for r in results if r["variant"] == "p.V600E")
            assert v600e_result["gene"] == "BRAF"
            assert "pathogenic" in v600e_result["analysis"]
            assert "melanoma" in v600e_result["analysis"]
    
    def test_analyze_all_genes(self):
        """Test analyzing all genes in the snippets."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_llm = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            # Set up different responses for different genes
            def generate_side_effect(prompt):
                if "BRCA1" in prompt:
                    return "BRCA1 is associated with hereditary breast and ovarian cancer."
                elif "BRAF" in prompt:
                    return "BRAF mutations are common in melanoma and other cancers."
                return ""
            
            mock_llm.generate.side_effect = generate_side_effect
            
            analyzer = LlmContextAnalyzer()
            analyzer.snippets = [
                {"variant": "c.123A>G", "gene": "BRCA1", "text": "Text about BRCA1"},
                {"variant": "p.V600E", "gene": "BRAF", "text": "Text about BRAF"},
                {"variant": "c.456G>T", "gene": "BRCA1", "text": "More text about BRCA1"}
            ]
            
            results = analyzer.analyze_all_genes()
            
            # Should be called twice (once for each unique gene)
            assert mock_llm.generate.call_count == 2
            assert len(results) == 2
            
            # Check first gene results
            brca1_result = next(r for r in results if r["gene"] == "BRCA1")
            assert len(brca1_result["variants"]) == 2
            assert "c.123A>G" in brca1_result["variants"]
            assert "c.456G>T" in brca1_result["variants"]
            assert "breast" in brca1_result["analysis"]
            assert "ovarian" in brca1_result["analysis"]
            
            # Check second gene results
            braf_result = next(r for r in results if r["gene"] == "BRAF")
            assert len(braf_result["variants"]) == 1
            assert "p.V600E" in braf_result["variants"]
            assert "melanoma" in braf_result["analysis"]
    
    # Integration tests
    
    def test_integration_load_analyze_save(self, snippets_data, temp_json_file, mock_llm):
        """Integration test for loading, analyzing, and saving results."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            # Write test data to temp file
            with open(temp_json_file, 'w', encoding='utf-8') as f:
                json.dump(snippets_data, f)
            
            # Initialize analyzer and load data
            analyzer = LlmContextAnalyzer(
                snippets_file_path=temp_json_file,
                model_name="test-model"
            )
            
            # Analyze all variants
            variant_results = analyzer.analyze_all_variants()
            assert len(variant_results) > 0
            
            # Save results to a new file
            output_file = f"{temp_json_file}_analysis.json"
            analyzer.save_analysis_results(variant_results, output_file)
            
            # Verify the file was created and contains the results
            assert os.path.exists(output_file)
            
            with open(output_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                assert len(saved_data) == len(variant_results)
                
                # Clean up the output file
                os.remove(output_file)
    
    def test_integration_full_pipeline(self, snippets_data, temp_json_file, mock_llm):
        """Integration test for running the full analysis pipeline."""
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager:
            mock_manager = MagicMock()
            mock_manager.get_llm.return_value = mock_llm
            mock_llm_manager.return_value = mock_manager
            
            # Write test data to temp file
            with open(temp_json_file, 'w', encoding='utf-8') as f:
                json.dump(snippets_data, f)
            
            # Initialize analyzer
            analyzer = LlmContextAnalyzer()
            
            # Load snippets
            analyzer.load_snippets(temp_json_file)
            
            # Analyze variants and genes
            variant_results = analyzer.analyze_all_variants()
            gene_results = analyzer.analyze_all_genes()
            
            # Save results
            variant_output = f"{temp_json_file}_variant_analysis.json"
            gene_output = f"{temp_json_file}_gene_analysis.json"
            
            analyzer.save_analysis_results(variant_results, variant_output)
            analyzer.save_analysis_results(gene_results, gene_output)
            
            # Verify files exist
            assert os.path.exists(variant_output)
            assert os.path.exists(gene_output)
            
            # Clean up
            os.remove(variant_output)
            os.remove(gene_output)

    def test_cache_integration():
        """Test integracyjny sprawdzający cache LlmContextAnalyzer."""
        pubtator_client_mock = Mock()
        
        # Przygotowanie atrapy LLM
        with patch("src.llm_context_analyzer.llm_context_analyzer.LlmManager") as mock_llm_manager_class, \
             patch("src.cache.cache.MemoryCache") as mock_memory_cache_class:
            
            # Konfiguracja atrapy LLM
            mock_llm = Mock()
            mock_llm.invoke.return_value = MagicMock(content=json.dumps({
                "relationships": [
                    {
                        "entity_type": "gene",
                        "entity_text": "BRAF",
                        "entity_id": "673",
                        "has_relationship": True,
                        "explanation": "BRAF is directly affected by the V600E mutation."
                    }
                ]
            }))
            
            mock_llm_manager = mock_llm_manager_class.return_value
            mock_llm_manager.get_llm.return_value = mock_llm
            
            # Wywołanie rzeczywistego konstruktora MemoryCache z symulowanym TTL
            memory_cache_instance = MagicMock()
            memory_cache_instance.has.return_value = False
            memory_cache_instance.get.return_value = None
            memory_cache_instance.set.return_value = True
            
            mock_memory_cache_class.return_value = memory_cache_instance
            
            from src.cache.cache import APICache
            with patch("src.llm_context_analyzer.llm_context_analyzer.APICache.create") as mock_create:
                mock_create.return_value = memory_cache_instance
                
                # Utworzenie analizatora z włączonym cache
                analyzer = LlmContextAnalyzer(
                    pubtator_client=pubtator_client_mock,
                    use_cache=True,
                    cache_storage_type="memory"
                )
                
                # Przygotowanie danych testowych
                variant_text = "V600E"
                entities = [
                    {"entity_type": "gene", "text": "BRAF", "id": "673", "offset": 0}
                ]
                passage_text = "V600E mutation in BRAF gene."
                
                # Pierwsze wywołanie - LLM jest wywoływany, wynik zapisywany do cache
                analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
                
                # Weryfikacja wywołania LLM
                assert mock_llm.invoke.call_count == 1
                
                # Weryfikacja zapisania wyniku do cache
                assert memory_cache_instance.set.call_count == 1
                
                # Symulacja istnienia danych w cache
                memory_cache_instance.has.return_value = True
                memory_cache_instance.get.return_value = [
                    {
                        "entity_type": "gene",
                        "entity_text": "BRAF",
                        "entity_id": "673",
                        "has_relationship": True,
                        "explanation": "BRAF is directly affected by the V600E mutation."
                    }
                ]
                
                # Drugie wywołanie - dane powinny być pobrane z cache
                analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
                
                # LLM nie powinien być wywoływany ponownie
                assert mock_llm.invoke.call_count == 1
                
                # Cache powinien być sprawdzony
                assert memory_cache_instance.has.call_count > 0
                
                # Dane powinny być pobrane z cache
                assert memory_cache_instance.get.call_count > 0 