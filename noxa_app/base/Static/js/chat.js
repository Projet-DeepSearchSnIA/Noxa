/**
 * NOXA Chat - JavaScript pour l'interface chatbot
 */

class NoxaChat {
    constructor(config) {
        this.config = config;
        this.conversationId = config.conversationId;
        this.isLoading = false;

        this.init();
    }

    init() {
        // Éléments DOM
        this.elements = {
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            chatForm: document.getElementById('chatForm'),
            messagesContainer: document.getElementById('messagesContainer'),
            charCount: document.getElementById('charCount'),
            typingIndicator: document.getElementById('typingIndicator'),
            conversationTitle: document.getElementById('conversationTitle'),
            newChatBtn: document.getElementById('newChatBtn'),
            newChatModal: document.getElementById('newChatModal'),
            closeModal: document.getElementById('closeModal'),
            cancelNewChat: document.getElementById('cancelNewChat'),
            confirmNewChat: document.getElementById('confirmNewChat'),
            newChatTopic: document.getElementById('newChatTopic'),
            conversationsList: document.getElementById('conversationsList'),
            chatWelcome: document.getElementById('chatWelcome'),
            attachBtn: document.getElementById('attachBtn'),
            fileInput: document.getElementById('fileInput'),
            filePreviewContainer: document.getElementById('filePreviewContainer'),
        };

        this.selectedFiles = []; // Changed from single file to array

        this.bindEvents();
        this.processExistingMessages();
        this.scrollToBottom();
    }

    bindEvents() {
        // Formulaire de message
        if (this.elements.chatForm) {
            this.elements.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Textarea auto-resize et compteur
        if (this.elements.messageInput) {
            this.elements.messageInput.addEventListener('input', () => this.handleInput());
            this.elements.messageInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        }

        // Bouton nouvelle conversation - création directe sans modal
        if (this.elements.newChatBtn) {
            this.elements.newChatBtn.addEventListener('click', () => this.createConversation());
        }

        // Modal
        if (this.elements.closeModal) {
            this.elements.closeModal.addEventListener('click', () => this.closeNewChatModal());
        }
        if (this.elements.cancelNewChat) {
            this.elements.cancelNewChat.addEventListener('click', () => this.closeNewChatModal());
        }
        if (this.elements.confirmNewChat) {
            this.elements.confirmNewChat.addEventListener('click', () => this.createConversation());
        }

        // Suggestions de questions
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.dataset.question;
                if (this.elements.messageInput) {
                    this.elements.messageInput.value = question;
                    this.handleInput();
                    this.elements.messageInput.focus();
                }
            });
        });

        // Toggle sources
        document.querySelectorAll('.sources-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => this.toggleSources(e));
        });

        // Feedback buttons
        document.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFeedback(e));
        });

        // Delete conversation buttons
        document.querySelectorAll('.delete-conv-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleDeleteConversation(e));
        });

        // Fermer modal en cliquant en dehors
        if (this.elements.newChatModal) {
            this.elements.newChatModal.addEventListener('click', (e) => {
                if (e.target === this.elements.newChatModal) {
                    this.closeNewChatModal();
                }
            });
        }

        // Pièces jointes
        if (this.elements.attachBtn) {
            this.elements.attachBtn.addEventListener('click', () => this.elements.fileInput.click());
        }
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
    }

    handleInput() {
        const input = this.elements.messageInput;
        const charCount = this.elements.charCount;
        const sendBtn = this.elements.sendBtn;

        // Compteur de caractères
        const count = input.value.length;
        charCount.textContent = `${count} / 2000`;

        // Activer/désactiver le bouton d'envoi
        // On autorise l'envoi si on a du texte OU des fichiers
        const hasFiles = this.selectedFiles.length > 0;
        sendBtn.disabled = (count === 0 && !hasFiles) || count > 2000 || this.isLoading;

        // Auto-resize du textarea
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        // Add new files to existing selection
        this.selectedFiles = [...this.selectedFiles, ...files];

        this.updateFilePreview();
        this.handleInput();

        // Clear input to allow re-selecting same files if needed
        e.target.value = '';
    }

    updateFilePreview() {
        const container = this.elements.filePreviewContainer;
        const uploadOptions = document.getElementById('uploadOptions');

        if (!container) return;

        if (this.selectedFiles.length === 0) {
            container.style.display = 'none';
            container.innerHTML = '';
            if (uploadOptions) uploadOptions.style.display = 'none';
            return;
        }

        container.style.display = 'flex';
        container.style.flexWrap = 'wrap';
        container.style.gap = '10px';

        // Show upload options option whenever there are files
        if (uploadOptions) uploadOptions.style.display = 'block';

        container.innerHTML = this.selectedFiles.map((file, index) => `
            <div class="file-preview">
                <div class="file-preview-icon">
                    ${this.getFileIcon(file.type)}
                </div>
                <div class="file-preview-info">
                    <span class="file-preview-name">${this.escapeHtml(file.name)}</span>
                    <span class="file-preview-size">${this.formatFileSize(file.size)}</span>
                </div>
                <button type="button" class="remove-file-btn" data-index="${index}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `).join('');

        // Bind remove events
        container.querySelectorAll('.remove-file-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.removeFile(index);
            });
        });
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFilePreview();
        this.handleInput();
    }

    getFileIcon(type) {
        if (!type || typeof type !== 'string') return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>';

        if (type.startsWith('image/')) return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>';
        if (type.startsWith('audio/')) return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>';
        if (type.startsWith('video/')) return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>';
        if (type === 'application/pdf') return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
        return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    handleKeydown(e) {
        // Envoyer avec Enter (sans Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.elements.sendBtn.disabled) {
                this.handleSubmit(e);
            }
        }
    }

    async handleSubmit(e) {
        e.preventDefault();

        const message = this.elements.messageInput.value.trim();
        // Allow sending if there are files, even if message is empty
        if ((!message && this.selectedFiles.length === 0) || this.isLoading) return;

        // Si pas de conversation active, en créer une d'abord (sans redirection)
        if (!this.conversationId) {
            const created = await this.createConversationSilent();
            if (!created) return;
        }

        this.isLoading = true;
        this.elements.sendBtn.disabled = true;
        this.elements.typingIndicator.style.display = 'flex';

        // Check if save to space is enabled
        const saveToSpace = document.getElementById('saveToSpace')?.checked || false;

        // Ajouter le message utilisateur à l'UI
        // Note: files passed here for UI display only
        this.addMessageToUI('user', message, this.selectedFiles);

        this.elements.messageInput.value = '';

        // Prepare data to send
        const filesToSend = [...this.selectedFiles];

        // Clear selection
        this.selectedFiles = [];
        this.updateFilePreview();
        this.handleInput();

        try {
            console.log("Sending message...", { message, filesToSend, saveToSpace });
            const response = await this.sendMessage(message, filesToSend, saveToSpace);
            console.log("Response received:", response);

            if (response.success) {
                // Ajouter la réponse de l'assistant
                this.addAssistantMessageToUI(response.assistant_message);

                // Mettre à jour le titre si c'est le premier message
                if (response.conversation_title) {
                    this.updateConversationTitle(response.conversation_title);
                }

                // Show notification if files were saved
                if (response.files_saved > 0) {
                    this.showToast(`${response.files_saved} fichier(s) sauvegardé(s) dans votre espace`, 'success');
                }
            } else {
                this.showError(response.error || 'Erreur lors de l\'envoi du message');
            }
        } catch (error) {
            console.error("Error in handleSubmit:", error);
            this.showError('Erreur de connexion : ' + error.message);
        } finally {
            this.isLoading = false;
            this.elements.sendBtn.disabled = false;
            this.elements.typingIndicator.style.display = 'none';
        }
    }

    async sendMessage(message, files = [], saveToSpace = false) {
        const url = this.config.urls.sendMessage;

        let body;
        let headers = {
            'X-CSRFToken': this.config.csrfToken
        };

        if (files.length > 0) {
            body = new FormData();
            body.append('message', message);

            // Append each file with the same key "files"
            files.forEach(file => {
                body.append('files', file);
            });

            if (saveToSpace) {
                body.append('save_to_space', 'true');
            }

            // Browser sets Content-Type automatically for FormData
        } else {
            body = JSON.stringify({ message });
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: body
        });

        return await response.json();
    }

    addMessageToUI(role, content, files = null) {
        console.log("Adding message to UI:", { role, content, files });

        // S'assurer que le container existe
        let container = document.getElementById('messagesContainer');

        if (!container) {
            console.log("Messages container not found, creating one...");
            const main = document.querySelector('.chat-main');
            const inputContainer = document.querySelector('.chat-input-container');

            container = document.createElement('div');
            container.className = 'messages-container';
            container.id = 'messagesContainer';

            if (main && inputContainer) {
                main.insertBefore(container, inputContainer);
            } else if (main) {
                main.appendChild(container);
            } else {
                document.body.appendChild(container); // Fallback extreme
            }
        }

        this.elements.messagesContainer = container;
        container.style.display = 'flex';

        // Masquer l'écran de bienvenue
        if (this.elements.chatWelcome) {
            this.elements.chatWelcome.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;

        let filesHTML = '';
        if (files) {
            const filesArray = Array.isArray(files) ? files : [files];
            filesHTML = filesArray.map(file => `
                <div class="message-file">
                    <div class="file-icon">${this.getFileIcon(file.type)}</div>
                    <div class="file-info">
                        <span class="file-name">${this.escapeHtml(file.name)}</span>
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                    </div>
                </div>
            `).join('');
        }

        const initial = role === 'user' ? 'U' : 'N';

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-${role}">${initial}</div>
            </div>
            <div class="message-content">
                ${filesHTML}
                <div class="message-text">${this.formatMessage(content)}</div>
            </div>
        `;

        messageDiv.classList.add('new-message');
        container.appendChild(messageDiv);
        this.renderMath(messageDiv);
        this.scrollToBottom();
    }

    addAssistantMessageToUI(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-assistant';
        messageDiv.dataset.id = messageData.id;

        let sourcesHTML = '';
        if (messageData.sources && messageData.sources.length > 0) {
            const sourceItems = messageData.sources.map(s => `
                <a href="${s.url}" class="source-item" target="_blank">
                    <strong>${this.escapeHtml(s.title)}</strong>
                    ${s.page_number ? `<span class="source-page">Page ${s.page_number}</span>` : ''}
                    <span class="source-score">${Math.round(s.relevance_score * 100)}%</span>
                </a>
            `).join('');

            sourcesHTML = `
                <div class="message-sources">
                    <button class="sources-toggle">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        ${messageData.sources.length} source${messageData.sources.length > 1 ? 's' : ''}
                    </button>
                    <div class="sources-list" style="display: none;">
                        ${sourceItems}
                    </div>
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-assistant">N</div>
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessage(messageData.content, messageData.sources)}</div>
                <div class="message-extras"></div>
                ${sourcesHTML}
                <div class="message-feedback">
                    <button class="feedback-btn" data-type="helpful" data-id="${messageData.id}" title="Utile">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                        </svg>
                    </button>
                    <button class="feedback-btn" data-type="not-helpful" data-id="${messageData.id}" title="Pas utile">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        messageDiv.classList.add('new-message');
        this.elements.messagesContainer.appendChild(messageDiv);

        // Bind events pour le nouveau message
        messageDiv.querySelectorAll('.sources-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => this.toggleSources(e));
        });
        messageDiv.querySelectorAll('.feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFeedback(e));
        });

        this.renderMath(messageDiv);

        // Render follow-up questions and images if available in metadata
        if (messageData.metadata) {
            const extrasContainer = messageDiv.querySelector('.message-extras');
            this.renderImages(extrasContainer, messageData.metadata.images_used);
            this.renderFollowUpQuestions(extrasContainer, messageData.metadata.follow_up_questions);
        }

        this.scrollToBottom();
    }

    formatMessage(content, sources = []) {
        // Fallback pour content vide
        if (!content) return '';

        // 1. Parsing Markdown
        let html = '';
        if (typeof marked !== 'undefined') {
            html = marked.parse(content);
        } else {
            html = content
                .split('\n\n')
                .map(para => `<p>${para.replace(/\n/g, '<br>')}</p>`)
                .join('');
        }

        // 1.5 Nettoyage de sécurité des tags résiduels (au cas où le backend en aurait raté)
        const tagsToStrip = ['SOURCES_USED', 'IMAGES_USED', 'EQUATIONS_USED', 'FOLLOW_UP_QUESTIONS'];
        tagsToStrip.forEach(tag => {
            const tagPattern = new RegExp(`${tag}\\s*:\\s*.*?(\\n|$)`, 'gi');
            html = html.replace(tagPattern, '');
        });

        // 2. Remplacer les citations [Source: document, page X] par des liens cliquables
        if (sources && sources.length > 0) {
            sources.forEach(s => {
                // Échapper les caractères spéciaux du titre pour la regex
                const escapedTitle = s.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                // Regex pour [Source: Titre, page X] ou [Source: Titre]
                const pattern = new RegExp(`\\[Source:\\s*${escapedTitle}(?:,\\s*page\\s*(\\d+))?\\]`, 'g');

                html = html.replace(pattern, (match, page) => {
                    const pageStr = page ? `, p.${page}` : '';
                    return `<a href="${s.url}" class="source-citation" target="_blank" title="${this.escapeHtml(s.title)}">[Source: ${this.escapeHtml(s.title)}${pageStr}]</a>`;
                });
            });
        }

        return html;
    }

    renderFollowUpQuestions(container, questions) {
        if (!questions || !Array.isArray(questions) || questions.length === 0) return;

        const followUpDiv = document.createElement('div');
        followUpDiv.className = 'follow-up-container';

        followUpDiv.innerHTML = `
            <div class="follow-up-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                Questions suggérées :
            </div>
        `;

        questions.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'follow-up-btn';
            btn.textContent = q;
            btn.addEventListener('click', () => {
                this.elements.messageInput.value = q;
                this.handleInput();
                this.handleSubmit(new Event('submit'));
                // Optionnel : défiler vers le bas immédiatement
                this.scrollToBottom();
            });
            followUpDiv.appendChild(btn);
        });

        container.appendChild(followUpDiv);
    }

    renderImages(container, imagePaths) {
        if (!imagePaths || !Array.isArray(imagePaths) || imagePaths.length === 0) return;

        imagePaths.forEach(path => {
            const imgContainer = document.createElement('div');
            imgContainer.className = 'message-image-container';

            // On suppose que le path est relatif à MEDIA_URL ou complet
            const fullUrl = path.startsWith('http') || path.startsWith('/') ? path : `/media/${path}`;

            imgContainer.innerHTML = `
                <img src="${fullUrl}" class="message-image" alt="Image extraite" loading="lazy" onclick="window.open(this.src, '_blank')">
                <div class="image-caption">Image extraite du document</div>
            `;
            container.appendChild(imgContainer);
        });
    }

    renderMath(element) {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(element, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\(', right: '\\)', display: false },
                    { left: '\\[', right: '\\]', display: true }
                ],
                throwOnError: false
            });
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    scrollToBottom() {
        if (this.elements.messagesContainer) {
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        }
    }

    toggleSources(e) {
        const btn = e.currentTarget;
        const sourcesList = btn.nextElementSibling;

        if (sourcesList) {
            const isHidden = sourcesList.style.display === 'none';
            sourcesList.style.display = isHidden ? 'flex' : 'none';
        }
    }

    async handleFeedback(e) {
        const btn = e.currentTarget;
        const messageId = btn.dataset.id;
        const type = btn.dataset.type;
        const isHelpful = type === 'helpful';

        // Toggle active state
        const parent = btn.parentElement;
        parent.querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        try {
            const url = this.config.urls.submitFeedback.replace('{id}', messageId);
            await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({ is_helpful: isHelpful })
            });
        } catch (error) {
        }
    }

    handleDeleteConversation(e) {
        e.preventDefault();
        e.stopPropagation();

        const btn = e.currentTarget;
        const convId = btn.dataset.id;

        // Afficher le modal de confirmation
        this.showDeleteModal(convId, btn);
    }

    showDeleteModal(convId, btn) {
        const modal = document.getElementById('deleteModal');
        const confirmBtn = document.getElementById('confirmDelete');
        const cancelBtn = document.getElementById('cancelDelete');

        if (!modal) return;

        modal.classList.add('show');

        // Gestionnaire pour confirmer
        const handleConfirm = async () => {
            await this.deleteConversation(convId, btn);
            modal.classList.remove('show');
            cleanup();
        };

        // Gestionnaire pour annuler
        const handleCancel = () => {
            modal.classList.remove('show');
            cleanup();
        };

        // Gestionnaire pour clic en dehors
        const handleOutsideClick = (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                cleanup();
            }
        };

        // Nettoyer les événements
        const cleanup = () => {
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
            modal.removeEventListener('click', handleOutsideClick);
        };

        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        modal.addEventListener('click', handleOutsideClick);
    }

    async deleteConversation(convId, btn) {
        try {
            const url = this.config.urls.deleteConversation.replace('{id}', convId);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                // Supprimer de l'UI
                const convItem = btn.closest('.conversation-item');
                if (convItem) {
                    convItem.remove();
                }

                // Afficher message toast
                this.showToast('Conversation supprimée', 'success');

                // Rediriger si c'est la conversation active
                if (this.conversationId === parseInt(convId)) {
                    setTimeout(() => {
                        window.location.href = '/chat/';
                    }, 500);
                }
            }
        } catch (error) {
            this.showToast('Erreur lors de la suppression', 'error');
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-messages') || this.createToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast-message toast-${type}`;
        toast.innerHTML = `
            <span>${message}</span>
            <button type="button" class="close-btn" aria-label="Close">&times;</button>
        `;
        toastContainer.appendChild(toast);

        // Auto-remove après 3 secondes
        setTimeout(() => {
            toast.style.animation = 'slideOutUp 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);

        // Close button
        toast.querySelector('.close-btn').addEventListener('click', () => {
            toast.style.animation = 'slideOutUp 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        });
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-messages';
        document.body.appendChild(container);
        return container;
    }

    openNewChatModal() {
        if (this.elements.newChatModal) {
            this.elements.newChatModal.style.display = 'flex';
        }
    }

    closeNewChatModal() {
        if (this.elements.newChatModal) {
            this.elements.newChatModal.style.display = 'none';
        }
    }

    async createConversation() {
        try {
            const response = await fetch(this.config.urls.createConversation, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({
                    topic_id: null
                })
            });

            const data = await response.json();

            if (data.success) {
                // Mettre à jour l'ID de conversation
                this.conversationId = data.conversation_id;

                // Mettre à jour l'URL de sendMessage
                this.config.urls.sendMessage = `/chat/api/conversation/${data.conversation_id}/send/`;

                // Rediriger vers la nouvelle conversation
                window.location.href = data.redirect_url;
            } else {
                this.showError(data.error || 'Erreur lors de la création');
            }
        } catch (error) {
            this.showError('Erreur de connexion');
        }
    }

    // Créer une conversation sans redirection (pour le premier message)
    async createConversationSilent() {
        try {
            const response = await fetch(this.config.urls.createConversation, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({ topic_id: null })
            });

            const data = await response.json();

            if (data.success) {
                // Mettre à jour l'ID de conversation
                this.conversationId = data.conversation_id;

                // Mettre à jour l'URL de sendMessage
                this.config.urls.sendMessage = `/chat/api/conversation/${data.conversation_id}/send/`;

                // Mettre à jour l'URL du navigateur sans recharger
                window.history.pushState({}, '', data.redirect_url);

                // Ajouter la conversation à la sidebar
                this.addConversationToSidebar(data.conversation_id, 'Nouvelle conversation');

                return true;
            } else {
                this.showError(data.error || 'Erreur lors de la création');
                return false;
            }
        } catch (error) {
            this.showError('Erreur de connexion');
            return false;
        }
    }

    // Ajouter une conversation à la sidebar
    addConversationToSidebar(convId, title) {
        const list = this.elements.conversationsList;
        if (!list) return;

        // Retirer le message "Aucune conversation" s'il existe
        const noConv = list.querySelector('.no-conversations');
        if (noConv) noConv.remove();

        // Retirer la classe active des autres conversations
        list.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });

        // Créer le nouvel élément
        const convItem = document.createElement('a');
        convItem.href = `/chat/conversation/${convId}/`;
        convItem.className = 'conversation-item active';
        convItem.dataset.id = convId;
        convItem.innerHTML = `
            <div class="conv-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>
            <div class="conv-info">
                <span class="conv-title">${title}</span>
                <span class="conv-date">À l'instant</span>
            </div>
            <button class="delete-conv-btn" data-id="${convId}" title="Supprimer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3,6 5,6 21,6"></polyline>
                    <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"></path>
                </svg>
            </button>
        `;

        // Ajouter au début de la liste
        list.insertBefore(convItem, list.firstChild);

        // Ajouter l'événement de suppression
        const deleteBtn = convItem.querySelector('.delete-conv-btn');
        deleteBtn.addEventListener('click', (e) => this.handleDeleteConversation(e));

        // Créer le header de conversation s'il n'existe pas
        this.createConversationHeader(title);
    }

    // Créer le header de conversation
    createConversationHeader(title) {
        const chatMain = document.querySelector('.chat-main');
        if (!chatMain) return;

        // Vérifier si le header existe déjà
        let header = chatMain.querySelector('.chat-header');
        if (header) {
            // Mettre à jour le titre existant
            const titleEl = header.querySelector('#conversationTitle');
            if (titleEl) titleEl.textContent = title;
            return;
        }

        // Créer le header
        header = document.createElement('header');
        header.className = 'chat-header';
        header.innerHTML = `
            <div class="chat-header-info">
                <h3 id="conversationTitle">${title}</h3>
            </div>
        `;

        // Insérer au début de chat-main
        chatMain.insertBefore(header, chatMain.firstChild);

        // Mettre à jour la référence
        this.elements.conversationTitle = header.querySelector('#conversationTitle');
    }

    // Mettre à jour le titre de la conversation dans la sidebar et le header
    updateConversationTitle(newTitle) {
        // Mettre à jour le header
        if (this.elements.conversationTitle) {
            this.elements.conversationTitle.textContent = newTitle;
        }

        // Mettre à jour dans la sidebar
        const activeConv = document.querySelector(`.conversation-item[data-id="${this.conversationId}"]`);
        if (activeConv) {
            const titleEl = activeConv.querySelector('.conv-title');
            if (titleEl) {
                titleEl.textContent = newTitle.length > 30 ? newTitle.substring(0, 30) + '...' : newTitle;
            }
        }
    }

    showError(message) {
        // Créer une notification d'erreur temporaire
        const notification = document.createElement('div');
        notification.className = 'chat-notification error';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #ef4444;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    processExistingMessages() {
        const assistantMessages = document.querySelectorAll('.message-assistant');
        assistantMessages.forEach(msgDiv => {
            const textDiv = msgDiv.querySelector('.message-text');
            const extrasContainer = msgDiv.querySelector('.message-extras');

            // 1. Handle citations in existing text
            if (textDiv && textDiv.dataset.sources) {
                try {
                    const sources = JSON.parse(textDiv.dataset.sources);
                    if (sources && sources.length > 0) {
                        let html = textDiv.innerHTML;
                        sources.forEach(s => {
                            const escapedTitle = s.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                            const pattern = new RegExp(`\\[Source:\\s*${escapedTitle}(?:,\\s*page\\s*(\\d+))?\\]`, 'g');
                            html = html.replace(pattern, (match, page) => {
                                const pageStr = page ? `, p.${page}` : '';
                                return `<a href="${s.url}" class="source-citation" target="_blank" title="${this.escapeHtml(s.title)}">[Source: ${this.escapeHtml(s.title)}${pageStr}]</a>`;
                            });
                        });
                        textDiv.innerHTML = html;
                    }
                } catch (e) {
                    console.error("Error parsing sources for historical message:", e);
                }
            }

            // 2. Handle extras (images, questions) from metadata
            if (extrasContainer && extrasContainer.dataset.metadata) {
                try {
                    let metadataRaw = extrasContainer.dataset.metadata;
                    if (metadataRaw && metadataRaw !== '{}' && metadataRaw !== 'None') {
                        // Safely parse JSON that might be Python-formatted in data attribute
                        let metadata;
                        try {
                            metadata = JSON.parse(metadataRaw);
                        } catch (parseErr) {
                            // Fallback for single quotes if any
                            metadata = JSON.parse(metadataRaw.replace(/'/g, '"'));
                        }

                        if (metadata && typeof metadata === 'object') {
                            this.renderImages(extrasContainer, metadata.images_used);
                            this.renderFollowUpQuestions(extrasContainer, metadata.follow_up_questions);
                        }
                    }
                } catch (e) {
                    console.warn("Could not parse metadata for message:", e);
                }
            }
        });
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    if (typeof CONFIG !== 'undefined') {
        window.noxaChat = new NoxaChat(CONFIG);
    }
});

// Animations CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateX(-50%) translateY(10px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
    @keyframes fadeOut {
        from { opacity: 1; transform: translateX(-50%) translateY(0); }
        to { opacity: 0; transform: translateX(-50%) translateY(10px); }
    }
`;
document.head.appendChild(style);
