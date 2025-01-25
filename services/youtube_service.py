from utils.logger import logger
from data_collect.YoutubeManager import YoutubeManager
from data_collect.AudioTranscriber import AudioTranscriber
from data_collect.AudioTranscriberOpenAI import AudioTranscriberOpenAI

class YoutubeService:
    def __init__(self, task_manager, rag_pipeline):
        self.task_manager = task_manager
        self.rag_pipeline = rag_pipeline
        self.youtube_manager = YoutubeManager(task_manager=task_manager)
        self._local_transcriber = None
        self._openai_transcriber = None
    
    @property
    def local_transcriber(self):
        if self._local_transcriber is None:
            self._local_transcriber = AudioTranscriber(task_manager=self.task_manager, output_dir="files/transcriptions")
        return self._local_transcriber

    @property
    def openai_transcriber(self):
        if self._openai_transcriber is None:
            self._openai_transcriber = AudioTranscriberOpenAI(task_manager=self.task_manager, output_dir="files/transcriptions")
        return self._openai_transcriber
    
    def process_videos(self, task_id, videos, transcription_model='local'):
        # Choisir le transcripteur approprié
        transcriber = (self.local_transcriber if transcription_model == 'local' 
                      else self.openai_transcriber)

        try:
            self.task_manager.update_task_status(task_id, {'status': 'downloading'})
            transcriptions = []
            total_videos = len(videos)
            
            for idx, (title, url) in enumerate(videos):
                self.task_manager.update_task_status(task_id, {
                    'current_file': title,
                    'progress': (idx / total_videos) * 100
                })
                
                mp3_path = self.youtube_manager.download_mp3(url, task_id)
                if not mp3_path:
                    continue
                    
                self.task_manager.update_task_status(task_id, {'status': 'transcribing'})
                transcript = transcriber.transcript_mp3(mp3_path, task_id)
                transcriptions.append({
                    'title': title,
                    'content': transcript,
                    'source': url
                })
            
            # Indexation dans le RAG
            self.task_manager.update_task_status(task_id, {'status': 'indexing'})
            
            # Convertir les transcriptions en format compatible avec le RAG
            documents = []
            for trans in transcriptions:
                documents.append({
                    'content': trans['content'],
                    'metadata': {
                        'source': trans['source'],
                        'title': trans['title'],
                        'type': 'youtube_transcript'
                    }
                })
            
            # Indexer les documents avec le RAG pipeline
            success = self.rag_pipeline.index_documents(documents)
            if not success:
                raise Exception("Failed to index transcriptions in RAG system")
            
            self.task_manager.update_task_status(task_id, {
                'status': 'completed',
                'progress': 100,
                'results': transcriptions
            })
            
        except Exception as e:
            logger.error(f"Error processing videos: {str(e)}")
            self.task_manager.update_task_status(task_id, {
                'status': 'error',
                'error': str(e)
            })

    def search_and_transcribe(self, query, lang="US", limit=3, task_id=None, transcription_model='local'):
        """Recherche et transcrit des vidéos en une seule opération"""
        try:
            # Recherche des vidéos
            videos = self.youtube_manager.search_videos(query, lang, limit)
            
            if task_id:
                self.task_manager.update_task_status(task_id, {
                    'status': 'processing',
                    'videos': videos
                })
            
            # Utilise process_videos pour le traitement
            self.process_videos(task_id, videos, transcription_model)
            
        except Exception as e:
            logger.error(f"Error in search_and_transcribe: {str(e)}")
            if task_id:
                self.task_manager.update_task_status(task_id, {
                    'status': 'error',
                    'error': str(e)
                })
            raise
