import os
from openai import OpenAI
import logging
import time
from pydub import AudioSegment
import tempfile

class AudioTranscriberOpenAI:
    def __init__(self, output_dir="cache/transcriptions", api_key=None, task_manager=None, provider='openai'):
        """
        Initialise le transcripteur audio avec l'API OpenAI.
        
        Args:
            output_dir (str): Dossier pour les transcriptions
            api_key (str): Clé API OpenAI (optionnel, utilise la variable d'environnement par défaut)
        """
        # Configurer le logger interne
        self.logger = logging.getLogger('transcriber')
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        self.logger.info("Initializing AudioTranscriberOpenAI")
        self.output_dir = output_dir
        self.task_manager = task_manager
        self.api_key = api_key
        self.provider = provider
        
        # Initialiser le client OpenAI
        try:
            self.logger.info(f"Initialisation du client OpenAI avec le provider: {provider}")
            
            # Afficher l'API key (masquée) pour debug
            api_key_masked = "Non définie" if not api_key else f"...{api_key[-4:]}" if len(api_key) > 4 else "Définie"
            self.logger.info(f"API key: {api_key_masked}")
            
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1" if provider == "deepseek" else None,
                timeout=300.0  # Augmenter le timeout à 5 minutes
            )
            self.logger.info("Client OpenAI initialisé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du client OpenAI: {str(e)}")
            raise
        
        # Créer le dossier de sortie
        os.makedirs(output_dir, exist_ok=True)
        self.logger.info(f"Dossier de sortie prêt: {output_dir}")

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
        file_size = os.path.getsize(mp3_path)
        file_size_mb = file_size / (1024 * 1024)
        self.logger.info(f"Taille du fichier à traiter: {file_size_mb:.2f} MB")
        
        if file_size <= self.MAX_FILE_SIZE:
            self.logger.info(f"Fichier en dessous de la limite de taille, pas de découpage nécessaire")
            return [mp3_path]

        self.logger.info(f"Fichier trop grand, découpage en segments: {mp3_path}")
        
        try:
            audio = AudioSegment.from_mp3(mp3_path)
            self.logger.info(f"Durée de l'audio: {len(audio) / 1000:.2f} secondes")
            segments = []
            
            # Créer un dossier temporaire pour les segments
            temp_dir = tempfile.mkdtemp()
            self.logger.info(f"Dossier temporaire pour les segments créé: {temp_dir}")
            
            # Découper l'audio en segments
            segment_count = (len(audio) + self.SEGMENT_LENGTH - 1) // self.SEGMENT_LENGTH  # Arrondir vers le haut
            self.logger.info(f"Découpage en {segment_count} segments de {self.SEGMENT_LENGTH/1000:.0f} secondes")
            
            for i, start in enumerate(range(0, len(audio), self.SEGMENT_LENGTH)):
                segment = audio[start:start + self.SEGMENT_LENGTH]
                segment_path = os.path.join(temp_dir, f"segment_{i}.mp3")
                self.logger.info(f"Création du segment {i+1}/{segment_count}: {segment_path}")
                
                start_time = time.time()
                segment.export(segment_path, format="mp3")
                end_time = time.time()
                
                segment_size_mb = os.path.getsize(segment_path) / (1024 * 1024)
                self.logger.info(f"Segment {i+1} créé en {end_time-start_time:.2f}s, taille: {segment_size_mb:.2f} MB")
                
                segments.append(segment_path)
                
            self.logger.info(f"Audio découpé en {len(segments)} segments")
            return segments
            
        except Exception as e:
            self.logger.error(f"Erreur lors du découpage audio: {str(e)}")
            raise

    def transcribe(self, audio_file_path, task_id=None):
        try:
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Le fichier audio {audio_file_path} n'existe pas")

            with open(audio_file_path, 'rb') as audio_file:
                if self.task_manager:
                    self.task_manager.update_task_status(task_id, {
                        'status': 'transcribing',
                        'progress': 0
                    })

                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

                if self.task_manager:
                    self.task_manager.update_task_status(task_id, {
                        'status': 'transcribing',
                        'progress': 100
                    })

                return response

        except Exception as e:
            if self.task_manager:
                self.task_manager.update_task_status(task_id, {
                    'status': 'error',
                    'error': str(e)
                })
            raise e

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
        start_time_global = time.time()
        self.logger.info(f"Début de la transcription pour: {mp3_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(mp3_path):
            self.logger.error(f"Fichier audio non trouvé: {mp3_path}")
            raise FileNotFoundError(f"Le fichier audio {mp3_path} n'existe pas")
            
        basename = os.path.splitext(os.path.basename(mp3_path))[0]
        output_file = os.path.join(self.output_dir, f"{basename}.txt")

        # Vérifier le cache
        if os.path.exists(output_file):
            self.logger.info(f"Utilisation de la transcription en cache: {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                return f.read()

        try:
            self.logger.info("Préparation des segments audio pour la transcription")
            segments = self.split_audio(mp3_path)
            full_transcript = []
            total_segments = len(segments)

            self.logger.info(f"Début de la transcription de {total_segments} segment(s)")

            for i, segment_path in enumerate(segments):
                segment_start_time = time.time()
                self.logger.info(f"Traitement du segment {i+1}/{total_segments}: {segment_path}")
                
                # Mise à jour du progrès de transcription
                progress = ((i + 1) / total_segments) * 100
                self.update_status(task_id, {
                    'status': 'transcribing',
                    'progress': progress,
                    'current_segment': i + 1,
                    'total_segments': total_segments
                })

                try:
                    with open(segment_path, "rb") as audio_file:
                        self.logger.info(f"Envoi du segment {i+1} à l'API pour transcription")
                        start_api_call = time.time()
                        
                        result = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                        
                        api_duration = time.time() - start_api_call
                        self.logger.info(f"API a répondu en {api_duration:.2f}s pour le segment {i+1}")
                        
                        # Résumé du résultat
                        result_preview = result[:50] + "..." if len(result) > 50 else result
                        self.logger.info(f"Résultat obtenu: {result_preview}")
                        
                    full_transcript.append(result)

                    # Nettoyer le segment temporaire si ce n'est pas le fichier original
                    if segment_path != mp3_path:
                        os.remove(segment_path)
                        self.logger.info(f"Segment temporaire supprimé: {segment_path}")
                        
                    segment_duration = time.time() - segment_start_time
                    self.logger.info(f"Segment {i+1}/{total_segments} traité en {segment_duration:.2f}s")
                    
                except Exception as e:
                    self.logger.error(f"Erreur pendant la transcription du segment {i+1}: {str(e)}")
                    raise

            # Assembler la transcription complète
            transcript = " ".join(full_transcript)
            self.logger.info(f"Transcription complète générée: {len(transcript)} caractères")

            if save_cache:
                self.logger.info(f"Sauvegarde de la transcription dans le cache: {output_file}")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(transcript)

            self.update_status(task_id, {
                'transcription_progress': 100
            })
            
            total_duration = time.time() - start_time_global
            self.logger.info(f"Transcription terminée avec succès en {total_duration:.2f}s")
            return transcript

        except Exception as e:
            self.logger.error(f"Erreur pendant la transcription: {str(e)}")
            raise
        finally:
            # Nettoyer le dossier temporaire si utilisé
            if 'segments' in locals() and segments[0] != mp3_path:
                try:
                    temp_dir = os.path.dirname(segments[0])
                    os.rmdir(temp_dir)
                    self.logger.info(f"Dossier temporaire nettoyé: {temp_dir}")
                except Exception as e:
                    self.logger.error(f"Impossible de nettoyer le dossier temporaire: {str(e)}")

# Exemple d'utilisation
if __name__ == "__main__":
    transcriber = AudioTranscriberOpenAI()
    try:
        transcript = transcriber.transcript_mp3("chemin/vers/fichier.mp3")
        print("Transcription réussie:")
        print(transcript)
    except Exception as e:
        print(f"Erreur: {e}")
