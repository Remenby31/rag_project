from flask import Blueprint, request, jsonify
from utils.logger import logger
import uuid


youtube_bp = Blueprint('youtube', __name__)

def init_routes(youtube_service, task_manager):
    
    @youtube_bp.route('/search', methods=['POST'])
    def youtube_search():
        try:
            data = request.json
            query = data.get('query')
            lang = data.get('lang', 'US')
            limit = data.get('limit', 5)
            
            results = youtube_service.youtube_manager.search_videos(query, lang, limit)
            
            # Transformer les résultats en dictionnaires
            formatted_results = []
            for title, url in results:
                formatted_results.append({
                    'title': title,
                    'url': url,
                    'isAdded': False,
                })
            
            return jsonify({'videos': formatted_results})
        except Exception as e:
            logger.error(f"Error in youtube search: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @youtube_bp.route('/process', methods=['POST'])
    def process_videos():
        try:
            data = request.json
            videos = data.get('videos', [])
            transcription_model = data.get('transcriptionModel', 'local')
            
            if not videos:
                return jsonify({'error': 'No videos provided'}), 400

            task_id = task_manager.create_task(initial_data={
                'status': 'pending',
                'progress': 0,
                'videos': videos,
                'transcription_model': transcription_model
            })

            # Lancer le traitement en arrière-plan avec le modèle choisi
            youtube_service.process_videos(
                task_id, 
                [(v['title'], v['url']) for v in videos],
                transcription_model=transcription_model
            )
            
            return jsonify({'task_id': task_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @youtube_bp.route('/tasks', methods=['GET'])
    def get_tasks():
        try:
            tasks = task_manager.get_all_tasks()
            logger.debug(f"Got tasks: {tasks}")
            return jsonify(tasks)
        except Exception as e:
            logger.error(f"Error getting tasks: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @youtube_bp.route('/status/<task_id>', methods=['GET'])
    def get_task_status(task_id):
        status = task_manager.get_task_status(task_id)
        if not status:
            logger.error(f"Task {task_id} not found")
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(status)

    return youtube_bp
