"""Tests for the generate_coordinate_csv.py script."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from io import StringIO
import json

# Add the parent directory to the path to import the script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.enhanced_generate_coordinate_csv import (
    extract_coordinates_from_variant,
    determine_variant_type,
    extract_hgvs_notation,
    merge_variant_data,
    analyze_pmids
)


class TestExtractCoordinatesFromVariant:
    """Tests for extract_coordinates_from_variant function."""

    def test_extract_coordinates_nc_format(self):
        """Test extraction from NC HGVS format."""
        variant_id = "tmVar:c|SUB|G|123|T;HGVS:NC_000007.13:g.117188683G>A;VariantGroup:0"
        chr_val, start, end = extract_coordinates_from_variant(variant_id)
        assert chr_val == "chr7"
        assert start == 117188683
        assert end == 117188683

    def test_no_coordinates(self):
        """Test when no coordinates can be extracted."""
        variant_id = "tmVar:c|SUB|G|123|T"
        chr_val, start, end = extract_coordinates_from_variant(variant_id)
        assert chr_val is None
        assert start is None
        assert end is None


class TestDetermineVariantType:
    """Tests for determine_variant_type function."""

    def test_deletion(self):
        """Test deletion variant type detection."""
        variant_text = "a deletion in gene"
        variant_id = "tmVar:c|DEL|G|123|"
        assert determine_variant_type(variant_text, variant_id) == "deletion"

    def test_insertion(self):
        """Test insertion variant type detection."""
        variant_text = "an insertion of A"
        variant_id = "tmVar:c|INS|A|123|"
        assert determine_variant_type(variant_text, variant_id) == "insertion"

    def test_substitution(self):
        """Test substitution variant type detection."""
        variant_text = "G>A mutation"
        variant_id = "tmVar:c|SUB|G|123|A"
        assert determine_variant_type(variant_text, variant_id) == "substitution"

    def test_unknown(self):
        """Test unknown variant type."""
        variant_text = "some variant"
        variant_id = "unknown"
        assert determine_variant_type(variant_text, variant_id) == "unknown"


class TestExtractHGVSNotation:
    """Tests for extract_hgvs_notation function."""

    def test_extract_hgvs(self):
        """Test extraction of HGVS notation."""
        variant_id = "tmVar:c|SUB|G|123|T;HGVS:NC_000007.13:g.117188683G>A;VariantGroup:0"
        hgvs = extract_hgvs_notation(variant_id)
        assert hgvs == "NC_000007.13:g.117188683G>A"

    def test_no_hgvs(self):
        """Test when no HGVS notation is present."""
        variant_id = "tmVar:c|SUB|G|123|T;VariantGroup:0"
        hgvs = extract_hgvs_notation(variant_id)
        assert hgvs is None


class TestMergeVariantData:
    """Tests for merge_variant_data function."""

    def test_merge_variant_data(self):
        """Test merging of variant data from different sources."""
        cooccurrence_data = [
            {
                'pmid': '12345',
                'variant_text': 'G>A mutation',
                'variant_id': 'tmVar:c|SUB|G|123|A;HGVS:NC_000007.13:g.117188683G>A',
                'genes': [{'text': 'GENE1', 'id': '123'}],
                'diseases': [{'text': 'DISEASE1', 'id': '456'}]
            }
        ]
        
        llm_data = [
            {
                'pmid': '12345',
                'variant_text': 'G>A mutation',
                'variant_id': 'tmVar:c|SUB|G|123|A;HGVS:NC_000007.13:g.117188683G>A',
                'llm_relationships': [
                    {
                        'entity_type': 'gene',
                        'entity_text': 'GENE2',
                        'entity_id': '789',
                        'has_relationship': True,
                        'explanation': 'This variant acts as an enhancer for GENE2.'
                    }
                ]
            }
        ]
        
        result = merge_variant_data(cooccurrence_data, llm_data)
        assert len(result) == 1
        assert result[0]['genes'] == 'GENE1 (123); GENE2 (789)'
        assert result[0]['diseases'] == 'DISEASE1 (456)'
        assert result[0]['variant_mode'] == 'enhancer'
        assert result[0]['variant_type'] == 'substitution'
        

@pytest.fixture
def mock_config():
    """Mock Config class."""
    config_mock = MagicMock()
    config_mock.get_contact_email.return_value = "test@example.com"
    config_mock.get_llm_model_name.return_value = "test_model"
    return config_mock


@pytest.fixture
def mock_pubtator_client():
    """Mock PubTatorClient class."""
    client_mock = MagicMock()
    return client_mock


@pytest.fixture
def mock_cooccurrence_analyzer():
    """Mock CooccurrenceContextAnalyzer class."""
    analyzer_mock = MagicMock()
    analyzer_mock.analyze_publications.return_value = [
        {
            'pmid': '12345',
            'variant_text': 'G>A mutation',
            'variant_id': 'tmVar:c|SUB|G|123|A;HGVS:NC_000007.13:g.117188683G>A',
            'genes': [{'text': 'GENE1', 'id': '123'}],
            'diseases': [{'text': 'DISEASE1', 'id': '456'}]
        }
    ]
    return analyzer_mock


@pytest.fixture
def mock_llm_analyzer():
    """Mock LlmContextAnalyzer class."""
    analyzer_mock = MagicMock()
    analyzer_mock.analyze_publications.return_value = [
        {
            'pmid': '12345',
            'variant_text': 'G>A mutation',
            'variant_id': 'tmVar:c|SUB|G|123|A;HGVS:NC_000007.13:g.117188683G>A',
            'llm_relationships': [
                {
                    'entity_type': 'gene',
                    'entity_text': 'GENE2',
                    'entity_id': '789',
                    'has_relationship': True,
                    'explanation': 'This variant acts as an enhancer for GENE2.'
                }
            ]
        }
    ]
    return analyzer_mock


@patch('scripts.generate_coordinate_csv.Config')
@patch('scripts.generate_coordinate_csv.PubTatorClient')
@patch('scripts.generate_coordinate_csv.CooccurrenceContextAnalyzer')
@patch('scripts.generate_coordinate_csv.LlmContextAnalyzer')
@patch('scripts.generate_coordinate_csv.os.path.exists')
@patch('scripts.generate_coordinate_csv.os.remove')
def test_analyze_pmids(
    mock_remove, mock_exists, mock_llm_class, mock_cooc_class, 
    mock_pubtator_class, mock_config_class, 
    mock_config, mock_pubtator_client, mock_cooccurrence_analyzer, mock_llm_analyzer
):
    """Test analyze_pmids function."""
    # Setup mocks
    mock_config_class.return_value = mock_config
    mock_pubtator_class.return_value = mock_pubtator_client
    mock_cooc_class.return_value = mock_cooccurrence_analyzer
    mock_llm_class.return_value = mock_llm_analyzer
    mock_exists.return_value = True
    
    # Call the function
    result = analyze_pmids(
        pmids=['12345', '67890', '12345'],  # Note the duplicate
        output_csv='test_output.csv',
        email='test@example.com',
        llm_model='test_model'
    )
    
    # Assertions
    assert len(mock_cooc_class.call_args_list) == 1
    assert len(mock_llm_class.call_args_list) == 1
    assert mock_cooccurrence_analyzer.analyze_publications.call_count == 1
    assert mock_llm_analyzer.analyze_publications.call_count == 1
    assert mock_remove.call_count == 2  # Two temp files should be removed


@patch('scripts.generate_coordinate_csv.argparse.ArgumentParser')
@patch('scripts.generate_coordinate_csv.analyze_pmids')
@patch('scripts.generate_coordinate_csv.Config')
def test_main_with_pmids_arguments(mock_config_class, mock_analyze_pmids, mock_arg_parser, mock_config):
    """Test main function with PMIDs as arguments."""
    # Setup mocks
    mock_config_class.return_value = mock_config
    mock_args = MagicMock()
    mock_args.pmids = ['12345', '67890']
    mock_args.file = None
    mock_args.output = 'test_output.csv'
    mock_args.model = 'test_model'
    mock_args.email = 'test@example.com'
    mock_arg_parser.return_value.parse_args.return_value = mock_args
    
    # Setup mock DataFrame
    mock_df = pd.DataFrame({
        'pmid': ['12345', '67890'],
        'genes': ['GENE1', 'GENE2'],
        'diseases': ['DISEASE1', 'DISEASE2']
    })
    mock_analyze_pmids.return_value = mock_df
    
    # Import and call main to avoid module-level patch conflicts
    import scripts.generate_coordinate_csv
    scripts.generate_coordinate_csv.main()
    
    # Check that analyze_pmids was called with the right arguments
    mock_analyze_pmids.assert_called_once_with(
        pmids=['12345', '67890'],
        output_csv='test_output.csv',
        email='test@example.com',
        llm_model='test_model'
    )


@patch('scripts.generate_coordinate_csv.argparse.ArgumentParser')
@patch('scripts.generate_coordinate_csv.analyze_pmids')
@patch('scripts.generate_coordinate_csv.Config')
@patch('builtins.open', new_callable=mock_open, read_data='12345\n67890\n')
def test_main_with_pmids_file(mock_file, mock_config_class, mock_analyze_pmids, mock_arg_parser, mock_config):
    """Test main function with PMIDs from file."""
    # Setup mocks
    mock_config_class.return_value = mock_config
    mock_args = MagicMock()
    mock_args.pmids = None
    mock_args.file = 'pmids.txt'
    mock_args.output = 'test_output.csv'
    mock_args.model = 'test_model'
    mock_args.email = 'test@example.com'
    mock_arg_parser.return_value.parse_args.return_value = mock_args
    
    # Setup mock DataFrame
    mock_df = pd.DataFrame({
        'pmid': ['12345', '67890'],
        'genes': ['GENE1', 'GENE2'],
        'diseases': ['DISEASE1', 'DISEASE2']
    })
    mock_analyze_pmids.return_value = mock_df
    
    # Import and call main to avoid module-level patch conflicts
    import scripts.generate_coordinate_csv
    scripts.generate_coordinate_csv.main()
    
    # Check that analyze_pmids was called with the right arguments
    mock_analyze_pmids.assert_called_once_with(
        pmids=['12345', '67890'],
        output_csv='test_output.csv',
        email='test@example.com',
        llm_model='test_model'
    ) 