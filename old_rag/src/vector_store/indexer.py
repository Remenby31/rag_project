# src/vector_store/indexer.py
from typing import List, Dict, Any, Optional
from utils.logger import logger
from src.document_processor.loader import Document
from src.embeddings.engine import EmbeddingEngine
from src.vector_store.database import VectorStore

class Indexer:
    """Gestion de l'indexation des documents"""
    
    def __init__(self, embedding_engine: EmbeddingEngine, 
                 vector_store: VectorStore):
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.logger = logger
    
    async def index_documents(self, documents: List[Document], 
                            batch_size: int = 100) -> bool:
        """
        Indexe une liste de documents
        
        Args:
            documents: Liste de documents à indexer
            batch_size: Taille des lots pour le traitement
            
        Returns:
            bool: Succès de l'opération
        """
        try:
            self.logger.info(f"Starting indexation of {len(documents)} documents")
            
            # Vérification de l'état initial
            initial_stats = self.vector_store.get_detailed_stats()
            self.logger.info(f"Initial collection state: {initial_stats}")
            
            # Génération des embeddings
            embeddings = await self.embedding_engine.generate_embeddings(
                documents, 
                use_cache=True
            )
            self.logger.info(f"Generated {len(embeddings)} embeddings")
            
            if not embeddings:
                self.logger.error("No embeddings generated")
                return False
            
            # Vérification des dimensions
            sample_embedding = next(iter(embeddings.values()))
            self.logger.info(f"Sample embedding dimension: {sample_embedding.shape}")
            
            # Indexation par lots
            success = True
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_embeddings = {
                    doc_id: emb for doc_id, emb in embeddings.items()
                    if doc_id in [doc.doc_id for doc in batch_docs]
                }
                
                if not self.vector_store.add_documents(batch_docs, batch_embeddings):
                    success = False
                    self.logger.error(f"Failed to index batch {i//batch_size + 1}")
            
            # Vérification de l'état final
            final_stats = self.vector_store.get_detailed_stats()
            self.logger.info(f"Final collection state: {final_stats}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error during indexing: {str(e)}", exc_info=True)
            return False
    
    async def update_documents(self, documents: List[Document]) -> bool:
        """Met à jour des documents existants"""
        try:
            # Récupération des IDs
            doc_ids = [doc.doc_id for doc in documents]
            
            # Suppression des anciens documents
            if not self.vector_store.delete_documents(doc_ids):
                return False
            
            # Réindexation des nouveaux documents
            return await self.index_documents(documents)
            
        except Exception as e:
            self.logger.error(f"Error updating documents: {str(e)}")
            return False
    
    def delete_documents(self, doc_ids: List[str]) -> bool:
        """Supprime des documents de l'index"""
        try:
            return self.vector_store.delete_documents(doc_ids)
        except Exception as e:
            self.logger.error(f"Error deleting documents: {str(e)}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un document indexé"""
        return self.vector_store.get_document(doc_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur l'index"""
        return self.vector_store.get_collection_stats()