# src/embeddings/engine.py
from typing import List, Dict, Any, Optional
import numpy as np
from utils.logger import logger
from tqdm import tqdm
import openai
from config.settings import Config, EMBEDDING_BATCH_SIZE 
from src.document_processor.loader import Document
from src.embeddings.cache import EmbeddingCache

class EmbeddingEngine:
    """Moteur de génération d'embeddings utilisant OpenAI"""
    
    def __init__(self, batch_size: int = EMBEDDING_BATCH_SIZE):
        self.config = Config.get_openai_config()
        self.batch_size = batch_size
        self.client = openai.OpenAI(api_key=self.config["api_key"])
        self.model = self.config["embedding_model"]
        self.logger = logger
        self.cache = EmbeddingCache()
        
    async def generate_embeddings(self, documents: List[Document], 
                                use_cache: bool = True) -> Dict[str, np.ndarray]:
        """
        Génère les embeddings pour une liste de documents
        
        Args:
            documents: Liste de documents
            use_cache: Utiliser le cache d'embeddings
            
        Returns:
            Dictionnaire {doc_id: embedding}
        """
        embeddings = {}
        documents_to_process = []
        
        self.logger.debug(f"Starting embedding generation for {len(documents)} documents")
        
        # Vérification du cache
        if use_cache:
            for doc in documents:
                cached_embedding = self.cache.get(doc.doc_id)
                if cached_embedding is not None:
                    self.logger.debug(f"Found cached embedding for doc_id: {doc.doc_id}")
                    embeddings[doc.doc_id] = cached_embedding
                else:
                    self.logger.debug(f"No cache found for doc_id: {doc.doc_id}")
                    documents_to_process.append(doc)
        else:
            documents_to_process = documents
        
        self.logger.debug(f"Documents to process: {len(documents_to_process)}")
        
        if not documents_to_process:
            return embeddings
        
        # Traitement par lots
        for batch_start in tqdm(range(0, len(documents_to_process), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(documents_to_process))
            batch = documents_to_process[batch_start:batch_end]
            
            try:
                batch_embeddings = await self._generate_batch_embeddings(batch)
                embeddings.update(batch_embeddings)
                
                # Mise en cache
                if use_cache:
                    for doc_id, embedding in batch_embeddings.items():
                        self.cache.add(doc_id, embedding)
                
            except Exception as e:
                self.logger.error(f"Error generating embeddings for batch {batch_start}-{batch_end}: {str(e)}")
                continue
        
        return embeddings
    
    async def _generate_batch_embeddings(self, documents: List[Document]) -> Dict[str, np.ndarray]:
        """Génère les embeddings pour un lot de documents"""
        texts = [doc.content for doc in documents]
        try:
            self.logger.debug(f"Sending batch of {len(texts)} texts to OpenAI API")
            self.logger.debug(f"First text sample: {texts[0][:100]}...")
            
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            self.logger.debug(f"Received response from OpenAI with {len(response.data)} embeddings")
            
            # Construction du dictionnaire de résultats
            embeddings = {}
            for doc, emb_data in zip(documents, response.data):
                embedding = np.array(emb_data.embedding)
                self.logger.debug(f"Generated embedding for doc_id {doc.doc_id}: shape={embedding.shape}, norm={np.linalg.norm(embedding)}")
                embeddings[doc.doc_id] = embedding
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            raise
    
    def get_embedding_dimension(self) -> int:
        """Retourne la dimension des embeddings pour le modèle utilisé"""
        # text-embedding-3-large = 3072 dimensions
        # Ajoutez d'autres modèles si nécessaire
        dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536
        }
        return dimensions.get(self.model, 3072)