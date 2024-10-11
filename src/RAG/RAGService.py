import os
import lancedb
import obonet
import yaml

from src.RAG.Embedder import Embedder

with open("../config/config.yaml", "r") as file:
    config = yaml.safe_load(file)


class RAGService:
    def __init__(self, setup=True):
        self.embedder = Embedder()
        self.connect_lancedb()
        self.setup_retriever() if setup else self.open_retriever()

    def parse_obo(self, file_path):
        graph = obonet.read_obo(file_path)
        data = []
        for id_, data_ in graph.nodes(data=True):
            term = {
                'id': id_,
                'name': data_.get('name', ''),
                'definition': data_.get('def', ''),
                # 'synonyms': ', '.join(data_.get('synonym', [])),
                # 'xref': data_.get('xref', ''),
                # 'parent_id': data_.get('is_a'),
                # 'parent_name': data_.get('is_a'),
                'comment': data_.get('comment')
            }
            term['vector'] = self.embedder.embed(f"""
                NAME:
                    {term.get('name')}
                DEFINITION:
                    {term.get('definition')}
                COMMENT:
                     {term.get('comment')}
            """)
                # SYNONYMS:
                #     {term.get('synonyms')}
                # PARENT_NAME:
                #     {term.get('parent_name')}
            # """)
            data.append(term)
        return data

    def connect_lancedb(self):
        lancedb_path = str(os.path.join(config['base_dir'], config['paths']['lancedb_path']))
        self.db = lancedb.connect(lancedb_path)

    def setup_retriever(self):
        obo_path = os.path.join(config['base_dir'], config['paths']['so_obo'])

        data = self.parse_obo(obo_path)
        self.table = self.db.create_table("ontology_data", data, mode='overwrite')

    def open_retriever(self):
        self.table = self.db.open_table("ontology_data")

    def vector_search(self, query, limit=10):
        return self.table.search(self.embedder.embed(query)) \
            .limit(limit) \
            .select(['name', 'definition', 'comment']) \
            .to_list()
