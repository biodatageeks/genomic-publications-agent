# PubTator3 API Client

The `pubtator_client.py` module contains an implementation of a class for handling the PubTator3 API, which allows for retrieving biomedical publications with annotations related to genes, diseases, tissue specificity, variants, and other biological concepts.

## Author Information

This module was created using code generation by Claude 3.7 Sonnet and Cursor AI.

## Features

- Retrieving publications based on PubMed identifiers (PMIDs)
- Searching for publications using text queries
- Support for different data formats (BioC JSON, PubTator, BioC XML)
- Extraction of annotations related to genes, diseases, genetic variants, and tissue specificity
- Grouping annotations by types

## Installation

1. Clone the repository

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage Example

```python
from src.pubtator_client.pubtator_client import PubTatorClient

# Initialize the client
client = PubTatorClient()

# Retrieve publications by PubMed identifiers
pmids = ["32735606", "32719766"]
publications = client.get_publications_by_pmids(pmids)

# Display information about publications
for pub in publications:
    print(f"Title: {pub.passages[0].text}")
    
    # Extract gene annotations
    genes = client.extract_gene_annotations(pub)
    print(f"Found {len(genes)} gene annotations:")
    for gene in genes[:5]:  # Display the first 5 annotations
        print(f"  - {gene['text']} (ID: {gene['normalized_id']})")
    
    # Extract disease annotations
    diseases = client.extract_disease_annotations(pub)
    print(f"Found {len(diseases)} disease annotations:")
    for disease in diseases[:5]:  # Display the first 5 annotations
        print(f"  - {disease['text']} (ID: {disease['normalized_id']})")
    
    # Extract genetic variant annotations
    variants = client.extract_variant_annotations(pub)
    print(f"Found {len(variants)} variant annotations:")
    for variant in variants[:5]:  # Display the first 5 annotations
        print(f"  - {variant['text']} (ID: {variant['normalized_id']})")
    
    # Extract tissue specificity annotations
    tissues = client.extract_tissue_specificity(pub)
    print(f"Found {len(tissues)} tissue annotations:")
    for tissue in tissues[:5]:  # Display the first 5 annotations
        print(f"  - {tissue['text']} (ID: {tissue['normalized_id']})")

# Search for publications
results = client.search_publications("BRCA1 AND cancer")
print(f"Found {len(results)} publications for the query 'BRCA1 AND cancer'")
```

## More Information

- [PubTator3 API Documentation](https://www.ncbi.nlm.nih.gov/research/pubtator3/api)
- [bioc Library Documentation](https://pypi.org/project/bioc/)
- [PubTator Central](https://www.ncbi.nlm.nih.gov/research/pubtator/) - A system for annotating biomedical publications

## License

This project is distributed under the MIT License. See the LICENSE file for more information. 