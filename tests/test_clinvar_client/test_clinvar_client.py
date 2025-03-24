"""
Tests for the ClinvarClient class from clinvar_client module.
"""
import os
import pytest
import json
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock, mock_open

from src.clinvar_client.clinvar_client import ClinVarClient


class TestClinvarClient:
    """
    Test suite for the ClinvarClient class.
    """
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        client = ClinVarClient()
        assert client.base_url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        assert client.email is None
        assert client.api_key is None
        assert client.tool == "pythonClinvarClient"
    
    def test_init_with_params(self):
        """Test initialization with custom parameters."""
        client = ClinVarClient(
            email="test@example.com",
            api_key="test_api_key",
            tool="custom_tool"
        )
        assert client.base_url == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        assert client.email == "test@example.com"
        assert client.api_key == "test_api_key"
        assert client.tool == "custom_tool"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_build_request_url(self, mock_get):
        """Test building a request URL."""
        mock_get.return_value = MagicMock(status_code=200)
        client = ClinVarClient(email="test@example.com", api_key="test_key")
        
        url = client._build_request_url("esearch", {"db": "clinvar", "term": "BRCA1"})
        
        assert "esearch.fcgi" in url
        assert "db=clinvar" in url
        assert "term=BRCA1" in url
        assert "email=test%40example.com" in url
        assert "api_key=test_key" in url
        assert "tool=pythonClinvarClient" in url
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_make_request(self, mock_get):
        """Test making a request to the ClinVar API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<Response>OK</Response>"
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        response = client._make_request("esearch", {"db": "clinvar", "term": "BRCA1"})
        
        mock_get.assert_called_once()
        assert response.status_code == 200
        assert response.text == "<Response>OK</Response>"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_make_request_error(self, mock_get):
        """Test handling error in request to the ClinVar API."""
        mock_get.side_effect = Exception("Connection error")
        
        client = ClinVarClient()
        with pytest.raises(Exception) as excinfo:
            client._make_request("esearch", {"db": "clinvar", "term": "BRCA1"})
        
        assert "Connection error" in str(excinfo.value)
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_search_clinvar(self, mock_get):
        """Test searching ClinVar database."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>10</Count>
            <IdList>
                <Id>1234</Id>
                <Id>5678</Id>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        result = client.search_clinvar("BRCA1 c.123A>G")
        
        assert result is not None
        assert isinstance(result, ET.Element)
        assert result.tag == "eSearchResult"
        id_list = result.find("IdList")
        assert id_list is not None
        ids = id_list.findall("Id")
        assert len(ids) == 2
        assert ids[0].text == "1234"
        assert ids[1].text == "5678"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_search_clinvar_no_results(self, mock_get):
        """Test searching ClinVar with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>0</Count>
            <IdList>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        result = client.search_clinvar("nonexistent variant")
        
        assert result is not None
        assert isinstance(result, ET.Element)
        assert result.tag == "eSearchResult"
        assert result.find("Count").text == "0"
        id_list = result.find("IdList")
        assert id_list is not None
        ids = id_list.findall("Id")
        assert len(ids) == 0
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_search_clinvar_error(self, mock_get):
        """Test handling error in ClinVar search."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Error"
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        with pytest.raises(Exception) as excinfo:
            client.search_clinvar("BRCA1 c.123A>G")
        
        assert "Error retrieving data from ClinVar" in str(excinfo.value)
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_clinvar_ids_by_gene(self, mock_get):
        """Test getting ClinVar IDs by gene name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>10</Count>
            <IdList>
                <Id>1234</Id>
                <Id>5678</Id>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        ids = client.get_clinvar_ids_by_gene("BRCA1")
        
        assert ids is not None
        assert isinstance(ids, list)
        assert len(ids) == 2
        assert "1234" in ids
        assert "5678" in ids
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_clinvar_ids_by_rsid(self, mock_get):
        """Test getting ClinVar IDs by rs ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        ids = client.get_clinvar_ids_by_rsid("rs123456")
        
        assert ids is not None
        assert isinstance(ids, list)
        assert len(ids) == 1
        assert "1234" in ids
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_clinvar_ids_by_variant(self, mock_get):
        """Test getting ClinVar IDs by variant notation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        ids = client.get_clinvar_ids_by_variant("c.123A>G")
        
        assert ids is not None
        assert isinstance(ids, list)
        assert len(ids) == 1
        assert "1234" in ids
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_fetch_clinvar_record(self, mock_get):
        """Test fetching a ClinVar record by ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eFetchResult>
            <ClinVarResult>
                <VariationReport>
                    <Allele>
                        <Name>c.123A>G</Name>
                    </Allele>
                    <ClinicalSignificance>
                        <Description>Pathogenic</Description>
                    </ClinicalSignificance>
                </VariationReport>
            </ClinVarResult>
        </eFetchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        record = client.fetch_clinvar_record("1234")
        
        assert record is not None
        assert isinstance(record, ET.Element)
        assert record.tag == "eFetchResult"
        result = record.find(".//ClinVarResult")
        assert result is not None
        variation = result.find(".//VariationReport")
        assert variation is not None
        allele = variation.find(".//Allele/Name")
        assert allele is not None
        assert allele.text == "c.123A>G"
        significance = variation.find(".//ClinicalSignificance/Description")
        assert significance is not None
        assert significance.text == "Pathogenic"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_fetch_clinvar_record_not_found(self, mock_get):
        """Test fetching a non-existent ClinVar record."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eFetchResult>
            <ClinVarResultList>
            </ClinVarResultList>
        </eFetchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        record = client.fetch_clinvar_record("9999")
        
        assert record is not None
        assert isinstance(record, ET.Element)
        results = record.find(".//ClinVarResultList")
        assert results is not None
        assert len(results.findall("*")) == 0
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_fetch_clinvar_records(self, mock_get):
        """Test fetching multiple ClinVar records by IDs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eFetchResult>
            <ClinVarResultList>
                <ClinVarResult>
                    <VariationReport>
                        <Allele>
                            <Name>c.123A>G</Name>
                        </Allele>
                    </VariationReport>
                </ClinVarResult>
                <ClinVarResult>
                    <VariationReport>
                        <Allele>
                            <Name>p.V600E</Name>
                        </Allele>
                    </VariationReport>
                </ClinVarResult>
            </ClinVarResultList>
        </eFetchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        records = client.fetch_clinvar_records(["1234", "5678"])
        
        assert records is not None
        assert isinstance(records, ET.Element)
        results = records.find(".//ClinVarResultList")
        assert results is not None
        variations = results.findall(".//ClinVarResult")
        assert len(variations) == 2
        allele1 = variations[0].find(".//Allele/Name")
        assert allele1.text == "c.123A>G"
        allele2 = variations[1].find(".//Allele/Name")
        assert allele2.text == "p.V600E"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_parse_clinical_significance(self, mock_get):
        """Test parsing clinical significance from a ClinVar record."""
        mock_xml = """
        <ClinVarResult>
            <VariationReport>
                <ClinicalSignificance>
                    <ReviewStatus>criteria provided, multiple submitters, no conflicts</ReviewStatus>
                    <Description>Pathogenic</Description>
                    <DateLastEvaluated>2019-01-01</DateLastEvaluated>
                </ClinicalSignificance>
            </VariationReport>
        </ClinVarResult>
        """
        record = ET.fromstring(mock_xml)
        
        client = ClinVarClient()
        significance = client.parse_clinical_significance(record)
        
        assert significance is not None
        assert isinstance(significance, dict)
        assert significance["classification"] == "Pathogenic"
        assert significance["review_status"] == "criteria provided, multiple submitters, no conflicts"
        assert significance["last_evaluated"] == "2019-01-01"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_parse_clinical_significance_missing_data(self, mock_get):
        """Test parsing clinical significance with missing data."""
        mock_xml = """
        <ClinVarResult>
            <VariationReport>
                <ClinicalSignificance>
                    <Description>Uncertain significance</Description>
                </ClinicalSignificance>
            </VariationReport>
        </ClinVarResult>
        """
        record = ET.fromstring(mock_xml)
        
        client = ClinVarClient()
        significance = client.parse_clinical_significance(record)
        
        assert significance is not None
        assert isinstance(significance, dict)
        assert significance["classification"] == "Uncertain significance"
        assert significance["review_status"] is None
        assert significance["last_evaluated"] is None
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_parse_variant_details(self, mock_get):
        """Test parsing variant details from a ClinVar record."""
        mock_xml = """
        <ClinVarResult>
            <VariationReport>
                <Allele>
                    <Name>c.123A>G</Name>
                    <VariantType>single nucleotide variant</VariantType>
                </Allele>
                <Gene>
                    <Symbol>BRCA1</Symbol>
                    <FullName>BRCA1 DNA repair associated</FullName>
                </Gene>
                <HGVS>
                    <Expression>NM_007294.3:c.123A>G</Expression>
                    <Expression>NP_009225.1:p.Lys41Glu</Expression>
                </HGVS>
            </VariationReport>
        </ClinVarResult>
        """
        record = ET.fromstring(mock_xml)
        
        client = ClinVarClient()
        details = client.parse_variant_details(record)
        
        assert details is not None
        assert isinstance(details, dict)
        assert details["name"] == "c.123A>G"
        assert details["type"] == "single nucleotide variant"
        assert details["gene_symbol"] == "BRCA1"
        assert details["gene_name"] == "BRCA1 DNA repair associated"
        assert "NM_007294.3:c.123A>G" in details["hgvs"]
        assert "NP_009225.1:p.Lys41Glu" in details["hgvs"]
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_parse_variant_details_missing_data(self, mock_get):
        """Test parsing variant details with missing data."""
        mock_xml = """
        <ClinVarResult>
            <VariationReport>
                <Allele>
                    <Name>c.123A>G</Name>
                </Allele>
            </VariationReport>
        </ClinVarResult>
        """
        record = ET.fromstring(mock_xml)
        
        client = ClinVarClient()
        details = client.parse_variant_details(record)
        
        assert details is not None
        assert isinstance(details, dict)
        assert details["name"] == "c.123A>G"
        assert details["type"] is None
        assert details["gene_symbol"] is None
        assert details["gene_name"] is None
        assert details["hgvs"] == []
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_variant_clinical_significance(self, mock_get):
        """Test getting clinical significance for a variant."""
        # First request (search)
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        
        # Second request (fetch)
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.text = """
        <eFetchResult>
            <ClinVarResult>
                <VariationReport>
                    <Allele>
                        <Name>c.123A>G</Name>
                    </Allele>
                    <ClinicalSignificance>
                        <ReviewStatus>criteria provided, single submitter</ReviewStatus>
                        <Description>Pathogenic</Description>
                    </ClinicalSignificance>
                </VariationReport>
            </ClinVarResult>
        </eFetchResult>
        """
        
        mock_get.side_effect = [first_response, second_response]
        
        client = ClinVarClient()
        significance = client.get_variant_clinical_significance("c.123A>G")
        
        assert significance is not None
        assert isinstance(significance, dict)
        assert significance["classification"] == "Pathogenic"
        assert significance["review_status"] == "criteria provided, single submitter"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_variant_clinical_significance_not_found(self, mock_get):
        """Test getting clinical significance for a non-existent variant."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>0</Count>
            <IdList>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        significance = client.get_variant_clinical_significance("nonexistent")
        
        assert significance is not None
        assert isinstance(significance, dict)
        assert significance["classification"] is None
        assert significance["review_status"] is None
        assert significance["message"] == "Variant not found in ClinVar"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_gene_variants(self, mock_get):
        """Test getting variants for a gene."""
        # First request (search)
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.text = """
        <eSearchResult>
            <Count>2</Count>
            <IdList>
                <Id>1234</Id>
                <Id>5678</Id>
            </IdList>
        </eSearchResult>
        """
        
        # Second request (fetch)
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.text = """
        <eFetchResult>
            <ClinVarResultList>
                <ClinVarResult>
                    <VariationReport>
                        <Allele>
                            <Name>c.123A>G</Name>
                        </Allele>
                        <ClinicalSignificance>
                            <Description>Pathogenic</Description>
                        </ClinicalSignificance>
                    </VariationReport>
                </ClinVarResult>
                <ClinVarResult>
                    <VariationReport>
                        <Allele>
                            <Name>c.456G>T</Name>
                        </Allele>
                        <ClinicalSignificance>
                            <Description>Benign</Description>
                        </ClinicalSignificance>
                    </VariationReport>
                </ClinVarResult>
            </ClinVarResultList>
        </eFetchResult>
        """
        
        mock_get.side_effect = [first_response, second_response]
        
        client = ClinVarClient()
        variants = client.get_gene_variants("BRCA1")
        
        assert variants is not None
        assert isinstance(variants, list)
        assert len(variants) == 2
        
        # Check first variant
        assert variants[0]["name"] == "c.123A>G"
        assert variants[0]["significance"]["classification"] == "Pathogenic"
        
        # Check second variant
        assert variants[1]["name"] == "c.456G>T"
        assert variants[1]["significance"]["classification"] == "Benign"
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_gene_variants_not_found(self, mock_get):
        """Test getting variants for a non-existent gene."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <eSearchResult>
            <Count>0</Count>
            <IdList>
            </IdList>
        </eSearchResult>
        """
        mock_get.return_value = mock_response
        
        client = ClinVarClient()
        variants = client.get_gene_variants("NONEXISTENT")
        
        assert variants is not None
        assert isinstance(variants, list)
        assert len(variants) == 0
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_get_variant_by_rsid(self, mock_get):
        """Test getting a variant by rs ID."""
        # First request (search)
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        
        # Second request (fetch)
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.text = """
        <eFetchResult>
            <ClinVarResult>
                <VariationReport>
                    <Allele>
                        <Name>c.123A>G</Name>
                    </Allele>
                    <Gene>
                        <Symbol>BRCA1</Symbol>
                    </Gene>
                    <ClinicalSignificance>
                        <Description>Pathogenic</Description>
                    </ClinicalSignificance>
                </VariationReport>
            </ClinVarResult>
        </eFetchResult>
        """
        
        mock_get.side_effect = [first_response, second_response]
        
        client = ClinVarClient()
        variant = client.get_variant_by_rsid("rs123456")
        
        assert variant is not None
        assert isinstance(variant, dict)
        assert variant["name"] == "c.123A>G"
        assert variant["gene_symbol"] == "BRCA1"
        assert variant["significance"]["classification"] == "Pathogenic"
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_save_variant_data(self, mock_get, mock_file):
        """Test saving variant data to a file."""
        variant_data = {
            "name": "c.123A>G",
            "gene_symbol": "BRCA1",
            "significance": {
                "classification": "Pathogenic",
                "review_status": "criteria provided, single submitter"
            }
        }
        
        client = ClinVarClient()
        client.save_variant_data(variant_data, "variant.json")
        
        mock_file.assert_called_once_with("variant.json", "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Verify JSON was written correctly
        json_str = mock_handle.write.call_args[0][0]
        saved_variant = json.loads(json_str)
        assert saved_variant["name"] == "c.123A>G"
        assert saved_variant["gene_symbol"] == "BRCA1"
        assert saved_variant["significance"]["classification"] == "Pathogenic"
    
    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_variant_data_file_error(self, mock_file):
        """Test handling file error when saving variant data."""
        variant_data = {"name": "c.123A>G"}
        
        client = ClinVarClient()
        with pytest.raises(IOError):
            client.save_variant_data(variant_data, "invalid/path.json")
    
    # Integration tests
    
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_integration_search_and_fetch(self, mock_get):
        """Integration test for searching and fetching a variant."""
        # First request (search)
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        
        # Second request (fetch)
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.text = """
        <eFetchResult>
            <ClinVarResult>
                <VariationReport>
                    <Allele>
                        <Name>c.123A>G</Name>
                        <VariantType>single nucleotide variant</VariantType>
                    </Allele>
                    <Gene>
                        <Symbol>BRCA1</Symbol>
                    </Gene>
                    <ClinicalSignificance>
                        <Description>Pathogenic</Description>
                        <ReviewStatus>criteria provided, single submitter</ReviewStatus>
                    </ClinicalSignificance>
                </VariationReport>
            </ClinVarResult>
        </eFetchResult>
        """
        
        mock_get.side_effect = [first_response, second_response]
        
        client = ClinVarClient()
        
        # Find the clinvar IDs
        ids = client.get_clinvar_ids_by_variant("c.123A>G")
        assert len(ids) == 1
        assert ids[0] == "1234"
        
        # Fetch the record
        record = client.fetch_clinvar_record(ids[0])
        assert record is not None
        
        # Parse the details
        details = client.parse_variant_details(record.find(".//ClinVarResult"))
        assert details["name"] == "c.123A>G"
        assert details["gene_symbol"] == "BRCA1"
        
        # Parse clinical significance
        significance = client.parse_clinical_significance(record.find(".//ClinVarResult"))
        assert significance["classification"] == "Pathogenic"
        assert significance["review_status"] == "criteria provided, single submitter"
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.clinvar_client.clinvar_client.requests.get')
    def test_integration_full_pipeline(self, mock_get, mock_file, temp_dir):
        """Integration test for running the full pipeline."""
        # Mock responses for search and fetch
        search_response = MagicMock()
        search_response.status_code = 200
        search_response.text = """
        <eSearchResult>
            <Count>1</Count>
            <IdList>
                <Id>1234</Id>
            </IdList>
        </eSearchResult>
        """
        
        fetch_response = MagicMock()
        fetch_response.status_code = 200
        fetch_response.text = """
        <eFetchResult>
            <ClinVarResult>
                <VariationReport>
                    <Allele>
                        <Name>c.123A>G</Name>
                        <VariantType>single nucleotide variant</VariantType>
                    </Allele>
                    <Gene>
                        <Symbol>BRCA1</Symbol>
                    </Gene>
                    <ClinicalSignificance>
                        <Description>Pathogenic</Description>
                        <ReviewStatus>criteria provided, multiple submitters, no conflicts</ReviewStatus>
                    </ClinicalSignificance>
                </VariationReport>
            </ClinVarResult>
        </eFetchResult>
        """
        
        mock_get.side_effect = [search_response, fetch_response]
        
        client = ClinVarClient()
        output_file = os.path.join(temp_dir, "variant_data.json")
        
        # Get variant information
        variant_info = client.get_variant_clinical_significance("c.123A>G")
        assert variant_info["classification"] == "Pathogenic"
        
        # Save to file
        client.save_variant_data({"variant": "c.123A>G", "significance": variant_info}, output_file)
        
        # Verify file was written
        mock_file.assert_called_once_with(output_file, "w", encoding="utf-8")
        mock_handle = mock_file()
        
        # Check saved content
        json_str = mock_handle.write.call_args[0][0]
        saved_data = json.loads(json_str)
        assert saved_data["variant"] == "c.123A>G"
        assert saved_data["significance"]["classification"] == "Pathogenic" 