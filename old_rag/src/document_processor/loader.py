# src/document_processor/loader.py
from typing import List, Union, Dict
from pathlib import Path
from utils.logger import logger
from dataclasses import dataclass
import mimetypes
import hashlib

@dataclass
class Document:
    """Classe représentant un document"""
    content: str
    metadata: Dict
    doc_id: str = None
    
    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique basé sur le contenu"""
        return hashlib.sha256(
            f"{self.content}{str(self.metadata)}".encode()
        ).hexdigest()[:16]

class DocumentLoader:
    """Classe pour charger les documents depuis différentes sources"""
    
    def __init__(self, logging_enabled: bool = True):
        self.logger = logger
    
    def load(self, source: Union[str, Path, List[Union[str, Path]]]) -> List[Document]:
        """
        Charge les documents depuis différentes sources
        
        Args:
            source: Chemin du fichier ou dossier, ou liste de chemins
            
        Returns:
            Liste de Documents
        """
        if isinstance(source, (str, Path)):
            sources = [source]
        else:
            sources = source
            
        documents = []
        for src in sources:
            try:
                docs = self._load_single_source(src)
                documents.extend(docs)
                self.logger.info(f"Loaded {len(docs)} documents from {src}")
            except Exception as e:
                self.logger.error(f"Error loading {src}: {str(e)}")
                continue
                
        return documents
    
    def _load_single_source(self, source: Union[str, Path]) -> List[Document]:
        """Charge un document depuis une source unique"""
        source = Path(source)
        
        if not source.exists():
            raise FileNotFoundError(f"Source {source} does not exist")
            
        if source.is_dir():
            return self._load_directory(source)
        else:
            return self._load_file(source)
    
    def _load_directory(self, directory: Path) -> List[Document]:
        """Charge tous les documents d'un répertoire"""
        documents = []
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    docs = self._load_file(file_path)
                    documents.extend(docs)
                except Exception as e:
                    self.logger.error(f"Error loading {file_path}: {str(e)}")
                    continue
        return documents
    
    def _load_file(self, file_path: Path) -> List[Document]:
        """Charge un fichier unique"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type is None:
            raise ValueError(f"Unsupported file type: {file_path}")
            
        if mime_type.startswith('text/'):
            return self._load_text_file(file_path)
        elif mime_type == 'application/pdf':
            return self._load_pdf_file(file_path)
        # Ajoutez d'autres types de fichiers selon vos besoins
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
    
    def _load_text_file(self, file_path: Path) -> List[Document]:
        """Charge un fichier texte"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {
                'source': str(file_path),
                'type': 'text',
                'size': file_path.stat().st_size,
                'created': file_path.stat().st_ctime,
                'modified': file_path.stat().st_mtime
            }
            
            return [Document(content=content, metadata=metadata)]
        
        except Exception as e:
            self.logger.error(f"Error reading text file {file_path}: {str(e)}")
            raise
    
    def _load_pdf_file(self, file_path: Path) -> List[Document]:
        """Charge un fichier PDF"""
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(str(file_path))
            documents = []
            
            for i, page in enumerate(reader.pages):
                content = page.extract_text()
                
                if not content.strip():
                    continue
                
                metadata = {
                    'source': str(file_path),
                    'type': 'pdf',
                    'page': i + 1,
                    'total_pages': len(reader.pages),
                    'size': file_path.stat().st_size,
                    'created': file_path.stat().st_ctime,
                    'modified': file_path.stat().st_mtime
                }
                
                documents.append(Document(content=content, metadata=metadata))
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error reading PDF file {file_path}: {str(e)}")
            raise