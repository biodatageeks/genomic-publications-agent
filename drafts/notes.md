Problemy
- Stworzyć benchmarki, które będą zawierały
    1. pubmed_id -> koordynaty
    2. Publikacja i koordynata -> kontekst
    3. Koordynata i kontekst -> mapping do sequence ontology
    4. Koordynata, kontekst, so_term, klucz, sprawdzana wartość -> występuje/nie występuje

INPUT BENCHMARK JSON:
[
    {
        "pubmed_id": "1234567890",
        "full_text": "...",
        "coordinates": [
            {
                "coordinate": "chr1:1000-2000",
                "context": "We used the coordinate chr1:1000-2000 to study the expression of the gene in the tissue.",
                "sequence_ontology_term": "SO:0000159",
                "pairs": [
                    {
                        "key": "gene_expression",
                        "value": "high"
                    },
                    {
                        "key": "region_type",
                        "value": "promoter"
                    }
                ]
            },
            {
                "coordinate": "chr1:1000-2000",
                "context": "We used this coordinate to study the expression of the gene in the tissue.",
                ...
            }
        ]
    }
]


Problem 1. pubmed_id -> koordynaty
- Lepiej zdefiniować formaty koordynat
- Dla każdej publikacji ze zbioru danych:
    1. Pobrać pełny tekst publikacji
    2. Pobrać metodą naiwną i złożoną za pomocą różnych narzędzi koordynaty
    3. Zweryfikować ręcznie ich obecność w tekście
    4. Sprawdzić jakoś czy nie ma innych koordynat - jak?
    5. Dodać do benchmarku
- Sprawdzić czy nie generuje się dodatkowy zagłuszający output w llamie

Problem 2. publikacja i koordynata -> kontekst
- Dla wszystkich koordynat z benchmarku:
    1. Ekstrakcja kontekstu z publikacji
    2. Sprawdzenie ręczne, czy to pasuje - jak?


Problem 3. Koordynata I kontekst -> mapping do sequence ontology
Jak można to usprawnić???
- Wyciąganie informacji opisowej bezpośrednio z koordynaty

Problem 4. Koordynata, kontekst, so_term, klucz, sprawdzana wartość -> występuje/nie występuje
- Wyciąganie informacji z koordynaty
