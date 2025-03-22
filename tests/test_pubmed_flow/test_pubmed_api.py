"""
Tests for PubmedAPI class from pubmed_flow module.
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from src.pubmed_flow.pubmed_api import PubmedAPI


class TestPubmedAPI:
    """
    Test suite for the PubmedAPI class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        api = PubmedAPI()
        assert api.email == "test@example.com"
        assert api.api_key is None
        assert api.tool == "pytest"
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        api = PubmedAPI(email="custom@email.com", api_key="abc123", tool="custom_tool")
        assert api.email == "custom@email.com"
        assert api.api_key == "abc123"
        assert api.tool == "custom_tool"
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_search_articles(self, mock_entrez_client):
        """Test searching for articles with a query."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_search_results = MagicMock()
        mock_search_results.ids = ["12345678", "23456789"]
        mock_client.efetch.return_value = "XML content"
        mock_client.esearch.return_value = mock_search_results
        
        # Create API and call method
        api = PubmedAPI(email="test@example.com")
        results = api.search_articles("BRCA1 cancer")
        
        # Verify method calls
        mock_entrez_client.assert_called_once_with(
            email="test@example.com", 
            api_key=None, 
            tool="pytest"
        )
        mock_client.esearch.assert_called_once_with(
            db="pubmed",
            term="BRCA1 cancer",
            retmax=20,
            sort="relevance"
        )
        
        # Check results
        assert results == ["12345678", "23456789"]
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_search_articles_with_params(self, mock_entrez_client):
        """Test searching for articles with custom parameters."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_search_results = MagicMock()
        mock_search_results.ids = ["12345678", "23456789", "34567890"]
        mock_client.esearch.return_value = mock_search_results
        
        # Create API and call method
        api = PubmedAPI()
        results = api.search_articles("BRAF mutation", retmax=100, sort="date")
        
        # Verify method calls
        mock_client.esearch.assert_called_once_with(
            db="pubmed",
            term="BRAF mutation",
            retmax=100,
            sort="date"
        )
        
        # Check results
        assert len(results) == 3
        assert results == ["12345678", "23456789", "34567890"]
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_search_articles_no_results(self, mock_entrez_client):
        """Test searching for articles with no results."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_search_results = MagicMock()
        mock_search_results.ids = []
        mock_client.esearch.return_value = mock_search_results
        
        # Create API and call method
        api = PubmedAPI()
        results = api.search_articles("nonexistenttermsxyz123")
        
        # Check results
        assert isinstance(results, list)
        assert len(results) == 0
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_search_articles_entrez_exception(self, mock_entrez_client):
        """Test error handling when Entrez API raises an exception."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.esearch.side_effect = Exception("API error")
        
        # Create API and call method
        api = PubmedAPI()
        
        # Expect exception to be handled and empty list returned
        results = api.search_articles("BRAF mutation")
        assert isinstance(results, list)
        assert len(results) == 0
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_article_by_pmid(self, mock_entrez_client):
        """Test fetching a single article by PMID."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.efetch.return_value = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                        <Abstract>
                            <AbstractText>This is a test abstract.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        # Create API and call method
        api = PubmedAPI()
        article = api.fetch_article_by_pmid("12345678")
        
        # Verify method calls
        mock_client.efetch.assert_called_once_with(
            db="pubmed",
            id="12345678",
            rettype="xml"
        )
        
        # Check results
        assert article is not None
        assert "12345678" in article
        assert "Test Article Title" in article
        assert "This is a test abstract" in article
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_article_by_pmid_not_found(self, mock_entrez_client):
        """Test fetching a non-existent article by PMID."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.efetch.return_value = "<PubmedArticleSet></PubmedArticleSet>"
        
        # Create API and call method
        api = PubmedAPI()
        article = api.fetch_article_by_pmid("99999999")
        
        # Verify method calls
        mock_client.efetch.assert_called_once()
        
        # Check results
        assert article is None
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_article_by_pmid_entrez_exception(self, mock_entrez_client):
        """Test error handling when Entrez API raises an exception during article fetch."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.efetch.side_effect = Exception("API error")
        
        # Create API and call method
        api = PubmedAPI()
        
        # Expect exception to be handled and None returned
        article = api.fetch_article_by_pmid("12345678")
        assert article is None
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_articles_by_pmids(self, mock_entrez_client):
        """Test fetching multiple articles by PMIDs."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.efetch.return_value = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Article 1</ArticleTitle>
                        <Abstract>
                            <AbstractText>This is abstract 1.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>23456789</PMID>
                    <Article>
                        <ArticleTitle>Test Article 2</ArticleTitle>
                        <Abstract>
                            <AbstractText>This is abstract 2.</AbstractText>
                        </Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        # Create API and call method
        api = PubmedAPI()
        articles = api.fetch_articles_by_pmids(["12345678", "23456789"])
        
        # Verify method calls
        mock_client.efetch.assert_called_once_with(
            db="pubmed",
            id=",".join(["12345678", "23456789"]),
            rettype="xml"
        )
        
        # Check results
        assert isinstance(articles, dict)
        assert len(articles) == 2
        assert "12345678" in articles
        assert "23456789" in articles
        assert "Test Article 1" in articles["12345678"]
        assert "Test Article 2" in articles["23456789"]
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_articles_by_pmids_empty_list(self, mock_entrez_client):
        """Test fetching articles with an empty PMID list."""
        # Create API and call method
        api = PubmedAPI()
        articles = api.fetch_articles_by_pmids([])
        
        # Verify no API calls were made
        mock_entrez_client.assert_not_called()
        
        # Check results
        assert isinstance(articles, dict)
        assert len(articles) == 0
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_fetch_articles_by_pmids_entrez_exception(self, mock_entrez_client):
        """Test error handling when Entrez API raises an exception during multiple article fetch."""
        # Set up mocks
        mock_client = MagicMock()
        mock_entrez_client.return_value = mock_client
        mock_client.efetch.side_effect = Exception("API error")
        
        # Create API and call method
        api = PubmedAPI()
        
        # Expect exception to be handled and empty dict returned
        articles = api.fetch_articles_by_pmids(["12345678", "23456789"])
        assert isinstance(articles, dict)
        assert len(articles) == 0
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_parse_article_xml_full(self, mock_entrez_client):
        """Test parsing a complete article XML."""
        # Create API instance
        api = PubmedAPI()
        
        # Test XML with all fields
        xml = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <DateCompleted>
                        <Year>2022</Year>
                        <Month>01</Month>
                        <Day>15</Day>
                    </DateCompleted>
                    <Article>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                        <Journal>
                            <Title>Journal of Testing</Title>
                            <JournalIssue>
                                <Volume>10</Volume>
                                <Issue>2</Issue>
                                <PubDate>
                                    <Year>2022</Year>
                                    <Month>Jan</Month>
                                </PubDate>
                            </JournalIssue>
                        </Journal>
                        <AuthorList>
                            <Author>
                                <LastName>Smith</LastName>
                                <ForeName>John</ForeName>
                                <Initials>J</Initials>
                            </Author>
                            <Author>
                                <LastName>Doe</LastName>
                                <ForeName>Jane</ForeName>
                                <Initials>J</Initials>
                            </Author>
                        </AuthorList>
                        <Abstract>
                            <AbstractText>This is a test abstract.</AbstractText>
                        </Abstract>
                    </Article>
                    <MeshHeadingList>
                        <MeshHeading>
                            <DescriptorName>DNA</DescriptorName>
                        </MeshHeading>
                        <MeshHeading>
                            <DescriptorName>RNA</DescriptorName>
                        </MeshHeading>
                    </MeshHeadingList>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        # Call the method
        result = api.parse_article_xml(xml)
        
        # Check results
        assert len(result) == 1
        article = result["12345678"]
        assert article["title"] == "Test Article Title"
        assert article["abstract"] == "This is a test abstract."
        assert article["journal"] == "Journal of Testing"
        assert article["publication_date"] == "2022 Jan"
        assert len(article["authors"]) == 2
        assert article["authors"][0] == "Smith J"
        assert article["authors"][1] == "Doe J"
        assert "DNA" in article["mesh_terms"]
        assert "RNA" in article["mesh_terms"]
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_parse_article_xml_minimal(self, mock_entrez_client):
        """Test parsing a minimal article XML."""
        # Create API instance
        api = PubmedAPI()
        
        # Test XML with minimal fields
        xml = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        # Call the method
        result = api.parse_article_xml(xml)
        
        # Check results
        assert len(result) == 1
        article = result["12345678"]
        assert article["title"] == "Test Article Title"
        assert article["abstract"] == ""
        assert article["journal"] == ""
        assert article["publication_date"] == ""
        assert article["authors"] == []
        assert article["mesh_terms"] == []
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_parse_article_xml_multiple(self, mock_entrez_client):
        """Test parsing XML with multiple articles."""
        # Create API instance
        api = PubmedAPI()
        
        # Test XML with multiple articles
        xml = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Article 1</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>23456789</PMID>
                    <Article>
                        <ArticleTitle>Article 2</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        # Call the method
        result = api.parse_article_xml(xml)
        
        # Check results
        assert len(result) == 2
        assert result["12345678"]["title"] == "Article 1"
        assert result["23456789"]["title"] == "Article 2"
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_parse_article_xml_invalid(self, mock_entrez_client):
        """Test parsing invalid XML."""
        # Create API instance
        api = PubmedAPI()
        
        # Test with invalid XML
        xml = "<InvalidXML>"
        
        # Call the method and expect empty result
        result = api.parse_article_xml(xml)
        assert isinstance(result, dict)
        assert len(result) == 0
    
    @patch('src.pubmed_flow.pubmed_api.EntrezClient')
    def test_parse_article_xml_empty(self, mock_entrez_client):
        """Test parsing empty XML."""
        # Create API instance
        api = PubmedAPI()
        
        # Test with empty XML
        xml = ""
        
        # Call the method and expect empty result
        result = api.parse_article_xml(xml)
        assert isinstance(result, dict)
        assert len(result) == 0
    
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.search_articles')
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.fetch_articles_by_pmids')
    def test_search_and_fetch(self, mock_fetch, mock_search):
        """Test combined search and fetch function."""
        # Set up mocks
        mock_search.return_value = ["12345678", "23456789"]
        mock_fetch.return_value = {
            "12345678": {"title": "Article 1", "abstract": "Abstract 1"},
            "23456789": {"title": "Article 2", "abstract": "Abstract 2"}
        }
        
        # Create API and call method
        api = PubmedAPI()
        results = api.search_and_fetch("BRCA1 cancer")
        
        # Verify method calls
        mock_search.assert_called_once_with("BRCA1 cancer", 20, "relevance")
        mock_fetch.assert_called_once_with(["12345678", "23456789"])
        
        # Check results
        assert len(results) == 2
        assert results["12345678"]["title"] == "Article 1"
        assert results["23456789"]["title"] == "Article 2"
    
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.search_articles')
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.fetch_articles_by_pmids')
    def test_search_and_fetch_no_results(self, mock_fetch, mock_search):
        """Test combined search and fetch with no search results."""
        # Set up mocks
        mock_search.return_value = []
        
        # Create API and call method
        api = PubmedAPI()
        results = api.search_and_fetch("nonexistenttermsxyz123")
        
        # Verify method calls
        mock_search.assert_called_once()
        mock_fetch.assert_not_called()  # Should not be called when search returns empty list
        
        # Check results
        assert isinstance(results, dict)
        assert len(results) == 0
    
    @patch('builtins.open', new_callable=MagicMock)
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.search_and_fetch')
    def test_search_and_save(self, mock_search_fetch, mock_open):
        """Test searching, fetching, and saving results to a file."""
        # Set up mocks
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_search_fetch.return_value = {
            "12345678": {"title": "Article 1", "abstract": "Abstract 1"},
            "23456789": {"title": "Article 2", "abstract": "Abstract 2"}
        }
        
        # Create API and call method
        api = PubmedAPI()
        api.search_and_save("BRCA1 cancer", "results.json")
        
        # Verify method calls
        mock_search_fetch.assert_called_once_with("BRCA1 cancer", 20, "relevance")
        mock_open.assert_called_once_with("results.json", "w", encoding="utf-8")
        
        # Check that the data was written correctly
        json_str = mock_file.write.call_args[0][0]
        data = json.loads(json_str)
        assert len(data) == 2
        assert "12345678" in data
        assert "23456789" in data
        assert data["12345678"]["title"] == "Article 1"
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    @patch('src.pubmed_flow.pubmed_api.PubmedAPI.search_and_fetch')
    def test_search_and_save_file_error(self, mock_search_fetch, mock_open):
        """Test error handling when saving to file fails."""
        # Set up mocks
        mock_search_fetch.return_value = {
            "12345678": {"title": "Article 1"}
        }
        
        # Create API and call method - should handle the exception gracefully
        api = PubmedAPI()
        
        # Expect an exception
        with pytest.raises(IOError):
            api.search_and_save("BRCA1", "invalid/path/results.json")
        
        # Verify method calls
        mock_search_fetch.assert_called_once()
        mock_open.assert_called_once_with("invalid/path/results.json", "w", encoding="utf-8") 