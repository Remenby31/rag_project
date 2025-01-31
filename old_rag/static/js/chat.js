function chatApp() {
    return {
        messages: [],
        newMessage: '',
        isLoading: false,
        messageId: 0,
        showSettings: false,
        maxPassages: 5,

        init() {
            // Auto-scroll when new messages are added
            this.$watch('messages', () => {
                this.$nextTick(() => {
                    const container = document.getElementById('chat-messages');
                    container.scrollTop = container.scrollHeight;
                });
            });
        },

        async sendMessage() {
            if (!this.newMessage.trim()) return;

            // Add user message
            this.messages.push({
                id: this.messageId++,
                content: this.newMessage,
                type: 'user'
            });

            const userMessage = this.newMessage;
            this.newMessage = '';
            this.isLoading = true;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        message: userMessage,
                        maxPassages: this.maxPassages
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Add assistant message with relevant passages
                    this.messages.push({
                        id: this.messageId++,
                        content: data.response,
                        type: 'assistant',
                        passages: data.relevant_passages.map(passage => ({
                            content: passage.content,
                            metadata: passage.metadata,
                            isExpanded: false
                        })),
                        showPassages: false
                    });
                } else {
                    throw new Error(data.error || 'Une erreur est survenue');
                }
            } catch (error) {
                console.error('Error:', error);
                this.messages.push({
                    id: this.messageId++,
                    content: "Désolé, une erreur est survenue. Veuillez réessayer.",
                    type: 'assistant'
                });
            } finally {
                this.isLoading = false;
            }
        }
    };
}