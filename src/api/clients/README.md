# ClinVar Client

The ClinVar API client for integration with the coordinates_lit tool, enabling the search and analysis of genetic variants.

## Features

- Retrieving information about variants based on ClinVar identifiers (VCV, RCV)
- Searching for variants by genomic coordinates
- Searching for variants for specific genes
- Searching for variants by rs identifiers (dbSNP)
- Searching for variants with a specific clinical significance
- Searching for variants associated with phenotypes
- Integration of ClinVar data with coordinates from coordinates_lit

## Requirements

- Python 3.6+
- requests
- logging

## Usage Examples

### Client Initialization

```python
from src.clinvar_client.clinvar_client import ClinVarClient

# Initializing the client with an email address (required by NCBI)
client = ClinVarClient(email="your.email@domain.com")

# Optionally with an API key for increased query limit
client = ClinVarClient(email="your.email@domain.com", api_key="your_api_key")
```

### Retrieving Variant Information by ID

```python
# Retrieving variant information in JSON format
variant_info = client.get_variant_by_id("VCV000124789")
print(f"Clinical significance: {variant_info['clinical_significance']}")

# Retrieving variant information in XML format
variant_info_xml = client.get_variant_by_id("VCV000124789", format_type="xml")
```

### Searching for Variants by Genomic Coordinates

```python
# Searching for variants in a chromosomal region
variants = client.search_by_coordinates(chromosome="1", start=100000, end=200000)
for variant in variants:
    print(f"Variant: {variant['name']} - {variant['clinical_significance']}")
```

### Searching for Variants by Gene

```python
# Searching for variants for the BRCA1 gene
brca1_variants = client.search_by_gene("BRCA1")
print(f"Found {len(brca1_variants)} variants for the BRCA1 gene")
```

### Searching by Clinical Significance

```python
# Searching for pathogenic variants
pathogenic_variants = client.search_by_clinical_significance("pathogenic")

# Searching for variants with multiple clinical significances
variants = client.search_by_clinical_significance(["pathogenic", "likely pathogenic"])
```

### Integration with coordinates_lit

```python
# Example data from coordinates_lit
coordinates_data = [
    {"chromosome": "1", "start": 100000, "end": 200000, "source": "Publication 1"},
    {"chromosome": "X", "start": 30000000, "end": 31000000, "source": "Publication 2"}
]

# Integrating ClinVar data with coordinates
enriched_data = client.integrate_with_coordinates_lit(coordinates_data)

# Analyzing the results
for entry in enriched_data:
    print(f"Region: {entry['chromosome']}:{entry['start']}-{entry['end']}")
    print(f"Source: {entry['source']}")
    print(f"Number of ClinVar variants: {len(entry['clinvar_data'])}")
```

## Error Handling

The ClinVar client implements a set of custom exceptions for different types of errors:

- `ClinVarError` - Base exception for all errors
- `APIRequestError` - Errors during API request execution
- `InvalidFormatError` - Unsupported response formats
- `ParseError` - Errors parsing the response
- `InvalidParameterError` - Invalid query parameters
- `RateLimitError` - Exceeding the API query limit

## Notes

- The NCBI E-utilities API requires the user's email address.
- To increase the query limit (from 3 to 10 per second), an NCBI API key can be registered.
- The client supports responses in JSON and XML formats.
- Implementation of automatic retry in case of server errors or rate limits. 