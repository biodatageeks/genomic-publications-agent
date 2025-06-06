#!/usr/bin/env python3
"""
Pełna analiza wszystkich PMIDów FOXF1
"""

import requests
import json
import pandas as pd
from pathlib import Path
import time
from typing import List, Dict, Any
import re
from datetime import datetime

class FullFOXF1Analyzer:
    """Kompletny analizator publikacji FOXF1"""
    
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
                journal = self._extract_xml_content(content, "Title")  # Journal title
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
        # Szukaj roku w różnych miejscach
        patterns = [
            r"<Year>(\d{4})</Year>",
            r"<PubDate>.*?(\d{4}).*?</PubDate>",
            r"(\d{4})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, xml)
            if match:
                year = match.group(1)
                if 1990 <= int(year) <= 2025:  # Sensowny zakres lat
                    return year
        return ""
    
    def _extract_authors(self, xml: str) -> str:
        """Ekstraktuje autorów"""
        # Prosty sposób - znajdź pierwszego autora
        pattern = r"<LastName>(.*?)</LastName>.*?<ForeName>(.*?)</ForeName>"
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return f"{match.group(2)} {match.group(1)}"
        return ""
    
    def analyze_foxf1_content(self, text: str) -> Dict[str, Any]:
        """Zaawansowana analiza tekstu pod kątem FOXF1"""
        # Rozszerzone słowa kluczowe
        foxf1_keywords = [
            "FOXF1", "FOXF2", "forkhead box F1", "forkhead box F2",
            "alveolar capillary dysplasia", "ACD", "lung development", 
            "pulmonary", "vascular", "enhancer", "regulatory", 
            "haploinsufficiency", "embryonic", "mesenchymal"
        ]
        
        disease_keywords = [
            "disease", "syndrome", "dysplasia", "malformation",
            "defect", "abnormality", "disorder", "phenotype",
            "pathology", "clinical"
        ]
        
        variant_keywords = [
            "mutation", "deletion", "variant", "polymorphism",
            "SNP", "CNV", "indel", "substitution", "frameshift",
            "nonsense", "missense", "splice", "genomic"
        ]
        
        development_keywords = [
            "development", "embryogenesis", "differentiation",
            "morphogenesis", "organogenesis", "pattern"
        ]
        
        text_lower = text.lower()
        
        # Zlicz wystąpienia
        foxf1_count = sum(1 for keyword in foxf1_keywords if keyword.lower() in text_lower)
        disease_count = sum(1 for keyword in disease_keywords if keyword.lower() in text_lower)
        variant_count = sum(1 for keyword in variant_keywords if keyword.lower() in text_lower)
        dev_count = sum(1 for keyword in development_keywords if keyword.lower() in text_lower)
        
        # Szukaj konkretnych wariantów
        variants_found = self._find_variants(text)
        genes_found = self._find_genes(text)
        
        # Oblicz score
        relevance_score = (foxf1_count * 3 + disease_count + variant_count * 2 + 
                         dev_count + len(variants_found) * 2 + len(genes_found))
        
        return {
            "foxf1_mentions": foxf1_count,
            "disease_mentions": disease_count,
            "variant_mentions": variant_count,
            "development_mentions": dev_count,
            "variants_found": ";".join(variants_found) if variants_found else "",
            "genes_found": ";".join(genes_found) if genes_found else "",
            "relevance_score": relevance_score,
            "is_relevant": relevance_score >= 5,
            "is_highly_relevant": relevance_score >= 10
        }
    
    def _find_variants(self, text: str) -> List[str]:
        """Znajdź warianty genomowe w tekście"""
        variant_patterns = [
            r'\b[cgpn]\.\d+[ATCG]>[ATCG]\b',  # c.123A>G
            r'\b[cgpn]\.\d+del[ATCG]*\b',      # c.123delA
            r'\b[cgpn]\.\d+ins[ATCG]+\b',      # c.123insA
            r'\b[cgpn]\.\d+_\d+del\b',         # c.123_125del
            r'\brs\d+\b',                      # rs123456
            r'\b[0-9]+[qp][0-9.]+\b'           # chromosomal locations
        ]
        
        variants = []
        for pattern in variant_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            variants.extend(matches)
        
        return list(set(variants))  # Usuń duplikaty
    
    def _find_genes(self, text: str) -> List[str]:
        """Znajdź geny w tekście"""
        gene_patterns = [
            r'\bFOXF[12]\b',
            r'\bFOX[A-Z][0-9]+\b',
            r'\b[A-Z]{2,8}[0-9]*\b'  # Ogólny pattern genów
        ]
        
        genes = []
        for pattern in gene_patterns:
            matches = re.findall(pattern, text)
            genes.extend(matches)
        
        # Filtruj znane geny
        known_genes = ['FOXF1', 'FOXF2', 'TP53', 'BRCA1', 'BRCA2', 'EGFR', 'MYC']
        genes = [g for g in genes if g.upper() in known_genes or 'FOX' in g.upper()]
        
        return list(set(genes))
    
    def analyze_pmids_batch(self, pmids: List[str], batch_size: int = 50) -> List[Dict[str, Any]]:
        """Analizuje PMIDy w batches"""
        results = []
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} PMIDs)")
            
            batch_results = []
            for j, pmid in enumerate(batch):
                print(f"  Processing PMID {pmid} ({j+1}/{len(batch)})")
                
                # Pobierz publikację
                pub = self.get_pubmed_abstract(pmid)
                if not pub:
                    continue
                
                # Analizuj zawartość
                analysis = self.analyze_foxf1_content(pub["full_text"])
                
                # Połącz wyniki
                result = {**pub, **analysis}
                batch_results.append(result)
                
                # Opóźnienie między zapytaniami
                time.sleep(0.3)
            
            results.extend(batch_results)
            print(f"  Completed batch {i//batch_size + 1}, total results: {len(results)}")
            
            # Zapisz checkpoint
            if len(results) > 0:
                self.save_checkpoint(results, f"checkpoint_batch_{i//batch_size + 1}.csv")
        
        return results
    
    def save_checkpoint(self, results: List[Dict[str, Any]], filename: str):
        """Zapisuje checkpoint wyników"""
        if results:
            df = pd.DataFrame(results)
            df.to_csv(f"checkpoints/{filename}", index=False)
    
    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """Zapisuje wyniki do CSV"""
        if not results:
            print("No results to save")
            return
        
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        print(f"Saved {len(results)} results to {output_path}")
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generuje raport z analizy"""
        if not results:
            return "No results to analyze"
        
        df = pd.DataFrame(results)
        
        # Podstawowe statystyki
        total_pubs = len(df)
        relevant_pubs = len(df[df['is_relevant']])
        highly_relevant = len(df[df['is_highly_relevant']])
        
        # Statystyki FOXF1
        foxf1_mentions = df['foxf1_mentions'].sum()
        variant_mentions = df['variant_mentions'].sum()
        
        # Najlepsze publikacje
        top_pubs = df.nlargest(5, 'relevance_score')[['pmid', 'title', 'year', 'relevance_score']]
        
        # Lata publikacji
        years = df[df['year'] != '']['year'].astype(int)
        year_dist = years.value_counts().sort_index()
        
        report = f"""
=== RAPORT ANALIZY FOXF1 ===
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PODSUMOWANIE:
- Przeanalizowane publikacje: {total_pubs}
- Relevantne publikacje: {relevant_pubs} ({relevant_pubs/total_pubs*100:.1f}%)
- Wysoce relevantne: {highly_relevant} ({highly_relevant/total_pubs*100:.1f}%)
- Średni wynik relevancji: {df['relevance_score'].mean():.2f}

STATYSTYKI TREŚCI:
- Wzmianki o FOXF1: {foxf1_mentions}
- Wzmianki o wariantach: {variant_mentions}
- Znalezione warianty: {len([r for r in results if r['variants_found']])}

TOP 5 PUBLIKACJI:
{top_pubs.to_string(index=False)}

ROZKŁAD CZASOWY:
{year_dist.tail(10).to_string()}

GENY ZNALEZIONE:
{pd.Series([g for r in results for g in r['genes_found'].split(';') if g]).value_counts().head(10).to_string()}
"""
        
        return report

def main():
    """Główna funkcja analizy"""
    # Przygotuj katalogi
    Path("checkpoints").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    
    # Wczytaj wszystkie PMIDy FOXF1
    pmids_file = "data/foxf1_pmids.txt"
    with open(pmids_file, 'r') as f:
        pmids = [line.strip() for line in f if line.strip()]
    
    print(f"Starting FULL analysis of {len(pmids)} PMIDs for FOXF1")
    
    # Inicjalizuj analizator
    analyzer = FullFOXF1Analyzer()
    
    # Uruchom analizę w batches
    results = analyzer.analyze_pmids_batch(pmids, batch_size=50)
    
    # Zapisz wyniki
    analyzer.save_results(results, "reports/foxf1_full_analysis.csv")
    
    # Generuj raport
    report = analyzer.generate_report(results)
    
    # Zapisz raport
    with open("reports/foxf1_analysis_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    
    return results

if __name__ == "__main__":
    results = main() 