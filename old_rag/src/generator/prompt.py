# src/generator/prompt.py
from typing import Dict, Any, List
from string import Template

class PromptTemplates:
    """Collection de templates pour les prompts"""
    
    @staticmethod
    def get_qa_template() -> Template:
        """Template pour les questions-réponses"""
        return Template("""Répondez à la question suivante en vous basant uniquement sur le contexte fourni.

Question: $question

Contexte:
$context

Instructions:
1. Utilisez uniquement les informations du contexte
2. Si le contexte est insuffisant, indiquez-le clairement
3. Citez vos sources
4. Soyez concis mais précis

Réponse:""")
    
    @staticmethod
    def get_summary_template() -> Template:
        """Template pour les résumés"""
        return Template("""Faites un résumé du texte suivant:

$context

Instructions:
1. Le résumé doit être concis mais informatif
2. Gardez les informations essentielles
3. Structurez le résumé de manière logique

Résumé:""")

class PromptBuilder:
    """Constructeur de prompts"""
    
    def __init__(self):
        self.templates = PromptTemplates()
    
    def build_qa_prompt(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        """Construit un prompt pour les questions-réponses"""
        # Préparation du contexte
        context_parts = []
        for doc in context_docs:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            
            context_parts.append(f"Source: {source}\n{content}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Construction du prompt final
        template = self.templates.get_qa_template()
        return template.substitute(
            question=question,
            context=context
        )
    
    def build_summary_prompt(self, context: str) -> str:
        """Construit un prompt pour les résumés"""
        template = self.templates.get_summary_template()
        return template.substitute(context=context)