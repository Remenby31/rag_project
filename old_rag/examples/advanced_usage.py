# examples/advanced_usage.py
import asyncio
from typing import Optional
from src.document_processor.cleaner import CleaningConfig, DocumentCleaner
from src.document_processor.chunker import ChunkingConfig, DocumentChunker
from src.vector_store.indexer import VectorStore, Indexer
from src.retriever.query import QueryProcessor
from examples.basic_usage import RAGPipeline

class CustomRAGPipeline(RAGPipeline):
    """Pipeline RAG personnalisé avec des configurations spécifiques"""
    
    def __init__(self, collection_name: str = "custom_collection"):
        super().__init__()
        
        # Personnalisation du nettoyage des documents
        self.document_cleaner = DocumentCleaner(
            CleaningConfig(
                remove_urls=False,  # Garder les URLs
                remove_email=True,
                normalize_whitespace=True,
                min_length=100,  # Documents plus longs
                remove_special_chars=False  # Garder les caractères spéciaux
            )
        )
        
        # Personnalisation du chunking
        self.document_chunker = DocumentChunker(
            ChunkingConfig(
                chunk_size=1500,
                chunk_overlap=300,
                split_by_sentence=True,
                respect_paragraph=True,
                max_chunks_per_doc=150
            )
        )
        
        # Personnalisation de la base vectorielle
        self.vector_store = VectorStore(
            collection_name=collection_name
        )
        
        # Mise à jour des composants qui dépendent de la base vectorielle
        self.indexer = Indexer(
            embedding_engine=self.embedding_engine,
            vector_store=self.vector_store
        )
        
        self.query_processor = QueryProcessor(
            embedding_engine=self.embedding_engine,
            vector_store=self.vector_store,
            max_results=7,  # Plus de résultats
            similarity_threshold=0.6  # Seuil de similarité plus bas
        )
    
    async def query_with_metadata_filter(self, 
                                       question: str,
                                       filter_dict: dict) -> Optional[str]:
        """
        Recherche avec filtrage sur les métadonnées
        
        Args:
            question: Question de l'utilisateur
            filter_dict: Critères de filtrage (ex: {'source': 'document1.pdf'})
            
        Returns:
            str: Réponse générée
        """
        relevant_docs = await self.query_processor.process_query(
            question,
            filter_dict=filter_dict
        )
        
        if not relevant_docs:
            return "Aucun document pertinent trouvé avec les critères spécifiés."
        
        return await self.response_generator.generate_response(
            query=question,
            context_docs=relevant_docs,
            temperature=0.5  # Réponses plus déterministes
        )

# Exemple d'utilisation avancée
async def advanced_demo():
    # Création du pipeline personnalisé
    custom_rag = CustomRAGPipeline("technical_docs")
    
    # Indexation avec plus de détails
    documents_to_index = ["technical_documentation/"]
    print("Indexing technical documentation...")
    success = await custom_rag.index_documents(documents_to_index)
    
    if success:
        print("Documentation indexed successfully")
        
        # Exemple de requête avec filtre
        question = "Comment configurer le système X?"
        filter_dict = {
            'type': 'technical',
            'version': 'latest'
        }
        
        print(f"\nQuestion: {question}")
        print("Applying metadata filters:", filter_dict)
        
        response = await custom_rag.query_with_metadata_filter(
            question,
            filter_dict
        )
        
        print(f"\nRéponse: {response}")
    
    # Affichage des statistiques
    stats = custom_rag.vector_store.get_stats()
    print("\nStatistiques de la base vectorielle:")
    print(f"- Documents indexés: {stats['total_documents']}")
    print(f"- Collection: {stats['collection_name']}")

if __name__ == "__main__":
    asyncio.run(advanced_demo())