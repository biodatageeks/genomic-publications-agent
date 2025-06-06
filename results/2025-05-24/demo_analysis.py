#!/usr/bin/env python3
"""
Demonstracyjna analiza 50 PMIDów FOXF1
"""

import requests
import json
import pandas as pd
from pathlib import Path
import time
from typing import List, Dict, Any
import re
from datetime import datetime

class DemoFOXF1Analyzer:
    """Demonstracyjny analizator publikacji FOXF1"""
    
    def __init__(self, email: str = "sitekwb@gmail.com"):
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
    def get_pubmed_abstract(self, pmid: str) -> Dict[str, Any]:
        """Pobiera abstrakt z PubMed"""
        url = f"{self.base_url}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "email": self.email
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                content = response.text
                
                # Ekstraktuj informacje
                title = self._extract_xml_content(content, "ArticleTitle")
                abstract = self._extract_xml_content(content, "AbstractText")
                journal = self._extract_xml_content(content, "Title")
                year = self._extract_year(content)
                authors = self._extract_authors(content)
                
                return {
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "journal": journal,
                    "year": year,
                    "authors": authors,
                    "full_text": title + " " + abstract
                }
            else:
                print(f"HTTP Error {response.status_code} for PMID {pmid}")
                return None
        except Exception as e:
            print(f"Error fetching PMID {pmid}: {e}")
            return None
    
    def _extract_xml_content(self, xml: str, tag: str) -> str:
        """Ekstraktuje zawartość tagu XML"""
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_year(self, xml: str) -> str:
        """Ekstraktuje rok publikacji"""
        patterns = [
            r"<Year>(\d{4})</Year>",
            r"<PubDate>.*?(\d{4}).*?</PubDate>",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, xml)
            if match:
                year = match.group(1)
                if 1990 <= int(year) <= 2025:
                    return year
        return ""
    
    def _extract_authors(self, xml: str) -> str:
        """Ekstraktuje autorów"""
        pattern = r"<LastName>(.*?)</LastName>.*?<ForeName>(.*?)</ForeName>"
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return f"{match.group(2)} {match.group(1)}"
        return ""
    
    def analyze_foxf1_content(self, text: str) -> Dict[str, Any]:
        """Analiza tekstu pod kątem FOXF1"""
        foxf1_keywords = [
            "FOXF1", "FOXF2", "forkhead box F1", "alveolar capillary dysplasia",
            "lung development", "pulmonary", "vascular", "enhancer"
        ]
        
        disease_keywords = [
            "disease", "syndrome", "dysplasia", "malformation", "disorder"
        ]
        
        variant_keywords = [
            "mutation", "deletion", "variant", "polymorphism", "CNV"
        ]
        
        text_lower = text.lower()
        
        # Zlicz wystąpienia
        foxf1_count = sum(1 for keyword in foxf1_keywords if keyword.lower() in text_lower)
        disease_count = sum(1 for keyword in disease_keywords if keyword.lower() in text_lower)
        variant_count = sum(1 for keyword in variant_keywords if keyword.lower() in text_lower)
        
        # Szukaj konkretnych wariantów
        variants_found = self._find_variants(text)
        
        # Oblicz score
        relevance_score = foxf1_count * 3 + disease_count + variant_count * 2 + len(variants_found) * 2
        
        return {
            "foxf1_mentions": foxf1_count,
            "disease_mentions": disease_count,
            "variant_mentions": variant_count,
            "variants_found": ";".join(variants_found) if variants_found else "",
            "relevance_score": relevance_score,
            "is_relevant": relevance_score >= 3
        }
    
    def _find_variants(self, text: str) -> List[str]:
        """Znajdź warianty genomowe w tekście"""
        variant_patterns = [
            r'\b[cgpn]\.\d+[ATCG]>[ATCG]\b',
            r'\b[cgpn]\.\d+del[ATCG]*\b',
            r'\brs\d+\b',
            r'\b[0-9]+[qp][0-9.]+\b'
        ]
        
        variants = []
        for pattern in variant_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            variants.extend(matches)
        
        return list(set(variants))
    
    def analyze_pmids(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Analizuje listę PMIDów"""
        results = []
        
        for i, pmid in enumerate(pmids):
            print(f"Processing PMID {pmid} ({i+1}/{len(pmids)})")
            
            pub = self.get_pubmed_abstract(pmid)
            if not pub:
                continue
            
            analysis = self.analyze_foxf1_content(pub["full_text"])
            result = {**pub, **analysis}
            results.append(result)
            
            time.sleep(0.3)
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generuje raport z analizy"""
        if not results:
            return "No results to analyze"
        
        df = pd.DataFrame(results)
        
        total_pubs = len(df)
        relevant_pubs = len(df[df['is_relevant']])
        
        # Top publikacje
        top_pubs = df.nlargest(5, 'relevance_score')[['pmid', 'title', 'year', 'relevance_score']]
        
        # Lata publikacji
        years = df[df['year'] != '']['year'].astype(int)
        year_dist = years.value_counts().sort_index()
        
        report = f"""
=== RAPORT DEMONSTRACYJNEJ ANALIZY FOXF1 ===
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PODSUMOWANIE:
- Przeanalizowane publikacje: {total_pubs}
- Relevantne publikacje: {relevant_pubs} ({relevant_pubs/total_pubs*100:.1f}%)
- Średni wynik relevancji: {df['relevance_score'].mean():.2f}

STATYSTYKI TREŚCI:
- Wzmianki o FOXF1: {df['foxf1_mentions'].sum()}
- Wzmianki o chorobach: {df['disease_mentions'].sum()}
- Wzmianki o wariantach: {df['variant_mentions'].sum()}

TOP 5 PUBLIKACJI:
{top_pubs.to_string(index=False)}

ROZKŁAD CZASOWY:
{year_dist.to_string()}

ZNALEZIONE WARIANTY:
{len([r for r in results if r['variants_found']])} publikacji zawiera warianty genomowe
"""
        
        return report

def main():
    """Główna funkcja demonstracyjnej analizy"""
    # Wczytaj pierwsze 50 PMIDów
    pmids_file = "data/foxf1_pmids.txt"
    with open(pmids_file, 'r') as f:
        all_pmids = [line.strip() for line in f if line.strip()]
    
    # Weź próbkę 50 PMIDów
    pmids = all_pmids[:50]
    
    print(f"Starting DEMO analysis of {len(pmids)} PMIDs for FOXF1")
    
    # Inicjalizuj analizator
    analyzer = DemoFOXF1Analyzer()
    
    # Uruchom analizę
    results = analyzer.analyze_pmids(pmids)
    
    # Zapisz wyniki
    df = pd.DataFrame(results)
    df.to_csv("reports/foxf1_demo_analysis.csv", index=False)
    print(f"Saved {len(results)} results to reports/foxf1_demo_analysis.csv")
    
    # Generuj raport
    report = analyzer.generate_report(results)
    
    # Zapisz raport
    with open("reports/foxf1_demo_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    
    return results

if __name__ == "__main__":
    results = main() 