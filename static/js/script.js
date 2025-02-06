// Configuration
const DOM = {
    messageInput: document.getElementById('messageInput'),
    chatMessages: document.getElementById('chatMessages'),
    fileInput: document.getElementById('fileUpload'),
    settingsModal: document.getElementById('settingsModal'),
    dropZone: document.getElementById('dropZone'),
    fileStatus: document.getElementById('fileStatus')
};

// Ajout de la clé de stockage pour l'historique
const localStorageKey = 'chatHistory';

// Configuration de marked
marked.setOptions({
    breaks: true,           // Permet les sauts de ligne avec un seul retour à la ligne
    gfm: true,             // GitHub Flavored Markdown
    headerIds: false,      // Désactive les IDs automatiques sur les en-têtes
    mangle: false,         // Désactive la transformation des liens email
    smartLists: true,      // Listes plus intelligentes
    xhtml: false           // Pas de tags auto-fermants style XHTML
});

let isProcessing = false;
let currentSources = [];
let chatHistory = [];

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initializeDragAndDrop();
    setupEventListeners();
    loadApiSettings();
    loadChatHistory(); // Ajout du chargement de l'historique
});

function setupEventListeners() {
    DOM.fileInput.addEventListener('change', handleFileSelect);
    document.getElementById('settingsButton').addEventListener('click', toggleSettings);
    document.getElementById('togglePassword').addEventListener('click', togglePasswordVisibility);
    document.getElementById('clearHistoryButton').addEventListener('click', clearHistory);
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
        formData.append('provider', getCookie('api_provider')); // Ajout du provider

        if (!formData.get('api_key')) {
            throw {error: 'Clé API manquante. Veuillez configurer votre clé API.'};
        }

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
let streamBuffer = '';

async function sendMessage() {
    if (isProcessing || !DOM.messageInput.value.trim()) return;
    isProcessing = true;

    const message = DOM.messageInput.value.trim();
    chatHistory.push({ role: 'user', content: message });
    
    addMessage(message, 'user');
    DOM.messageInput.value = '';
    streamBuffer = '';
    currentMessageDiv = addMessage('', 'bot');
    
    try {
        const apiKey = getCookie('api_key');
        const provider = getCookie('api_provider');
        const nbResults = getCookie('nb_results') || '5'; // valeur par défaut si non définie
        if (!apiKey) throw new Error('API key missing');

        const params = new URLSearchParams({
            message: message,
            api_key: apiKey,
            provider: provider,
            nb_results: nbResults,
            history: JSON.stringify(chatHistory)
        });

        const eventSource = new EventSource(`/chat?${params.toString()}`);
        let hasReceivedData = false;

        eventSource.onopen = () => {
            hasReceivedData = false;
            showStatusMessage('Connexion établie', 'success');
        };
        
        eventSource.addEventListener('message', function(event) {
            try {
                hasReceivedData = true;
                const data = JSON.parse(event.data);
                
                if (data.type === 'sources') {
                    currentSources = data.content;
                    showStatusMessage('Génération en cours...', 'success');
                } 
                else if (data.type === 'response') {
                    streamBuffer += data.content;
                    updateMessageContent(streamBuffer);
                }
                else if (data.type === 'status' && data.content === 'done') {
                    chatHistory.push({ role: 'assistant', content: streamBuffer });
                    saveChatHistory();
                    finalizeBotMessage(streamBuffer, currentSources);
                    eventSource.close();
                    isProcessing = false;
                    showStatusMessage('Prêt', 'success');
                }
                else if (data.type === 'error') {
                    showStatusMessage(data.content, 'error');
                    eventSource.close();
                    isProcessing = false;
                }
            } catch (error) {
                console.error('Error parsing SSE:', error);
            }
        });

        eventSource.onerror = function(error) {
            if (!hasReceivedData) {
                console.error('SSE Error:', error);
                eventSource.close();
                isProcessing = false;
                showStatusMessage('Erreur de connexion', 'error');
            }
        };

    } catch (error) {
        showStatusMessage(error.message, 'error');
        isProcessing = false;
    }
}

function updateMessageContent(content) {
    if (!currentMessageDiv) return;
    
    try {
        const htmlContent = DOMPurify.sanitize(marked.parse(content), {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span'],
            ALLOWED_ATTR: ['href', 'class']
        });

        requestAnimationFrame(() => {
            currentMessageDiv.innerHTML = htmlContent;
            
            // Ajouter le bouton de copie
            const copyButton = document.createElement('button');
            copyButton.className = 'copy-button';
            copyButton.innerHTML = '<i class="fas fa-copy"></i> Copier';
            copyButton.onclick = () => {
                navigator.clipboard.writeText(content);
                copyButton.innerHTML = '<i class="fas fa-check"></i> Copié';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i> Copier';
                }, 2000);
            };
            
            currentMessageDiv.parentElement.appendChild(copyButton);
            
            if (window.Prism) {
                Prism.highlightAllUnder(currentMessageDiv);
            }
            DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
        });
    } catch (error) {
        console.error('Error updating message content:', error);
    }
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
        const htmlContent = marked.parse(content);
        contentDiv.innerHTML = DOMPurify.sanitize(htmlContent, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a'],
            ALLOWED_ATTR: ['href']
        });
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
    
    // Mise à jour finale du contenu avec le même traitement que pendant le streaming
    updateMessageContent(content);

    // Ajout des sources si disponibles
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
    const apiKey = document.getElementById('apiKey').value.trim();
    const provider = document.getElementById('apiProvider').value;
    const nbResults = document.getElementById('nbResults').value;
    
    const validation = validateApiKey(apiKey);
    
    if (!validation.valid) {
        showStatusMessage(validation.message, 'error');
        return;
    }
    
    setCookie('api_key', apiKey, 30);
    setCookie('api_provider', provider, 30);
    setCookie('nb_results', nbResults, 30);
    
    toggleSettings();
    showStatusMessage('Configuration API sauvegardée', 'success');
}

function loadApiSettings() {
    const apiKey = getCookie('api_key');
    const provider = getCookie('api_provider');
    const nbResults = getCookie('nb_results');
    
    if (apiKey) {
        document.getElementById('apiKey').value = apiKey;
        showStatusMessage('Configuration API chargée', 'success');
    }
    
    if (provider) {
        document.getElementById('apiProvider').value = provider;
    }

    if (nbResults) {
        document.getElementById('nbResults').value = nbResults;
    }
}

function togglePasswordVisibility() {
    const apiKeyInput = document.getElementById('apiKey');
    const toggleBtn = document.getElementById('togglePassword');
    
    if (apiKeyInput.type === 'password') {
        apiKeyInput.type = 'text';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        apiKeyInput.type = 'password';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

function validateApiKey(apiKey) {
    const provider = document.getElementById('apiProvider').value;
    
    if (!apiKey) {
        return { valid: false, message: 'La clé API est requise' };
    }
    
    if (provider === 'openai' && !apiKey.startsWith('sk-')) {
        return { valid: false, message: 'La clé OpenAI doit commencer par sk-' };
    }
    
    if (apiKey.length < 20) {
        return { valid: false, message: 'La clé API semble trop courte' };
    }
    
    return { valid: true };
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

function loadChatHistory() {
    const saved = localStorage.getItem(localStorageKey);
    if (saved) {
        chatHistory = JSON.parse(saved);
        // Restaurer les messages précédents
        chatHistory.forEach(msg => {
            addMessage(msg.content, msg.role === 'assistant' ? 'bot' : 'user');
        });
    }
}

function saveChatHistory() {
    localStorage.setItem(localStorageKey, JSON.stringify(chatHistory));
}

function clearHistory() {
    if (confirm('Voulez-vous vraiment effacer tout l\'historique de conversation ?')) {
        chatHistory = [];
        localStorage.removeItem(localStorageKey);
        DOM.chatMessages.innerHTML = '';
    }
}