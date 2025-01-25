# src/document_processor/chunker.py
from typing import List
from utils.logger import logger
from dataclasses import dataclass
from src.document_processor.loader import Document
from config.settings import Config
import re
import tiktoken

@dataclass
class ChunkingConfig:
    """Configuration pour le chunking des documents"""
    chunk_size: int = Config.get_document_config()["chunk_size"]
    chunk_overlap: int = Config.get_document_config()["chunk_overlap"]
    split_by_sentence: bool = True
    respect_paragraph: bool = True
    max_chunks_per_doc: int = 100

class DocumentChunker:
    """Classe pour découper les documents en chunks"""
    
    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()
        self.logger = logger
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def create_chunks(self, documents: List[Document]) -> List[Document]:
        """Découpe une liste de documents en chunks"""
        chunked_documents = []
        
        for doc in documents:
            try:
                chunks = self._chunk_document(doc)
                chunked_documents.extend(chunks)
                self.logger.info(f"Created {len(chunks)} chunks from document {doc.doc_id}")
            except Exception as e:
                self.logger.error(f"Error chunking document {doc.doc_id}: {str(e)}")
                continue
        
        return chunked_documents
    
    def _chunk_document(self, document: Document) -> List[Document]:
        """Découpe un document en chunks"""
        content = document.content
        
        # Séparation en paragraphes si demandé
        if self.config.respect_paragraph:
            paragraphs = self._split_into_paragraphs(content)
        else:
            paragraphs = [content]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            # Séparation en phrases si demandé
            if self.config.split_by_sentence:
                sentences = self._split_into_sentences(paragraph)
            else:
                sentences = [paragraph]
            
            for sentence in sentences:
                sentence_size = len(self.tokenizer.encode(sentence))
                
                # Si la phrase seule dépasse la taille maximale, on la découpe
                if sentence_size > self.config.chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk_document(
                            " ".join(current_chunk), 
                            document, 
                            len(chunks)
                        ))
                        current_chunk = []
                        current_size = 0
                    
                    sub_chunks = self._split_long_sentence(sentence)
                    for sub_chunk in sub_chunks:
                        chunks.append(self._create_chunk_document(
                            sub_chunk, 
                            document, 
                            len(chunks)
                        ))
                    continue
                
                # Si l'ajout de la phrase dépasse la taille maximale
                if current_size + sentence_size > self.config.chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk_document(
                            " ".join(current_chunk), 
                            document, 
                            len(chunks)
                        ))
                        
                        # Gestion du chevauchement
                        if self.config.chunk_overlap > 0:
                            overlap_size = 0
                            overlap_chunk = []
                            
                            for s in reversed(current_chunk):
                                s_size = len(self.tokenizer.encode(s))
                                if overlap_size + s_size <= self.config.chunk_overlap:
                                    overlap_chunk.insert(0, s)
                                    overlap_size += s_size
                                else:
                                    break
                            
                            current_chunk = overlap_chunk
                            current_size = overlap_size
                        else:
                            current_chunk = []
                            current_size = 0
                
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Dernier chunk
        if current_chunk:
            chunks.append(self._create_chunk_document(
                " ".join(current_chunk), 
                document, 
                len(chunks)
            ))
        
        # Limitation du nombre de chunks si nécessaire
        if len(chunks) > self.config.max_chunks_per_doc:
            chunks = chunks[:self.config.max_chunks_per_doc]
            self.logger.warning(f"Document {document.doc_id} truncated to {self.config.max_chunks_per_doc} chunks")
        
        return chunks
    
    def _create_chunk_document(self, content: str, original_doc: Document, chunk_index: int) -> Document:
        """Crée un nouveau Document pour un chunk"""
        return Document(
            content=content,
            metadata={
                **original_doc.metadata,
                'chunk_index': chunk_index,
                'original_doc_id': original_doc.doc_id,
                'is_chunk': True
            }
        )
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Divise le texte en paragraphes"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return paragraphs
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divise le texte en phrases"""
        # Regex simplifiée pour la séparation en phrases
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Découpe une phrase trop longue"""
        words = sentence.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(self.tokenizer.encode(word))
            
            if current_size + word_size > self.config.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks