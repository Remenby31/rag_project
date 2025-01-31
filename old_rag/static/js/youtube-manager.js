function youtubeManager() {
    return {
        searchQuery: '',
        searchLimit: 5,
        searchResults: [],
        videoInputs: [],
        tasks: [],
        activePollingTasks: new Set(), // Pour suivre les tâches en cours de polling
        transcriptionModel: 'local',

        init() {
            this.videoInputs = [{ title: '', url: '' }];
        },

        async searchVideos() {
            if (!this.searchQuery) return;

            try {
                const response = await fetch('/api/youtube/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: this.searchQuery,
                        limit: parseInt(this.searchLimit),
                        lang: 'US'
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    this.searchResults = data.videos;
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                alert('Erreur lors de la recherche: ' + error.message);
            }
        },

        addSearchResult(result) {
            const exists = this.videoInputs.some(v => v.url === result.url);
            if (!exists) {
                this.videoInputs.push({
                    title: result.title,
                    url: result.url
                });
                
                const index = this.searchResults.findIndex(r => r.url === result.url);
                if (index !== -1) {
                    this.searchResults[index].isAdded = true;
                }
            }
        },

        addVideo() {
            this.videoInputs.push({ title: '', url: '' });
        },

        removeVideo(index) {
            this.videoInputs.splice(index, 1);
            if (this.videoInputs.length === 0) {
                this.addVideo();
            }
        },

        async submitVideos() {
            console.log('Toutes les entrées:', this.videoInputs);
            const videos = this.videoInputs.filter(v => v.title && v.url);
            console.log('Vidéos filtrées:', videos);
            
            if (videos.length === 0) {
                console.warn('Aucune vidéo valide à soumettre');
                return;
            }

            try {
                const requestBody = {
                    videos,
                    transcriptionModel: this.transcriptionModel
                };
                console.log('Envoi de la requête avec:', requestBody);

                const response = await fetch('/api/youtube/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });

                console.log('Status de la réponse:', response.status);
                console.log('Headers de la réponse:', Object.fromEntries(response.headers.entries()));
                
                const responseText = await response.text();
                console.log('Réponse brute:', responseText);

                let data;
                try {
                    data = JSON.parse(responseText);
                    console.log('Données parsées:', data);
                } catch (e) {
                    console.error('Erreur parsing JSON:', e);
                    throw new Error('Réponse invalide du serveur');
                }

                if (response.ok) {
                    if (!data.task_id) {
                        throw new Error('Pas de task_id dans la réponse');
                    }

                    const newTask = {
                        id: data.task_id,
                        status: 'pending',
                        progress: 0,
                        current_file: videos[0].title
                    };
                    
                    this.tasks.unshift(newTask);
                    // Démarrer le polling directement
                    setInterval(() => this.pollTask(data.task_id), 2000);
                    this.videoInputs = [{ title: '', url: '' }];
                } else {
                    throw new Error(data.error || 'Erreur serveur');
                }
            } catch (error) {
                console.error('Erreur complète:', error);
                console.error('Stack trace:', error.stack);
                alert('Erreur lors de la soumission: ' + error.message);
            }
        },

        async pollTask(taskId) {
            try {
                const response = await fetch(`/api/youtube/status/${taskId}`);
                if (!response.ok) return;
                
                const taskData = await response.json();
                
                // Mettre à jour la tâche dans la liste
                const taskIndex = this.tasks.findIndex(t => t.id === taskId);
                if (taskIndex !== -1) {
                    this.tasks[taskIndex] = { id: taskId, ...taskData };
                }

                // Trier les tâches
                this.tasks.sort((a, b) => {
                    const activeStatuses = ['downloading', 'transcribing', 'indexing'];
                    const aActive = activeStatuses.includes(a.status);
                    const bActive = activeStatuses.includes(b.status);
                    return aActive && !bActive ? -1 : (!aActive && bActive ? 1 : 0);
                });
            } catch (error) {
                console.error('Erreur lors du polling:', error);
            }
        },

        getStatusColor(status) {
            const colors = {
                'pending': 'bg-yellow-100 text-yellow-800',
                'downloading': 'bg-blue-100 text-blue-800',
                'transcribing': 'bg-purple-100 text-purple-800',
                'indexing': 'bg-indigo-100 text-indigo-800',
                'completed': 'bg-green-100 text-green-800',
                'error': 'bg-red-100 text-red-800'
            };
            return colors[status] || 'bg-gray-100 text-gray-800';
        }
    };
}