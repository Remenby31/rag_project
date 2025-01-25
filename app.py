from flask import Flask, render_template, request, jsonify
import asyncio
from examples.basic_usage import RAGPipeline
from services.task_manager import TaskManager
from services.youtube_service import YoutubeService
from routes.youtube_routes import init_routes
from utils.logger import logger
import os

app = Flask(__name__)

# Initialize services
rag = RAGPipeline()
task_manager = TaskManager()
youtube_service = YoutubeService(task_manager, rag)

# Register blueprints
youtube_bp = init_routes(youtube_service, task_manager)
app.register_blueprint(youtube_bp, url_prefix='/api/youtube')

async def init_rag():
    # Initialize RAG system with all the files contained in the 'files' folder
    documents_to_index = []
    docs_folder = "./files"

    if not os.path.exists(docs_folder):
        logger.error(f"Folder {docs_folder} does not exist!")
        return False
    
    # Get all files in the folder
    supported_extensions = {'.txt', '.pdf', '.doc', '.docx'}

    for file_path in os.listdir(docs_folder):
        if (file_path.endswith(tuple(supported_extensions))):
            documents_to_index.append(os.path.join(docs_folder, file_path))

    if not documents_to_index:
        logger.error("No compatible documents found in the folder!")
        return False
        
    # Index the documents
    success = await rag.index_documents(documents_to_index)
    return success

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        question = data.get('message')
        max_passages = int(data.get('maxPassages', 5))
        
        relevant_docs = asyncio.run(rag.query_processor.process_query(question))
        response = asyncio.run(rag.query(question))
        
        passages_with_metadata = [
            {
                'content': doc.content,
                'metadata': {
                    'filename': doc.metadata.get('source', 'Document inconnu'),
                    'page': doc.metadata.get('page', 'N/A')
                }
            } for doc in relevant_docs[:max_passages]
        ]
        
        return jsonify({
            'response': response,
            'relevant_passages': passages_with_metadata
        })
    except ValueError as ve:
        logger.error(f"Invalid maxPassages value: {str(ve)}")
        return jsonify({'error': 'Invalid maxPassages parameter'}), 400
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/youtube-manager')
def youtube_manager():
    return render_template('youtube-manager.html')

if __name__ == '__main__':
    success = asyncio.run(init_rag())
    if not success:
        logger.error("Failed to initialize RAG system")
        exit(1)
    app.run(debug=True)