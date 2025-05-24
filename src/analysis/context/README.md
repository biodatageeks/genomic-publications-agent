# Cooccurrence Context Analyzer

A Python module for analyzing the context of co-occurring biomedical entities in scientific publications using PubTator3 API annotations.

## Overview

This module builds on the `pubtator_client` to extract relationships between variants and other biomedical entities (genes, diseases, tissues, species, chemicals) that appear in the same passage context within biomedical publications. It helps researchers identify potential biological relationships and gain insights from literature.

## Features

- Analyze single or multiple publications by their PubMed IDs (PMIDs)
- Extract variants (mutations) from publications
- Identify genes, diseases, tissues, and other entities appearing in the same passage context as variants
- Generate structured relationship data in CSV or JSON format
- Filter relationships by specific entity types and values

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/your-repo.git
cd your-repo

# Install dependencies
pip install -r requirements.txt
```

## Usage Examples

### Basic Usage

```python
from src.cooccurrence_context_analyzer import CooccurrenceContextAnalyzer

# Initialize the analyzer
analyzer = CooccurrenceContextAnalyzer()

# Analyze a single publication
pmid = "32735606"  # Example PMID
relationships = analyzer.analyze_publication(pmid)

# Analyze multiple publications
pmids = ["32735606", "32719766"]
relationships = analyzer.analyze_publications(pmids)

# Save relationships to CSV
analyzer.save_relationships_to_csv(relationships, "variant_relationships.csv")

# Save relationships to JSON
analyzer.save_relationships_to_json(relationships, "variant_relationships.json")
```

### Filtering Results

```python
# Filter relationships by gene
braf_relationships = analyzer.filter_relationships_by_entity(relationships, "gene", "BRAF")

# Filter relationships by disease
cancer_relationships = analyzer.filter_relationships_by_entity(relationships, "disease", "Melanoma")

# Filter relationships by entity ID
gene_id_relationships = analyzer.filter_relationships_by_entity(relationships, "gene", "673")  # BRAF gene ID
```

## Output Format

### CSV Output

The CSV output contains the following columns:
- `pmid`: PubMed ID of the publication
- `variant_text`: Text of the variant
- `variant_offset`: Offset position of the variant in the text
- `variant_id`: Identifier for the variant
- `gene_text`: Text of the co-occurring gene
- `gene_id`: Identifier for the gene
- `disease_text`: Text of the co-occurring disease
- `disease_id`: Identifier for the disease
- `tissue_text`: Text of the co-occurring tissue
- `tissue_id`: Identifier for the tissue
- `passage_text`: The text of the passage where the co-occurrence was found

### JSON Output

The JSON output provides more detailed information with the following structure:
```json
[
  {
    "pmid": "32735606",
    "variant_text": "V600E",
    "variant_offset": 100,
    "variant_id": "p.Val600Glu",
    "genes": [
      {"text": "BRAF", "id": "673", "offset": 50}
    ],
    "diseases": [
      {"text": "Melanoma", "id": "D008545", "offset": 75}
    ],
    "tissues": [],
    "species": [],
    "chemicals": [],
    "passage_text": "The BRAF gene with V600E mutation is associated with Melanoma."
  }
]
```

## Requirements

- Python 3.6+
- bioc
- requests

## Related Projects

- [PubTator Client](https://github.com/yourusername/pubtator-client): The underlying client for accessing the PubTator3 API

## License

This project is licensed under the MIT License - see the LICENSE file for details. 