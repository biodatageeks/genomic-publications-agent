"""
Test configuration for the entire project.
"""
import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
import json

from src.utils.llm import LlmManager


@pytest.fixture
def sample_text():
    """Sample scientific publication text."""
    return """
    The study found a mutation c.123A>G in the BRCA1 gene, which is associated 
    with an increased risk of breast cancer. Additionally, the variant p.Val600Glu (also known as p.V600E) 
    in the BRAF gene is frequently observed in melanoma. Studies on chromosome 7 
    in the region chr7:140453136-140453136 also revealed a mutation c.76_78delACT.
    """


@pytest.fixture
def sample_variants():
    """List of sample genomic variants."""
    return [
        "c.123A>G",
        "p.Val600Glu",
        "p.V600E",
        "chr7:140453136-140453136",
        "c.76_78delACT"
    ]


@pytest.fixture
def sample_pubmed_ids():
    """List of sample PubMed identifiers."""
    return ["12345678", "23456789", "34567890"]


@pytest.fixture
def temp_json_file():
    """Creates a temporary JSON file."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture
def temp_csv_file():
    """Creates a temporary CSV file."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture
def temp_txt_file():
    """Creates a temporary text file."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture
def temp_dir():
    """Creates a temporary directory."""
    temp_dir = tempfile.TemporaryDirectory()
    yield temp_dir.name
    temp_dir.cleanup()


@pytest.fixture
def mock_llm():
    """Mock of an LLM object."""
    mock = MagicMock()
    mock.invoke = MagicMock(return_value="c.123A>G, p.V600E, chr7:140453136-140453136")
    return mock


@pytest.fixture
def mock_llm_manager():
    """Mock of the LlmManager object."""
    mock = MagicMock(spec=LlmManager)
    mock.get_llm.return_value = MagicMock()
    return mock


@pytest.fixture
def sample_genes():
    """List of sample genes."""
    return ["BRCA1", "BRCA2", "TP53", "BRAF", "KRAS"]


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame with variants and genes."""
    data = {
        'Gene': ['BRCA1', 'BRCA2', 'TP53', 'BRAF', 'KRAS'],
        'Variant ID': ['c.123A>G', 'c.456G>T', 'c.789C>A', 'p.V600E', 'p.G12D'],
        'Disease': ['Breast Cancer', 'Breast Cancer', 'Li-Fraumeni Syndrome', 'Melanoma', 'Colorectal Cancer'],
        'PMID(s)': ['12345678', '23456789; 34567890', '45678901', '56789012', '67890123']
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_response():
    """Sample HTTP response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """{"id": "123", "rsid": "rs123", "gene": "BRCA1"}
{"id": "456", "rsid": "rs456", "gene": "BRCA2"}"""
    mock_response.json.return_value = [
        {"id": "123", "rsid": "rs123", "gene": "BRCA1"},
        {"id": "456", "rsid": "rs456", "gene": "BRCA2"}
    ]
    return mock_response


@pytest.fixture
def snippets_data():
    """Sample snippet data with coordinates."""
    return [
        {
            "text": "Found a mutation c.123A>G in the BRCA1 gene.",
            "variant": "c.123A>G",
            "gene": "BRCA1",
            "pmid": "12345678"
        },
        {
            "text": "The variant p.Val600Glu (p.V600E) in the BRAF gene is common in melanoma.",
            "variant": "p.V600E",
            "gene": "BRAF",
            "pmid": "23456789"
        },
        {
            "text": "Studies on chromosome 7 in region chr7:140453136-140453136 revealed a mutation.",
            "variant": "chr7:140453136-140453136",
            "gene": "KRAS",
            "pmid": "34567890"
        }
    ]


@pytest.fixture
def entrez_search_result():
    """Mock of Entrez search results."""
    mock_result = MagicMock()
    mock_result.ids = ["12345678", "23456789", "34567890"]
    return mock_result


@pytest.fixture
def pubmed_article_xml():
    """Sample PubMed article XML."""
    return """
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345678</PMID>
                <Article>
                    <ArticleTitle>Test Article on BRCA1 mutation</ArticleTitle>
                    <Abstract>
                        <AbstractText>The study found a mutation c.123A>G in BRCA1.</AbstractText>
                    </Abstract>
                    <AuthorList>
                        <Author>
                            <LastName>Smith</LastName>
                            <ForeName>John</ForeName>
                            <Initials>J</Initials>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """ 