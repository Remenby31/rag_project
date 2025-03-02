from yt_dlp import YoutubeDL
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging

class YoutubeManager:
    def __init__(self, output_dir="cache/downloads", task_manager=None):
        self.logger = logging
        self.logger.info("Initializing YoutubeManager")
        self.output_dir = output_dir
        self.task_manager = task_manager
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Created output directory: {self.output_dir}")

    def update_status(self, task_id, status_data):
        if self.task_manager and task_id:
            self.task_manager.update_task_status(task_id, status_data)

    def search_videos(self, query, lang="US", limit=3):
        limit = int(limit)
        self.logger.info(f"Searching videos for query: '{query}', lang: {lang}, limit: {limit}")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-cookies")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument(f"--lang=en-{lang}")
        chrome_options.add_argument(f"--accept-lang=en-{lang},en;q=0.9")
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            url = f"https://www.youtube.com/results?search_query={query}&gl={lang}&hl=en"
            self.logger.debug(f"Accessing URL: {url}")
            driver.get(url)
            # On enregistre la page pour le débogage
            driver.save_screenshot("cache/youtube_search.png")
            
            wait = WebDriverWait(driver, 3)
            videos = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#video-title")
            ))
            
            results = []
            for video in videos[:limit]:
                title = video.get_attribute('title')
                url = video.get_attribute('href')
                if title and url:
                    results.append((title, url))
            
                    
            self.logger.info(f"Found {len(results)} videos")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during video search: {str(e)}")
            raise
        finally:
            driver.quit()

    def _sanitize_filename(self, filename):
        """Nettoie le nom de fichier en remplaçant les caractères problématiques"""
        # Remplacer les caractères spéciaux par des underscores
        import re
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        # Supprimer les espaces multiples
        filename = re.sub(r'\s+', ' ', filename)
        return filename.strip()

    def download_mp3(self, url: str, task_id=None) -> str:
        try:
            # Mise à jour initiale du statut
            self.update_status(task_id, {
                'status': 'downloading',
                'progress': 0
            })

            # Configuration yt-dlp
            with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                # Récupérer les informations
                info = ydl.extract_info(url, download=False)
                safe_title = self._sanitize_filename(info['title'])
                
                # Configuration pour le téléchargement
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        if total > 0:
                            progress = (downloaded / total) * 100
                            self.update_status(task_id, {
                                'status': 'downloading',
                                'progress': progress
                            })

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(self.output_dir, f'{safe_title}.%(ext)s'),
                    'progress_hooks': [progress_hook],
                }

                # Téléchargement
                with YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])

                mp3_path = os.path.join(self.output_dir, f"{safe_title}.mp3")
                return mp3_path

        except Exception as e:
            self.logger.error(f"Error during MP3 download: {str(e)}")
            raise

    def transcribe_video(self, url: str, task_id=None, transcriber=None) -> str:
        """
        Télécharge la vidéo en MP3 et la transcrit.
        """
        try:
            # Téléchargement
            mp3_path = self.download_mp3(url, task_id)
            if not mp3_path:
                raise Exception("Échec du téléchargement MP3")

            # Transcription
            if transcriber is None:
                from AudioTranscriberOpenAI import AudioTranscriberOpenAI
                transcriber = AudioTranscriberOpenAI()
            
            transcript = transcriber.transcript_mp3(mp3_path, task_id)

            # Nettoyage
            os.remove(mp3_path)
            return transcript

        except Exception as e:
            self.logger.error(f"Erreur lors de la transcription: {str(e)}")
            raise


# Exemple d'utilisation
if __name__ == "__main__":
    manager = YoutubeManager()
    
    manager.extract_transcriptions("machine learning", lang="US", limit=2)