# src/vector_store/database.py
from typing import List, Dict, Any, Optional, Tuple
from utils.logger import logger
import chromadb
from chromadb.config import Settings
import chromadb.errors
import numpy as np
from src.document_processor.loader import Document
from config.settings import Config

class VectorStore:
    """Gestion de la base de données vectorielle avec ChromaDB"""
    
    def __init__(self, collection_name: str = "rag_collection"):
        self.config = Config.get_vector_db_config()
        self.collection_name = collection_name
        self.logger = logger
        
        # Initialisation de ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.config["path"],
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Création ou récupération de la collection
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Récupère ou crée une collection"""
        try:
            return self.client.get_collection(self.collection_name)
        except chromadb.errors.InvalidCollectionException:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Utilisation de la similarité cosinus
            )
    
    def add_documents(self, documents: List[Document], 
                     embeddings: Dict[str, np.ndarray]) -> bool:
        """
        Ajoute des documents et leurs embeddings à la base
        
        Args:
            documents: Liste de documents
            embeddings: Dictionnaire {doc_id: embedding}
            
        Returns:
            bool: Succès de l'opération
        """
        try:
            # Préparation des données pour ChromaDB
            ids = []
            documents_content = []
            metadatas = []
            embeddings_list = []
            
            for doc in documents:
                if doc.doc_id not in embeddings:
                    self.logger.warning(f"No embedding found for document {doc.doc_id}")
                    continue
                    
                ids.append(doc.doc_id)
                documents_content.append(doc.content)
                metadatas.append(doc.metadata)
                embeddings_list.append(embeddings[doc.doc_id].tolist())
            
            # Ajout par lots pour optimiser les performances
            batch_size = 1000
            for i in range(0, len(ids), batch_size):
                end_idx = min(i + batch_size, len(ids))
                self.collection.add(
                    ids=ids[i:end_idx],
                    documents=documents_content[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    embeddings=embeddings_list[i:end_idx]
                )
            
            self.logger.info(f"Successfully added {len(ids)} documents to the vector store")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {str(e)}")
            return False
    
    def search(self, query_embedding: np.ndarray, 
              n_results: int = 5, 
              filter_dict: Optional[Dict] = None,
              similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """
        Recherche les documents les plus similaires
        
        Args:
            query_embedding: Embedding de la requête
            n_results: Nombre de résultats à retourner
            filter_dict: Filtres à appliquer sur les métadonnées
            similarity_threshold: Seuil minimal de similarité
            
        Returns:
            Liste de documents avec leurs scores
        """
        try:
            self.logger.debug(f"Starting vector search with query embedding shape: {query_embedding.shape}")
            self.logger.debug(f"Search parameters: n_results={n_results}, threshold={similarity_threshold}")
            if filter_dict:
                self.logger.debug(f"Applying filters: {filter_dict}")

            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where=filter_dict,
                include=["documents", "metadatas", "distances"]
            )
            
            self.logger.debug(f"Raw search results: {len(results['ids'][0])} matches found")
            self.logger.debug(f"Distance scores: {results['distances'][0]}")
            
            # Transformation des résultats
            documents = []
            for i in range(len(results['ids'][0])):
                similarity_score = 1 - results['distances'][0][i]
                self.logger.debug(f"Document {results['ids'][0][i]}: similarity={similarity_score:.4f}")
                
                if similarity_threshold and similarity_score < similarity_threshold:
                    self.logger.debug(f"Skipping document {results['ids'][0][i]}: below threshold")
                    continue
                
                doc = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': similarity_score
                }
                documents.append(doc)
                self.logger.debug(f"Added document to results: {doc['id']}")
            
            self.logger.debug(f"Final filtered results: {len(documents)} documents")
            return documents
            
        except Exception as e:
            self.logger.error(f"Error during vector search: {str(e)}", exc_info=True)
            return []
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un document par son ID"""
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if not result['documents']:
                return None
                
            return {
                'id': doc_id,
                'content': result['documents'][0],
                'metadata': result['metadatas'][0]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting document {doc_id}: {str(e)}")
            return None
    
    def delete_documents(self, doc_ids: List[str]) -> bool:
        """Supprime des documents par leurs IDs"""
        try:
            self.collection.delete(ids=doc_ids)
            self.logger.info(f"Successfully deleted {len(doc_ids)} documents")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting documents: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la collection"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name
            }
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {str(e)}")
            return {}

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques détaillées sur la collection"""
        try:
            stats = {
                "total_documents": self.collection.count(),
                "collection_name": self.collection_name,
            }
            
            # Récupérer un échantillon pour vérifier la structure
            peek = self.collection.peek()
            if peek and peek['ids']:
                stats.update({
                    "sample_document_id": peek['ids'][0],
                    "has_embeddings": peek.get('embeddings') is not None,
                    "embedding_dim": len(peek['embeddings'][0]) if peek.get('embeddings') is not None else None
                })
            
            self.logger.info(f"Collection stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting detailed stats: {str(e)}", exc_info=True)
            return {}