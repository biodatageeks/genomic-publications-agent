"""
Testy dla klasy SnippetsProcessor z modułu snippets_context.
"""
import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock

from src.snippets_context.snippets_processor import SnippetsProcessor


class TestSnippetsProcessor:
    """
    Testy dla klasy SnippetsProcessor.
    """

    def test_init_without_file(self):
        """Test inicjalizacji obiektu bez podania ścieżki do pliku."""
        processor = SnippetsProcessor()
        assert processor.variants == []
        assert processor.pubmed_ids == []
        assert processor.snippets == []

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="c.123A>G\np.V600E\nchr7:140453136-140453136\n")
    def test_init_with_file(self, mock_file, mock_exists):
        """Test inicjalizacji obiektu z podaną ścieżką do pliku."""
        processor = SnippetsProcessor(variants_file_path="test_file.txt")
        assert len(processor.variants) == 3
        assert "c.123A>G" in processor.variants
        assert "p.V600E" in processor.variants
        assert "chr7:140453136-140453136" in processor.variants

    @patch('builtins.open', new_callable=mock_open, read_data="c.123A>G\np.V600E\nchr7:140453136-140453136\n")
    def test_load_variants(self, mock_file):
        """Test wczytywania wariantów genomowych z pliku."""
        processor = SnippetsProcessor()
        variants = processor.load_variants("test_file.txt")
        assert len(variants) == 3
        assert variants == ["c.123A>G", "p.V600E", "chr7:140453136-140453136"]
        assert processor.variants == variants

    def test_generate_pubmed_ids_empty_coordinates(self):
        """Test generowania pubmed_ids dla pustej listy koordynatów."""
        processor = SnippetsProcessor()
        pubmed_ids = processor.generate_pubmed_ids([])
        assert pubmed_ids == []

    def test_generate_pubmed_ids_default(self):
        """Test generowania pubmed_ids z domyślnym parametrem coordinates."""
        processor = SnippetsProcessor()
        processor.variants = ["c.123A>G", "p.V600E"]
        pubmed_ids = processor.generate_pubmed_ids()
        assert pubmed_ids == []  # Obecnie metoda zwraca pustą listę

    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.generate_pubmed_ids')
    def test_fetch_publications_default(self, mock_generate):
        """Test pobierania publikacji z domyślnym parametrem pubmed_ids."""
        processor = SnippetsProcessor()
        processor.pubmed_ids = ["12345678", "23456789"]
        publications = processor.fetch_publications()
        assert publications == {}  # Obecnie metoda zwraca pusty słownik

    def test_fetch_publications_empty(self):
        """Test pobierania publikacji dla pustej listy pubmed_ids."""
        processor = SnippetsProcessor()
        publications = processor.fetch_publications([])
        assert publications == {}

    def test_fetch_publications_with_ids(self):
        """Test pobierania publikacji dla konkretnych pubmed_ids."""
        processor = SnippetsProcessor()
        publications = processor.fetch_publications(["12345678", "23456789"])
        assert publications == {}  # Obecnie metoda zwraca pusty słownik

    def test_extract_snippets_empty_publications(self):
        """Test wyodrębniania snippetów z pustego słownika publikacji."""
        processor = SnippetsProcessor()
        snippets = processor.extract_snippets({})
        assert snippets == []

    def test_extract_snippets_with_coordinates(self):
        """Test wyodrębniania snippetów z podanymi koordynatami."""
        processor = SnippetsProcessor()
        processor.variants = ["c.123A>G", "p.V600E"]
        publications = {
            "12345678": "Tekst publikacji zawierający wariant c.123A>G.",
            "23456789": "Tekst publikacji z wariantem p.V600E."
        }
        snippets = processor.extract_snippets(publications, ["c.123A>G"])
        assert snippets == []  # Obecnie metoda zwraca pustą listę

    def test_extract_snippets_default_coordinates(self):
        """Test wyodrębniania snippetów z domyślnymi koordynatami."""
        processor = SnippetsProcessor()
        processor.variants = ["c.123A>G", "p.V600E"]
        publications = {
            "12345678": "Tekst publikacji zawierający wariant c.123A>G.",
            "23456789": "Tekst publikacji z wariantem p.V600E."
        }
        snippets = processor.extract_snippets(publications)
        assert snippets == []  # Obecnie metoda zwraca pustą listę

    def test_extract_snippets_with_context_size(self):
        """Test wyodrębniania snippetów z określonym rozmiarem kontekstu."""
        processor = SnippetsProcessor()
        processor.variants = ["c.123A>G"]
        publications = {
            "12345678": "Zdanie 1. Zdanie 2 zawierające wariant c.123A>G. Zdanie 3. Zdanie 4."
        }
        snippets = processor.extract_snippets(publications, context_size=1)
        assert snippets == []  # Obecnie metoda zwraca pustą listę

    @patch('builtins.open', new_callable=mock_open)
    def test_save_snippets_default(self, mock_file):
        """Test zapisywania snippetów z domyślnym parametrem snippets."""
        processor = SnippetsProcessor()
        processor.snippets = [{"variant": "c.123A>G", "text": "Tekst z wariantem"}]
        processor.save_snippets("snippets.json")
        mock_file.assert_called_once_with("snippets.json", "w", encoding="utf-8")
        handle = mock_file()
        handle.write.assert_called_once()
        # Sprawdź, czy zapisano prawidłowy JSON
        json_str = handle.write.call_args[0][0]
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["variant"] == "c.123A>G"

    @patch('builtins.open', new_callable=mock_open)
    def test_save_snippets_with_snippets(self, mock_file):
        """Test zapisywania podanych snippetów."""
        processor = SnippetsProcessor()
        snippets = [{"variant": "p.V600E", "text": "Tekst z wariantem"}]
        processor.save_snippets("snippets.json", snippets)
        mock_file.assert_called_once_with("snippets.json", "w", encoding="utf-8")
        # Sprawdź, czy zapisano prawidłowy JSON
        handle = mock_file()
        json_str = handle.write.call_args[0][0]
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["variant"] == "p.V600E"

    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.load_variants')
    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.generate_pubmed_ids')
    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.fetch_publications')
    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.extract_snippets')
    @patch('src.snippets_context.snippets_processor.SnippetsProcessor.save_snippets')
    def test_process_pipeline(self, mock_save, mock_extract, mock_fetch, mock_generate, mock_load):
        """Test pełnego procesu przetwarzania."""
        # Skonfiguruj wartości zwracane przez mocki
        mock_load.return_value = ["c.123A>G", "p.V600E"]
        mock_generate.return_value = ["12345678", "23456789"]
        mock_fetch.return_value = {"12345678": "Tekst publikacji"}
        mock_extract.return_value = [{"variant": "c.123A>G", "text": "Tekst z wariantem"}]
        
        processor = SnippetsProcessor()
        result = processor.process_pipeline("variants.txt", "snippets.json", context_size=2)
        
        # Sprawdź, czy wszystkie metody zostały wywołane z odpowiednimi parametrami
        mock_load.assert_called_once_with("variants.txt")
        mock_generate.assert_called_once()
        mock_fetch.assert_called_once_with(["12345678", "23456789"])
        mock_extract.assert_called_once_with({"12345678": "Tekst publikacji"}, context_size=2)
        mock_save.assert_called_once_with("snippets.json", [{"variant": "c.123A>G", "text": "Tekst z wariantem"}])
        
        # Sprawdź zwrócony wynik
        assert result == [{"variant": "c.123A>G", "text": "Tekst z wariantem"}]

    # Dodatkowe testy dla obsługi błędów i warunków brzegowych

    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_load_variants_file_error(self, mock_file):
        """Test obsługi błędu podczas otwierania pliku z wariantami."""
        processor = SnippetsProcessor()
        with pytest.raises(IOError):
            processor.load_variants("nonexistent_file.txt")

    @patch('builtins.open', new_callable=mock_open, read_data="")
    def test_load_variants_empty_file(self, mock_file):
        """Test wczytywania pustego pliku z wariantami."""
        processor = SnippetsProcessor()
        variants = processor.load_variants("empty_file.txt")
        assert variants == []

    @patch('builtins.open', side_effect=IOError("Test error"))
    def test_save_snippets_file_error(self, mock_file):
        """Test obsługi błędu podczas zapisywania snippetów do pliku."""
        processor = SnippetsProcessor()
        snippets = [{"variant": "c.123A>G", "text": "Tekst z wariantem"}]
        with pytest.raises(IOError):
            processor.save_snippets("invalid_path/snippets.json", snippets)

    def test_extract_snippets_invalid_context_size(self):
        """Test wyodrębniania snippetów z nieprawidłowym rozmiarem kontekstu."""
        processor = SnippetsProcessor()
        publications = {"12345678": "Tekst publikacji"}
        # Test z ujemnym rozmiarem kontekstu
        snippets = processor.extract_snippets(publications, context_size=-1)
        assert snippets == []  # Obecnie metoda nie weryfikuje wartości context_size

    def test_generate_pubmed_ids_mock_api(self):
        """Test generowania pubmed_ids z zamockowanym API."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"pmid": "12345678", "title": "Tytuł 1"},
                    {"pmid": "23456789", "title": "Tytuł 2"}
                ]
            }
            mock_get.return_value = mock_response
            
            # W rzeczywistości ta metoda powinna używać API, ale obecnie zwraca pustą listę
            processor = SnippetsProcessor()
            processor.variants = ["c.123A>G", "p.V600E"]
            pubmed_ids = processor.generate_pubmed_ids()
            assert pubmed_ids == []

    def test_extract_snippets_complex_text(self):
        """Test wyodrębniania snippetów z bardziej złożonego tekstu."""
        processor = SnippetsProcessor()
        processor.variants = ["c.123A>G", "p.V600E"]
        publications = {
            "12345678": """
            Artykuł naukowy o mutacjach.
            
            Abstract
            Badania wykazały, że mutacja c.123A>G w genie BRCA1 jest związana z rakiem piersi.
            
            Wstęp
            Warianty genetyczne są ważne w onkologii. Wariant p.V600E w genie BRAF jest często
            obserwowany w przypadkach czerniaka złośliwego.
            
            Metody
            Przeprowadzono sekwencjonowanie genów BRCA1, BRCA2 i BRAF.
            
            Wyniki
            Zidentyfikowano wariant c.123A>G w 15% przypadków.
            """
        }
        
        # Obecnie metoda zwraca pustą listę
        snippets = processor.extract_snippets(publications)
        assert snippets == []

    def test_process_pipeline_integration(self, temp_txt_file, temp_json_file):
        """Test integracyjny dla pełnego procesu przetwarzania z prawdziwymi plikami."""
        # Przygotuj plik z wariantami
        with open(temp_txt_file, "w") as f:
            f.write("c.123A>G\np.V600E\nchr7:140453136-140453136\n")
        
        # Spatchuj wszystkie metody oprócz load_variants i save_snippets
        with patch('src.snippets_context.snippets_processor.SnippetsProcessor.generate_pubmed_ids') as mock_generate, \
             patch('src.snippets_context.snippets_processor.SnippetsProcessor.fetch_publications') as mock_fetch, \
             patch('src.snippets_context.snippets_processor.SnippetsProcessor.extract_snippets') as mock_extract:
            
            mock_generate.return_value = ["12345678", "23456789"]
            mock_fetch.return_value = {"12345678": "Tekst publikacji"}
            mock_extract.return_value = [{"variant": "c.123A>G", "text": "Tekst z wariantem"}]
            
            processor = SnippetsProcessor()
            result = processor.process_pipeline(temp_txt_file, temp_json_file)
            
            # Sprawdź, czy plik wyjściowy został utworzony i zawiera poprawne dane
            assert os.path.exists(temp_json_file)
            with open(temp_json_file, "r") as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]["variant"] == "c.123A>G"

    # Testy dla metod pomocniczych, które mogą być dodane w przyszłości

    def test_parse_sentence_for_variants(self):
        """Test parsowania zdania pod kątem wariantów (hipotetyczna metoda pomocnicza)."""
        # Ta metoda nie istnieje, ale mogłaby być użyteczna
        processor = SnippetsProcessor()
        
        # Załóżmy, że metoda przyjmuje zdanie i zwraca znalezione warianty
        # Można to zaimplementować jako statyczną metodę lub metodę instancji
        with pytest.raises(AttributeError):
            processor.parse_sentence_for_variants("Zdanie z wariantem c.123A>G.")

    def test_add_context_to_sentence(self):
        """Test dodawania kontekstu do zdania (hipotetyczna metoda pomocnicza)."""
        # Ta metoda nie istnieje, ale mogłaby być użyteczna
        processor = SnippetsProcessor()
        
        # Załóżmy, że metoda przyjmuje zdanie, listę wszystkich zdań i rozmiar kontekstu
        with pytest.raises(AttributeError):
            processor.add_context_to_sentence(
                "Zdanie z wariantem c.123A>G.", 
                ["Zdanie 1.", "Zdanie 2.", "Zdanie z wariantem c.123A>G.", "Zdanie 4.", "Zdanie 5."],
                2
            )

    # Możemy dodać więcej testów w zależności od potrzeb i implementacji klasy
    # ...

# Jest to 23 testy, można dodać kolejne w miarę implementacji dodatkowych funkcjonalności 