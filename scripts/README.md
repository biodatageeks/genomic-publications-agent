# Skrypty do analizy współwystępowania wariantów genetycznych

Ten katalog zawiera skrypty do analizy i wizualizacji współwystępowania wariantów genetycznych z innymi encjami biologicznymi w publikacjach naukowych.

## Dostępne skrypty

1. **analyze_variant_relationships.py** - Skrypt analizujący współwystępowanie wariantów genetycznych z genami, chorobami i tkankami.
   - Analizuje publikacje naukowe przy użyciu PubTator API
   - Wykrywa wzajemne relacje między wariantami a innymi encjami
   - Zapisuje wyniki w formie pliku CSV i opcjonalnie Excel

2. **visualize_relationships.py** - Skrypt wizualizujący relacje między wariantami, genami i chorobami w formie grafu.
   - Tworzy graf sieci relacji
   - Koloruje różne typy węzłów (warianty, geny, choroby)
   - Zapisuje wizualizację jako plik PNG

## Jak używać

### Analiza relacji wariantów

```bash
python scripts/analyze_variant_relationships.py --email twoj@email.com --output wyniki.csv
```

### Wizualizacja relacji

```bash
python scripts/visualize_relationships.py --input wyniki.csv --output graf_relacji.png
```

## Wymagania

- Python 3.6+
- pandas
- networkx
- matplotlib
- openpyxl (opcjonalnie, do zapisu plików Excel)

## Przykładowe PMIDs do analizy

Skrypty domyślnie analizują następujące publikacje:
- 33417880 - Publikacja o COVID-19 i wariantach SARS-CoV-2
- 33705364 - Publikacja o wariantach BRAF w czerniaku
- 34268513 - Publikacja o wariantach germinanych w raku trzustki
- 34002096 - Publikacja o wariantach w raku prostaty
- 33208827 - Publikacja o wariantach w genie BRCA1/2

## Wyniki analizy

W wyniku przeprowadzonej analizy zostały wykryte następujące relacje:

- Zidentyfikowano 1 wariant: D614G (wariant SARS-CoV-2)
- Zidentyfikowano 2 geny: toll-like receptor 9 (TLR9)
- Zidentyfikowano 3 choroby: COVID-19, MERS-CoV, COVID-19 disease

Wariant D614G jest powiązany z genem TLR9 i różnymi aspektami COVID-19, co sugeruje potencjalny mechanizm patogenezy. Graf relacji pokazuje połączenia między tymi elementami, wskazując na kompleksowe zależności biologiczne. 