# src/retriever/query.py
from typing import List, Dict, Any, Optional
from utils.logger import logger
from src.embeddings.engine import EmbeddingEngine
from src.vector_store.database import VectorStore
from src.document_processor.loader import Document
from src.generator.llm import ResponseGenerator
from src.retriever.models import QueryResult

class QueryProcessor:
    """Traitement des requêtes et recherche de documents pertinents"""
    
    def __init__(self, embedding_engine: EmbeddingEngine,
                 vector_store: VectorStore,
                 max_results: int = 5,
                 similarity_threshold: float = 0.7):
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.max_results = max_results
        self.similarity_threshold = similarity_threshold
        self.logger = logger
        self.llm = ResponseGenerator()  # Pour reformuler la question

    async def _reformulate_query(self, query: str) -> str:
        """
        Utilise le LLM pour reformuler la requête afin d'améliorer la recherche
        """
        system_prompt = """Tu es un expert en recherche d'information. 
        Reformule la question donnée pour optimiser la recherche documentaire.
        Ajoute des termes pertinents et des synonymes.
        Garde l'essence de la question originale.
        Réponds uniquement avec la reformulation, sans explication."""

        user_prompt = f"""Question originale: {query}
        Reformule cette question en l'enrichissant pour une meilleure recherche documentaire."""

        try:
            reformulated = await self.llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            self.logger.info(f"Question reformulée: {reformulated}")
            return reformulated
        except Exception as e:
            self.logger.warning(f"Erreur lors de la reformulation: {str(e)}")
            return query

    async def process_query(self, query: str,
                          filter_dict: Optional[Dict] = None) -> List[QueryResult]:
        """
        Traite une requête et retourne les documents pertinents
        
        Args:
            query: Requête utilisateur
            filter_dict: Filtres optionnels pour la recherche
            
        Returns:
            Liste de résultats pertinents
        """
        try:
            self.logger.debug(f"Processing query: {query}")
            
            # Reformulation de la requête
            reformulated_query = await self._reformulate_query(query)
            self.logger.debug(f"Reformulated query: {reformulated_query}")
            
            self.logger.debug("Generating query embedding...")
            # Génération de l'embedding de la requête reformulée
            query_embedding_dict = await self.embedding_engine.generate_embeddings(
                [Document(content=reformulated_query, metadata={}, doc_id="query")]
            )
            
            if not query_embedding_dict:
                self.logger.error("Failed to generate query embedding - empty result")
                raise ValueError("Failed to generate query embedding")
                
            query_embedding = list(query_embedding_dict.values())[0]
            self.logger.debug(f"Query embedding shape: {query_embedding.shape}")
            
            self.logger.debug("Searching for similar documents...")
            # Recherche des documents similaires
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=self.max_results,
                filter_dict=filter_dict,
                similarity_threshold=self.similarity_threshold
            )
            
            self.logger.debug(f"Found {len(results)} matching documents")
            for result in results:
                self.logger.debug(f"Match: id={result['id']}, score={result['similarity_score']:.4f}")
            
            # Conversion en QueryResult
            query_results = []
            for result in results:
                query_results.append(QueryResult(
                    content=result['content'],
                    metadata=result['metadata'],
                    similarity_score=result['similarity_score'],
                    doc_id=result['id']
                ))
            
            return query_results
            
        except Exception as e:
            self.logger.error(f"Error processing query: {str(e)}")
            return []
    
    def _rerank_results(self, results: List[QueryResult]) -> List[QueryResult]:
        """
        Réordonne les résultats en fonction de critères supplémentaires
        (à implémenter selon vos besoins spécifiques)
        """
        # Exemple de reranking basé sur une combinaison de score de similarité
        # et d'autres métadonnées
        
        def compute_final_score(result: QueryResult) -> float:
            # Score de base (similarité)
            final_score = result.similarity_score
            
            # Bonus pour les documents plus récents (si timestamp disponible)
            if 'timestamp' in result.metadata:
                age_penalty = 0.1  # À ajuster selon vos besoins
                final_score += age_penalty
            
            # Bonus pour les documents plus longs (si pertinent)
            if 'length' in result.metadata:
                length_bonus = 0.05  # À ajuster selon vos besoins
                final_score += length_bonus
            
            return final_score
        
        # Tri des résultats selon le score final
        results.sort(key=lambda x: compute_final_score(x), reverse=True)
        return results