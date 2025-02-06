# app.py
import os
import shutil
import uuid
import logging
import json
from flask import Flask, request, jsonify, session, Response, render_template
from werkzeug.utils import secure_filename
from langchain.text_splitter import TokenTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from openai_wrapper import OpenAIEmbeddingsWrapper
import PyPDF2
from openai import OpenAI
from chromadb.config import Settings
from youtube_routes import youtube_bp

# Désactivation de la télémétrie Chroma
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

# Configuration des logs plus détaillée
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.secret_key = os.urandom(24)


# Configuration
UPLOAD_FOLDER = 'cache/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
PERSIST_DIRECTORY = 'cache/vector_store'
CHUNK_SIZE = 512  # En tokens
OVERLAP_SIZE = 50  # En tokens
NB_RESULTS = 10
EMBEDDING_PROVIDER = "openai"  # ou "local"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2" if EMBEDDING_PROVIDER == "local" else "text-embedding-3-small"

# Initialisation
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def read_pdf_file(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def read_file(file_path):
    extension = file_path.split('.')[-1].lower()
    if extension == 'txt':
        return read_text_file(file_path)
    elif extension == 'pdf':
        return read_pdf_file(file_path)
    else:
        raise ValueError(f"Type de fichier non supporté: {extension}")

def get_embeddings():
    """Retourne l'instance d'embedding appropriée selon le provider configuré"""
    if EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingsWrapper(model=EMBEDDING_MODEL)
    else:
        return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def process_documents():
    try:
        embeddings = get_embeddings()

        # Configuration de Chroma avec similarité cosinus
        client_settings = Settings(
            persist_directory=PERSIST_DIRECTORY,
            anonymized_telemetry=False
        )
        
        # Vérifier si le vector store existe déjà
        if os.path.exists(PERSIST_DIRECTORY):
            vector_store = Chroma(
                persist_directory=PERSIST_DIRECTORY, 
                embedding_function=embeddings,
                collection_metadata={"hnsw:space": "cosine"}  # Force l'utilisation de la similarité cosinus
            )
        else:
            vector_store = None

        text_splitter = TokenTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=OVERLAP_SIZE
        )

        documents = []
        metadatas = []
        total_chunks = 0
        
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                text = read_file(file_path)
                chunks = text_splitter.split_text(text)
                total_chunks += len(chunks)
                
                for chunk in chunks:
                    documents.append(chunk)
                    metadatas.append({"source": filename})
                    
                logging.info(f"Fichier {filename} découpé en {len(chunks)} chunks")
                    
            except Exception as e:
                logging.error(f"Erreur de traitement de {filename}: {e}")

        logging.info(f"Total de chunks générés: {total_chunks}")
        
        if documents:  # Seulement créer/mettre à jour si nous avons des documents
            if vector_store is None:
                Chroma.from_texts(
                    texts=documents,
                    embedding=embeddings,
                    metadatas=metadatas,
                    persist_directory=PERSIST_DIRECTORY,
                    collection_metadata={"hnsw:space": "cosine"}  # Force l'utilisation de la similarité cosinus
                )
            else:
                vector_store.add_texts(texts=documents, metadatas=metadatas)

            vector_store.persist()
    except Exception as e:
        logging.error(f"Erreur lors du traitement des documents: {str(e)}")
        return False

def get_vector_store():
    logging.info("Initialisation du vector store")
    try:
        if not os.path.exists(PERSIST_DIRECTORY) or not os.listdir(PERSIST_DIRECTORY):
            logging.warning("Le dossier de persistance n'existe pas ou est vide")
            return None
            
        embeddings = get_embeddings()
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY, 
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"}  # Force l'utilisation de la similarité cosinus
        )
        logging.info(f"Vector store initialisé avec succès. Collection count: {vector_store._collection.count()}")
        return vector_store
    except Exception as e:
        logging.error(f"Erreur lors de l'initialisation du vector store: {str(e)}", exc_info=True)
        return None

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logging.error('Aucun fichier fourni')
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    api_key = request.form.get('api_key')
    provider = request.form.get('provider', 'openai')
    
    if not api_key:
        logging.error('Clé API requise')
        return jsonify({'error': 'Clé API requise'}), 400

    files = request.files.getlist('file')
    valid_files = 0
    
    for file in files:
        logging.info(f"Traitement du fichier: {file.filename}")
        if file and allowed_file(file.filename):
            logging.info(f"-> Fichier valide: {file.filename}")
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            valid_files += 1
    
    if valid_files == 0:
        logging.error(f"Aucun fichier valide uploadé : {files}")
        return jsonify({'error': 'Aucun fichier valide'}), 400
    
    try:
        process_documents()
    except Exception as e:
        logging.error(f'Erreur de traitement: {str(e)}')
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': f'{valid_files} fichiers uploadés'}), 200

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Fichier supprimé: {filename}")
            
            # Régénération complète du vector store
            if os.path.exists(PERSIST_DIRECTORY):
                shutil.rmtree(PERSIST_DIRECTORY)
                logging.info("Ancien vector store supprimé")
            
            process_documents()
            return jsonify({'message': 'Fichier supprimé avec succès'}), 200
        return jsonify({'error': 'Fichier non trouvé'}), 404
    except Exception as e:
        logging.error(f'Erreur de suppression: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return jsonify({'files': files})

def reformulate_question(message, api_key, provider="openai"):
    """Reformule la question pour améliorer la recherche RAG"""
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com" if provider == "deepseek" else None
        )
        
        system_prompt = """Tu es un expert en reformulation de questions pour la recherche documentaire.
        Ton rôle est de reformuler la question de l'utilisateur pour maximiser la pertinence des résultats de recherche.
        Garde l'essentiel de la question mais ajoute des termes et concepts connexes pertinents.
        Réponds uniquement avec la question reformulée, sans autre commentaire."""

        response = client.chat.completions.create(
            model="deepseek-chat" if provider == "deepseek" else "gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Voici la question de l'utilisateur : {message}"}
            ],
            stream=False
        )
        
        reformulated = response.choices[0].message.content.strip()
        logging.info(f"Question originale: {message}")
        logging.info(f"Question reformulée: {reformulated}")
        return reformulated
    except Exception as e:
        logging.warning(f"Erreur lors de la reformulation: {str(e)}")
        return message  # En cas d'erreur, on utilise la question originale

@app.route('/chat', methods=['GET'])
def chat():
    logging.info('Requête chat reçue')
    message = request.args.get('message')
    api_key = request.args.get('api_key')
    provider = request.args.get('provider', 'openai')
    history = json.loads(request.args.get('history', '[]'))  # Récupération de l'historique
    
    # Ajout de la gestion du nombre de résultats
    try:
        nb_results = int(request.args.get('nb_results', '5'))
        # Limiter le nombre entre 1 et 20
        nb_results = max(0, min(30, nb_results))
    except ValueError:
        logging.warning('Nombre de résultats invalide')
        nb_results = 5  # Valeur par défaut si invalide
    
    if not api_key or not message:
        logging.error('Clé API ou message manquant')
        return jsonify({'error': 'Clé API et message requis'}), 400
    
    if len(api_key.strip()) < 8:
        logging.error('Clé API invalide')
        return jsonify({'error': 'Clé API invalide'}), 400

    try:
        # Reformulation de la question
        reformulated_message = reformulate_question(message, api_key, provider)
        
        # Initialiser les variables context et sources
        context = ""
        sources = []
        
        # Tenter de récupérer le contexte si disponible
        vectordb = get_vector_store()
        if vectordb is not None:
            collection_count = vectordb._collection.count()
            if collection_count > 0:
                # Utiliser nb_results au lieu de la constante NB_RESULTS
                actual_results = min(nb_results, collection_count)
                docs = vectordb.similarity_search(reformulated_message, k=actual_results)
                context = "\n\n".join([doc.page_content for doc in docs])
                sources = [{
                    "source": doc.metadata['source'],
                    "content": doc.page_content,
                    "id": str(uuid.uuid4())[:8]
                } for doc in docs]
        else:
            logging.info("Vectordb non initialisé, on l'initialise maintenant a partir des fichiers dans UPLOAD_FOLDER")
            process_documents()
            vectordb = get_vector_store()
            if vectordb is not None:
                collection_count = vectordb._collection.count()
                if collection_count > 0:
                    # Utiliser nb_results ici aussi
                    actual_results = min(nb_results, collection_count)
                    docs = vectordb.similarity_search(reformulated_message, k=actual_results)
                    context = "\n\n".join([doc.page_content for doc in docs])
                    sources = [{
                        "source": doc.metadata['source'],
                        "content": doc.page_content,
                        "id": str(uuid.uuid4())[:8]
                    } for doc in docs]


        def generate():
            try:
                yield "data: {}\n\n"

                if sources:
                    sources_json = json.dumps({'type': 'sources', 'content': sources})
                    yield f"data: {sources_json}\n\n"
                
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com" if provider == "deepseek" else None
                )
                
                model = "deepseek-chat" if provider == "deepseek" else "gpt-4o"
                
                # Nouveau message système plus simple
                system_prompt = (
                    """Tu es un assistant de création de contenu de formation, alimenté par une recherche documentaire.
                    Sers-toi des informations fournies pour répondre à la question de l'utilisateur, en citant les passages pertinents provenant du contenu qui t'ont aider a répondre.
                    Quand tu cite, utilise le format suivant : "(source: nom du document, page: numéro de page)".
                    """
                )
                
                messages = [{"role": "system", "content": system_prompt}]
                
                if history:
                    messages.extend(history)
                
                # Ajout du contexte RAG comme un message assistant avant la question
                logging.info(f"Contexte RAG: {len(context)} caractères")
                if context:
                    messages.append({
                        "role": "assistant",
                        "content": "D'après les documents consultés, voici les informations pertinentes :\n\n" + context
                    })
                
                messages.append({"role": "user", "content": message})
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        chunk_json = json.dumps({'type': 'response', 'content': content})
                        yield f"data: {chunk_json}\n\n"
                        if hasattr(response, 'flush'):
                            response.flush()

                yield f"data: {json.dumps({'type': 'status', 'content': 'done'})}\n\n"
            
            except Exception as e:
                logging.error(f"Erreur pendant la génération: {str(e)}", exc_info=True)
                error_json = json.dumps({'type': 'error', 'content': str(e)})
                yield f"data: {error_json}\n\n"
                yield f"data: {json.dumps({'type': 'status', 'content': 'done'})}\n\n"

        response = Response(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    except Exception as e:
        logging.error(f'Erreur globale du chat: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    session['api_key'] = request.json.get('api_key')
    return jsonify({'message': 'Clé API enregistrée'})

@app.route('/refresh_vector_db', methods=['POST'])
def refresh_vector_db():
    try:
        process_documents()
        return jsonify({'message': 'Vecteur DB rafraîchi'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

# Ajout de la nouvelle route pour la page de gestion des fichiers
@app.route('/files')
def files():
    return render_template('index_file.html')

@app.route('/file_size/<filename>')
def get_file_size(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            return jsonify({'size': size})
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Enregistrement des blueprints
app.register_blueprint(youtube_bp, url_prefix='/youtube')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18900, debug=False)