import os
from openai import OpenAI
from utils.logger import logger
from pydub import AudioSegment
import tempfile

class AudioTranscriberOpenAI:
    def __init__(self, output_dir="cache/transcriptions", api_key=None, task_manager=None):
        """
        Initialise le transcripteur audio avec l'API OpenAI.
        
        Args:
            output_dir (str): Dossier pour les transcriptions
            api_key (str): Clé API OpenAI (optionnel, utilise la variable d'environnement par défaut)
        """
        self.logger = logger
        self.logger.info("Initializing AudioTranscriberOpenAI")
        self.output_dir = output_dir
        self.task_manager = task_manager
        
        # Initialiser le client OpenAI
        self.client = OpenAI(api_key=api_key)
        self.logger.info("OpenAI client initialized")
        
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
        Transcrit un fichier MP3 en texte en utilisant l'API OpenAI.
        Gère automatiquement le découpage des fichiers longs.
        
        Args:
            mp3_path (str): Chemin vers le fichier MP3
            task_id (str): ID de la tâche pour le suivi de progression
            save_cache (bool): Si True, sauvegarde la transcription dans le cache
            
        Returns:
            str: La transcription du fichier audio
        """
        self.logger.info(f"Starting transcription for: {mp3_path}")
        basename = os.path.splitext(os.path.basename(mp3_path))[0]
        output_file = os.path.join(self.output_dir, f"{basename}.txt")

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
                self.update_status(task_id, {
                    'status': 'transcribing',
                    'transcription_progress': (i / total_segments) * 100
                })

                with open(segment_path, "rb") as audio_file:
                    result = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                full_transcript.append(result)

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
    transcriber = AudioTranscriberOpenAI()
    try:
        transcript = transcriber.transcript_mp3("chemin/vers/fichier.mp3")
        print("Transcription réussie:")
        print(transcript)
    except Exception as e:
        print(f"Erreur: {e}")
