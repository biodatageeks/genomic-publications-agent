"""
Testy jednostkowe dla LlmContextAnalyzer.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

import bioc
from bioc import BioCDocument, BioCPassage, BioCAnnotation, BioCLocation
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from src.api.clients.exceptions import PubTatorError
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer


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


def test_cache_functionality():
    """Test sprawdzający poprawność działania cache w LlmContextAnalyzer."""
    # Tworzenie analizatora z włączonym cache
    pubtator_client_mock = Mock()
    
    with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager') as mock_llm_manager_class, \
         patch('src.llm_context_analyzer.llm_context_analyzer.APICache') as mock_api_cache_class:
        
        # Przygotowanie atrapy LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = AIMessage(content=json.dumps(MOCK_LLM_RESPONSE))
        
        mock_llm_manager = mock_llm_manager_class.return_value
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Przygotowanie atrapy cache'a
        mock_cache = Mock()
        mock_cache.has.return_value = False  # Na początku nie ma danych w cache
        mock_cache.get.return_value = MOCK_LLM_RESPONSE["relationships"]
        mock_cache.set.return_value = True
        
        mock_api_cache_class.create.return_value = mock_cache
        
        # Utworzenie analizatora z włączonym cache
        analyzer = LlmContextAnalyzer(pubtator_client=pubtator_client_mock, use_cache=True)
        
        # Przygotowanie danych testowych
        variant_text = "V600E"
        entities = [
            {"entity_type": "gene", "text": "BRAF", "id": "673", "offset": 0},
            {"entity_type": "disease", "text": "melanoma", "id": "D008545", "offset": 24}
        ]
        passage_text = "BRAF with V600E mutation in melanoma."
        
        # Pierwszy wywołanie - dane powinny być obliczone przez LLM i zapisane do cache
        result1 = analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        
        # Weryfikacja wywołania LLM
        assert mock_llm.invoke.call_count == 1
        
        # Weryfikacja zapisu do cache
        assert mock_cache.set.call_count == 1
        
        # Symulacja istnienia danych w cache przy następnym wywołaniu
        mock_cache.has.return_value = True
        
        # Drugie wywołanie z tymi samymi parametrami - dane powinny być pobrane z cache
        result2 = analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        
        # LLM nie powinien być wywoływany ponownie
        assert mock_llm.invoke.call_count == 1
        
        # Cache powinien być sprawdzony
        assert mock_cache.has.call_count > 0
        
        # Dane powinny być pobrane z cache
        assert mock_cache.get.call_count > 0
        
        # Wyniki powinny być identyczne
        assert result1 == result2


def test_cache_disabled():
    """Test sprawdzający działanie, gdy cache jest wyłączone."""
    # Tworzenie analizatora z wyłączonym cache
    pubtator_client_mock = Mock()
    
    with patch('src.llm_context_analyzer.llm_context_analyzer.LlmManager') as mock_llm_manager_class:
        # Przygotowanie atrapy LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = AIMessage(content=json.dumps(MOCK_LLM_RESPONSE))
        
        mock_llm_manager = mock_llm_manager_class.return_value
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Utworzenie analizatora z wyłączonym cache
        analyzer = LlmContextAnalyzer(pubtator_client=pubtator_client_mock, use_cache=False)
        assert analyzer.cache is None
        
        # Przygotowanie danych testowych
        variant_text = "V600E"
        entities = [
            {"entity_type": "gene", "text": "BRAF", "id": "673", "offset": 0},
            {"entity_type": "disease", "text": "melanoma", "id": "D008545", "offset": 24}
        ]
        passage_text = "BRAF with V600E mutation in melanoma."
        
        # Wywołanie metody dwukrotnie
        analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        analyzer._analyze_relationships_with_llm(variant_text, entities, passage_text)
        
        # LLM powinien być wywoływany dwukrotnie
        assert mock_llm.invoke.call_count == 2 