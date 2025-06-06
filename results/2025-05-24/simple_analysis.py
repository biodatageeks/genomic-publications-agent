#!/usr/bin/env python3
"""
Prosta analiza FOXF1 z bezpośrednim dostępem do PubMed/PubTator
"""

import requests
import json
import pandas as pd
from pathlib import Path
import time
from typing import List, Dict, Any

class SimpleFOXF1Analyzer:
    """Prosty analizator publikacji FOXF1"""
    
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
                # Prosta ekstraktowanie tekstu z XML
                content = response.text
                # Znajdź tytuł i abstrakt (prosta metoda)
                title_start = content.find("<ArticleTitle>")
                title_end = content.find("</ArticleTitle>")
                abstract_start = content.find("<AbstractText>")
                abstract_end = content.find("</AbstractText>")
                
                title = ""
                abstract = ""
                
                if title_start != -1 and title_end != -1:
                    title = content[title_start + 14:title_end]
                
                if abstract_start != -1 and abstract_end != -1:
                    abstract = content[abstract_start + 14:abstract_end]
                
                return {
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "full_text": title + " " + abstract
                }
            else:
                print(f"HTTP Error {response.status_code} for PMID {pmid}")
                return None
        except Exception as e:
            print(f"Error fetching PMID {pmid}: {e}")
            return None
    
    def analyze_foxf1_content(self, text: str) -> Dict[str, Any]:
        """Prosta analiza tekstu pod kątem FOXF1"""
        # Słowa kluczowe związane z FOXF1
        foxf1_keywords = [
            "FOXF1", "FOXF2", "alveolar capillary dysplasia",
            "lung development", "pulmonary", "vascular",
            "enhancer", "regulatory", "deletion", "mutation",
            "haploinsufficiency", "embryonic"
        ]
        
        disease_keywords = [
            "disease", "syndrome", "dysplasia", "malformation",
            "defect", "abnormality", "disorder"
        ]
        
        variant_keywords = [
            "mutation", "deletion", "variant", "polymorphism",
            "SNP", "CNV", "indel", "substitution"
        ]
        
        text_lower = text.lower()
        
        # Zlicz wystąpienia
        foxf1_count = sum(1 for keyword in foxf1_keywords if keyword.lower() in text_lower)
        disease_count = sum(1 for keyword in disease_keywords if keyword.lower() in text_lower)
        variant_count = sum(1 for keyword in variant_keywords if keyword.lower() in text_lower)
        
        # Oblicz score
        relevance_score = foxf1_count * 2 + disease_count + variant_count
        
        return {
            "foxf1_mentions": foxf1_count,
            "disease_mentions": disease_count,
            "variant_mentions": variant_count,
            "relevance_score": relevance_score,
            "is_relevant": relevance_score >= 3
        }
    
    def analyze_pmids(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Analizuje listę PMIDów"""
        results = []
        
        for i, pmid in enumerate(pmids):
            print(f"Processing PMID {pmid} ({i+1}/{len(pmids)})")
            
            # Pobierz publikację
            pub = self.get_pubmed_abstract(pmid)
            if not pub:
                continue
            
            # Analizuj zawartość
            analysis = self.analyze_foxf1_content(pub["full_text"])
            
            # Połącz wyniki
            result = {**pub, **analysis}
            results.append(result)
            
            # Opóźnienie między zapytaniami
            time.sleep(0.5)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """Zapisuje wyniki do CSV"""
        if not results:
            print("No results to save")
            return
        
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        print(f"Saved {len(results)} results to {output_path}")

def main():
    """Główna funkcja analizy"""
    # Wczytaj PMIDy
    pmids_file = "data/foxf1_sample_pmids.txt"
    with open(pmids_file, 'r') as f:
        pmids = [line.strip() for line in f if line.strip()]
    
    print(f"Starting analysis of {len(pmids)} PMIDs for FOXF1")
    
    # Inicjalizuj analizator
    analyzer = SimpleFOXF1Analyzer()
    
    # Uruchom analizę
    results = analyzer.analyze_pmids(pmids)
    
    # Zapisz wyniki
    analyzer.save_results(results, "reports/foxf1_simple_analysis.csv")
    
    # Podsumowanie
    relevant_results = [r for r in results if r["is_relevant"]]
    print(f"\nAnalysis Summary:")
    print(f"Total publications analyzed: {len(results)}")
    print(f"Relevant publications: {len(relevant_results)}")
    print(f"Average relevance score: {sum(r['relevance_score'] for r in results) / len(results):.2f}")
    
    return results

if __name__ == "__main__":
    results = main() 