# src/generator/llm.py
from typing import List, Dict, Any, Optional
from utils.logger import logger
import openai
from config.settings import Config
from src.retriever.models import QueryResult

class ResponseGenerator:
    """Génération de réponses avec le LLM"""
    
    def __init__(self):
        self.config = Config.get_openai_config()
        self.client = openai.OpenAI(api_key=self.config["api_key"])
        self.model = self.config["llm_model"]
        self.logger = logger
    
    async def generate_response(self, 
                              query: str,
                              context_docs: List[QueryResult],
                              max_tokens: int = 1000,
                              temperature: float = 0.7) -> Optional[str]:
        """
        Génère une réponse à partir de la requête et du contexte
        
        Args:
            query: Question de l'utilisateur
            context_docs: Documents de contexte
            max_tokens: Nombre maximum de tokens pour la réponse
            temperature: Température pour la génération
            
        Returns:
            Réponse générée ou None en cas d'erreur
        """
        try:
            # Préparation du contexte
            context = self._prepare_context(context_docs)
            
            # Construction du prompt
            prompt = self._build_prompt(query, context)
            
            # Génération de la réponse
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return None
    
    async def generate_completion(self, system_prompt: str, user_prompt: str) -> str:
        """
        Génère une réponse simple basée sur un prompt système et utilisateur
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Température basse pour des réponses plus précises
                max_tokens=200    # Limite la longueur de la reformulation
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error in completion generation: {str(e)}")
            exit(1)  # Arrêt du programme en cas d'erreur pour éviter de générer des réponses incorrectes
            raise

    def _prepare_context(self, context_docs: List[QueryResult]) -> str:
        """Prépare le contexte à partir des documents"""
        context_parts = []
        
        for doc in context_docs:
            # Ajout des métadonnées pertinentes
            meta_str = f"Source: {doc.metadata.get('source', 'Unknown')}"
            if 'page' in doc.metadata:
                meta_str += f", Page: {doc.metadata['page']}"
            
            # Ajout du contenu avec score de confiance
            context_parts.append(
                f"{meta_str}\n"
                f"Relevance Score: {doc.similarity_score:.2f}\n"
                f"Content: {doc.content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Retourne le prompt système"""
        return """You are a helpful AI assistant. Format your answers using Markdown.
        Follow these guidelines:
        1. Only use information provided in the context
        2. If the context doesn't contain enough information, acknowledge this
        3. Cite sources when possible
        4. Be concise but thorough
        5. If there are contradictions in the context, point them out
        6. Maintain a professional and helpful tone
        7. Use Markdown formatting:
           - Use **bold** for emphasis
           - Use bullet points for lists
           - Use numbered lists when sequence matters
           - Use > for quotes, and provide the source
           - Use proper line breaks between paragraphs (double space)"""
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Construit le prompt final"""
        return f"""Please answer the following question based on the provided context.

Question: {query}

Context:
{context}

Answer:"""