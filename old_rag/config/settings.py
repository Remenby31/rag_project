# config/settings.py
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import os

# Chargement des variables d'environnement
load_dotenv()

# Configuration générale
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Configuration OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-4o-mini"

# Configuration du traitement des documents
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_TOKENS_PER_DOC = 4000

# Configuration de la base vectorielle
VECTOR_DB_PATH = BASE_DIR / "vector_db"
VECTOR_DB_PATH.mkdir(exist_ok=True)

# Configuration du logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "rag.log"

# Configuration des embeddings
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_CACHE_PATH = CACHE_DIR / "embeddings_cache.pkl"

# Configuration du système de requêtes
MAX_RELEVANT_CHUNKS = 5
SIMILARITY_THRESHOLD = 0.7

class Config:
    """Classe de configuration centralisée"""
    
    @staticmethod
    def get_openai_config() -> Dict[str, Any]:
        return {
            "api_key": OPENAI_API_KEY,
            "embedding_model": EMBEDDING_MODEL,
            "llm_model": LLM_MODEL
        }
    
    @staticmethod
    def get_document_config() -> Dict[str, Any]:
        return {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "max_tokens": MAX_TOKENS_PER_DOC
        }
    
    @staticmethod
    def get_vector_db_config() -> Dict[str, Any]:
        return {
            "path": str(VECTOR_DB_PATH),
            "similarity_threshold": SIMILARITY_THRESHOLD
        }
    
    @staticmethod
    def get_logging_config() -> Dict[str, Any]:
        return {
            "log_file": str(LOG_FILE)
        }
    
    @staticmethod
    def get_embedding_config() -> Dict[str, Any]:
        return {
            "batch_size": EMBEDDING_BATCH_SIZE,
            "cache_path": str(EMBEDDING_CACHE_PATH)
        }