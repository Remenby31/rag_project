document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const videoUrlInput = document.getElementById('video-url');
    const platformSelect = document.getElementById('platform-select');
    const downloadBtn = document.getElementById('download-btn');
    const statusContainer = document.getElementById('status-container');
    const statusText = document.getElementById('status-text');
    const resultContainer = document.getElementById('result-container');
    const videoPreview = document.getElementById('video-preview');
    const directDownloadBtn = document.getElementById('direct-download-btn');
    const copyLinkBtn = document.getElementById('copy-link-btn');
    const transcribeBtn = document.getElementById('transcribe-btn');
    const errorContainer = document.getElementById('error-container');
    const errorText = document.getElementById('error-text');
    const tryAgainBtn = document.getElementById('try-again-btn');
    const toast = document.getElementById('toast');
    const apiStatus = document.getElementById('api-status');
    const expiryTime = document.getElementById('expiry-time');
    
    // Nouveaux éléments DOM pour la transcription
    const transcriptionContainer = document.getElementById('transcription-container');
    const transcriptionStatus = document.getElementById('transcription-status');
    const transcriptionContent = document.getElementById('transcription-content');
    const transcriptionText = document.querySelector('.transcription-text');
    const copyTranscriptionBtn = document.getElementById('copy-transcription-btn');
    const downloadTranscriptionBtn = document.getElementById('download-transcription-btn');
    const closeTranscriptionBtn = document.getElementById('close-transcription-btn');
    const transcriptionError = document.getElementById('transcription-error');

    // Configuration
    const API_BASE_URL = 'https://knowledgerag.duckdns.org'; // Suppression du slash final
    let videoData = null;
    let expiryInterval = null;
    let transcriptionData = null;

    // Vérifier le statut de l'API
    checkApiStatus();

    // Gestionnaires d'événements
    downloadBtn.addEventListener('click', handleDownload);
    tryAgainBtn.addEventListener('click', resetUI);
    copyLinkBtn.addEventListener('click', copyVideoLink);
    transcribeBtn.addEventListener('click', handleTranscription);
    videoUrlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleDownload();
        }
    });
    
    // Nouveaux gestionnaires d'événements pour la transcription
    copyTranscriptionBtn.addEventListener('click', copyTranscriptionText);
    downloadTranscriptionBtn.addEventListener('click', downloadTranscriptionText);
    closeTranscriptionBtn.addEventListener('click', closeTranscription);

    // Vérifier l'état de l'API
    function checkApiStatus() {
        fetch(`${API_BASE_URL}/social/info`)
            .then(response => {
                if (response.ok) {
                    apiStatus.textContent = 'En ligne';
                    apiStatus.classList.add('online');
                } else {
                    throw new Error('API indisponible');
                }
            })
            .catch(error => {
                console.error('Erreur API:', error);
                apiStatus.textContent = 'Hors ligne';
                apiStatus.classList.add('offline');
                apiStatus.classList.remove('online');
            });
    }

    // Gérer le téléchargement de la vidéo
    function handleDownload() {
        const url = videoUrlInput.value.trim();
        const platform = platformSelect.value;

        // Validation de l'URL
        if (!url) {
            showError('Veuillez entrer une URL');
            return;
        }

        // Réinitialiser l'UI
        resetUI(false);

        // Afficher le conteneur de statut
        statusContainer.classList.remove('hidden');
        
        // Effectuer la requête à l'API appropriée
        const endpoint = `${API_BASE_URL}/social/download/${platform}?url=${encodeURIComponent(url)}`;
        
        fetch(endpoint)
            .then(response => {
                if (!response.ok) {
                    // Vérifier si la réponse est JSON ou non
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return response.json().then(data => {
                            throw new Error(data.error || `Erreur ${response.status}`);
                        });
                    } else {
                        // Si ce n'est pas du JSON, renvoyer une erreur générique
                        throw new Error(`Le serveur a renvoyé une erreur (${response.status})`);
                    }
                }
                return response.json();
            })
            .then(data => {
                videoData = data;
                displayResult(data);
            })
            .catch(error => {
                console.error('Erreur de téléchargement:', error);
                showError(error.message || 'Une erreur est survenue');
            });
    }

    // Afficher le résultat du téléchargement
    function displayResult(data) {
        // Cacher le conteneur de statut
        statusContainer.classList.add('hidden');
        
        // Afficher le conteneur de résultat
        resultContainer.classList.remove('hidden');
        
        // Configurer la prévisualisation de la vidéo
        videoPreview.src = data.video_url;
        videoPreview.load();
        
        // Configurer le bouton de téléchargement direct
        directDownloadBtn.href = data.video_url;
        directDownloadBtn.download = getPlatformPrefix() + getVideoIdFromUrl(videoUrlInput.value) + '.mp4';
        
        // Démarrer le compte à rebours d'expiration
        startExpiryCountdown(data.expiry);
    }

    // Gérer la transcription de la vidéo
    function handleTranscription() {
        if (!videoData || !videoData.video_id) {
            showError("Aucune vidéo disponible à transcrire");
            return;
        }
        
        // Désactiver le bouton pendant la transcription
        transcribeBtn.disabled = true;
        transcribeBtn.classList.add('disabled');
        
        // Afficher le conteneur de transcription et l'état de chargement
        transcriptionContainer.classList.remove('hidden');
        transcriptionStatus.classList.remove('hidden');
        transcriptionContent.classList.add('hidden');
        transcriptionError.classList.add('hidden');
        
        // Faire défiler vers le conteneur de transcription
        transcriptionContainer.scrollIntoView({ behavior: 'smooth' });
        
        console.log(`Début de la transcription pour la vidéo ID: ${videoData.video_id}`);
        
        // Variable pour gérer les timeouts
        let timeoutId = null;
        const timeoutDuration = 300000; // 5 minutes en ms
        
        // Fonction pour gérer le timeout côté client
        const handleTimeout = () => {
            console.warn("La transcription a pris trop de temps (timeout côté client)");
            showTranscriptionError("La transcription a pris trop de temps. Veuillez réessayer ou utiliser une vidéo plus courte.");
            transcribeBtn.disabled = false;
            transcribeBtn.classList.remove('disabled');
        };
        
        // Fonction pour mettre à jour périodiquement le statut d'attente
        let waitingTime = 0;
        const waitInterval = setInterval(() => {
            waitingTime += 5;
            console.log(`Attente de la transcription: ${waitingTime} secondes`);
        }, 5000);
        
        // Démarrer le timer de timeout
        timeoutId = setTimeout(handleTimeout, timeoutDuration);
        
        // Appeler l'API de transcription
        fetch(`${API_BASE_URL}/social/transcribe/${videoData.video_id}`)
            .then(response => {
                console.log(`Réponse reçue avec statut: ${response.status}`);
                // Annuler le timeout puisque nous avons reçu une réponse
                clearTimeout(timeoutId);
                clearInterval(waitInterval);
                
                if (!response.ok) {
                    // Vérifier si la réponse est JSON ou non
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return response.json().then(data => {
                            throw new Error(data.error || `Erreur ${response.status}`);
                        });
                    } else {
                        // Si ce n'est pas du JSON, renvoyer une erreur générique
                        if (response.status === 504) {
                            throw new Error(`Le serveur a mis trop de temps à répondre (erreur 504). La vidéo est peut-être trop longue.`);
                        } else {
                            throw new Error(`Le serveur a renvoyé une erreur (${response.status})`);
                        }
                    }
                }
                return response.json();
            })
            .then(data => {
                console.log("Transcription reçue avec succès");
                transcriptionData = data;
                displayTranscription(data.transcription);
            })
            .catch(error => {
                console.error('Erreur de transcription:', error);
                showTranscriptionError(error.message || "Erreur lors de la transcription");
            })
            .finally(() => {
                // Réactiver le bouton
                transcribeBtn.disabled = false;
                transcribeBtn.classList.remove('disabled');
                // S'assurer que les intervalles sont nettoyés
                clearTimeout(timeoutId);
                clearInterval(waitInterval);
            });
    }

    // Afficher la transcription
    function displayTranscription(text) {
        transcriptionStatus.classList.add('hidden');
        transcriptionContent.classList.remove('hidden');
        transcriptionText.textContent = text;
        
        // Préparer le bouton de téléchargement
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        downloadTranscriptionBtn.href = url;
        downloadTranscriptionBtn.download = getPlatformPrefix() + getVideoIdFromUrl(videoUrlInput.value) + '_transcription.txt';
    }
    
    // Afficher une erreur de transcription
    function showTranscriptionError(message) {
        transcriptionStatus.classList.add('hidden');
        transcriptionError.classList.remove('hidden');
        transcriptionError.querySelector('span').textContent = message;
    }
    
    // Copier le texte de la transcription
    function copyTranscriptionText() {
        if (!transcriptionData || !transcriptionData.transcription) {
            return;
        }
        
        navigator.clipboard.writeText(transcriptionData.transcription)
            .then(() => {
                showToast('Transcription copiée dans le presse-papier !');
            })
            .catch(err => {
                console.error('Erreur lors de la copie:', err);
                // Fallback
                const tempTextarea = document.createElement('textarea');
                tempTextarea.value = transcriptionData.transcription;
                document.body.appendChild(tempTextarea);
                tempTextarea.select();
                document.execCommand('copy');
                document.body.removeChild(tempTextarea);
                showToast('Transcription copiée dans le presse-papier !');
            });
    }
    
    // Télécharger le texte de transcription
    function downloadTranscriptionText(e) {
        // Le téléchargement est géré par l'attribut href et download du lien
        // Cette fonction est laissée pour d'éventuelles modifications futures
    }
    
    // Fermer le conteneur de transcription
    function closeTranscription() {
        transcriptionContainer.classList.add('hidden');
    }

    // Obtenir un préfixe pour le nom de fichier basé sur la plateforme
    function getPlatformPrefix() {
        return platformSelect.value === 'instagram' ? 'instagram_' : 'tiktok_';
    }

    // Extraire l'ID de la vidéo depuis l'URL
    function getVideoIdFromUrl(url) {
        let videoId = 'video';
        
        try {
            if (platformSelect.value === 'instagram') {
                const match = url.match(/instagram\.com\/(?:p|reel)\/([^/?]+)/);
                if (match && match[1]) {
                    videoId = match[1];
                }
            } else if (platformSelect.value === 'tiktok') {
                const match = url.match(/video\/(\d+)/);
                if (match && match[1]) {
                    videoId = match[1];
                }
            }
        } catch (e) {
            console.error('Erreur lors de l\'extraction de l\'ID:', e);
        }
        
        return videoId;
    }

    // Démarrer le compte à rebours d'expiration
    function startExpiryCountdown(expirySeconds) {
        // Nettoyer l'intervalle précédent s'il existe
        if (expiryInterval) {
            clearInterval(expiryInterval);
        }
        
        // Convertir en minutes pour l'affichage
        let remainingMinutes = Math.floor(expirySeconds / 60);
        expiryTime.textContent = remainingMinutes;
        
        // Mettre à jour chaque minute
        expiryInterval = setInterval(() => {
            remainingMinutes--;
            
            if (remainingMinutes <= 0) {
                clearInterval(expiryInterval);
                resetUI();
                showError('La vidéo a expiré. Veuillez la télécharger à nouveau.');
            } else {
                expiryTime.textContent = remainingMinutes;
            }
        }, 60000); // Mise à jour chaque minute
    }

    // Copier le lien de la vidéo dans le presse-papier
    function copyVideoLink() {
        if (!videoData || !videoData.video_url) {
            return;
        }
        
        // Utiliser l'API Clipboard
        navigator.clipboard.writeText(videoData.video_url)
            .then(() => {
                showToast('Lien copié dans le presse-papier !');
            })
            .catch(err => {
                console.error('Erreur lors de la copie:', err);
                // Fallback pour les navigateurs qui ne supportent pas l'API Clipboard
                const tempInput = document.createElement('input');
                document.body.appendChild(tempInput);
                tempInput.value = videoData.video_url;
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                showToast('Lien copié dans le presse-papier !');
            });
    }

    // Afficher un message toast temporaire
    function showToast(message) {
        toast.textContent = message;
        toast.classList.remove('hidden');
        
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }

    // Afficher une erreur
    function showError(message) {
        errorContainer.classList.remove('hidden');
        errorText.textContent = message;
    }

    // Réinitialiser l'interface utilisateur
    function resetUI(clearInput = true) {
        // Cacher tous les conteneurs de statut
        statusContainer.classList.add('hidden');
        resultContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
        transcriptionContainer.classList.add('hidden');
        
        // Réinitialiser la vidéo
        videoPreview.src = '';
        
        // Nettoyer l'intervalle d'expiration
        if (expiryInterval) {
            clearInterval(expiryInterval);
            expiryInterval = null;
        }
        
        // Réinitialiser les données
        videoData = null;
        transcriptionData = null;
        
        // Optionnellement effacer l'entrée
        if (clearInput) {
            videoUrlInput.value = '';
        }
        
        // Remettre le focus sur l'entrée
        videoUrlInput.focus();
    }
});

// Détection du thème sombre du système
function detectDarkMode() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.body.classList.add('dark-mode');
    }
    
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (e.matches) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    });
}

// Appeler la détection du thème sombre
detectDarkMode();