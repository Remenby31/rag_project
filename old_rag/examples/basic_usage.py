# examples/basic_usage.py
import asyncio
from utils.logger import logger
from typing import List, Optional, Union

from src.document_processor.loader import DocumentLoader
from src.document_processor.cleaner import DocumentCleaner, CleaningConfig
from src.document_processor.chunker import DocumentChunker, ChunkingConfig
from src.embeddings.engine import EmbeddingEngine
from src.vector_store.database import VectorStore
from src.vector_store.indexer import Indexer
from src.retriever.query import QueryProcessor
from src.generator.llm import ResponseGenerator

class RAGPipeline:
    """Pipeline complet pour le système RAG"""
    
    def __init__(self):
        # Configuration du logging
        self.logger = logger
        
        # Initialisation des composants
        self.document_loader = DocumentLoader()
        self.document_cleaner = DocumentCleaner(
            CleaningConfig(
                remove_urls=True,
                remove_email=True,
                normalize_whitespace=True,
                min_length=50
            )
        )
        self.document_chunker = DocumentChunker(
            ChunkingConfig(
                chunk_size=1000,
                chunk_overlap=200,
                split_by_sentence=True
            )
        )
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore("my_rag_collection")
        self.indexer = Indexer(
            embedding_engine=self.embedding_engine,
            vector_store=self.vector_store
        )
        self.query_processor = QueryProcessor(
            embedding_engine=self.embedding_engine,
            vector_store=self.vector_store,
            max_results=20,
            similarity_threshold=0
        )
        self.response_generator = ResponseGenerator()
    
    async def index_documents(self, documents: Union[List[str], List[dict]]) -> bool:
        """
        Indexe une liste de documents ou de chemins de documents
        
        Args:
            documents: Liste des chemins vers les documents ou documents déjà formatés
            
        Returns:
            bool: Succès de l'opération
        """
        try:
            if all(isinstance(doc, str) for doc in documents):
                # Si ce sont des chemins de fichiers
                self.logger.info("Loading documents...")
                documents = self.document_loader.load(documents)
                
                # Nettoyage des documents
                self.logger.info("Cleaning documents...")
                cleaned_documents = self.document_cleaner.clean_documents(documents)
                
                # Chunking des documents
                self.logger.info("Chunking documents...")
                chunked_documents = self.document_chunker.create_chunks(cleaned_documents)
            else:
                # Si ce sont des documents déjà formatés
                chunked_documents = documents

            # Indexation
            self.logger.info("Indexing documents...")
            success = await self.indexer.index_documents(chunked_documents)
            
            if success:
                self.logger.info("Documents successfully indexed")
            else:
                self.logger.error("Failed to index documents")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in indexing pipeline: {str(e)}")
            return False
    
    async def query(self, question: str) -> Optional[str]:
        """
        Traite une question et génère une réponse
        
        Args:
            question: Question de l'utilisateur
            
        Returns:
            str: Réponse générée ou None en cas d'erreur
        """
        try:
            # 1. Recherche des documents pertinents
            self.logger.info("Processing query...")
            relevant_docs = await self.query_processor.process_query(question)
            
            if not relevant_docs:
                return "Je n'ai pas trouvé de documents pertinents pour répondre à votre question."
            
            # 2. Génération de la réponse
            self.logger.info("Generating response...")
            response = await self.response_generator.generate_response(
                query=question,
                context_docs=relevant_docs
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in query pipeline: {str(e)}")
            return None

# Exemple d'utilisation
async def main():
    # Création du pipeline
    rag = RAGPipeline()
    
    # Indexation des documents
    documents_to_index = [
        "path/to/document1.pdf",
        "path/to/document2.txt",
        "path/to/folder_with_documents"
    ]
    
    success = await rag.index_documents(documents_to_index)
    if not success:
        print("Failed to index documents")
        return
    
    # Exemple de requête
    question = "Quelle est la différence entre X et Y?"
    response = await rag.query(question)
    
    if response:
        print(f"Question: {question}")
        print(f"Réponse: {response}")
    else:
        print("Failed to generate response")

if __name__ == "__main__":
    asyncio.run(main())