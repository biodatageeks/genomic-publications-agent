"""
Tests for the VariantRecognizer class from bio_ner module.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.analysis.bio_ner.variant_recognizer import VariantRecognizer


class TestVariantRecognizer:
    """
    Test suite for the VariantRecognizer class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        recognizer = VariantRecognizer()
        assert recognizer.llm_manager is None
        assert recognizer.model_name == "gpt-3.5-turbo"
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        mock_llm_manager = MagicMock()
        model_name = "gpt-4"
        
        recognizer = VariantRecognizer(llm_manager=mock_llm_manager, model_name=model_name)
        
        assert recognizer.llm_manager == mock_llm_manager
        assert recognizer.model_name == model_name
    
    def test_init_with_only_llm_manager(self):
        """Test initialization with only LLM manager parameter."""
        mock_llm_manager = MagicMock()
        
        recognizer = VariantRecognizer(llm_manager=mock_llm_manager)
        
        assert recognizer.llm_manager == mock_llm_manager
        assert recognizer.model_name == "gpt-3.5-turbo"
    
    def test_init_with_only_model_name(self):
        """Test initialization with only model name parameter."""
        model_name = "gpt-4"
        
        recognizer = VariantRecognizer(model_name=model_name)
        
        assert recognizer.llm_manager is None
        assert recognizer.model_name == model_name
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.LlmManager')
    def test_get_llm_no_manager(self, mock_llm_manager_class):
        """Test getting LLM without a manager provided during initialization."""
        # Set up the mock
        mock_llm_manager_instance = MagicMock()
        mock_llm_manager_class.return_value = mock_llm_manager_instance
        mock_llm = MagicMock()
        mock_llm_manager_instance.get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer with no LLM manager
        recognizer = VariantRecognizer()
        
        # Call the method
        llm = recognizer.get_llm()
        
        # Verify results
        mock_llm_manager_class.assert_called_once()
        mock_llm_manager_instance.get_llm.assert_called_once()
        assert llm == mock_llm
    
    def test_get_llm_with_manager(self):
        """Test getting LLM with a manager provided during initialization."""
        # Set up the mock
        mock_llm_manager = MagicMock()
        mock_llm = MagicMock()
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer with the mock LLM manager
        recognizer = VariantRecognizer(llm_manager=mock_llm_manager)
        
        # Call the method
        llm = recognizer.get_llm()
        
        # Verify results
        mock_llm_manager.get_llm.assert_called_once()
        assert llm == mock_llm
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.get_llm')
    def test_recognize_variants_text(self, mock_get_llm):
        """Test recognizing variants in text."""
        # Set up the mock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "c.123A>G, p.V600E, chr7:140453136-140453136"
        mock_get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        text = "Sample text with variants c.123A>G and p.V600E"
        variants = recognizer.recognize_variants_text(text)
        
        # Verify results
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()
        assert isinstance(variants, list)
        assert len(variants) == 3
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert "chr7:140453136-140453136" in variants
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.get_llm')
    def test_recognize_variants_text_empty_response(self, mock_get_llm):
        """Test recognizing variants in text with empty LLM response."""
        # Set up the mock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = ""
        mock_get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        text = "Sample text with no variants"
        variants = recognizer.recognize_variants_text(text)
        
        # Verify results
        assert isinstance(variants, list)
        assert len(variants) == 0
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.get_llm')
    def test_recognize_variants_text_no_variants(self, mock_get_llm):
        """Test recognizing variants in text where no variants are found."""
        # Set up the mock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "No variants found."
        mock_get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        text = "Sample text with no variants"
        variants = recognizer.recognize_variants_text(text)
        
        # Verify results
        assert isinstance(variants, list)
        assert len(variants) == 0
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.get_llm')
    def test_recognize_variants_text_with_formatting(self, mock_get_llm):
        """Test recognizing variants in text with different formatting."""
        # Set up the mock
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = """
        1. c.123A>G
        2. p.V600E
        3. chr7:140453136-140453136
        """
        mock_get_llm.return_value = mock_llm
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        text = "Sample text with variants c.123A>G and p.V600E"
        variants = recognizer.recognize_variants_text(text)
        
        # Verify results
        assert isinstance(variants, list)
        assert len(variants) == 3
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert "chr7:140453136-140453136" in variants
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.get_llm')
    def test_generate_llm_prompt(self, mock_get_llm):
        """Test the generation of LLM prompt."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        text = "Sample text with variants c.123A>G and p.V600E"
        prompt = recognizer.generate_llm_prompt(text)
        
        # Verify results
        assert isinstance(prompt, str)
        assert "Sample text with variants" in prompt
        assert "c.123A>G" in prompt
        assert "p.V600E" in prompt
    
    def test_parse_llm_response(self):
        """Test parsing the LLM response."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Test case 1: Simple comma-separated list
        response = "c.123A>G, p.V600E, chr7:140453136-140453136"
        variants = recognizer.parse_llm_response(response)
        assert isinstance(variants, list)
        assert len(variants) == 3
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert "chr7:140453136-140453136" in variants
        
        # Test case 2: List with numbers
        response = """
        1. c.123A>G
        2. p.V600E
        3. chr7:140453136-140453136
        """
        variants = recognizer.parse_llm_response(response)
        assert isinstance(variants, list)
        assert len(variants) == 3
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert "chr7:140453136-140453136" in variants
        
        # Test case 3: List with dashes
        response = """
        - c.123A>G
        - p.V600E
        - chr7:140453136-140453136
        """
        variants = recognizer.parse_llm_response(response)
        assert isinstance(variants, list)
        assert len(variants) == 3
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert "chr7:140453136-140453136" in variants
        
        # Test case 4: Empty response
        response = ""
        variants = recognizer.parse_llm_response(response)
        assert isinstance(variants, list)
        assert len(variants) == 0
        
        # Test case 5: No variants found message
        response = "No variants found in the text."
        variants = recognizer.parse_llm_response(response)
        assert isinstance(variants, list)
        assert len(variants) == 0
    
    @patch('builtins.open', new_callable=MagicMock)
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.recognize_variants_text')
    def test_recognize_variants_file(self, mock_recognize_text, mock_open):
        """Test recognizing variants in a file."""
        # Set up the mocks
        mock_file = MagicMock()
        mock_file.read.return_value = "Sample text with variants c.123A>G and p.V600E"
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_recognize_text.return_value = ["c.123A>G", "p.V600E"]
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        file_path = "test.txt"
        variants = recognizer.recognize_variants_file(file_path)
        
        # Verify results
        mock_open.assert_called_once_with(file_path, 'r', encoding='utf-8')
        mock_file.read.assert_called_once()
        mock_recognize_text.assert_called_once_with("Sample text with variants c.123A>G and p.V600E")
        assert variants == ["c.123A>G", "p.V600E"]
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_recognize_variants_file_error(self, mock_open):
        """Test handling file error when recognizing variants in a file."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method and expect an exception
        with pytest.raises(IOError):
            recognizer.recognize_variants_file("nonexistent.txt")
        
        # Verify the mock was called
        mock_open.assert_called_once_with("nonexistent.txt", 'r', encoding='utf-8')
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.recognize_variants_text')
    def test_recognize_variants_dir(self, mock_recognize_text):
        """Test recognizing variants in all files in a directory."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Set up the mocks and temporary directory with files
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('builtins.open', create=True) as mock_open:
            
            # Set up mock behavior
            mock_listdir.return_value = ["file1.txt", "file2.txt", "file3.docx"]
            mock_isfile.side_effect = lambda x: True  # All paths are files
            
            # Mock file contents
            mock_file_handles = [MagicMock(), MagicMock()]
            mock_file_handles[0].read.return_value = "Text in file1"
            mock_file_handles[1].read.return_value = "Text in file2"
            mock_open.side_effect = lambda p, m, **kwargs: {
                "test_dir/file1.txt": mock_file_handles[0],
                "test_dir/file2.txt": mock_file_handles[1]
            }[p].__enter__()
            
            # Mock recognize_variants_text to return different results for each file
            mock_recognize_text.side_effect = [
                ["c.123A>G"], 
                ["p.V600E", "chr7:140453136-140453136"]
            ]
            
            # Call the method
            result = recognizer.recognize_variants_dir("test_dir", extensions=[".txt"])
            
            # Verify results
            assert len(result) == 2
            assert result["file1.txt"] == ["c.123A>G"]
            assert result["file2.txt"] == ["p.V600E", "chr7:140453136-140453136"]
            assert "file3.docx" not in result
            
            # Ensure recognize_variants_text was called twice
            assert mock_recognize_text.call_count == 2
    
    @patch(\'src.analysis.bio_ner.variant_recognizer.VariantRecognizer.recognize_variants_text')
    def test_recognize_variants_dir_no_matching_files(self, mock_recognize_text):
        """Test recognizing variants in a directory with no matching files."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Set up the mocks
        with patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile:
            
            # Set up mock behavior
            mock_listdir.return_value = ["file1.docx", "file2.pdf"]
            mock_isfile.side_effect = lambda x: True  # All paths are files
            
            # Call the method
            result = recognizer.recognize_variants_dir("test_dir", extensions=[".txt"])
            
            # Verify results
            assert isinstance(result, dict)
            assert len(result) == 0
            mock_recognize_text.assert_not_called()
    
    @patch('os.listdir', side_effect=OSError("Test error"))
    def test_recognize_variants_dir_error(self, mock_listdir):
        """Test handling directory error when recognizing variants in a directory."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method and expect an exception
        with pytest.raises(OSError):
            recognizer.recognize_variants_dir("nonexistent_dir")
        
        # Verify the mock was called
        mock_listdir.assert_called_once_with("nonexistent_dir")
    
    @patch('builtins.open', new_callable=MagicMock)
    def test_save_variants_to_file(self, mock_open):
        """Test saving variants to a file."""
        # Set up the mock
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method
        variants = ["c.123A>G", "p.V600E", "chr7:140453136-140453136"]
        file_path = "variants.txt"
        recognizer.save_variants_to_file(variants, file_path)
        
        # Verify results
        mock_open.assert_called_once_with(file_path, 'w', encoding='utf-8')
        for variant in variants:
            mock_file.write.assert_any_call(f"{variant}\n")
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_variants_to_file_error(self, mock_open):
        """Test handling file error when saving variants to a file."""
        # Create a VariantRecognizer
        recognizer = VariantRecognizer()
        
        # Call the method and expect an exception
        with pytest.raises(IOError):
            recognizer.save_variants_to_file(["c.123A>G"], "invalid/path/variants.txt")
        
        # Verify the mock was called
        mock_open.assert_called_once_with("invalid/path/variants.txt", 'w', encoding='utf-8')
    
    # Integration tests with fixtures
    
    def test_integration_with_sample_text(self, sample_text, mock_llm):
        """Integration test with sample text fixture."""
        # Set up a VariantRecognizer with the mock LLM manager
        with patch('src.bio_ner.variant_recognizer.LlmManager') as mock_llm_manager_class:
            mock_llm_manager = MagicMock()
            mock_llm_manager_class.return_value = mock_llm_manager
            mock_llm_manager.get_llm.return_value = mock_llm
            
            recognizer = VariantRecognizer()
            variants = recognizer.recognize_variants_text(sample_text)
            
            # Verify that the LLM was invoked with sample_text
            mock_llm.invoke.assert_called_once()
            prompt = mock_llm.invoke.call_args[0][0]
            assert sample_text in prompt
            
            # Verify results
            assert isinstance(variants, list)
            assert len(variants) > 0
    
    def test_integration_full_pipeline(self, sample_text, temp_txt_file, temp_dir, mock_llm):
        """Integration test for the full pipeline - recognize from text and save to file."""
        # Set up a VariantRecognizer with the mock LLM manager
        with patch('src.bio_ner.variant_recognizer.LlmManager') as mock_llm_manager_class:
            mock_llm_manager = MagicMock()
            mock_llm_manager_class.return_value = mock_llm_manager
            mock_llm_manager.get_llm.return_value = mock_llm
            
            # Write sample text to file
            with open(temp_txt_file, 'w', encoding='utf-8') as f:
                f.write(sample_text)
            
            # Create an output file path
            output_file = os.path.join(temp_dir, "detected_variants.txt")
            
            # Create a VariantRecognizer and process the file
            recognizer = VariantRecognizer()
            variants = recognizer.recognize_variants_file(temp_txt_file)
            recognizer.save_variants_to_file(variants, output_file)
            
            # Verify results
            assert os.path.exists(output_file)
            with open(output_file, 'r', encoding='utf-8') as f:
                saved_variants = [line.strip() for line in f.readlines()]
            
            assert len(saved_variants) == len(variants)
            for variant in variants:
                assert variant in saved_variants 