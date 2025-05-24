"""
Klasa PubmedEndpoint służy do komunikacji z API PubMed i pobierania
pełnych tekstów publikacji na podstawie identyfikatorów.
"""

import requests
import logging
from typing import Optional, Dict, List, Any


class PubmedEndpoint:
    """
    Klasa do komunikacji z API PubMed w celu pobierania pełnych tekstów publikacji.
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    @staticmethod
    def fetch_full_text_from_pubmed_id(pubmed_id: str) -> str:
        """
        Pobiera pełny tekst publikacji z PubMed na podstawie identyfikatora.
        
        Args:
            pubmed_id: Identyfikator publikacji w PubMed
            
        Returns:
            Pełny tekst publikacji lub pusty ciąg znaków w przypadku niepowodzenia
        """
        logging.info(f"Pobieranie publikacji o ID: {pubmed_id}")
        
        try:
            # Próba pobrania artykułu z PubMed Central
            text = PubmedEndpoint._fetch_from_pmc(pubmed_id)
            if text:
                return text
            
            # Jeśli nie udało się pobrać z PMC, próba pobrania abstraktu z PubMed
            text = PubmedEndpoint._fetch_abstract_from_pubmed(pubmed_id)
            if text:
                return text
            
            logging.warning(f"Nie udało się pobrać tekstu dla publikacji {pubmed_id}")
            return ""
            
        except Exception as e:
            logging.error(f"Błąd podczas pobierania publikacji {pubmed_id}: {str(e)}")
            return ""
    
    @staticmethod
    def _fetch_from_pmc(pubmed_id: str) -> Optional[str]:
        """
        Próbuje pobrać pełny tekst z PubMed Central.
        
        Args:
            pubmed_id: Identyfikator publikacji w PubMed
            
        Returns:
            Pełny tekst publikacji lub None w przypadku niepowodzenia
        """
        # Najpierw znajdź identyfikator PMC
        pmc_id = PubmedEndpoint._get_pmc_id(pubmed_id)
        if not pmc_id:
            return None
        
        # Pobierz pełny tekst z PMC
        url = f"{PubmedEndpoint.BASE_URL}/efetch.fcgi"
        params = {
            "db": "pmc",
            "id": pmc_id,
            "retmode": "xml",
            "rettype": "full"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            # Przetwarzanie XML z tekstem
            text = PubmedEndpoint._extract_text_from_pmc_xml(response.text)
            if text:
                logging.info(f"Pobrano pełny tekst z PMC dla publikacji {pubmed_id}")
                return text
        
        return None
    
    @staticmethod
    def _get_pmc_id(pubmed_id: str) -> Optional[str]:
        """
        Pobiera identyfikator PMC na podstawie identyfikatora PubMed.
        
        Args:
            pubmed_id: Identyfikator publikacji w PubMed
            
        Returns:
            Identyfikator PMC lub None, jeśli nie znaleziono
        """
        url = f"{PubmedEndpoint.BASE_URL}/elink.fcgi"
        params = {
            "dbfrom": "pubmed",
            "db": "pmc",
            "id": pubmed_id,
            "retmode": "json"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200 and response.text:
            # Obsługa odpowiedzi XML lub JSON w zależności od formatu
            try:
                if "LinkSetDb" in response.text:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)
                    links = root.findall(".//Link/Id")
                    if links and len(links) > 0:
                        return links[0].text
                else:
                    data = response.json()
                    link_sets = data.get("linksets", [])
                    if link_sets and len(link_sets) > 0:
                        link_set = link_sets[0]
                        if "linksetdbs" in link_set and len(link_set["linksetdbs"]) > 0:
                            links = link_set["linksetdbs"][0].get("links", [])
                            if links and len(links) > 0:
                                return str(links[0])
            except Exception as e:
                logging.error(f"Błąd podczas przetwarzania odpowiedzi dla identyfikatora PMC: {str(e)}")
        
        return None
    
    @staticmethod
    def _fetch_abstract_from_pubmed(pubmed_id: str) -> Optional[str]:
        """
        Pobiera abstrakt publikacji z PubMed.
        
        Args:
            pubmed_id: Identyfikator publikacji w PubMed
            
        Returns:
            Abstrakt publikacji lub None w przypadku niepowodzenia
        """
        url = f"{PubmedEndpoint.BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": pubmed_id,
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            # Przetwarzanie XML z abstraktem
            text = PubmedEndpoint._extract_abstract_from_pubmed_xml(response.text)
            if text:
                logging.info(f"Pobrano abstrakt dla publikacji {pubmed_id}")
                return text
        
        return None
    
    @staticmethod
    def _extract_text_from_pmc_xml(xml_content: str) -> str:
        """
        Wyciąga tekst z XML publikacji PubMed Central.
        
        Args:
            xml_content: Zawartość XML z PMC
            
        Returns:
            Wyciągnięty tekst publikacji
        """
        try:
            import xml.etree.ElementTree as ET
            
            # Uproszczone przetwarzanie XML - w rzeczywistości wymaga bardziej złożonej logiki
            root = ET.fromstring(xml_content)
            
            # Zbierz tekst z różnych sekcji artykułu
            text_parts = []
            
            # Tytuł
            title_elements = root.findall(".//article-title")
            for elem in title_elements:
                if elem.text:
                    text_parts.append(elem.text)
            
            # Abstrakt
            abstract_elements = root.findall(".//abstract//p")
            for elem in abstract_elements:
                if elem.text:
                    text_parts.append(elem.text)
            
            # Treść artykułu
            body_elements = root.findall(".//body//p")
            for elem in body_elements:
                if elem.text:
                    text_parts.append(elem.text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logging.error(f"Błąd podczas przetwarzania XML PMC: {str(e)}")
            return ""
    
    @staticmethod
    def _extract_abstract_from_pubmed_xml(xml_content: str) -> str:
        """
        Wyciąga abstrakt z XML publikacji PubMed.
        
        Args:
            xml_content: Zawartość XML z PubMed
            
        Returns:
            Wyciągnięty abstrakt publikacji
        """
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            
            # Zbierz tekst z abstraktu
            text_parts = []
            
            # Tytuł
            title_elements = root.findall(".//ArticleTitle")
            for elem in title_elements:
                if elem.text:
                    text_parts.append(elem.text)
            
            # Abstrakt
            abstract_elements = root.findall(".//Abstract//AbstractText")
            for elem in abstract_elements:
                if elem.text:
                    text_parts.append(elem.text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logging.error(f"Błąd podczas przetwarzania XML PubMed: {str(e)}")
            return ""
            
    @staticmethod
    def save_publication_text(text: str, output_path: str) -> None:
        """
        Zapisuje tekst publikacji do pliku.
        
        Args:
            text: Tekst publikacji
            output_path: Ścieżka do pliku wyjściowego
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(text)
            logging.info(f"Zapisano tekst publikacji do pliku: {output_path}")
        except Exception as e:
            logging.error(f"Błąd podczas zapisywania tekstu do pliku {output_path}: {str(e)}")
            
    @staticmethod
    def load_publication_text(input_path: str) -> str:
        """
        Wczytuje tekst publikacji z pliku.
        
        Args:
            input_path: Ścieżka do pliku wejściowego
            
        Returns:
            Tekst publikacji
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                text = file.read()
            logging.info(f"Wczytano tekst publikacji z pliku: {input_path}")
            return text
        except Exception as e:
            logging.error(f"Błąd podczas wczytywania tekstu z pliku {input_path}: {str(e)}")
            return "" 