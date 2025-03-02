from flask import Flask, request, jsonify, send_file, Response, url_for, Blueprint, render_template
import os
import time
import uuid
import re
import instaloader
import pyktok as pyk
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Créer le blueprint au lieu de l'app
social_media_bp = Blueprint('social_media', __name__)

# Configuration stockée au niveau du blueprint
social_media_bp.config = {
    'UPLOAD_FOLDER': 'videos',
    'MAX_CONTENT_LENGTH': 500 * 1024 * 1024,  # Limite à 500 MB
    'VIDEO_EXPIRY': 3600  # Temps en secondes avant suppression des vidéos (1 heure)
}

# Assurer que le dossier existe
if not os.path.exists(social_media_bp.config['UPLOAD_FOLDER']):
    os.makedirs(social_media_bp.config['UPLOAD_FOLDER'])

# Stockage temporaire des vidéos (clé: ID unique, valeur: chemin du fichier)
video_cache = {}

def nettoyer_cache():
    """Nettoie les fichiers temporaires qui ont dépassé le temps d'expiration"""
    temps_actuel = time.time()
    for video_id, (chemin_fichier, timestamp) in list(video_cache.items()):
        if temps_actuel - timestamp > social_media_bp.config['VIDEO_EXPIRY']:
            try:
                if os.path.exists(chemin_fichier):
                    os.remove(chemin_fichier)
                del video_cache[video_id]
            except Exception as e:
                app.logger.error(f"Erreur lors du nettoyage de {chemin_fichier}: {str(e)}")

def telecharger_video_instagram(url):
    """
    Télécharge une vidéo Instagram à partir de son URL
    
    Paramètres:
    url (str): URL de la vidéo Instagram
    
    Retourne:
    tuple: (chemin_fichier, message) ou (None, message d'erreur)
    """
    try:
        # Extraction du shortcode depuis l'URL
        #https://www.instagram.com/reels/DEFuLvpsqtJ/
        shortcode_match = re.search(r'/reels/([^/]+)', url)
        if not shortcode_match:
            return None, "URL Instagram invalide. Format attendu: instagram.com/reels/SHORTCODE"
        
        shortcode = shortcode_match.group(1)

        # Initialisation d'Instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=True,
            download_video_thumbnails=False,
            compress_json=False,
            save_metadata=False
        )
        
        # Téléchargement de la publication par shortcode
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Vérification que c'est bien une vidéo
        if not post.is_video:
            return None, "Cette publication n'est pas une vidéo"
            
        # Téléchargement avec le nom de fichier personnalisé
        nom_fichier = f"instagram_{shortcode}_{uuid.uuid4().hex}.mp4"
        chemin_complet = os.path.join(social_media_bp.config['UPLOAD_FOLDER'], nom_fichier)
        
        # Si mode anonyme ne fonctionne pas, essayer avec connexion
        try:
            video_url = post.video_url
            response = requests.get(video_url, stream=True)
            
            with open(chemin_complet, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            return chemin_complet, "Vidéo téléchargée avec succès"
        
        except instaloader.exceptions.LoginRequiredException:
            return None, "Cette vidéo nécessite une connexion Instagram"
            
    except Exception as e:
        return None, f"Erreur lors du téléchargement: {str(e)}"


def telecharger_video_tiktok(url):
    """
    Télécharge une vidéo TikTok à partir de son URL
    
    Paramètres:
    url (str): URL de la vidéo TikTok
    
    Retourne:
    tuple: (chemin_fichier, message) ou (None, message d'erreur)
    """
    try:
        # Configuration de pyktok
        pyk.specify_browser('chrome')  # Peut être changé en 'firefox', 'edge', etc.
        
        # Extraction de l'ID de la vidéo depuis l'URL
        video_id_match = re.search(r'video/(\d+)', url)
        if not video_id_match:
            return None, "URL TikTok invalide. Format attendu: tiktok.com/@utilisateur/video/ID"
        
        video_id = video_id_match.group(1)
        nom_fichier = f"tiktok_{video_id}_{uuid.uuid4().hex}.mp4"
        chemin_complet = os.path.join(social_media_bp.config['UPLOAD_FOLDER'], nom_fichier)
        
        # Téléchargement de la vidéo
        pyk.save_tiktok(
            url,
            save_video=True,
            metadata_fn=None,  # On ne sauvegarde pas les métadonnées
            video_fn=chemin_complet  # Chemin personnalisé pour la vidéo
        )
        
        return chemin_complet, "Vidéo téléchargée avec succès"
        
    except Exception as e:
        return None, f"Erreur lors du téléchargement: {str(e)}"


@social_media_bp.route('/download/instagram', methods=['GET'])
def download_instagram():
    """Endpoint pour télécharger une vidéo Instagram"""
    # Récupération de l'URL depuis les paramètres de la requête
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Paramètre 'url' manquant"}), 400
    
    # Nettoyage du cache avant traitement
    nettoyer_cache()
    
    # Téléchargement de la vidéo
    chemin_fichier, message = telecharger_video_instagram(url)
    
    if not chemin_fichier:
        return jsonify({"error": message}), 400
    
    # Génération d'un ID unique pour cette vidéo
    video_id = uuid.uuid4().hex
    video_cache[video_id] = (chemin_fichier, time.time())
    
    # Construction de l'URL pour récupérer la vidéo
    video_url = url_for('social_media.get_video', video_id=video_id, _external=True)
    
    return jsonify({
        "message": message,
        "video_id": video_id,
        "video_url": video_url,
        "expiry": social_media_bp.config['VIDEO_EXPIRY']
    })


@social_media_bp.route('/download/tiktok', methods=['GET'])
def download_tiktok():
    """Endpoint pour télécharger une vidéo TikTok"""
    # Récupération de l'URL depuis les paramètres de la requête
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Paramètre 'url' manquant"}), 400
    
    # Nettoyage du cache avant traitement
    nettoyer_cache()
    
    # Téléchargement de la vidéo
    chemin_fichier, message = telecharger_video_tiktok(url)
    
    if not chemin_fichier:
        return jsonify({"error": message}), 400
    
    # Génération d'un ID unique pour cette vidéo
    video_id = uuid.uuid4().hex
    video_cache[video_id] = (chemin_fichier, time.time())
    
    # Construction de l'URL pour récupérer la vidéo
    video_url = url_for('social_media.get_video', video_id=video_id, _external=True)
    
    return jsonify({
        "message": message,
        "video_id": video_id,
        "video_url": video_url,
        "expiry": social_media_bp.config['VIDEO_EXPIRY']
    })


@social_media_bp.route('/video/<video_id>', methods=['GET'])
def get_video(video_id):
    """Endpoint pour récupérer une vidéo téléchargée"""
    # Vérification que l'ID existe dans le cache
    if video_id not in video_cache:
        return jsonify({"error": "Vidéo non trouvée ou expirée"}), 404
    
    chemin_fichier, _ = video_cache[video_id]
    
    # Vérification que le fichier existe
    if not os.path.exists(chemin_fichier):
        del video_cache[video_id]
        return jsonify({"error": "Fichier vidéo non trouvé"}), 404
    
    # Streaming du fichier vidéo
    return send_file(chemin_fichier, 
                    mimetype='video/mp4',
                    as_attachment=True,
                    download_name=os.path.basename(chemin_fichier))


@social_media_bp.route('/info', methods=['GET'])
def api_info():
    """Endpoint pour obtenir des informations sur l'API"""
    return jsonify({
        "name": "Video Downloader API",
        "endpoints": {
            "instagram": "/social/download/instagram?url=URL_INSTAGRAM",
            "tiktok": "/social/download/tiktok?url=URL_TIKTOK",
            "video": "/social/video/VIDEO_ID"
        },
        "expiry": f"{social_media_bp.config['VIDEO_EXPIRY']} secondes",
        "max_size": f"{social_media_bp.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)} MB"
    })

@social_media_bp.route('/social_media', methods=['GET'])
def social_media():
    """Endpoint pour envoyer le index_social_media.html"""
    return render_template('index_social_media.html')

# Enregistrer le blueprint dans l'application principale
app.register_blueprint(social_media_bp, url_prefix='/social')

if __name__ == '__main__':
    # Configuration pour le développement
    app.run(debug=True, host='0.0.0.0', port=5000)