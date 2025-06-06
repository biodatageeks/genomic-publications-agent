import os
import lancedb
import yaml

try:
    import obonet
    HAS_OBONET = True
except ImportError:
    HAS_OBONET = False
    obonet = None

from src.analysis.Embedder import Embedder
from src.utils.config.config import Config

try:
    config = Config()
    config_data = config._config  # Access internal config data
except Exception:
    # Fallback config if main Config fails
    config_data = {
        'base_dir': '.',
        'paths': {
            'lancedb_path': 'data/lancedb',
            'so_obo': 'data/so.obo'
        }
    }

class RAGService:
    def __init__(self, setup=True):
        self.embedder = Embedder()
        self.connect_lancedb()
        self.setup_retriever() if setup else self.open_retriever()

    def parse_obo(self, file_path):
        if not HAS_OBONET:
            raise ImportError("obonet is required for parsing OBO files. Install with: pip install obonet")
        
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
        lancedb_path = str(os.path.join(config_data['base_dir'], config_data['paths']['lancedb_path']))
        self.db = lancedb.connect(lancedb_path)

    def setup_retriever(self):
        obo_path = os.path.join(config_data['base_dir'], config_data['paths']['so_obo'])

        data = self.parse_obo(obo_path)
        self.table = self.db.create_table("ontology_data", data, mode='overwrite')

    def open_retriever(self):
        self.table = self.db.open_table("ontology_data")

    def vector_search(self, query, limit=10):
        return self.table.search(self.embedder.embed(query)) \
            .limit(limit) \
            .select(['name', 'definition', 'comment']) \
            .to_list()
