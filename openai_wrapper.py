import logging
from openai import OpenAI

class OpenAIEmbeddingsWrapper:
    def __init__(self, model="text-embedding-3-small"):
        self.client = OpenAI()
        self.model = model

    def embed_documents(self, texts):
        """Embed a list of texts."""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logging.error(f"Erreur lors de l'embedding OpenAI: {str(e)}")
            raise e

    def embed_query(self, text):
        """Embed a single text."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Erreur lors de l'embedding OpenAI: {str(e)}")
            raise e