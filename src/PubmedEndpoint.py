import logging

import requests
from xml.etree import ElementTree
import pandas as pd


class PubmedEndpoint:

    @staticmethod
    def pubmed_search(query, retmax=10):
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "xml",
            "retmax": retmax
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()

        tree = ElementTree.fromstring(response.content)
        ids = [id_elem.text for id_elem in tree.findall(".//Id")]

        return ids

    @staticmethod
    def fetch_details(id_list):
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        ids = ",".join(id_list)
        params = {
            "db": "pubmed",
            "id": ids,
            "retmode": "xml",
            "rettype": "abstract"
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()

        return response.content

    @staticmethod
    def preprocess_details_to_dataframe(xml_data):
        tree = ElementTree.fromstring(xml_data)
        articles = []

        for article in tree.findall(".//PubmedArticle"):
            article_data = {}

            # Extracting the title
            title_elem = article.find(".//ArticleTitle")
            article_data['Title'] = title_elem.text if title_elem is not None else "N/A"

            # Extracting the authors
            authors = []
            for author in article.findall(".//Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and fore_name is not None:
                    authors.append(f"{fore_name.text} {last_name.text}")
            article_data['Authors'] = ", ".join(authors) if authors else "N/A"

            # Extracting the journal name
            journal_elem = article.find(".//Journal/Title")
            article_data['Journal'] = journal_elem.text if journal_elem is not None else "N/A"

            # Extracting the publication date
            pub_date_elem = article.find(".//PubDate")
            if pub_date_elem is not None:
                year_elem = pub_date_elem.find("Year")
                month_elem = pub_date_elem.find("Month")
                day_elem = pub_date_elem.find("Day")
                pub_date = f"{year_elem.text if year_elem is not None else ''}-{month_elem.text if month_elem is not None else ''}-{day_elem.text if day_elem is not None else ''}"
                article_data['Publication Date'] = pub_date
            else:
                article_data['Publication Date'] = "N/A"

            # Extracting the abstract
            abstract_elem = article.find(".//Abstract/AbstractText")
            article_data['Abstract'] = abstract_elem.text if abstract_elem is not None else "N/A"

            articles.append(article_data)

        df = pd.DataFrame(articles)
        return df

    @staticmethod
    def fetch_full_text(pmc_id):
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            "db": "pmc",
            "id": pmc_id,
            "retmode": "xml"
        }

        response = requests.get(base_url, params=params)
        response.raise_for_status()

        return response.content

    @staticmethod
    def preprocess_full_text_to_plain_text(xml_data):
        tree = ElementTree.fromstring(xml_data)
        text_content = []

        # Extract text from <body> element of the article
        body_elem = tree.find(".//body")
        if body_elem is not None:
            for elem in body_elem.iter():
                if elem.text:
                    text_content.append(elem.text.strip())
                if elem.tail:
                    text_content.append(elem.tail.strip())

        plain_text = "\n".join(text_content)
        return plain_text

    @staticmethod
    def fetch_full_text_from_pubmed_id(id):
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching full text for article with PubMed ID: {id}")
        # Convert PubMed ID to PMC ID using eLink
        elink_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
        elink_params = {
            "dbfrom": "pubmed",
            "db": "pmc",
            "id": id,
            "retmode": "xml"
        }

        elink_response = requests.get(elink_base_url, params=elink_params)
        elink_response.raise_for_status()

        elink_tree = ElementTree.fromstring(elink_response.content)
        pmc_id_elem = elink_tree.find(".//LinkSetDb/Link/Id")
        if pmc_id_elem is not None:
            pmc_id = pmc_id_elem.text
            full_text_xml = PubmedEndpoint.fetch_full_text(pmc_id)
            return full_text_xml.decode('utf-8')
        else:
            print("Full text not available in PMC for this article.")
            # Return the abstract instead

            return None

    @staticmethod
    def fetch_articles_from_query(query):
        ids = PubmedEndpoint.pubmed_search(query, retmax=10)  # You can adjust retmax to get more results

        if ids:
            details = PubmedEndpoint.fetch_details(ids)
            df = PubmedEndpoint.preprocess_details_to_dataframe(details)

            return df, ids
        else:
            print("No results found")
            return None, None


