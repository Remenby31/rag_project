import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
from transformers import pipeline
import torch
from utils.logger import logger
from pydub import AudioSegment
import tempfile

# Configuration pour réduire la consommation mémoire
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

class CallbackHandler:
    def __init__(self, task_manager, task_id, total_segments, current_segment):
        self.task_manager = task_manager
        self.task_id = task_id
        self.total_segments = total_segments
        self.current_segment = current_segment

    def update_progress(self, current_step, total_steps):
        if self.task_manager and self.task_id:
            segment_progress = (self.current_segment / self.total_segments) * 100
            step_progress = (current_step / total_steps) * (100 / self.total_segments)
            total_progress = segment_progress + step_progress
            
            self.task_manager.update_task_status(self.task_id, {
                'status': 'transcribing',
                'transcription_progress': total_progress,
                'current_segment': self.current_segment + 1,
                'total_segments': self.total_segments,
                'segment_progress': (current_step / total_steps) * 100
            })

class AudioTranscriber:
    def __init__(self, output_dir="cache/transcriptions", task_manager=None):
        """
        Initialise le transcripteur audio avec Whisper Turbo.
        
        Args:
            output_dir (str): Dossier pour les transcriptions
        """
        self.logger = logger
        self.task_manager = task_manager
        self.logger.info("Initializing AudioTranscriber")
        self.output_dir = os.path.normpath(output_dir)
        
        # Détection du device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Using device: {self.device}")
        
        # Initialiser le pipeline avec support GPU
        self.logger.info("Loading Whisper model...")
        self.pipe = pipeline(
            "automatic-speech-recognition", 
            model="openai/whisper-large-v3-turbo",
            device=self.device,
            chunk_length_s=30,
            batch_size=8 if self.device == "cuda" else 4,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        self.logger.info("Whisper model loaded successfully")
        
        # Créer le dossier de sortie
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"Output directory ready: {output_dir}")
        
        self.MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB en octets
        self.SEGMENT_LENGTH = 10 * 60 * 1000    # 10 minutes en millisecondes

    def update_status(self, task_id, status_data):
        if self.task_manager and task_id:
            self.task_manager.update_task_status(task_id, status_data)

    def split_audio(self, mp3_path):
        """
        Découpe un fichier audio en segments si nécessaire.
        
        Returns:
            list: Liste des chemins des segments ou [mp3_path] si pas de découpage nécessaire
        """
        # Vérifier la taille du fichier
        if os.path.getsize(mp3_path) <= self.MAX_FILE_SIZE:
            return [mp3_path]

        self.logger.info(f"File too large, splitting into segments: {mp3_path}")
        audio = AudioSegment.from_mp3(mp3_path)
        segments = []
        
        # Créer un dossier temporaire pour les segments
        temp_dir = tempfile.mkdtemp()
        
        # Découper l'audio en segments
        for i, start in enumerate(range(0, len(audio), self.SEGMENT_LENGTH)):
            segment = audio[start:start + self.SEGMENT_LENGTH]
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp3")
            segment.export(segment_path, format="mp3")
            segments.append(segment_path)
            
        self.logger.info(f"Split audio into {len(segments)} segments")
        return segments

    def transcript_mp3(self, mp3_path: str, task_id=None, save_cache: bool = True) -> str:
        """
        Transcrit un fichier MP3 en texte.
        
        Args:
            mp3_path (str): Chemin vers le fichier MP3
            save_cache (bool): Si True, sauvegarde la transcription dans le cache
            
        Returns:
            str: La transcription du fichier audio
        """
        mp3_path = os.path.normpath(mp3_path)  # Normalisation du chemin d'entrée
        self.logger.info(f"Starting transcription for: {mp3_path}")
        basename = os.path.splitext(os.path.basename(mp3_path))[0]
        output_file = os.path.normpath(os.path.join(self.output_dir, f"{basename}.txt"))

        # Vérifier que le fichier existe
        if not os.path.exists(mp3_path):
            error_msg = f"Le fichier audio n'existe pas: {mp3_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Vérifier le cache
        if os.path.exists(output_file):
            self.logger.info(f"Using cached transcription: {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                return f.read()

        try:
            segments = self.split_audio(mp3_path)
            full_transcript = []
            total_segments = len(segments)

            for i, segment_path in enumerate(segments):
                self.logger.info(f"Processing segment {i+1}/{total_segments}")
                
                callback = CallbackHandler(self.task_manager, task_id, total_segments, i)
                
                # Estimer la durée totale du segment audio
                audio = AudioSegment.from_mp3(segment_path)
                total_duration = len(audio) / 1000  # Durée en secondes
                steps = int(total_duration / 30) + 1  # Estimation des étapes (30s par chunk)
                
                # Traiter l'audio
                result = self.pipe(segment_path, return_timestamps=True)
                
                # Simuler la progression
                for step in range(steps):
                    callback.update_progress(step + 1, steps)
                
                if isinstance(result, dict) and 'chunks' in result:
                    transcript = " ".join(chunk['text'] for chunk in result['chunks'])
                else:
                    transcript = result['text']
                    
                full_transcript.append(transcript)

                # Nettoyer le segment temporaire si ce n'est pas le fichier original
                if segment_path != mp3_path:
                    os.remove(segment_path)

            # Assembler la transcription complète
            transcript = " ".join(full_transcript)

            if save_cache:
                self.logger.info(f"Saving transcription to cache: {output_file}")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(transcript)

            self.update_status(task_id, {
                'transcription_progress': 100
            })

            self.logger.info("Transcription completed successfully")
            return transcript

        except Exception as e:
            self.logger.error(f"Error during transcription: {str(e)}")
            raise
        finally:
            # Nettoyer le dossier temporaire si utilisé
            if 'segments' in locals() and segments[0] != mp3_path:
                try:
                    os.rmdir(os.path.dirname(segments[0]))
                except:
                    pass

# Exemple d'utilisation
if __name__ == "__main__":
    transcriber = AudioTranscriber()
    try:
        transcript = transcriber.transcript_mp3("chemin/vers/fichier.mp3")
        print("Transcription réussie:")
        print(transcript)
    except Exception as e:
        print(f"Erreur: {e}")