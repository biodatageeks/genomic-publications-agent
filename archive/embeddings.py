
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import obonet

# Step 1: Load the OBO file and parse it
file_path = '../../data/sequence-ontology/so-edit.obo'
graph = obonet.read_obo(file_path)

# Step 2: Extract relevant text data from the ontology
terms = []
for id_, data in graph.nodes(data=True):
    name = data.get('name')
    definition = data.get('def')
    if name and definition:
        terms.append(f"{name}: {definition}")

# Step 3: Load a bioinformatics-specific embedding model
model = SentenceTransformer('pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb')

# Step 4: Generate embeddings for the extracted terms
embeddings = model.encode(terms)

# Step 5: Build the FAISS index
d = embeddings.shape[1]  # Dimension of embeddings
index = faiss.IndexFlatL2(d)  # Create a FAISS index
index.add(np.array(embeddings))  # Add embeddings to the index

# Step 6: Save the index and terms for later use
faiss.write_index(index, "../index/ontology_faiss_index.index")
np.save("../../index/ontology_terms.npy", np.array(terms))
