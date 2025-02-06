let activeDownloads = new Map();

// Ajout des fonctions de gestion des cookies
function setCookie(name, value, days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 86400000));
    document.cookie = `${name}=${value};expires=${date.toUTCString()};path=/`;
}

function getCookie(name) {
    return document.cookie.split('; ')
        .find(row => row.startsWith(`${name}=`))
        ?.split('=')[1] || '';
}

async function searchVideos() {
    const query = document.getElementById('searchInput').value;
    const response = await fetch('/youtube/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query, limit: 5})
    });
    
    const data = await response.json();
    if (data.success) {
        displayResults(data.results);
    }
}

function displayResults(results) {
    const container = document.getElementById('results');
    container.innerHTML = '';
    
    results.forEach(([title, url]) => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="title">
                <i class="fab fa-youtube"></i>
                ${title}
            </div>
            <button onclick="downloadVideo('${url}')">
                <i class="fas fa-closed-captioning"></i> Transcrire
            </button>
        `;
        container.appendChild(div);
        
        // Animation d'apparition
        setTimeout(() => div.style.opacity = '1', 10);
    });
}

async function downloadVideo(url) {
    // Récupérer la clé API et le provider des cookies
    const apiKey = getCookie('api_key');
    const provider = getCookie('api_provider');

    if (!apiKey) {
        alert('Veuillez configurer votre clé API dans les paramètres');
        return;
    }

    const response = await fetch('/youtube/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            url,
            api_key: apiKey,
            provider: provider
        })
    });
    
    const data = await response.json();
    if (data.success) {
        createDownloadItem(data.task_id);
        monitorDownload(data.task_id);
    } else {
        alert(data.error || 'Erreur lors de la transcription');
    }
}

function createDownloadItem(taskId) {
    const div = document.createElement('div');
    div.id = `download-${taskId}`;
    div.className = 'download-item';
    div.style.opacity = '0';
    div.innerHTML = `
        <div class="download-header">
            <i class="fas fa-sync fa-spin"></i>
            <span class="status">Démarrage...</span>
        </div>
        <div class="progress-bar">
            <div class="progress" style="width: 0%"></div>
        </div>
    `;
    document.getElementById('downloadsList').appendChild(div);
    
    // Animation d'apparition
    setTimeout(() => div.style.opacity = '1', 10);
}

async function monitorDownload(taskId) {
    activeDownloads.set(taskId, true);
    
    while (activeDownloads.get(taskId)) {
        const response = await fetch(`/youtube/status/${taskId}`);
        const status = await response.json();
        
        updateDownloadStatus(taskId, status);
        
        if (status.status === 'completed' || status.status === 'error') {
            activeDownloads.delete(taskId);
            break;
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

function updateDownloadStatus(taskId, status) {
    const element = document.getElementById(`download-${taskId}`);
    if (!element) return;
    
    const progressBar = element.querySelector('.progress');
    const statusText = element.querySelector('.status');
    const icon = element.querySelector('.download-header i');
    
    // Mise à jour de la progression
    if (status.progress !== undefined) {
        progressBar.style.width = `${status.progress}%`;
    }

    switch (status.status) {
        case 'starting':
            statusText.textContent = 'Démarrage...';
            icon.className = 'fas fa-sync fa-spin';
            break;
            
        case 'downloading':
            statusText.textContent = `Téléchargement: ${Math.round(status.progress)}%`;
            icon.className = 'fas fa-download';
            break;
            
        case 'transcribing':
            let segmentInfo = status.current_segment ? 
                ` (${status.current_segment}/${status.total_segments})` : '';
            statusText.textContent = `Transcription: ${Math.round(status.progress)}%${segmentInfo}`;
            icon.className = 'fas fa-closed-captioning';
            break;
            
        case 'completed':
            progressBar.style.width = '100%';
            statusText.textContent = 'Transcription terminée';
            icon.className = 'fas fa-check-circle';
            
            const transcriptDiv = document.createElement('div');
            transcriptDiv.className = 'transcript';
            transcriptDiv.innerHTML = `
                <div class="transcript-header">
                    <i class="fas fa-file-alt"></i> Transcription
                    <div class="transcript-actions">
                        <button onclick="copyTranscript(this)" class="action-btn">
                            <i class="fas fa-copy"></i> Copier
                        </button>
                        <a href="${status.download_url}" download class="action-btn">
                            <i class="fas fa-download"></i> Télécharger .txt
                        </a>
                    </div>
                </div>
                <div class="transcript-content">${status.transcript}</div>
            `;
            element.appendChild(transcriptDiv);
            break;
            
        case 'error':
            statusText.textContent = `Erreur: ${status.error}`;
            icon.className = 'fas fa-exclamation-circle';
            element.classList.add('error');
            break;
    }
}

function copyTranscript(btn) {
    const content = btn.closest('.transcript').querySelector('.transcript-content').textContent;
    navigator.clipboard.writeText(content);
    
    // Feedback visuel
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Copié!';
    setTimeout(() => btn.innerHTML = originalText, 2000);
}
