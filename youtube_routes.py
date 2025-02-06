from flask import Blueprint, jsonify, request, render_template
from YoutubeManager import YoutubeManager
import uuid
import os

class TaskManager:
    def __init__(self):
        self.tasks = {}

    def update_task_status(self, task_id, status_data):
        if task_id in self.tasks:
            self.tasks[task_id].update(status_data)
        else:
            self.tasks[task_id] = status_data

    def get_task_status(self, task_id):
        return self.tasks.get(task_id, {})

task_manager = TaskManager()
youtube_bp = Blueprint('youtube', __name__)
youtube_manager = YoutubeManager()  # Ne pas passer le task_manager ici

def get_task_manager():
    return task_manager

@youtube_bp.route('/')
def index():
    return render_template('index_yt.html')

@youtube_bp.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    lang = data.get('lang', 'US')
    limit = data.get('limit', 5)
    try:
        results = youtube_manager.search_videos(query, lang, limit)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@youtube_bp.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    api_key = data.get('api_key')
    provider = data.get('provider', 'openai')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL required'})
        
    if not api_key:
        return jsonify({'success': False, 'error': 'API key required'})
    
    task_id = str(uuid.uuid4())
    task_manager.update_task_status(task_id, {'status': 'starting', 'progress': 0})
    
    def transcribe_task():
        try:
            from AudioTranscriberOpenAI import AudioTranscriberOpenAI
            # Passer la clé API au transcriber
            transcriber = AudioTranscriberOpenAI(
                task_manager=task_manager,
                api_key=api_key,
                provider=provider
            )
            transcript = youtube_manager.transcribe_video(url, task_id, transcriber)
            
            filename = f"transcript_{task_id}.txt"
            filepath = os.path.join('static', 'transcripts', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(transcript)
                
            task_manager.update_task_status(task_id, {
                'status': 'completed',
                'progress': 100,
                'transcript': transcript,
                'download_url': f'/static/transcripts/{filename}'
            })
        except Exception as e:
            task_manager.update_task_status(task_id, {
                'status': 'error',
                'error': str(e)
            })
    
    import threading
    thread = threading.Thread(target=transcribe_task)
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id
    })

@youtube_bp.route('/status/<task_id>')
def status(task_id):
    task_status = task_manager.get_task_status(task_id)
    return jsonify(task_status)
