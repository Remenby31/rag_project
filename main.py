# main.py
import asyncio
import os
from pathlib import Path
from typing import Optional
from examples.basic_usage import RAGPipeline

class RAGInterface:
    def __init__(self, documents_folder: str):
        self.documents_folder = Path(documents_folder)
        self.rag = RAGPipeline()
        
    async def load_documents(self) -> bool:
        """Charge tous les documents du dossier spécifié"""
        if not self.documents_folder.exists():
            print(f"Le dossier {self.documents_folder} n'existe pas!")
            return False
            
        # Récupération de tous les fichiers du dossier
        document_paths = []
        supported_extensions = {'.txt', '.pdf', '.doc', '.docx'}  # Ajoutez les extensions que vous supportez
        
        for file_path in self.documents_folder.rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                document_paths.append(str(file_path))
        
        if not document_paths:
            print("Aucun document compatible trouvé dans le dossier!")
            return False
        
        print(f"Chargement de {len(document_paths)} documents...")
        success = await self.rag.index_documents(document_paths)
        
        if success:
            print("Documents chargés avec succès!")
        else:
            print("Erreur lors du chargement des documents.")
        
        return success
    
    async def ask_question(self, question: str) -> Optional[str]:
        """Pose une question au système RAG"""
        response = await self.rag.query(question)
        return response

async def interactive_mode():
    # Configuration
    docs_folder = "./files"  # Dossier contenant les documents à charger
    rag_interface = RAGInterface(docs_folder)
    
    # Chargement des documents
    print("\nChargement des documents...")
    success = await rag_interface.load_documents()
    
    if not success:
        print("Impossible de continuer sans documents chargés.")
        return
    
    print("\nVous pouvez maintenant poser vos questions (tapez 'quit' pour quitter)")
    
    # Boucle de questions-réponses
    while True:
        question = input("\nVotre question : ")
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question.strip():
            continue
        
        try:
            response = await rag_interface.ask_question(question)
            if response:
                print("\nRéponse :")
                print(response)
            else:
                print("Désolé, je n'ai pas pu générer une réponse.")
        except Exception as e:
            print(f"Erreur lors du traitement de la question: {str(e)}")

def main():
    # Vérification de la clé API
    if not os.getenv("OPENAI_API_KEY"):
        print("Erreur: OPENAI_API_KEY non trouvée dans le fichier .env")
        print("Veuillez créer un fichier .env avec votre clé API OpenAI")
        return
    
    print("=== Système RAG ===")
    print("Ce système va charger vos documents et répondre à vos questions en se basant sur leur contenu.")
    
    # Lancement du mode interactif
    asyncio.run(interactive_mode())

if __name__ == "__main__":
    main()