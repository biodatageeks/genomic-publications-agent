from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.llms import OpenAI
import faiss
import numpy as np
import getpass
import os

from src.flow.PubmedEndpoint import PubmedEndpoint

print("Step 1: Load the FAISS index and the terms")
index = faiss.read_index("ontology_faiss_index.index")
terms = np.load("ontology_terms.npy", allow_pickle=True).tolist()

print("Step 2: Load the embedding model and prepare FAISS store")
embedding_model = OpenAIEmbeddings()
faiss_store = FAISS(embedding_model, index, terms)

def chunk_text(text, chunk_size, overlap):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


print("Step 4: Initialize the LangChain components")
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")
memory = ConversationBufferMemory()
llm = OpenAI(model="gpt-4o-mini", temperature=0.7)  # Assuming OpenAI model is accessible
prompt = ChatPromptTemplate.from_template("{question}\n\nContext:\n{context}")


def process_publication(question, publication, chunk_size=1000, overlap=200):
    # Split publication into chunks
    chunks = chunk_text(publication, chunk_size, overlap)

    responses = []
    # Iterate through each chunk, making a query to the model
    for chunk in chunks:
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=faiss_store.as_retriever(),
            memory=memory,
            prompt=prompt
        )
        response = chain.run(input={"question": question, "context": chunk})
        responses.append(response)
    return responses


print("Step 5: Process a publication")

pubmed_id = '24212882'
text = PubmedEndpoint.fetch_text_from_pubmed_id(pubmed_id)
question = ("Please give me all fragments of text (of length circa 25 words) where there are genomic region "
            "coordinates in the format like here or similar: chr10:23508365, chrY:∼124349-409949; chrY:∼134349–439949")
responses = process_publication(question, text)
with open("out/responses.txt", "w+") as file:
    for item in responses:
        file.write("%s\n" % item)
