// Configuration
const DOM = {
    messageInput: document.getElementById('messageInput'),
    chatMessages: document.getElementById('chatMessages'),
    fileInput: document.getElementById('fileUpload'),
    settingsModal: document.getElementById('settingsModal'),
    dropZone: document.getElementById('dropZone'),
    fileStatus: document.getElementById('fileStatus')
};

let isProcessing = false;
let currentSources = [];

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initializeDragAndDrop();
    setupEventListeners();
});

function setupEventListeners() {
    DOM.fileInput.addEventListener('change', handleFileSelect);
    document.getElementById('settingsButton').addEventListener('click', toggleSettings);
}

function initializeDragAndDrop() {
    document.addEventListener('dragover', e => {
        e.preventDefault();
        DOM.dropZone.classList.add('active');
    });

    document.addEventListener('dragleave', () => {
        DOM.dropZone.classList.remove('active');
    });

    document.addEventListener('drop', e => {
        e.preventDefault();
        DOM.dropZone.classList.remove('active');
        if (e.dataTransfer.files.length) {
            DOM.fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
}

// File Handling
function handleFileSelect() {
    const files = DOM.fileInput.files;
    if (files.length === 0) return;

    DOM.fileStatus.textContent = `${files.length} fichier${files.length > 1 ? 's' : ''} sélectionné${files.length > 1 ? 's' : ''}`;
    uploadFiles(files);
}

async function uploadFiles(files) {
    if (isProcessing) return;
    isProcessing = true;

    try {
        const formData = new FormData();
        Array.from(files).forEach(file => formData.append('file', file)); // Changé de 'files' à 'file'
        formData.append('api_key', getCookie('api_key'));

        const response = await fetch('/upload', { 
            method: 'POST', 
            body: formData 
        });
        
        if (!response.ok) throw await response.json();

        showStatusMessage('Fichiers transférés avec succès', 'success');
        DOM.fileStatus.textContent += ' ✓';
    } catch (error) {
        showStatusMessage(`Erreur: ${error.error || 'Échec du transfert'}`, 'error');
    } finally {
        setTimeout(() => DOM.fileStatus.textContent = '', 3000);
        isProcessing = false;
    }
}

// Chat Handling
let currentMessageContent = null;
let currentMessageDiv = null;

async function sendMessage() {
    if (isProcessing || !DOM.messageInput.value.trim()) return;
    isProcessing = true;

    const message = DOM.messageInput.value.trim();
    addMessage(message, 'user');
    DOM.messageInput.value = '';
    currentMessageContent = '';

    try {
        const apiKey = getCookie('api_key');
        if (!apiKey) throw new Error('API key missing');

        const eventSource = new EventSource(`/chat?message=${encodeURIComponent(message)}&api_key=${apiKey}`);
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'sources') {
                    currentSources = data.content;
                    // Initialiser le message bot sans les sources
                    currentMessageDiv = addMessage('', 'bot');
                } 
                else if (data.type === 'response') {
                    currentMessageContent += data.content;
                    // Mettre à jour le contenu sans les sources
                    updateMessageContent(currentMessageContent);
                }
                else if (data.type === 'status' && data.content === 'done') {
                    // Ajouter les sources une fois que tout est terminé
                    finalizeBotMessage(currentMessageContent, currentSources);
                    currentSources = null;
                    currentMessageContent = null;
                    currentMessageDiv = null;
                    eventSource.close();
                    isProcessing = false;
                }
                else if (data.type === 'error') {
                    showStatusMessage(data.content, 'error');
                    eventSource.close();
                }
            } catch (error) {
                console.error('Error parsing SSE:', error);
            }
        };

        eventSource.onerror = () => {
            eventSource.close();
            isProcessing = false;
        };

    } catch (error) {
        showStatusMessage(error.message, 'error');
        isProcessing = false;
    }
}

function updateMessageContent(content) {
    if (!currentMessageDiv) return;
    currentMessageDiv.innerHTML = DOMPurify.sanitize(marked.parse(content));
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
}

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = `<i class="fas fa-${type === 'bot' ? 'robot' : 'user'}"></i>`;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (content) {
        contentDiv.innerHTML = DOMPurify.sanitize(marked.parse(content));
    }
    
    wrapper.appendChild(contentDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(wrapper);
    DOM.chatMessages.appendChild(messageDiv);
    
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
    return contentDiv;
}

function finalizeBotMessage(content, sources) {
    if (!currentMessageDiv) return;
    
    const wrapper = currentMessageDiv.parentElement;
    
    // Mettre à jour le contenu final
    currentMessageDiv.innerHTML = DOMPurify.sanitize(marked.parse(content));
    
    // Ajouter les sources à la fin
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = `
            <details>
                <summary>Sources (${sources.length})</summary>
                ${sources.map(s => `
                    <div class="source-item">
                        <i class="fas fa-file-alt"></i>
                        <span>${s.source} - ${s.content}</span>
                    </div>
                `).join('')}
            </details>
        `;
        wrapper.appendChild(sourcesDiv);
    }
    
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
}

// UI Helpers
function toggleSettings() {
    DOM.settingsModal.style.display = 
        DOM.settingsModal.style.display === 'block' ? 'none' : 'block';
}

function showStatusMessage(message, type) {
    const status = document.getElementById('modelStatus');
    status.textContent = message;
    status.style.color = type === 'error' ? '#dc3545' : '#10a37f'; // Remplace var(--primary)
}

function setApiKey() {
    const apiKey = document.getElementById('apiKey').value;
    const provider = document.getElementById('apiProvider').value;
    
    if (apiKey.length < 8) {
        showStatusMessage('Clé API invalide', 'error');
        return;
    }
    
    setCookie('api_key', apiKey, 7);
    setCookie('api_provider', provider, 7);
    DOM.settingsModal.style.display = 'none';
    showStatusMessage('Configuration sauvegardée', 'success');
}

// Cookie Handling
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

// Close modal on outside click
window.onclick = function(event) {
    if (event.target === DOM.settingsModal) {
        DOM.settingsModal.style.display = 'none';
    }
}