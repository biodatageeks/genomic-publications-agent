"""
Testy jednostkowe dla LlmContextAnalyzer.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

import bioc
from bioc import BioCDocument, BioCPassage, BioCAnnotation, BioCLocation
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from src.pubtator_client.exceptions import PubTatorError
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer


# Funkcje pomocnicze do tworzenia atrap obiektów BioCDocument
def create_mock_annotation(text, anno_type, identifier="", offset=0, length=0):
    """Tworzy atrapy adnotacji BioCAnnotation."""
    anno = Mock(spec=BioCAnnotation)
    anno.text = text
    anno.infons = {"type": anno_type, "identifier": identifier}
    
    location = Mock(spec=BioCLocation)
    location.offset = offset
    location.length = length
    anno.locations = [location]
    
    return anno


def create_mock_passage(text, annotations):
    """Tworzy atrapy pasażu BioCPassage."""
    passage = Mock(spec=BioCPassage)
    passage.text = text
    passage.annotations = annotations
    return passage


def create_mock_document(pmid, passages):
    """Tworzy atrapy dokumentu BioCDocument."""
    document = Mock(spec=BioCDocument)
    document.id = pmid
    document.passages = passages
    return document


# Atrapa odpowiedzi LLM
MOCK_LLM_RESPONSE = {
    "relationships": [
        {
            "entity_type": "gene",
            "entity_text": "BRAF",
            "entity_id": "673",
            "has_relationship": True,
            "explanation": "Wariant V600E jest powszechnie występującą mutacją w genie BRAF."
        },
        {
            "entity_type": "disease",
            "entity_text": "melanoma",
            "entity_id": "D008545",
            "has_relationship": True,
            "explanation": "Mutacja V600E w genie BRAF jest często powiązana z czerniakiem (melanoma)."
        }
    ]
}


# Fixtures
@pytest.fixture
def llm_analyzer():
    """Tworzy analizator z atrapą klienta pubtator i atrapą LLM."""
    mock_pubtator_client = Mock()
    
    # Tworzenie atrapy LlmManager i modelu LLM
    with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager') as mock_llm_manager_class:
        mock_llm = Mock()
        mock_llm.invoke.return_value = AIMessage(content=json.dumps(MOCK_LLM_RESPONSE))
        
        mock_llm_manager = mock_llm_manager_class.return_value
        mock_llm_manager.get_llm.return_value = mock_llm
        
        analyzer = LlmContextAnalyzer(pubtator_client=mock_pubtator_client)
        return analyzer


# Testy
def test_initialization():
    """Test poprawności inicjalizacji analizatora."""
    # Test z własnym klientem
    mock_pubtator_client = Mock()
    
    with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager') as mock_llm_manager_class:
        mock_llm = Mock()
        mock_llm_manager = mock_llm_manager_class.return_value
        mock_llm_manager.get_llm.return_value = mock_llm
        
        analyzer = LlmContextAnalyzer(mock_pubtator_client)
        assert analyzer.pubtator_client == mock_pubtator_client
        mock_llm_manager_class.assert_called_once_with('together', 'meta-llama/Meta-Llama-3.1-8B-Instruct')


def test_analyze_passage(llm_analyzer):
    """Test analizy pasażu z użyciem LLM."""
    pmid = "12345678"
    
    # Tworzenie atrapy pasażu z adnotacjami
    gene_anno = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
    variant_anno = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
    disease_anno = create_mock_annotation("melanoma", "Disease", "D008545", 24, 8)
    
    passage = create_mock_passage(
        "BRAF with V600E mutation in melanoma.", 
        [gene_anno, variant_anno, disease_anno]
    )
    
    # Test analizy
    result = llm_analyzer._analyze_passage(pmid, passage)
    
    # Weryfikacja wyniku
    assert len(result) == 1
    assert result[0]["pmid"] == pmid
    assert result[0]["variant_text"] == "V600E"
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRAF"
    assert len(result[0]["diseases"]) == 1
    assert result[0]["diseases"][0]["text"] == "melanoma"


def test_analyze_passage_no_variants(llm_analyzer):
    """Test analizy pasażu, gdy nie ma wariantów."""
    # Tworzenie atrapy pasażu bez wariantów
    gene_anno = create_mock_annotation("BRCA1", "Gene")
    disease_anno = create_mock_annotation("Cancer", "Disease")
    
    passage = create_mock_passage(
        "BRCA1 is associated with cancer.", 
        [gene_anno, disease_anno]
    )
    
    # Test analizy
    result = llm_analyzer._analyze_passage("12345678", passage)
    
    # Weryfikacja wyniku - powinna być pusta lista
    assert result == []


def test_analyze_publication(llm_analyzer):
    """Test analizy kompletnej publikacji."""
    pmid = "12345678"
    
    # Pasaż 1 z wariantem, genem i chorobą
    gene_anno1 = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
    variant_anno1 = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
    disease_anno1 = create_mock_annotation("melanoma", "Disease", "D008545", 24, 8)
    passage1 = create_mock_passage(
        "BRAF with V600E mutation in melanoma.", 
        [gene_anno1, variant_anno1, disease_anno1]
    )
    
    # Pasaż 2 bez wariantów
    gene_anno2 = create_mock_annotation("p53", "Gene", "7157", 0, 3)
    passage2 = create_mock_passage(
        "p53 is a tumor suppressor gene", 
        [gene_anno2]
    )
    
    # Tworzenie dokumentu
    document = create_mock_document(pmid, [passage1, passage2])
    
    # Test analizy
    result = llm_analyzer._analyze_publication(document)
    
    # Weryfikacja wyniku
    assert len(result) == 1  # Tylko jeden pasaż ma warianty
    assert result[0]["pmid"] == pmid
    assert result[0]["variant_text"] == "V600E"
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRAF"
    assert len(result[0]["diseases"]) == 1
    assert result[0]["diseases"][0]["text"] == "melanoma"


def test_analyze_publication_by_pmid(llm_analyzer):
    """Test analizy publikacji po PMID."""
    pmid = "12345678"
    
    # Tworzenie atrapy publikacji
    gene_anno = create_mock_annotation("BRAF", "Gene", "673", 0, 4)
    variant_anno = create_mock_annotation("V600E", "Mutation", "p.Val600Glu", 10, 5)
    disease_anno = create_mock_annotation("melanoma", "Disease", "D008545", 24, 8)
    
    passage = create_mock_passage(
        "BRAF with V600E mutation in melanoma.", 
        [gene_anno, variant_anno, disease_anno]
    )
    
    document = create_mock_document(pmid, [passage])
    
    # Atrapa metody get_publication_by_pmid
    llm_analyzer.pubtator_client.get_publication_by_pmid.return_value = document
    
    # Test analizy
    result = llm_analyzer.analyze_publication(pmid)
    
    # Weryfikacja wyniku
    assert len(result) == 1
    assert result[0]["pmid"] == pmid
    assert result[0]["variant_text"] == "V600E"
    assert len(result[0]["genes"]) == 1
    assert result[0]["genes"][0]["text"] == "BRAF"
    assert len(result[0]["diseases"]) == 1
    assert result[0]["diseases"][0]["text"] == "melanoma"
    
    # Weryfikacja wywołania metody klienta
    llm_analyzer.pubtator_client.get_publication_by_pmid.assert_called_once_with(pmid)


def test_analyze_publication_not_found(llm_analyzer):
    """Test analizy publikacji, której nie znaleziono."""
    pmid = "99999999"
    
    # Atrapa metody get_publication_by_pmid
    llm_analyzer.pubtator_client.get_publication_by_pmid.return_value = None
    
    # Test analizy
    result = llm_analyzer.analyze_publication(pmid)
    
    # Weryfikacja wyniku - powinna być pusta lista
    assert result == []
    
    # Weryfikacja wywołania metody klienta
    llm_analyzer.pubtator_client.get_publication_by_pmid.assert_called_once_with(pmid)


def test_process_llm_results():
    """Test przetwarzania wyników z LLM."""
    # Tworzenie analizatora bez patchowania LlmManager (nie potrzebujemy go w tym teście)
    with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager'):
        analyzer = LlmContextAnalyzer()
    
    # Przygotowanie danych testowych
    relationship = {
        "pmid": "12345678",
        "variant_text": "V600E",
        "variant_id": "p.Val600Glu",
        "genes": [],
        "diseases": [],
        "tissues": [],
        "species": [],
        "chemicals": [],
        "passage_text": "Test passage text"
    }
    
    llm_results = {
        "relationships": [
            {
                "entity_type": "gene",
                "entity_text": "BRAF",
                "entity_id": "673",
                "has_relationship": True,
                "explanation": "Wariant V600E jest powszechnie występującą mutacją w genie BRAF."
            },
            {
                "entity_type": "disease",
                "entity_text": "melanoma",
                "entity_id": "D008545",
                "has_relationship": True,
                "explanation": "Mutacja V600E w genie BRAF jest często powiązana z czerniakiem."
            },
            {
                "entity_type": "gene",
                "entity_text": "KRAS",
                "entity_id": "3845",
                "has_relationship": False,
                "explanation": "Brak bezpośredniej relacji z wariantem V600E."
            }
        ]
    }
    
    # Wykonanie metody
    analyzer._process_llm_results(relationship, llm_results)
    
    # Weryfikacja wyników
    assert len(relationship["genes"]) == 1
    assert relationship["genes"][0]["text"] == "BRAF"
    assert relationship["genes"][0]["id"] == "673"
    assert "BRAF" in relationship["genes"][0]["explanation"]
    
    assert len(relationship["diseases"]) == 1
    assert relationship["diseases"][0]["text"] == "melanoma"
    assert relationship["diseases"][0]["id"] == "D008545"
    assert "czerniakiem" in relationship["diseases"][0]["explanation"]
    
    # Sprawdzenie, czy nie dodano bytów bez relacji
    assert not any(gene["text"] == "KRAS" for gene in relationship["genes"]) 