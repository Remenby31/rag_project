# src/document_processor/cleaner.py
import re
from typing import List, Dict, Any
from utils.logger import logger
from dataclasses import dataclass
from src.document_processor.loader import Document

@dataclass
class CleaningConfig:
    """Configuration pour le nettoyage des documents"""
    remove_urls: bool = True
    remove_email: bool = True
    remove_phone: bool = True
    normalize_whitespace: bool = True
    min_length: int = 50
    remove_special_chars: bool = True
    lowercase: bool = False

class DocumentCleaner:
    """Classe pour nettoyer et prétraiter les documents"""
    
    def __init__(self, config: CleaningConfig = None):
        self.config = config or CleaningConfig()
        self.logger = logger
    
    def clean_documents(self, documents: List[Document]) -> List[Document]:
        """Nettoie une liste de documents"""
        cleaned_documents = []
        
        for doc in documents:
            try:
                cleaned_content = self._clean_text(doc.content)
                if self._is_valid_content(cleaned_content):
                    cleaned_doc = Document(
                        content=cleaned_content,
                        metadata={**doc.metadata, 'cleaned': True}
                    )
                    cleaned_documents.append(cleaned_doc)
                else:
                    self.logger.warning(f"Document {doc.doc_id} skipped: content too short or invalid")
            except Exception as e:
                self.logger.error(f"Error cleaning document {doc.doc_id}: {str(e)}")
                continue
        
        return cleaned_documents
    
    def _clean_text(self, text: str) -> str:
        """Applique les règles de nettoyage au texte"""
        if not text:
            return ""
        
        # Copie du texte original
        cleaned = text
        
        # Suppression des URLs
        if self.config.remove_urls:
            cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                           ' ', cleaned)
        
        # Suppression des emails
        if self.config.remove_email:
            cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', ' ', cleaned)
        
        # Suppression des numéros de téléphone
        if self.config.remove_phone:
            cleaned = re.sub(r'\+?[\d\s-]{10,}', ' ', cleaned)
        
        # Suppression des caractères spéciaux
        if self.config.remove_special_chars:
            cleaned = re.sub(r'[^\w\s.,!?-]', ' ', cleaned)
        
        # Normalisation des espaces
        if self.config.normalize_whitespace:
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = cleaned.strip()
        
        # Conversion en minuscules
        if self.config.lowercase:
            cleaned = cleaned.lower()
        
        return cleaned
    
    def _is_valid_content(self, content: str) -> bool:
        """Vérifie si le contenu nettoyé est valide"""
        if not content:
            return False
            
        if len(content.split()) < self.config.min_length:
            return False
            
        return True