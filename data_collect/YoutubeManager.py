from yt_dlp import YoutubeDL
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from utils.logger import logger

class YoutubeManager:
    def __init__(self, output_dir="cache/downloads", task_manager=None):
        self.logger = logger
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

    def download_mp3(self, url: str, task_id=None) -> str:
        self.logger.info(f"Starting MP3 download for URL: {url}")
        
        class ProgressHook:
            def __init__(self, manager, task_id):
                self.manager = manager
                self.task_id = task_id
                
            def __call__(self, d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes')
                    downloaded = d.get('downloaded_bytes', 0)
                    if total:
                        progress = (downloaded / total) * 100
                        self.manager.update_status(self.task_id, {
                            'download_progress': progress,
                            'status': 'downloading'
                        })

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [ProgressHook(self, task_id).__call__],
            'quiet': False,
            'no_warnings': False
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                mp3_path = os.path.join(self.output_dir, f"{info['title']}.mp3")
                
                if os.path.exists(mp3_path):
                    self.logger.info(f"File already exists: {mp3_path}")
                    return mp3_path
                    
                self.logger.info(f"Downloading and converting to MP3: {info['title']}")
                info = ydl.extract_info(url, download=True)
                self.logger.info(f"Download completed: {mp3_path}")
                return mp3_path
                
        except Exception as e:
            self.logger.error(f"Error during MP3 download: {str(e)}")
            return None


# Exemple d'utilisation
if __name__ == "__main__":
    manager = YoutubeManager()
    
    manager.extract_transcriptions("machine learning", lang="US", limit=2)