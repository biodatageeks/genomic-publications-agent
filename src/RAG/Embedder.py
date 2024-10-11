from transformers import AutoTokenizer, AutoModel
import torch


class Embedder:

    def __init__(self, model_name="NeuML/pubmedbert-base-embeddings"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed(self, chunk):
        # Tokenize the input text
        tokens = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)

        # Get the model's output (including embeddings)
        with torch.no_grad():
            model_output = self.model(**tokens)

        # Extract the embeddings
        embeddings = model_output.last_hidden_state[:, 0, :]
        embed = embeddings[0].numpy()
        return embed
