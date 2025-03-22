"""
Tests for the PubtatorClient class from pubtator_client module.
"""
import os
import pytest
import json
import requests
from unittest.mock import patch, MagicMock, mock_open

from src.pubtator_client.pubtator_client import PubtatorClient


class TestPubtatorClient:
    """
    Test suite for the PubtatorClient class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        client = PubtatorClient()
        assert client.base_url == "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
        assert client.timeout == 30
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        client = PubtatorClient(base_url="https://custom-pubtator.example.com", timeout=60)
        assert client.base_url == "https://custom-pubtator.example.com"
        assert client.timeout == 60
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_annotations_by_pmid(self, mock_get):
        """Test getting annotations for a specific PMID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "This study examines BRCA1 mutations.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        result = client.get_annotations_by_pmid("12345678")
        
        mock_get.assert_called_once_with(
            "https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson",
            params={"pmids": "12345678"},
            timeout=30
        )
        
        assert result is not None
        assert result["pmid"] == "12345678"
        assert "passages" in result
        assert len(result["passages"][0]["annotations"]) == 1
        assert result["passages"][0]["annotations"][0]["text"] == "BRCA1"
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_annotations_by_pmid_error(self, mock_get):
        """Test handling error when getting annotations for a PMID."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.side_effect = ValueError("No JSON data")
        mock_response.text = "Not found"
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        with pytest.raises(Exception) as excinfo:
            client.get_annotations_by_pmid("99999999")
        
        assert "Error retrieving annotations" in str(excinfo.value)
        assert "404" in str(excinfo.value)
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_annotations_by_pmid_connection_error(self, mock_get):
        """Test handling connection error when getting annotations."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        client = PubtatorClient()
        with pytest.raises(Exception) as excinfo:
            client.get_annotations_by_pmid("12345678")
        
        assert "Connection error" in str(excinfo.value)
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_annotations_for_multiple_pmids(self, mock_get):
        """Test getting annotations for multiple PMIDs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "pmid": "12345678",
                "passages": [
                    {
                        "text": "This study examines BRCA1 mutations.",
                        "annotations": [
                            {
                                "id": "672",
                                "infons": {"type": "Gene"},
                                "text": "BRCA1"
                            }
                        ]
                    }
                ]
            },
            {
                "pmid": "23456789",
                "passages": [
                    {
                        "text": "We found a p.V600E mutation in BRAF.",
                        "annotations": [
                            {
                                "id": "673",
                                "infons": {"type": "Gene"},
                                "text": "BRAF"
                            },
                            {
                                "id": "674",
                                "infons": {"type": "Mutation"},
                                "text": "p.V600E"
                            }
                        ]
                    }
                ]
            }
        ]
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        results = client.get_annotations_for_multiple_pmids(["12345678", "23456789"])
        
        mock_get.assert_called_once_with(
            "https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson",
            params={"pmids": "12345678,23456789"},
            timeout=30
        )
        
        assert results is not None
        assert len(results) == 2
        assert results[0]["pmid"] == "12345678"
        assert results[1]["pmid"] == "23456789"
        assert len(results[0]["passages"][0]["annotations"]) == 1
        assert len(results[1]["passages"][0]["annotations"]) == 2
        assert results[1]["passages"][0]["annotations"][1]["text"] == "p.V600E"
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_annotations_for_multiple_pmids_empty_list(self, mock_get):
        """Test getting annotations for an empty list of PMIDs."""
        client = PubtatorClient()
        results = client.get_annotations_for_multiple_pmids([])
        
        mock_get.assert_not_called()
        assert results == []
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_extract_mutations_from_annotations(self, mock_get):
        """Test extracting mutations from annotations."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We found c.123A>G and p.V600E mutations.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Mutation"},
                            "text": "c.123A>G"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Mutation"},
                            "text": "p.V600E"
                        },
                        {
                            "id": "674",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        mutations = client.extract_mutations_from_annotations(annotations)
        
        assert mutations is not None
        assert len(mutations) == 2
        assert "c.123A>G" in mutations
        assert "p.V600E" in mutations
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_extract_mutations_no_mutations(self, mock_get):
        """Test extracting mutations when no mutations are present."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "This study examines BRCA1 gene.",
                    "annotations": [
                        {
                            "id": "674",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        mutations = client.extract_mutations_from_annotations(annotations)
        
        assert mutations is not None
        assert len(mutations) == 0
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_extract_genes_from_annotations(self, mock_get):
        """Test extracting genes from annotations."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We examined BRCA1 and BRAF genes.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Gene"},
                            "text": "BRAF"
                        },
                        {
                            "id": "674",
                            "infons": {"type": "Mutation"},
                            "text": "p.V600E"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        genes = client.extract_genes_from_annotations(annotations)
        
        assert genes is not None
        assert len(genes) == 2
        assert "BRCA1" in genes
        assert "BRAF" in genes
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_extract_genes_no_genes(self, mock_get):
        """Test extracting genes when no genes are present."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We found c.123A>G mutation.",
                    "annotations": [
                        {
                            "id": "674",
                            "infons": {"type": "Mutation"},
                            "text": "c.123A>G"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        genes = client.extract_genes_from_annotations(annotations)
        
        assert genes is not None
        assert len(genes) == 0
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_extract_diseases_from_annotations(self, mock_get):
        """Test extracting diseases from annotations."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We studied breast cancer and melanoma patients.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Disease"},
                            "text": "breast cancer"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Disease"},
                            "text": "melanoma"
                        },
                        {
                            "id": "674",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        diseases = client.extract_diseases_from_annotations(annotations)
        
        assert diseases is not None
        assert len(diseases) == 2
        assert "breast cancer" in diseases
        assert "melanoma" in diseases
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_mutations_for_pmid(self, mock_get):
        """Test getting mutations for a specific PMID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We found c.123A>G and p.V600E mutations.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Mutation"},
                            "text": "c.123A>G"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Mutation"},
                            "text": "p.V600E"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        mutations = client.get_mutations_for_pmid("12345678")
        
        assert mutations is not None
        assert len(mutations) == 2
        assert "c.123A>G" in mutations
        assert "p.V600E" in mutations
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_genes_for_pmid(self, mock_get):
        """Test getting genes for a specific PMID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We examined BRCA1 and BRAF genes.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Gene"},
                            "text": "BRAF"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        genes = client.get_genes_for_pmid("12345678")
        
        assert genes is not None
        assert len(genes) == 2
        assert "BRCA1" in genes
        assert "BRAF" in genes
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_diseases_for_pmid(self, mock_get):
        """Test getting diseases for a specific PMID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We studied breast cancer and melanoma patients.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Disease"},
                            "text": "breast cancer"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Disease"},
                            "text": "melanoma"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        diseases = client.get_diseases_for_pmid("12345678")
        
        assert diseases is not None
        assert len(diseases) == 2
        assert "breast cancer" in diseases
        assert "melanoma" in diseases
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_get_mutations_for_multiple_pmids(self, mock_get):
        """Test getting mutations for multiple PMIDs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "pmid": "12345678",
                "passages": [
                    {
                        "annotations": [
                            {
                                "id": "672",
                                "infons": {"type": "Mutation"},
                                "text": "c.123A>G"
                            }
                        ]
                    }
                ]
            },
            {
                "pmid": "23456789",
                "passages": [
                    {
                        "annotations": [
                            {
                                "id": "673",
                                "infons": {"type": "Mutation"},
                                "text": "p.V600E"
                            }
                        ]
                    }
                ]
            }
        ]
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        mutations_by_pmid = client.get_mutations_for_multiple_pmids(["12345678", "23456789"])
        
        assert mutations_by_pmid is not None
        assert isinstance(mutations_by_pmid, dict)
        assert len(mutations_by_pmid) == 2
        assert "12345678" in mutations_by_pmid
        assert "23456789" in mutations_by_pmid
        assert "c.123A>G" in mutations_by_pmid["12345678"]
        assert "p.V600E" in mutations_by_pmid["23456789"]
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_save_annotations(self, mock_get, mock_file):
        """Test saving annotations to a file."""
        annotations = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "This is a test passage.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        client.save_annotations(annotations, "annotations.json")
        
        mock_file.assert_called_once_with("annotations.json", "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Verify JSON was written correctly
        json_str = mock_handle.write.call_args[0][0]
        saved_annotations = json.loads(json_str)
        assert saved_annotations["pmid"] == "12345678"
        assert len(saved_annotations["passages"][0]["annotations"]) == 1
        assert saved_annotations["passages"][0]["annotations"][0]["text"] == "BRCA1"
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_annotations_file_error(self, mock_file):
        """Test handling file error when saving annotations."""
        annotations = {"pmid": "12345678"}
        
        client = PubtatorClient()
        with pytest.raises(IOError):
            client.save_annotations(annotations, "invalid/path.json")
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_merge_annotations(self, mock_get):
        """Test merging annotations from multiple sources."""
        annotation1 = {
            "pmid": "12345678",
            "passages": [
                {
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        }
                    ]
                }
            ]
        }
        
        annotation2 = {
            "pmid": "12345678",
            "passages": [
                {
                    "annotations": [
                        {
                            "id": "673",
                            "infons": {"type": "Mutation"},
                            "text": "c.123A>G"
                        }
                    ]
                }
            ]
        }
        
        client = PubtatorClient()
        merged = client.merge_annotations([annotation1, annotation2])
        
        assert merged is not None
        assert merged["pmid"] == "12345678"
        assert len(merged["passages"]) == 2
        annotations = []
        for passage in merged["passages"]:
            annotations.extend(passage["annotations"])
        
        assert len(annotations) == 2
        annotation_texts = [a["text"] for a in annotations]
        assert "BRCA1" in annotation_texts
        assert "c.123A>G" in annotation_texts
    
    # Integration tests
    
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_integration_get_and_extract(self, mock_get):
        """Integration test for getting and extracting annotations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pmid": "12345678",
            "passages": [
                {
                    "text": "We found c.123A>G mutation in BRCA1 related to breast cancer.",
                    "annotations": [
                        {
                            "id": "672",
                            "infons": {"type": "Mutation"},
                            "text": "c.123A>G"
                        },
                        {
                            "id": "673",
                            "infons": {"type": "Gene"},
                            "text": "BRCA1"
                        },
                        {
                            "id": "674",
                            "infons": {"type": "Disease"},
                            "text": "breast cancer"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        
        # Get annotations
        annotations = client.get_annotations_by_pmid("12345678")
        assert annotations is not None
        
        # Extract mutations
        mutations = client.extract_mutations_from_annotations(annotations)
        assert len(mutations) == 1
        assert "c.123A>G" in mutations
        
        # Extract genes
        genes = client.extract_genes_from_annotations(annotations)
        assert len(genes) == 1
        assert "BRCA1" in genes
        
        # Extract diseases
        diseases = client.extract_diseases_from_annotations(annotations)
        assert len(diseases) == 1
        assert "breast cancer" in diseases
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.pubtator_client.pubtator_client.requests.get')
    def test_integration_full_pipeline(self, mock_get, mock_file, temp_dir):
        """Integration test for running the full annotation pipeline."""
        # Mock response for multiple PMIDs
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "pmid": "12345678",
                "passages": [
                    {
                        "text": "We found c.123A>G mutation in BRCA1.",
                        "annotations": [
                            {
                                "id": "672",
                                "infons": {"type": "Mutation"},
                                "text": "c.123A>G"
                            },
                            {
                                "id": "673",
                                "infons": {"type": "Gene"},
                                "text": "BRCA1"
                            }
                        ]
                    }
                ]
            },
            {
                "pmid": "23456789",
                "passages": [
                    {
                        "text": "p.V600E mutation in BRAF is associated with melanoma.",
                        "annotations": [
                            {
                                "id": "674",
                                "infons": {"type": "Mutation"},
                                "text": "p.V600E"
                            },
                            {
                                "id": "675",
                                "infons": {"type": "Gene"},
                                "text": "BRAF"
                            },
                            {
                                "id": "676",
                                "infons": {"type": "Disease"},
                                "text": "melanoma"
                            }
                        ]
                    }
                ]
            }
        ]
        mock_get.return_value = mock_response
        
        client = PubtatorClient()
        pmids = ["12345678", "23456789"]
        output_file = os.path.join(temp_dir, "annotations.json")
        
        # Get annotations for multiple PMIDs
        annotations = client.get_annotations_for_multiple_pmids(pmids)
        assert len(annotations) == 2
        
        # Extract mutations for all PMIDs
        mutations_by_pmid = client.get_mutations_for_multiple_pmids(pmids)
        assert len(mutations_by_pmid) == 2
        assert "c.123A>G" in mutations_by_pmid["12345678"]
        assert "p.V600E" in mutations_by_pmid["23456789"]
        
        # Save the first annotation to file
        client.save_annotations(annotations[0], output_file)
        
        # Verify file was written
        mock_file.assert_called_once_with(output_file, "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Check saved content
        json_str = mock_handle.write.call_args[0][0]
        saved_data = json.loads(json_str)
        assert saved_data["pmid"] == "12345678"
        assert len(saved_data["passages"][0]["annotations"]) == 2 