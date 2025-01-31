# src/embeddings/cache.py
import pickle
from typing import Dict, Optional
import numpy as np
from utils.logger import logger
from pathlib import Path
from config.settings import EMBEDDING_CACHE_PATH

class EmbeddingCache:
    """Système de cache pour les embeddings"""
    
    def __init__(self, cache_path: Path = EMBEDDING_CACHE_PATH):
        self.cache_path = cache_path
        self.cache: Dict[str, np.ndarray] = {}
        self.logger = logger
        self._load_cache()
    
    def _load_cache(self):
        """Charge le cache depuis le disque"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'rb') as f:
                    self.cache = pickle.load(f)
                self.logger.info(f"Loaded {len(self.cache)} embeddings from cache")
            except Exception as e:
                self.logger.error(f"Error loading cache: {str(e)}")
                self.cache = {}
    
    def _save_cache(self):
        """Sauvegarde le cache sur le disque"""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'wb') as f:
                pickle.dump(self.cache, f)
            self.logger.info(f"Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            self.logger.error(f"Error saving cache: {str(e)}")
    
    def get(self, doc_id: str) -> Optional[np.ndarray]:
        """Récupère un embedding depuis le cache"""
        return self.cache.get(doc_id)
    
    def add(self, doc_id: str, embedding: np.ndarray):
        """Ajoute un embedding au cache"""
        self.cache[doc_id] = embedding
        self._save_cache()
    
    def remove(self, doc_id: str):
        """Supprime un embedding du cache"""
        if doc_id in self.cache:
            del self.cache[doc_id]
            self._save_cache()
    
    def clear(self):
        """Vide le cache"""
        self.cache.clear()
        self._save_cache()
    
    def get_size(self) -> int:
        """Retourne la taille du cache"""
        return len(self.cache)
    
    def contains(self, doc_id: str) -> bool:
        """Vérifie si un document est dans le cache"""
        return doc_id in self.cache
    
    def get_memory_usage(self) -> float:
        """Retourne l'utilisation mémoire du cache en MB"""
        total_bytes = sum(embedding.nbytes for embedding in self.cache.values())
        return total_bytes / (1024 * 1024)  # Conversion en MB