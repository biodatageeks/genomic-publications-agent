"""
Tests for the CooccurrenceContextAnalyzer class from cooccurrence_context_analyzer module.
"""
import os
import pytest
import json
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, mock_open

from src.cooccurrence_context_analyzer.cooccurrence_analyzer import CooccurrenceContextAnalyzer


class TestCooccurrenceContextAnalyzer:
    """
    Test suite for the CooccurrenceContextAnalyzer class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        analyzer = CooccurrenceContextAnalyzer()
        assert analyzer.snippets == []
        assert analyzer.snippets_file_path is None
        assert analyzer.cooccurrence_matrix is None
        assert analyzer.variants == []
        assert analyzer.pmids == []
    
    def test_init_with_snippets_file(self):
        """Test initialization with snippets file path."""
        with patch('builtins.open', new_callable=mock_open, read_data='[{"variant": "c.123A>G", "pmid": "12345678"}]'):
            analyzer = CooccurrenceContextAnalyzer(snippets_file_path="test_snippets.json")
            assert analyzer.snippets_file_path == "test_snippets.json"
            assert len(analyzer.snippets) == 1
            assert analyzer.snippets[0]["variant"] == "c.123A>G"
    
    def test_init_with_snippets_list(self):
        """Test initialization with snippets list."""
        snippets = [{"variant": "c.123A>G", "pmid": "12345678"}]
        analyzer = CooccurrenceContextAnalyzer(snippets=snippets)
        assert analyzer.snippets == snippets
        assert analyzer.snippets_file_path is None
    
    @patch('builtins.open', new_callable=mock_open, read_data='[{"variant": "c.123A>G", "pmid": "12345678"}]')
    def test_load_snippets(self, mock_file):
        """Test loading snippets from a file."""
        analyzer = CooccurrenceContextAnalyzer()
        snippets = analyzer.load_snippets("test_snippets.json")
        
        mock_file.assert_called_once_with("test_snippets.json", "r", encoding="utf-8")
        assert len(snippets) == 1
        assert snippets[0]["variant"] == "c.123A>G"
        assert analyzer.snippets == snippets
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_load_snippets_file_error(self, mock_file):
        """Test handling file error when loading snippets."""
        analyzer = CooccurrenceContextAnalyzer()
        with pytest.raises(IOError):
            analyzer.load_snippets("nonexistent.json")
    
    def test_extract_variants_and_pmids(self):
        """Test extracting unique variants and PMIDs from snippets."""
        snippets = [
            {"variant": "c.123A>G", "pmid": "12345678"},
            {"variant": "p.V600E", "pmid": "23456789"},
            {"variant": "c.123A>G", "pmid": "34567890"}
        ]
        analyzer = CooccurrenceContextAnalyzer(snippets=snippets)
        
        variants, pmids = analyzer.extract_variants_and_pmids()
        
        assert len(variants) == 2
        assert "c.123A>G" in variants
        assert "p.V600E" in variants
        assert len(pmids) == 3
        assert "12345678" in pmids
        assert "23456789" in pmids
        assert "34567890" in pmids
        assert analyzer.variants == variants
        assert analyzer.pmids == pmids
    
    def test_build_cooccurrence_matrix(self):
        """Test building the cooccurrence matrix."""
        snippets = [
            {"variant": "c.123A>G", "pmid": "12345678"},
            {"variant": "p.V600E", "pmid": "23456789"},
            {"variant": "c.123A>G", "pmid": "34567890"},
            {"variant": "p.V600E", "pmid": "12345678"}  # Both variants co-occur in this PMID
        ]
        analyzer = CooccurrenceContextAnalyzer(snippets=snippets)
        
        # Extract variants and pmids first
        analyzer.extract_variants_and_pmids()
        
        # Build the matrix
        matrix = analyzer.build_cooccurrence_matrix()
        
        assert matrix is not None
        assert matrix.shape == (2, 2)  # 2x2 matrix for 2 variants
        
        # Check co-occurrence values
        variant_indices = {v: i for i, v in enumerate(analyzer.variants)}
        c123_idx = variant_indices["c.123A>G"]
        v600e_idx = variant_indices["p.V600E"]
        
        # Both variants should co-occur with themselves
        assert matrix[c123_idx, c123_idx] > 0
        assert matrix[v600e_idx, v600e_idx] > 0
        
        # They should also co-occur with each other in PMID 12345678
        assert matrix[c123_idx, v600e_idx] > 0
        assert matrix[v600e_idx, c123_idx] > 0
    
    def test_normalize_cooccurrence_matrix(self):
        """Test normalizing the cooccurrence matrix."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Create a simple co-occurrence matrix
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T"]
        raw_matrix = np.array([
            [3, 1, 0],
            [1, 2, 1],
            [0, 1, 1]
        ])
        analyzer.cooccurrence_matrix = raw_matrix
        
        normalized_matrix = analyzer.normalize_cooccurrence_matrix()
        
        assert normalized_matrix is not None
        assert normalized_matrix.shape == (3, 3)
        
        # Check normalization
        # For cosine similarity, diagonal elements should be 1.0
        for i in range(3):
            assert normalized_matrix[i, i] == 1.0
        
        # The similarity between variant 0 and 1 should be positive but less than 1
        assert 0 < normalized_matrix[0, 1] < 1
        assert normalized_matrix[0, 1] == normalized_matrix[1, 0]  # Symmetric
        
        # The similarity between variant 0 and 2 should be 0 as they don't co-occur
        assert normalized_matrix[0, 2] == 0
        assert normalized_matrix[2, 0] == 0
    
    def test_get_most_similar_variants(self):
        """Test getting most similar variants."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Set up the analyzer with a normalized matrix
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T", "p.G12D"]
        analyzer.cooccurrence_matrix = np.array([
            [1.0, 0.7, 0.2, 0.0],
            [0.7, 1.0, 0.5, 0.3],
            [0.2, 0.5, 1.0, 0.6],
            [0.0, 0.3, 0.6, 1.0]
        ])
        
        # Get most similar variants for c.123A>G
        similar_variants = analyzer.get_most_similar_variants("c.123A>G", top_n=2)
        
        assert len(similar_variants) == 2
        assert similar_variants[0][0] == "p.V600E"  # Most similar
        assert similar_variants[0][1] == 0.7
        assert similar_variants[1][0] == "c.456G>T"  # Second most similar
        assert similar_variants[1][1] == 0.2
        
        # Get most similar variants for an unknown variant
        with pytest.raises(ValueError):
            analyzer.get_most_similar_variants("unknown", top_n=2)
    
    def test_get_variant_pairs_above_threshold(self):
        """Test getting variant pairs above similarity threshold."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Set up the analyzer with a normalized matrix
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T", "p.G12D"]
        analyzer.cooccurrence_matrix = np.array([
            [1.0, 0.7, 0.2, 0.0],
            [0.7, 1.0, 0.5, 0.3],
            [0.2, 0.5, 1.0, 0.6],
            [0.0, 0.3, 0.6, 1.0]
        ])
        
        # Get pairs with similarity > 0.5
        pairs = analyzer.get_variant_pairs_above_threshold(0.5)
        
        assert len(pairs) == 3
        # Check that each expected pair is in the results
        assert any(p[0] == "c.123A>G" and p[1] == "p.V600E" and p[2] >= 0.5 for p in pairs)
        assert any(p[0] == "p.V600E" and p[1] == "c.456G>T" and p[2] >= 0.5 for p in pairs)
        assert any(p[0] == "c.456G>T" and p[1] == "p.G12D" and p[2] >= 0.5 for p in pairs)
    
    def test_create_variant_network(self):
        """Test creating a variant network from the cooccurrence matrix."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Set up the analyzer with a normalized matrix
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T", "p.G12D"]
        analyzer.cooccurrence_matrix = np.array([
            [1.0, 0.7, 0.2, 0.0],
            [0.7, 1.0, 0.5, 0.3],
            [0.2, 0.5, 1.0, 0.6],
            [0.0, 0.3, 0.6, 1.0]
        ])
        
        # Create a network with threshold of 0.4
        network = analyzer.create_variant_network(threshold=0.4)
        
        assert len(network["nodes"]) == 4  # All 4 variants should be in the network
        assert len(network["links"]) == 3  # 3 links with similarity > 0.4
        
        # Check node IDs
        node_ids = [node["id"] for node in network["nodes"]]
        for variant in analyzer.variants:
            assert variant in node_ids
        
        # Check links
        links = network["links"]
        # c.123A>G -- p.V600E (0.7)
        assert any(link["source"] == "c.123A>G" and link["target"] == "p.V600E" and link["value"] == 0.7 for link in links)
        # p.V600E -- c.456G>T (0.5)
        assert any(link["source"] == "p.V600E" and link["target"] == "c.456G>T" and link["value"] == 0.5 for link in links)
        # c.456G>T -- p.G12D (0.6)
        assert any(link["source"] == "c.456G>T" and link["target"] == "p.G12D" and link["value"] == 0.6 for link in links)
    
    def test_identify_variant_clusters(self):
        """Test identifying variant clusters based on the cooccurrence matrix."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Set up the analyzer with a normalized matrix
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T", "p.G12D", "c.789C>T"]
        analyzer.cooccurrence_matrix = np.array([
            [1.0, 0.7, 0.2, 0.0, 0.0],
            [0.7, 1.0, 0.5, 0.1, 0.0],
            [0.2, 0.5, 1.0, 0.6, 0.0],
            [0.0, 0.1, 0.6, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0]
        ])
        
        # Identify clusters with threshold 0.4
        clusters = analyzer.identify_variant_clusters(threshold=0.4)
        
        assert len(clusters) == 2  # Should find 2 clusters
        
        # Check clusters content
        cluster_variants = [set(cluster) for cluster in clusters]
        assert {"c.123A>G", "p.V600E", "c.456G>T", "p.G12D"} in cluster_variants  # First cluster
        assert {"c.789C>T"} in cluster_variants  # Second cluster (isolated variant)
    
    def test_get_shared_pmids(self):
        """Test getting shared PMIDs between variants."""
        snippets = [
            {"variant": "c.123A>G", "pmid": "12345678"},
            {"variant": "p.V600E", "pmid": "23456789"},
            {"variant": "c.123A>G", "pmid": "34567890"},
            {"variant": "p.V600E", "pmid": "12345678"}  # Both variants share this PMID
        ]
        analyzer = CooccurrenceContextAnalyzer(snippets=snippets)
        
        shared_pmids = analyzer.get_shared_pmids("c.123A>G", "p.V600E")
        
        assert len(shared_pmids) == 1
        assert "12345678" in shared_pmids
    
    def test_get_shared_context(self):
        """Test getting shared context between variants."""
        snippets = [
            {"variant": "c.123A>G", "pmid": "12345678", "text": "Text about c.123A>G and p.V600E"},
            {"variant": "p.V600E", "pmid": "23456789", "text": "Text about p.V600E only"},
            {"variant": "c.123A>G", "pmid": "34567890", "text": "Another text about c.123A>G"},
            {"variant": "p.V600E", "pmid": "12345678", "text": "Text about p.V600E and c.123A>G"}
        ]
        analyzer = CooccurrenceContextAnalyzer(snippets=snippets)
        
        shared_context = analyzer.get_shared_context("c.123A>G", "p.V600E")
        
        assert len(shared_context) == 1
        assert shared_context[0]["pmid"] == "12345678"
        assert "c.123A>G" in shared_context[0]["text"]
        assert "p.V600E" in shared_context[0]["text"]
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_network(self, mock_file):
        """Test saving the variant network to a file."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Create a simple network
        network = {
            "nodes": [
                {"id": "c.123A>G", "group": 1},
                {"id": "p.V600E", "group": 1}
            ],
            "links": [
                {"source": "c.123A>G", "target": "p.V600E", "value": 0.7}
            ]
        }
        
        analyzer.save_network(network, "network.json")
        
        mock_file.assert_called_once_with("network.json", "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Verify JSON was written correctly
        json_str = mock_handle.write.call_args[0][0]
        saved_network = json.loads(json_str)
        assert len(saved_network["nodes"]) == 2
        assert len(saved_network["links"]) == 1
        assert saved_network["nodes"][0]["id"] == "c.123A>G"
        assert saved_network["links"][0]["value"] == 0.7
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_network_file_error(self, mock_file):
        """Test handling file error when saving network."""
        analyzer = CooccurrenceContextAnalyzer()
        
        network = {"nodes": [], "links": []}
        
        with pytest.raises(IOError):
            analyzer.save_network(network, "invalid/path.json")
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_clusters(self, mock_file):
        """Test saving variant clusters to a file."""
        analyzer = CooccurrenceContextAnalyzer()
        
        clusters = [
            ["c.123A>G", "p.V600E"],
            ["c.456G>T"]
        ]
        
        analyzer.save_clusters(clusters, "clusters.json")
        
        mock_file.assert_called_once_with("clusters.json", "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Verify JSON was written correctly
        json_str = mock_handle.write.call_args[0][0]
        saved_clusters = json.loads(json_str)
        assert len(saved_clusters) == 2
        assert saved_clusters[0] == ["c.123A>G", "p.V600E"]
        assert saved_clusters[1] == ["c.456G>T"]
    
    def test_generate_cooccurrence_report(self):
        """Test generating a cooccurrence report for variants."""
        analyzer = CooccurrenceContextAnalyzer()
        
        # Set up test data
        analyzer.variants = ["c.123A>G", "p.V600E", "c.456G>T"]
        analyzer.cooccurrence_matrix = np.array([
            [1.0, 0.7, 0.2],
            [0.7, 1.0, 0.5],
            [0.2, 0.5, 1.0]
        ])
        
        snippets = [
            {"variant": "c.123A>G", "pmid": "12345678", "text": "Text about c.123A>G and p.V600E"},
            {"variant": "p.V600E", "pmid": "12345678", "text": "Text about p.V600E and c.123A>G"},
            {"variant": "p.V600E", "pmid": "23456789", "text": "Text about p.V600E and c.456G>T"},
            {"variant": "c.456G>T", "pmid": "23456789", "text": "Text about c.456G>T and p.V600E"}
        ]
        analyzer.snippets = snippets
        
        report = analyzer.generate_cooccurrence_report("c.123A>G")
        
        assert report is not None
        assert "c.123A>G" in report
        assert "p.V600E" in report  # Most similar variant
        assert "0.7" in report  # Similarity score
        assert "12345678" in report  # Shared PMID
    
    # Integration tests
    
    def test_integration_build_and_analyze(self, snippets_data, temp_json_file):
        """Integration test for building and analyzing cooccurrence matrix."""
        # Add PMIDs to the snippets data
        for i, snippet in enumerate(snippets_data):
            snippet["pmid"] = f"PMID{i+1}"
        
        # Force co-occurrence by making two variants appear in the same PMID
        snippets_data[0]["pmid"] = "PMID_shared"
        snippets_data[1]["pmid"] = "PMID_shared"
        
        # Write test data to temp file
        with open(temp_json_file, 'w', encoding='utf-8') as f:
            json.dump(snippets_data, f)
        
        # Initialize analyzer and load data
        analyzer = CooccurrenceContextAnalyzer(snippets_file_path=temp_json_file)
        
        # Extract variants and PMIDs
        variants, pmids = analyzer.extract_variants_and_pmids()
        assert len(variants) > 0
        assert len(pmids) > 0
        
        # Build and normalize matrix
        matrix = analyzer.build_cooccurrence_matrix()
        normalized_matrix = analyzer.normalize_cooccurrence_matrix()
        assert matrix is not None
        assert normalized_matrix is not None
        
        # Get similar variants for the first variant
        first_variant = variants[0]
        similar_variants = analyzer.get_most_similar_variants(first_variant, top_n=1)
        assert len(similar_variants) <= 1  # Might be 0 if no similar variants
        
        # Create network
        network = analyzer.create_variant_network(threshold=0.1)
        assert len(network["nodes"]) == len(variants)
    
    def test_integration_full_pipeline(self, snippets_data, temp_json_file, temp_dir):
        """Integration test for running the full analysis pipeline."""
        # Add PMIDs to the snippets data
        for i, snippet in enumerate(snippets_data):
            snippet["pmid"] = f"PMID{i+1}"
            if i % 2 == 0:  # Make some variants co-occur
                snippet["pmid"] = "PMID_shared"
        
        # Write test data to temp file
        input_file = os.path.join(temp_dir, "snippets.json")
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(snippets_data, f)
        
        # Output files
        network_file = os.path.join(temp_dir, "network.json")
        clusters_file = os.path.join(temp_dir, "clusters.json")
        
        # Initialize analyzer
        analyzer = CooccurrenceContextAnalyzer()
        
        # Run the full pipeline
        analyzer.load_snippets(input_file)
        analyzer.extract_variants_and_pmids()
        analyzer.build_cooccurrence_matrix()
        analyzer.normalize_cooccurrence_matrix()
        
        network = analyzer.create_variant_network(threshold=0.1)
        analyzer.save_network(network, network_file)
        
        clusters = analyzer.identify_variant_clusters(threshold=0.1)
        analyzer.save_clusters(clusters, clusters_file)
        
        # Verify output files exist
        assert os.path.exists(network_file)
        assert os.path.exists(clusters_file)
        
        # Check content of files
        with open(network_file, 'r', encoding='utf-8') as f:
            saved_network = json.load(f)
            assert "nodes" in saved_network
            assert "links" in saved_network
        
        with open(clusters_file, 'r', encoding='utf-8') as f:
            saved_clusters = json.load(f)
            assert isinstance(saved_clusters, list) 