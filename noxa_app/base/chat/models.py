from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Conversation(models.Model):
    """
    Représente une session de conversation avec le chatbot.
    Chaque conversation peut être liée à un topic spécifique pour contextualiser les réponses.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_conversations'
    )
    title = models.CharField(max_length=255, blank=True)
    topic = models.ForeignKey(
        'base.Topic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Topic spécifique pour cibler les réponses du RAG"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        return self.title or f"Conversation {self.id} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"Nouvelle conversation - {timezone.now().strftime('%d/%m/%Y %H:%M')}"
        super().save(*args, **kwargs)

    def get_messages_count(self):
        return self.messages.count()

    def get_last_message(self):
        return self.messages.first()


class ChatMessage(models.Model):
    """
    Un message dans une conversation.
    Peut être de l'utilisateur ou de l'assistant (chatbot).
    """
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('assistant', 'Assistant'),
        ('system', 'Système'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Métadonnées pour le RAG
    query_embedding_time = models.FloatField(null=True, blank=True, help_text="Temps pour générer l'embedding (ms)")
    retrieval_time = models.FloatField(null=True, blank=True, help_text="Temps de récupération des documents (ms)")
    generation_time = models.FloatField(null=True, blank=True, help_text="Temps de génération de la réponse (ms)")
    total_time = models.FloatField(null=True, blank=True, help_text="Temps total de traitement (ms)")

    # Feedback utilisateur
    is_helpful = models.BooleanField(null=True, blank=True)
    feedback_text = models.TextField(blank=True)

    # Pièces jointes (audio, documents, etc.)
    file = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True, help_text="Métadonnées extraites (questions suivies, images citées, etc.)")

    class Meta:
        ordering = ['created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"[{self.role}] {preview}"


class ChatSource(models.Model):
    """
    Source/référence utilisée pour générer une réponse.
    Lie un message assistant aux publications qui ont servi de contexte.
    """
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    publication = models.ForeignKey(
        'base.Publication',
        on_delete=models.CASCADE,
        related_name='chat_references',
        null=True,
        blank=True
    )
    attachment = models.ForeignKey(
        'ChatAttachment',
        on_delete=models.CASCADE,
        related_name='chat_references',
        null=True,
        blank=True
    )
    chunk_index = models.IntegerField(help_text="Index du chunk utilisé dans le document")
    relevance_score = models.FloatField(help_text="Score de similarité (0-1)")
    excerpt = models.TextField(help_text="Extrait du texte utilisé comme contexte")
    page_number = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-relevance_score']
        verbose_name = "Source"
        verbose_name_plural = "Sources"

    def __str__(self):
        source_name = self.publication.theme if self.publication else (self.attachment.filename if self.attachment else "Unknown source")
        return f"{source_name} (score: {self.relevance_score:.2f})"


class ChatFeedback(models.Model):
    """
    Feedback détaillé sur une réponse du chatbot.
    Permet d'améliorer le système au fil du temps.
    """
    RATING_CHOICES = [
        (1, 'Très mauvais'),
        (2, 'Mauvais'),
        (3, 'Moyen'),
        (4, 'Bon'),
        (5, 'Excellent'),
    ]

    ISSUE_CHOICES = [
        ('irrelevant', 'Réponse non pertinente'),
        ('incorrect', 'Information incorrecte'),
        ('incomplete', 'Réponse incomplète'),
        ('unclear', 'Réponse pas claire'),
        ('sources_wrong', 'Mauvaises sources citées'),
        ('other', 'Autre'),
    ]

    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='detailed_feedback'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    issue_type = models.CharField(max_length=20, choices=ISSUE_CHOICES, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"

    def __str__(self):
        return f"Feedback pour message {self.message.id} - {self.rating}/5"


class ChatAttachment(models.Model):
    """
    Fichier joint à un message.
    Permet d'avoir plusieurs fichiers par message.
    """
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='chat_attachments/')
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    file_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"

    def __str__(self):
        return self.filename or f"Attachment {self.id}"

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except:
                pass
        super().save(*args, **kwargs)
