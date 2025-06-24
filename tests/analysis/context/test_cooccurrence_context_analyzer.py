"""
Unit tests for CooccurrenceContextAnalyzer.
"""

import pytest
import os
import tempfile
import json
import csv
import requests
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

import bioc
from bioc import BioCDocument, BioCPassage, BioCAnnotation, BioCLocation

from src.api.clients.exceptions import PubTatorError
from src.analysis.context.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer

# Sample test data
SAMPLE_BIOC_DOC = {
    "id": "12345678",
    "infons": {},
    "passages": [
        {
            "offset": 0,
            "infons": {"section": "title"},
            "text": "BRAF with V600E mutation in melanoma.",
            "annotations": [
                {
                    "id": "T1",
                    "text": "BRAF",
                    "infons": {"type": "Gene", "identifier": "673"},
                    "locations": [{"offset": 0, "length": 4}]
                },
                {
                    "id": "T2",
                    "text": "V600E",
                    "infons": {"type": "Mutation", "identifier": "p.Val600Glu"},
                    "locations": [{"offset": 10, "length": 5}]
                },
                {
                    "id": "T3",
                    "text": "melanoma",
                    "infons": {"type": "Disease", "identifier": "D008545"},
                    "locations": [{"offset": 24, "length": 8}]
                }
            ]
        },
        {
            "offset": 50,
            "infons": {"section": "abstract"},
            "text": "The KRAS G12D mutation is found in pancreatic cancer.",
            "annotations": [
                {
                    "id": "T4",
                    "text": "KRAS",
                    "infons": {"type": "Gene", "identifier": "3845"},
                    "locations": [{"offset": 4, "length": 4}]
                },
                {
                    "id": "T5",
                    "text": "G12D",
                    "infons": {"type": "Mutation", "identifier": "p.Gly12Asp"},
                    "locations": [{"offset": 9, "length": 4}]
                },
                {
                    "id": "T6",
                    "text": "pancreatic cancer",
                    "infons": {"type": "Disease", "identifier": "D010190"},
                    "locations": [{"offset": 29, "length": 17}]
                }
            ]
        },
        {
            "offset": 100,
            "infons": {"section": "body"},
            "text": "p53 is a tumor suppressor gene.",
            "annotations": [
                {
                    "id": "T7",
                    "text": "p53",
                    "infons": {"type": "Gene", "identifier": "7157"},
                    "locations": [{"offset": 0, "length": 3}]
                }
            ]
        }
    ]
}

# Helper function to convert dict to BioCDocument
def dict_to_bioc_document(doc_data):
    """Convert a dictionary to a BioCDocument object."""
    doc = bioc.BioCDocument()
    doc.id = doc_data["id"]
    doc.infons = doc_data["infons"]
    
    for passage_data in doc_data["passages"]:
        passage = bioc.BioCPassage()
        passage.offset = passage_data["offset"]
        passage.text = passage_data["text"]
        passage.infons = passage_data["infons"]
        
        for anno_data in passage_data.get("annotations", []):
            anno = bioc.BioCAnnotation()
            anno.id = anno_data["id"]
            anno.text = anno_data["text"]
            anno.infons = anno_data["infons"]
            
            for loc_data in anno_data.get("locations", []):
                loc = bioc.BioCLocation(offset=loc_data["offset"], length=loc_data["length"])
                anno.add_location(loc)
                
            passage.add_annotation(anno)
            
        doc.add_passage(passage)
    
    return doc

# Helper functions for creating test objects
def create_mock_annotation(text, anno_type, anno_id=None, offset=0, length=None):
    """Create a mock BioCAnnotation."""
    annotation = bioc.BioCAnnotation()
    annotation.text = text
    annotation.infons["type"] = anno_type
    if anno_id:
        annotation.infons["identifier"] = anno_id
    
    # Create a location for the annotation
    if length is None:
        length = len(text)
    location = bioc.BioCLocation(offset=offset, length=length)
    annotation.add_location(location)
    
    return annotation

def create_mock_passage(text, annotations=None):
    """Create a mock BioCPassage."""
    passage = bioc.BioCPassage()
    passage.text = text
    passage.offset = 0
    
    if annotations:
        for annotation in annotations:
            passage.add_annotation(annotation)
    
    return passage

def create_mock_document(pmid, passages=None):
    """Create a mock BioCDocument."""
    document = bioc.BioCDocument()
    document.id = pmid
    
    if passages:
        for passage in passages:
            document.add_passage(passage)
    
    return document

# Fixtures
@pytest.fixture
def analyzer():
    """Create an analyzer with mocked pubtator client."""
    mock_pubtator_client = Mock()
    return CooccurrenceContextAnalyzer(mock_pubtator_client)

@pytest.fixture
def mock_document():
    """Create a sample BioCDocument for testing."""
    # Convert the dict to a BioCDocument object
    doc_data = SAMPLE_BIOC_DOC
    return dict_to_bioc_document(doc_data)

# Tests
def test_initialization():
    """Test that the analyzer initializes correctly."""
    # Test with a custom client
    mock_pubtator_client = Mock()
    analyzer = CooccurrenceContextAnalyzer(mock_pubtator_client)
    assert analyzer.pubtator_client == mock_pubtator_client
    
    # Test with default client
    with patch('src.cooccurrence_context_analyzer.cooccurrence_context_analyzer.PubTatorClient') as mock_client_class:
        analyzer = CooccurrenceContextAnalyzer()
        mock_client_class.assert_called_once()

def test_group_annotations_by_type(analyzer):
    """Test grouping annotations by type."""
    # Create mock annotations
    gene_anno = create_mock_annotation("BRCA1", "Gene")
    disease_anno = create_mock_annotation("Cancer", "Disease")
    variant_anno = create_mock_annotation("p.Val600Glu", "Mutation")
    
    # Create a passage with these annotations
    passage = create_mock_passage("BRCA1 is associated with cancer. The p.Val600Glu mutation...", 
                                 [gene_anno, disease_anno, variant_anno])
    
    # Test grouping
    result = analyzer._group_annotations_by_type(passage)
    
    # Verify results
    assert "Gene" in result
    assert "Disease" in result
    assert "Mutation" in result
    assert len(result["Gene"]) == 1
    assert len(result["Disease"]) == 1
    assert len(result["Mutation"]) == 1
    assert result["Gene"][0].text == "BRCA1"
    assert result["Disease"][0].text == "Cancer"
    assert result["Mutation"][0].text == "p.Val600Glu"

def test_analyze_passage_no_variants(analyzer):
    """Test that _analyze_passage returns an empty list when no variants are present."""
    # Create mock annotations without variants
    gene_anno = create_mock_annotation("BRCA1", "Gene")
    disease_anno = create_mock_annotation("Cancer", "Disease")
    
    # Create a passage with these annotations
    passage = create_mock_passage("BRCA1 is associated with cancer.", 
                                 [gene_anno, disease_anno])
    
    # Test analysis
    result = analyzer._analyze_passage("12345678", passage)
    
    # Verify results
    assert result == []

def test_analyze_passage_with_variants(analyzer):
    """Test that _analyze_passage correctly identifies relationships in a passage with variants."""
    # Create mock annotations
    gene_anno = create_mock_annotation("BRCA1", "Gene", "6932", 0, 5)
    disease_anno = create_mock_annotation("Cancer", "Disease", "D009369", 25, 6)
    variant_anno = create_mock_annotation("p.Val600Glu", "Mutation", "p.Val600Glu", 50, 10)
    
    # Create a passage with these annotations
    passage_text = "BRCA1 is associated with cancer. The p.Val600Glu mutation is significant."
    passage = create_mock_passage(passage_text, 
                                 [gene_anno, disease_anno, variant_anno])
    
    # Test analysis
    result = analyzer._analyze_passage("12345678", passage)
    
    # Verify results
    assert len(result) == 1
    assert result[0]["pmid"] == "12345678"
    assert result[0]["variant_text"] == "p.Val600Glu"
    assert result[0]["variant_id"] == "p.Val600Glu"
    assert result[0]["variant_offset"] == 50
    assert result[0]["passage_text"] == passage_text
    
    # Check genes
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRCA1"
    assert result[0]["genes"][0]["id"] == "6932"
    assert result[0]["genes"][0]["offset"] == 0
    
    # Check diseases
    assert len(result[0]["diseases"]) == 1
    assert result[0]["diseases"][0]["text"] == "Cancer"
    assert result[0]["diseases"][0]["id"] == "D009369"
    assert result[0]["diseases"][0]["offset"] == 25

def test_analyze_publication(analyzer):
    """Test analyzing a complete publication."""
    # Create a mock document with multiple passages
    pmid = "12345678"
    
    # Passage 1 with a variant and gene
    gene_anno1 = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
    variant_anno1 = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
    passage1 = create_mock_passage("BRAF with V600E mutation", [gene_anno1, variant_anno1])
    
    # Passage 2 with a variant and disease
    disease_anno2 = create_mock_annotation("Melanoma", "Disease", "D008545", 0, 8)
    variant_anno2 = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 20, 5)
    passage2 = create_mock_passage("Melanoma carries V600E mutation", [disease_anno2, variant_anno2])
    
    # Passage 3 with no variants
    gene_anno3 = create_mock_annotation("p53", "Gene", "7157", 0, 3)
    passage3 = create_mock_passage("p53 is a tumor suppressor gene", [gene_anno3])
    
    # Create document
    document = create_mock_document(pmid, [passage1, passage2, passage3])
    
    # Test analysis
    result = analyzer._analyze_publication(document)
    
    # Verify results
    assert len(result) == 2  # Two passages have variants
    
    # Check first passage relationship
    assert result[0]["pmid"] == pmid
    assert result[0]["variant_text"] == "V600E"
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRAF"
    
    # Check second passage relationship
    assert result[1]["pmid"] == pmid
    assert result[1]["variant_text"] == "V600E"
    assert len(result[1]["diseases"]) == 1
    assert result[1]["diseases"][0]["text"] == "Melanoma"

def test_analyze_publication_by_pmid(analyzer):
    """Test analyzing a publication by PMID."""
    pmid = "12345678"
    
    # Create a mock publication
    gene_anno = create_mock_annotation("BRAF", "Gene")
    variant_anno = create_mock_annotation("V600E", "Mutation")
    passage = create_mock_passage("BRAF with V600E mutation", [gene_anno, variant_anno])
    document = create_mock_document(pmid, [passage])
    
    # Mock the pubtator client get_publication_by_pmid method
    analyzer.pubtator_client.get_publication_by_pmid.return_value = document
    
    # Test analysis
    result = analyzer.analyze_publication(pmid)
    
    # Verify result
    assert len(result) == 1
    assert result[0]["pmid"] == pmid
    assert result[0]["variant_text"] == "V600E"
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRAF"
    
    # Verify client method was called
    analyzer.pubtator_client.get_publication_by_pmid.assert_called_once_with(pmid)

def test_analyze_publication_not_found(analyzer):
    """Test analyzing a publication that doesn't exist."""
    pmid = "99999999"
    
    # Mock the pubtator client to return None (publication not found)
    analyzer.pubtator_client.get_publication_by_pmid.return_value = None
    
    # Test analysis
    result = analyzer.analyze_publication(pmid)
    
    # Verify result is empty
    assert result == []
    
    # Verify client method was called
    analyzer.pubtator_client.get_publication_by_pmid.assert_called_once_with(pmid)

def test_analyze_publication_api_error(analyzer):
    """Test analyzing a publication when the API returns an error."""
    pmid = "12345678"
    
    # Mock the pubtator client to raise a PubTatorError
    analyzer.pubtator_client.get_publication_by_pmid.side_effect = PubTatorError("API error")
    
    # Test analysis
    with pytest.raises(PubTatorError):
        analyzer.analyze_publication(pmid)
    
    # Verify client method was called
    analyzer.pubtator_client.get_publication_by_pmid.assert_called_once_with(pmid)

def test_analyze_publications(analyzer):
    """Test analyzing multiple publications."""
    pmids = ["12345678", "87654321"]
    
    # Create mock publications
    gene_anno1 = create_mock_annotation("BRAF", "Gene")
    variant_anno1 = create_mock_annotation("V600E", "Mutation")
    passage1 = create_mock_passage("BRAF with V600E mutation", [gene_anno1, variant_anno1])
    document1 = create_mock_document(pmids[0], [passage1])
    
    gene_anno2 = create_mock_annotation("KRAS", "Gene")
    variant_anno2 = create_mock_annotation("G12D", "Mutation")
    passage2 = create_mock_passage("KRAS with G12D mutation", [gene_anno2, variant_anno2])
    document2 = create_mock_document(pmids[1], [passage2])
    
    # Mock the pubtator client get_publications_by_pmids method
    analyzer.pubtator_client.get_publications_by_pmids.return_value = [document1, document2]
    
    # Test analysis
    result = analyzer.analyze_publications(pmids)
    
    # Verify result
    assert len(result) == 2
    assert result[0]["pmid"] == pmids[0]
    assert result[0]["variant_text"] == "V600E"
    assert result[0]["genes"][0]["text"] == "BRAF"
    assert result[1]["pmid"] == pmids[1]
    assert result[1]["variant_text"] == "G12D"
    assert result[1]["genes"][0]["text"] == "KRAS"
    
    # Verify client method was called
    analyzer.pubtator_client.get_publications_by_pmids.assert_called_once_with(pmids)

def test_analyze_publications_api_error(analyzer):
    """Test analyzing publications when the API returns an error."""
    pmids = ["12345678", "87654321"]
    
    # Mock the pubtator client to raise a PubTatorError
    analyzer.pubtator_client.get_publications_by_pmids.side_effect = PubTatorError("API error")
    
    # Test analysis
    with pytest.raises(PubTatorError):
        analyzer.analyze_publications(pmids)
    
    # Verify client method was called
    analyzer.pubtator_client.get_publications_by_pmids.assert_called_once_with(pmids)

def test_save_relationships_to_csv(analyzer):
    """Test saving relationships to a CSV file."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "variant_offset": 100,
            "variant_id": "p.Val600Glu",
            "genes": [{"text": "BRAF", "id": "673", "offset": 0}],
            "diseases": [{"text": "Melanoma", "id": "D008545", "offset": 50}],
            "tissues": [],
            "passage_text": "BRAF gene is associated with Melanoma with V600E mutation."
        }
    ]
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save relationships to the temp file
        analyzer.save_relationships_to_csv(relationships, temp_path)
        
        # Read the CSV file and verify contents
        with open(temp_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            # Should be one row per gene-disease-tissue combination
            assert len(rows) == 1
            
            # Verify the content of the row
            assert rows[0]["pmid"] == "12345678"
            assert rows[0]["variant_text"] == "V600E"
            assert rows[0]["gene_text"] == "BRAF"
            assert rows[0]["gene_id"] == "673"
            assert rows[0]["disease_text"] == "Melanoma"
            assert rows[0]["disease_id"] == "D008545"
            assert rows[0]["tissue_text"] == ""
            assert rows[0]["tissue_id"] == ""
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_save_relationships_to_csv_empty(analyzer):
    """Test saving empty relationships to a CSV file."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save empty relationships
        analyzer.save_relationships_to_csv([], temp_path)
        
        # File should not have been created or should be empty
        assert os.path.getsize(temp_path) == 0
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_save_relationships_to_json(analyzer):
    """Test saving relationships to a JSON file."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "variant_offset": 100,
            "variant_id": "p.Val600Glu",
            "genes": [{"text": "BRAF", "id": "673", "offset": 0}],
            "diseases": [{"text": "Melanoma", "id": "D008545", "offset": 50}],
            "tissues": [],
            "passage_text": "BRAF gene is associated with Melanoma with V600E mutation."
        }
    ]
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save relationships to the temp file
        analyzer.save_relationships_to_json(relationships, temp_path)
        
        # Read the JSON file and verify contents
        with open(temp_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            
            # Should be one entry
            assert len(data) == 1
            
            # Verify the content
            assert data[0]["pmid"] == "12345678"
            assert data[0]["variant_text"] == "V600E"
            assert data[0]["genes"][0]["text"] == "BRAF"
            assert data[0]["diseases"][0]["text"] == "Melanoma"
            assert data[0]["passage_text"] == "BRAF gene is associated with Melanoma with V600E mutation."
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_save_relationships_to_json_empty(analyzer):
    """Test saving empty relationships to a JSON file."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save empty relationships
        analyzer.save_relationships_to_json([], temp_path)
        
        # File should not have been created or should be empty
        assert os.path.getsize(temp_path) == 0
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_filter_relationships_by_entity_gene(analyzer):
    """Test filtering relationships by gene."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "genes": [{"text": "BRAF", "id": "673"}],
            "diseases": [{"text": "Melanoma", "id": "D008545"}]
        },
        {
            "pmid": "87654321",
            "variant_text": "G12D",
            "genes": [{"text": "KRAS", "id": "3845"}],
            "diseases": [{"text": "Pancreatic cancer", "id": "D010190"}]
        }
    ]
    
    # Filter by BRAF gene
    filtered = analyzer.filter_relationships_by_entity(relationships, "gene", "BRAF")
    
    # Verify only the BRAF relationship is returned
    assert len(filtered) == 1
    assert filtered[0]["pmid"] == "12345678"
    assert filtered[0]["variant_text"] == "V600E"
    assert filtered[0]["genes"][0]["text"] == "BRAF"

def test_filter_relationships_by_entity_disease(analyzer):
    """Test filtering relationships by disease."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "genes": [{"text": "BRAF", "id": "673"}],
            "diseases": [{"text": "Melanoma", "id": "D008545"}]
        },
        {
            "pmid": "87654321",
            "variant_text": "G12D",
            "genes": [{"text": "KRAS", "id": "3845"}],
            "diseases": [{"text": "Pancreatic cancer", "id": "D010190"}]
        }
    ]
    
    # Filter by Pancreatic cancer
    filtered = analyzer.filter_relationships_by_entity(relationships, "disease", "Pancreatic cancer")
    
    # Verify only the Pancreatic cancer relationship is returned
    assert len(filtered) == 1
    assert filtered[0]["pmid"] == "87654321"
    assert filtered[0]["variant_text"] == "G12D"
    assert filtered[0]["diseases"][0]["text"] == "Pancreatic cancer"

def test_filter_relationships_by_entity_id(analyzer):
    """Test filtering relationships by entity ID."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "genes": [{"text": "BRAF", "id": "673"}],
            "diseases": [{"text": "Melanoma", "id": "D008545"}]
        },
        {
            "pmid": "87654321",
            "variant_text": "G12D",
            "genes": [{"text": "KRAS", "id": "3845"}],
            "diseases": [{"text": "Pancreatic cancer", "id": "D010190"}]
        }
    ]
    
    # Filter by BRAF gene ID
    filtered = analyzer.filter_relationships_by_entity(relationships, "gene", "673")
    
    # Verify only the BRAF relationship is returned
    assert len(filtered) == 1
    assert filtered[0]["pmid"] == "12345678"
    assert filtered[0]["genes"][0]["id"] == "673"

def test_filter_relationships_by_entity_no_matches(analyzer):
    """Test filtering relationships when there are no matches."""
    # Create test relationships
    relationships = [
        {
            "pmid": "12345678",
            "variant_text": "V600E",
            "genes": [{"text": "BRAF", "id": "673"}],
            "diseases": [{"text": "Melanoma", "id": "D008545"}]
        }
    ]
    
    # Filter by a non-existent gene
    filtered = analyzer.filter_relationships_by_entity(relationships, "gene", "TP53")
    
    # Verify no relationships are returned
    assert len(filtered) == 0

def test_filter_relationships_by_entity_empty(analyzer):
    """Test filtering an empty list of relationships."""
    # Filter empty relationships
    filtered = analyzer.filter_relationships_by_entity([], "gene", "BRAF")
    
    # Verify empty list is returned
    assert filtered == []

def test_csv_flattening_multiple_combinations(analyzer):
    """Test that the CSV flattening correctly handles multiple entity combinations."""
    # Create a relationship with multiple genes, diseases, and tissues
    relationship = {
        "pmid": "12345678",
        "variant_text": "V600E",
        "variant_offset": 100,
        "variant_id": "p.Val600Glu",
        "genes": [
            {"text": "BRAF", "id": "673", "offset": 0},
            {"text": "NRAS", "id": "4893", "offset": 10}
        ],
        "diseases": [
            {"text": "Melanoma", "id": "D008545", "offset": 50},
            {"text": "Thyroid cancer", "id": "D013964", "offset": 60}
        ],
        "tissues": [
            {"text": "Skin", "id": "T-01000", "offset": 70}
        ],
        "passage_text": "BRAF and NRAS genes are associated with Melanoma and Thyroid cancer in Skin tissue with V600E mutation."
    }
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Save relationship to the temp file
        analyzer.save_relationships_to_csv([relationship], temp_path)
        
        # Read the CSV file and verify contents
        with open(temp_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            # Should be 2 genes * 2 diseases * 1 tissue = 4 rows
            assert len(rows) == 4
            
            # Check combination counts
            braf_melanoma = 0
            braf_thyroid = 0
            nras_melanoma = 0
            nras_thyroid = 0
            
            for row in rows:
                gene = row["gene_text"]
                disease = row["disease_text"]
                
                if gene == "BRAF" and disease == "Melanoma":
                    braf_melanoma += 1
                elif gene == "BRAF" and disease == "Thyroid cancer":
                    braf_thyroid += 1
                elif gene == "NRAS" and disease == "Melanoma":
                    nras_melanoma += 1
                elif gene == "NRAS" and disease == "Thyroid cancer":
                    nras_thyroid += 1
            
            # Verify all combinations exist
            assert braf_melanoma == 1
            assert braf_thyroid == 1
            assert nras_melanoma == 1
            assert nras_thyroid == 1
            
            # Verify tissue is the same in all rows
            for row in rows:
                assert row["tissue_text"] == "Skin"
    finally:
        # Clean up the temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_analyze_document_with_multiple_mutation_types(analyzer):
    """Test analyzing a document with different types of mutations/variants."""
    # Create a document with DNAMutation and Mutation
    pmid = "12345678"
    
    # Passage with DNAMutation
    gene_anno1 = create_mock_annotation("EGFR", "Gene", "1956", 0, 4)
    mutation_anno1 = create_mock_annotation("T790M", "DNAMutation", "p.Thr790Met", 10, 5)
    passage1 = create_mock_passage("EGFR with T790M mutation", [gene_anno1, mutation_anno1])
    
    # Passage with Variant
    gene_anno2 = create_mock_annotation("PTEN", "Gene", "5728", 0, 4)
    variant_anno2 = create_mock_annotation("rs123456", "Variant", "rs123456", 10, 8)
    passage2 = create_mock_passage("PTEN with rs123456 variant", [gene_anno2, variant_anno2])
    
    # Create document
    document = create_mock_document(pmid, [passage1, passage2])
    
    # Test analysis
    result = analyzer._analyze_publication(document)
    
    # Verify both mutation types were detected
    assert len(result) == 2
    mutation_texts = [r["variant_text"] for r in result]
    assert "T790M" in mutation_texts
    assert "rs123456" in mutation_texts

def test_extract_all_annotation_types(analyzer):
    """Test that all annotation types are properly extracted."""
    # Create a document with various entity types
    pmid = "12345678"

    # Create annotations
    gene_anno = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
    mutation_anno = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
    disease_anno = create_mock_annotation("Melanoma", "Disease", "D008545", 20, 8)
    tissue_anno = create_mock_annotation("Skin", "Tissue", "T-01000", 30, 4)
    species_anno = create_mock_annotation("Human", "Species", "9606", 40, 5)
    chemical_anno = create_mock_annotation("Vemurafenib", "Chemical", "C0392477", 50, 10)

    # Create passage with all annotations
    passage = create_mock_passage(
        "BRAF V600E mutation in Melanoma of Skin tissue in Human treated with Vemurafenib",
        [gene_anno, mutation_anno, disease_anno, tissue_anno, species_anno, chemical_anno]
    )

    # Create document
    document = create_mock_document(pmid, [passage])

    # Debugging - sprawdź, czy adnotacje są poprawnie pogrupowane
    entities_by_type = analyzer._group_annotations_by_type(passage)
    print(f"DEBUG - Entities by type: {entities_by_type.keys()}")
    for key, value in entities_by_type.items():
        print(f"DEBUG - {key}: {[a.text for a in value]}")

    # Override ENTITY_TYPES, aby upewnić się, że typy species i chemical są poprawnie skonfigurowane
    original_entity_types = analyzer.ENTITY_TYPES.copy()
    analyzer.ENTITY_TYPES = {
        "variant": ["Mutation", "DNAMutation", "Variant"],
        "gene": ["Gene"],
        "disease": ["Disease"],
        "tissue": ["Tissue"],
        "species": ["Species"],
        "chemical": ["Chemical"]
    }

    try:
        # Test analysis
        result = analyzer._analyze_publication(document)
        
        # Debugging - pokaż rezultat
        print(f"DEBUG - Result: {result}")
        if result:
            print(f"DEBUG - Result keys: {result[0].keys()}")
            for key, value in result[0].items():
                if isinstance(value, list):
                    print(f"DEBUG - {key}: {value}")

        # Verify all entity types were extracted
        assert len(result) == 1
        assert len(result[0]["genes"]) == 1
        assert len(result[0]["diseases"]) == 1
        assert len(result[0]["tissues"]) == 1
        assert len(result[0]["species"]) == 1
        assert len(result[0]["chemicals"]) == 1
    finally:
        # Restore original ENTITY_TYPES
        analyzer.ENTITY_TYPES = original_entity_types

def test_real_world_sample(analyzer):
    """Test with a realistic BioC document sample."""
    # Convert the sample BioC document to a BioCDocument
    document = dict_to_bioc_document(SAMPLE_BIOC_DOC)
    
    # Test analysis
    result = analyzer._analyze_publication(document)
    
    # Verify passage-level analysis
    assert len(result) == 2  # Two passages with variants/mutations
    
    # First passage (BRAF V600E with melanoma)
    assert result[0]["variant_text"] == "V600E"
    assert result[0]["genes"][0]["text"] == "BRAF"
    assert result[0]["diseases"][0]["text"] == "melanoma"
    
    # Second passage (KRAS G12D with pancreatic cancer)
    assert result[1]["variant_text"] == "G12D"
    assert result[1]["genes"][0]["text"] == "KRAS"
    assert result[1]["diseases"][0]["text"] == "pancreatic cancer"

def test_entity_types_config():
    """Test that the entity types configuration is correct."""
    analyzer = CooccurrenceContextAnalyzer()
    
    # Check entity types configuration
    assert "variant" in analyzer.ENTITY_TYPES
    assert "gene" in analyzer.ENTITY_TYPES
    assert "disease" in analyzer.ENTITY_TYPES
    assert "tissue" in analyzer.ENTITY_TYPES
    
    # Check variant types
    assert "Mutation" in analyzer.ENTITY_TYPES["variant"]
    assert "DNAMutation" in analyzer.ENTITY_TYPES["variant"]
    assert "Variant" in analyzer.ENTITY_TYPES["variant"]
    
    # Check gene types
    assert "Gene" in analyzer.ENTITY_TYPES["gene"]
    
    # Check disease types
    assert "Disease" in analyzer.ENTITY_TYPES["disease"]

def test_error_handling_in_analyze_publications(analyzer):
    """Test error handling in analyze_publications method."""
    pmids = ["12345678", "87654321"]
    
    # Mock get_publications_by_pmids to raise different exceptions
    
    # 1. Test with connection error
    analyzer.pubtator_client.get_publications_by_pmids.side_effect = requests.ConnectionError("Connection failed")
    with pytest.raises(PubTatorError) as exc_info:
        # Użyj patch, aby zamockować podnoszenie PubTatorError
        with patch('src.cooccurrence_context_analyzer.cooccurrence_context_analyzer.PubTatorError', side_effect=PubTatorError) as mock_error:
            analyzer.analyze_publications(pmids)
    
    # 2. Test with timeout error
    analyzer.pubtator_client.get_publications_by_pmids.side_effect = requests.Timeout("Request timed out")
    with pytest.raises(PubTatorError) as exc_info:
        # Użyj patch, aby zamockować podnoszenie PubTatorError
        with patch('src.cooccurrence_context_analyzer.cooccurrence_context_analyzer.PubTatorError', side_effect=PubTatorError) as mock_error:
            analyzer.analyze_publications(pmids)
    
    # 3. Test with HTTP error
    analyzer.pubtator_client.get_publications_by_pmids.side_effect = requests.HTTPError("404 Not Found")
    with pytest.raises(PubTatorError) as exc_info:
        # Użyj patch, aby zamockować podnoszenie PubTatorError
        with patch('src.cooccurrence_context_analyzer.cooccurrence_context_analyzer.PubTatorError', side_effect=PubTatorError) as mock_error:
            analyzer.analyze_publications(pmids)

def test_malformed_annotation(analyzer):
    """Test handling of malformed annotation without locations."""
    # Create a malformed annotation without locations
    malformed_anno = bioc.BioCAnnotation()
    malformed_anno.text = "Malformed"
    malformed_anno.infons["type"] = "Mutation"
    
    # Create a passage with the malformed annotation
    passage = create_mock_passage("Passage with malformed annotation", [malformed_anno])
    
    # Test analysis
    result = analyzer._analyze_passage("12345678", passage)
    
    # Verify the annotation was processed but offset is None
    assert len(result) == 1
    assert result[0]["variant_text"] == "Malformed"
    assert result[0]["variant_offset"] is None 