import pandas as pd
import re


class CsvReader:

    @staticmethod
    def create_queries(row):
        gene_name = re.sub(r'[^a-zA-Z0-9]', '', row['Gene name'].lower())  # Remove non-alphanumeric characters
        queries = []
        if pd.notna(row['Literature']):
            for ref in row['Literature'].split(';'):
                ref = ref.strip()
                parts = ref.split()
                if len(parts) >= 3:
                    # Remove 'et al.' and 'i wsp.' from the author's name
                    if 'et' in parts and 'al.' in parts:
                        etal_index = parts.index('et')
                        first_author_surname = ' '.join(parts[:etal_index])
                    elif 'i' in parts and 'wsp.' in parts:
                        iwsp_index = parts.index('i')
                        first_author_surname = ' '.join(parts[:iwsp_index])
                    else:
                        first_author_surname = ' '.join(
                            parts[:-1])  # Include all parts except the last one as the surname

                    year_of_publication = parts[-1].strip(';,')
                    query = f"{gene_name} {first_author_surname} AND {year_of_publication}[dp]"
                    queries.append(query)
        return queries

    @staticmethod
    def get_list_of_queries(csv_path):
        df = pd.read_csv(csv_path)
        queries = df.apply(CsvReader.create_queries, axis=1)
        return queries.explode().tolist()
