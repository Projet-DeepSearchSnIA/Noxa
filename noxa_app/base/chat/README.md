# NOXA Chat - Documentation Technique

## Vue d'ensemble

NOXA Chat est un système de chatbot RAG (Retrieval-Augmented Generation) intégré à l'application NOXA. Il permet aux utilisateurs de poser des questions sur les mémoires et rapports académiques stockés dans la base de données.

---

## Architecture des fichiers

```
chat/
├── __init__.py
├── admin.py              # Configuration admin Django
├── apps.py               # Configuration de l'application
├── models.py             # Modèles de données
├── views.py              # Vues et API endpoints
├── urls.py               # Routes URL
├── services.py           # Service RAG
├── templates/
│   └── chat/
│       └── chat_interface.html   # Interface utilisateur
└── README.md             # Cette documentation
```

### Fichiers statiques associés
```
static/
├── css/
│   └── chat.css          # Styles de l'interface
└── js/
    └── chat.js           # Logique JavaScript
```

---

## Modèles de données (`models.py`)

### Conversation
Représente une session de chat entre un utilisateur et le système.

| Champ | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey | Utilisateur propriétaire |
| `topic` | ForeignKey | Topic optionnel pour filtrer les réponses |
| `title` | CharField | Titre de la conversation (auto-généré) |
| `created_at` | DateTimeField | Date de création |
| `updated_at` | DateTimeField | Dernière mise à jour |
| `is_active` | BooleanField | Si la conversation est active (soft delete) |

### ChatMessage
Un message individuel dans une conversation.

| Champ | Type | Description |
|-------|------|-------------|
| `conversation` | ForeignKey | Conversation parente |
| `role` | CharField | 'user' ou 'assistant' |
| `content` | TextField | Contenu du message |
| `created_at` | DateTimeField | Date de création |
| `is_helpful` | BooleanField | Feedback rapide (pouce) |
| `query_embedding_time` | FloatField | Temps d'embedding |
| `retrieval_time` | FloatField | Temps de recherche |
| `generation_time` | FloatField | Temps de génération |
| `total_time` | FloatField | Temps total |

### ChatSource
Source citée dans une réponse de l'assistant.

| Champ | Type | Description |
|-------|------|-------------|
| `message` | ForeignKey | Message associé |
| `publication` | ForeignKey | Publication source |
| `chunk_index` | IntegerField | Index du chunk |
| `relevance_score` | FloatField | Score de pertinence (0-1) |
| `excerpt` | TextField | Extrait du texte |
| `page_number` | IntegerField | Numéro de page |

### ChatFeedback
Feedback détaillé sur une réponse.

| Champ | Type | Description |
|-------|------|-------------|
| `message` | ForeignKey | Message évalué |
| `user` | ForeignKey | Utilisateur |
| `rating` | IntegerField | Note (1-5) |
| `issue_type` | CharField | Type de problème |
| `comment` | TextField | Commentaire libre |

---

## Vues et API (`views.py`)

### Pages

| Vue | URL | Description |
|-----|-----|-------------|
| `chat_home` | `/chat/` | Page d'accueil du chat |
| `conversation_view` | `/chat/conversation/<id>/` | Affiche une conversation |

### API Endpoints

| Endpoint | Méthode | URL | Description |
|----------|---------|-----|-------------|
| `create_conversation` | POST | `/chat/api/conversation/create/` | Créer une conversation |
| `send_message` | POST | `/chat/api/conversation/<id>/send/` | Envoyer un message |
| `delete_conversation` | POST | `/chat/api/conversation/<id>/delete/` | Supprimer une conversation |
| `submit_feedback` | POST | `/chat/api/message/<id>/feedback/` | Soumettre un feedback |
| `get_suggestions` | GET | `/chat/api/suggestions/` | Obtenir des suggestions |
| `conversation_history` | GET | `/chat/api/conversation/<id>/history/` | Historique paginé |

---

## Service RAG (`services.py`)

Le service RAG gère la logique de récupération et génération de réponses.

### Fonctionnalités principales

1. **Embedding des requêtes** : Convertit la question en vecteur
2. **Recherche vectorielle** : Trouve les chunks pertinents dans Pinecone
3. **Génération de réponse** : Utilise AWS Bedrock (Claude) pour générer la réponse
4. **Gestion des sources** : Retourne les publications citées

### Classe `RAGService`

```python
class RAGService:
    def process_query(query, topic_id, topic_name, conversation_history, top_k):
        """
        Traite une requête utilisateur et retourne une réponse.

        Args:
            query: Question de l'utilisateur
            topic_id: ID du topic (optionnel)
            topic_name: Nom du topic (optionnel)
            conversation_history: Historique de la conversation
            top_k: Nombre de résultats à récupérer

        Returns:
            RAGResponse avec answer, sources et métriques
        """
```

---

## Interface utilisateur (`chat_interface.html`)

### Structure HTML

```
chat-container
├── chat-sidebar          # Barre latérale
│   ├── sidebar-header    # En-tête avec bouton retour
│   ├── new-chat-btn      # Bouton nouvelle conversation
│   ├── topic-filter      # Filtre par topic
│   └── conversations-list # Liste des conversations
│
├── chat-main             # Zone principale
│   ├── chat-header       # En-tête conversation
│   ├── messages-container # Zone des messages
│   ├── chat-welcome      # Écran de bienvenue
│   └── chat-input-container # Zone de saisie
│
└── delete-modal          # Modal de suppression
```

### Fonctionnalités

- **Écran de bienvenue** : Logo NOXA + message d'accueil
- **Historique** : Liste des conversations dans la sidebar
- **Messages** : Affichage des messages user/assistant
- **Sources** : Bouton pour voir les sources citées
- **Feedback** : Boutons pouce haut/bas
- **Suppression** : Modal de confirmation moderne

---

## JavaScript (`chat.js`)

### Classe `NoxaChat`

Gère toute la logique côté client.

#### Méthodes principales

| Méthode | Description |
|---------|-------------|
| `handleSubmit()` | Gère l'envoi d'un message |
| `sendMessage()` | Appel API pour envoyer un message |
| `addMessageToUI()` | Ajoute un message à l'interface |
| `addAssistantMessageToUI()` | Ajoute une réponse avec sources |
| `createConversation()` | Crée une conversation (avec redirection) |
| `createConversationSilent()` | Crée une conversation (sans redirection) |
| `addConversationToSidebar()` | Ajoute dynamiquement à la sidebar |
| `updateConversationTitle()` | Met à jour le titre |
| `handleDeleteConversation()` | Gère la suppression |
| `showDeleteModal()` | Affiche le modal de confirmation |
| `deleteConversation()` | Supprime effectivement |
| `showToast()` | Affiche une notification |
| `toggleSources()` | Affiche/masque les sources |
| `handleFeedback()` | Gère le feedback |

#### Flux de création de conversation

```
1. Utilisateur tape un message
2. Si pas de conversation active:
   a. createConversationSilent() crée la conversation
   b. addConversationToSidebar() l'ajoute à la liste
   c. createConversationHeader() crée l'en-tête
   d. URL mise à jour sans rechargement
3. Message envoyé via sendMessage()
4. Réponse ajoutée avec addAssistantMessageToUI()
5. Titre mis à jour via updateConversationTitle()
```

---

## Styles CSS (`chat.css`)

### Variables CSS

```css
:root {
    --primary-blue: #0066FF;      /* Couleur principale */
    --primary-blue-hover: #0052CC;
    --bg-white: #FFFFFF;
    --bg-light: #F7F9FC;
    --text-primary: #1A202C;
    --danger: #EF4444;
    --success: #10B981;
}
```

### Sections principales

| Section | Description |
|---------|-------------|
| `.chat-container` | Layout flex pleine page |
| `.chat-sidebar` | Sidebar 280px, fond blanc/gris |
| `.chat-main` | Zone principale flex |
| `.messages-container` | Scroll vertical, centré |
| `.message` | Style des messages (user/assistant) |
| `.chat-welcome` | Écran de bienvenue centré |
| `.chat-input-container` | Zone de saisie en bas |
| `.delete-modal` | Modal de confirmation |
| `.toast-messages` | Notifications toast |

### Responsive

- Sidebar en overlay sur mobile (< 768px)
- Padding réduit sur petits écrans
- Grille suggestions en colonne unique

---

## Routes URL (`urls.py`)

```python
urlpatterns = [
    # Pages
    path('', views.chat_home, name='home'),
    path('conversation/<int:conversation_id>/', views.conversation_view, name='conversation'),

    # API
    path('api/conversation/create/', views.create_conversation, name='create_conversation'),
    path('api/conversation/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('api/conversation/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('api/conversation/<int:conversation_id>/history/', views.conversation_history, name='conversation_history'),
    path('api/message/<int:message_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/suggestions/', views.get_suggestions, name='get_suggestions'),
    path('api/search/', views.search_publications, name='search_publications'),
]
```

---

## Intégration avec l'application principale

### Configuration (`noxa/urls.py`)

```python
urlpatterns = [
    path('chat/', include('chat.urls', namespace='chat')),
]
```

### Bouton flottant (`main.html`)

Un bouton flottant en bas à droite permet d'accéder au chat depuis n'importe quelle page :

```html
<a href="{% url 'chat:home' %}" class="floating-chat-btn">
    <!-- Icône SVG -->
</a>
```

---

## Fonctionnalités clés

### 1. Création dynamique de conversations
- Pas de modal de topic
- Création silencieuse au premier message
- Ajout dynamique à la sidebar
- URL mise à jour sans rechargement

### 2. Gestion des messages
- Affichage en temps réel
- Indicateur "NOXA réfléchit..."
- Sources avec score de pertinence
- Feedback (pouce haut/bas)

### 3. Interface moderne
- Design inspiré de Claude/ChatGPT
- Écran de bienvenue avec logo
- Modal de suppression élégant
- Notifications toast

### 4. Historique persistant
- Conversations sauvegardées en BDD
- Chargement paresseux (pagination)
- Soft delete (is_active=False)

---

## Sécurité

- `@login_required` sur toutes les vues
- Vérification propriétaire conversation
- CSRF token sur tous les appels API
- Validation des entrées utilisateur

---

## Performance

- Prefetch des sources avec `prefetch_related`
- Pagination de l'historique
- Chargement asynchrone (fetch API)
- Pas de rechargement de page

---

## Améliorations futures possibles

1. **Streaming** : Afficher la réponse au fur et à mesure
2. **Export** : Exporter une conversation en PDF
3. **Partage** : Partager une conversation
4. **Recherche** : Rechercher dans l'historique
5. **Favoris** : Marquer des conversations importantes
6. **Tags** : Organiser par tags personnalisés
