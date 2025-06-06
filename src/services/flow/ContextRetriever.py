from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from getpass import getpass
import yaml
import os
from src.utils.config.config import Config


config = Config()

class ContextRetriever:
    # TODO EXPAND WITH GIVING THE LOCATION IN THE TEXT
    prompt = f"""
    SYSTEM:
    
    You are a context retriever. Your task is to extract context regarding specific genomic coordinate from a text. 
    Extract the context of the coordinate given in the section COORDINATE from the text provided in the section 
    PUBLICATION. Please extract all the sentences strictly regarding this coordinate. Try to stick to the close 
    context of the coordinate, but also include relevant sentences from the further context."""

    def __init__(self, llm):
        self.llm = llm

    def extract_context_from_coordinate(self, publication_text: str, coordinate: str):
        model_response = self.ask_model(self.prompt, publication_text, coordinate)
        return self.preprocess_model_response(model_response)

    def preprocess_model_response(self, model_response: str):
        # TODO EXPAND WITH LOCATION IN THE TEXT
        return model_response

    def ask_model(self, system_prompt: str, publication_text: str, coordinate: str):
        prompt = ChatPromptTemplate.from_template("{system} \nPUBLICATION: {publication} \nCOORDINATE: {coordinate}")
        llm_chain = LLMChain(llm=self.llm, prompt=prompt)
        return llm_chain.run({
            "system": system_prompt,
            "publication": publication_text,
            "coordinate": coordinate
        })
