class FileManager {
    constructor() {
        this.files = [];
        this.isGridView = true;
        this.initElements();
        this.initEventListeners();
        this.loadFiles();
    }

    initElements() {
        this.fileList = document.getElementById('fileList');
        this.dropZone = document.getElementById('dropZone');
        this.searchInput = document.getElementById('searchInput');
        this.viewToggle = document.getElementById('viewToggle');
        this.fileInput = document.getElementById('fileInput');
        this.template = document.getElementById('fileTemplate');
    }

    initEventListeners() {
        this.dropZone.addEventListener('dragover', e => {
            e.preventDefault();
            this.dropZone.classList.add('active');
        });

        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('active');
        });

        this.dropZone.addEventListener('drop', e => this.handleDrop(e));
        this.fileInput.addEventListener('change', e => this.handleFileSelect(e));
        this.searchInput.addEventListener('input', () => this.filterFiles());
        this.viewToggle.addEventListener('click', () => this.toggleView());
    }

    async loadFiles() {
        try {
            const response = await fetch('/list_files');
            const data = await response.json();
            this.files = data.files;
            this.renderFiles();
            this.updateStats();
        } catch (error) {
            console.error('Erreur lors du chargement des fichiers:', error);
        }
    }

    getFileIcon(filename) {
        const extension = filename.toLowerCase().split('.').pop();
        switch (extension) {
            case 'pdf':
                return 'fa-file-pdf';
            case 'doc':
            case 'docx':
                return 'fa-file-word';
            case 'txt':
                return 'fa-file-alt';
            case 'rtf':
                return 'fa-file-alt';
            default:
                return 'fa-file';
        }
    }

    renderFiles() {
        this.fileList.innerHTML = '';
        const filteredFiles = this.filterFiles();
        
        filteredFiles.forEach(file => {
            const element = this.template.content.cloneNode(true);
            const fileItem = element.querySelector('.file-item');
            fileItem.setAttribute('data-filename', file);
            
            const loading = element.querySelector('.file-loading');
            loading.classList.add('hidden');
            
            const fileInfo = element.querySelector('.file-info');
            
            // Mettre à jour l'icône en fonction du type de fichier
            const iconClass = this.getFileIcon(file);
            fileItem.querySelector('.file-icon i').className = `fas ${iconClass}`;
            
            // Ajouter le nom du fichier avec une classe pour contrôler l'overflow
            fileItem.querySelector('.file-name').textContent = file;
            
            // Calculer et formater la taille du fichier
            fetch(`/file_size/${encodeURIComponent(file)}`)
                .then(response => response.json())
                .then(data => {
                    const size = this.formatFileSize(data.size);
                    fileInfo.querySelector('.file-meta').textContent = size;
                })
                .catch(error => console.error('Erreur:', error));
            
            fileItem.querySelector('.delete-btn').onclick = () => this.deleteFile(file);
            
            fileItem.style.animationDelay = `${Math.random() * 0.3}s`;
            this.fileList.appendChild(element);
        });
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async deleteFile(filename) {
        if (!confirm(`Supprimer ${filename} ?`)) return;

        const fileItem = this.fileList.querySelector(`[data-filename="${filename}"]`);
        const loading = fileItem.querySelector('.file-loading');
        loading.classList.remove('hidden');

        try {
            const response = await fetch(`/delete/${filename}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.files = this.files.filter(f => f !== filename);
                this.renderFiles();
                this.updateStats();
            } else {
                throw new Error('Erreur lors de la suppression');
            }
        } catch (error) {
            console.error('Erreur:', error);
            loading.classList.add('hidden');
        }
    }

    filterFiles() {
        const searchTerm = this.searchInput.value.toLowerCase();
        return this.files.filter(file => 
            file.toLowerCase().includes(searchTerm)
        );
    }

    toggleView() {
        this.isGridView = !this.isGridView;
        this.fileList.classList.toggle('list-view');
        const icon = this.viewToggle.querySelector('i');
        icon.className = this.isGridView ? 
            'fas fa-list' : 
            'fas fa-th-large';
        
        // Ajouter une animation subtile
        this.fileList.style.opacity = '0';
        this.fileList.style.transition = 'opacity 0.2s ease-out';
        
        setTimeout(() => {
            this.fileList.style.opacity = '1';
        }, 50);
    }

    updateStats() {
        document.getElementById('fileCount').textContent = 
            `${this.files.length} fichier${this.files.length > 1 ? 's' : ''}`;
    }

    async handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('active');
        const files = e.dataTransfer.files;
        await this.uploadFiles(files);
    }

    async handleFileSelect(e) {
        const files = e.target.files;
        await this.uploadFiles(files);
    }

    async uploadFiles(files) {
        const uploads = Array.from(files).map(async file => {
            const formData = new FormData();
            formData.append('file', file);
            
            const apiKey = this.getCookie('api_key');
            if (!apiKey) {
                console.error('Clé API manquante');
                return;
            }
            formData.append('api_key', apiKey);

            // Créer un élément temporaire pour le fichier en cours d'upload
            const tempElement = this.template.content.cloneNode(true);
            const fileItem = tempElement.querySelector('.file-item');
            fileItem.setAttribute('data-filename', file.name);
            fileItem.querySelector('.file-name').textContent = file.name;
            fileItem.querySelector('.file-meta').textContent = this.formatFileSize(file.size);
            fileItem.querySelector('.file-loading').classList.remove('hidden');
            
            this.fileList.appendChild(tempElement);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Erreur lors de l\'upload');
                }
            } catch (error) {
                console.error('Erreur:', error.message);
            }
        });

        await Promise.all(uploads);
        await this.loadFiles(); // Recharger tous les fichiers après les uploads
    }

    getCookie(name) {
        return document.cookie.split('; ')
            .find(row => row.startsWith(`${name}=`))
            ?.split('=')[1] || '';
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    new FileManager();
});
