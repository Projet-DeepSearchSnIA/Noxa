"""
Tests pour le module Chat RAG
À exécuter avec: python manage.py test noxa.base.chat.tests
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from .models import Conversation, ChatMessage, ChatSource, ChatFeedback
from base.models import Topic, Publication

User = get_user_model()


class ChatModelTestCase(TestCase):
    """Tests des modèles du chat"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.topic = Topic.objects.create(
            name='Test Topic',
            description='Test description'
        )
    
    def test_conversation_creation(self):
        """Test la création d'une conversation"""
        conv = Conversation.objects.create(
            user=self.user,
            topic=self.topic,
            title='Test Conversation'
        )
        self.assertEqual(conv.title, 'Test Conversation')
        self.assertEqual(conv.user, self.user)
        self.assertTrue(conv.is_active)
    
    def test_chat_message_creation(self):
        """Test la création d'un message"""
        conv = Conversation.objects.create(
            user=self.user,
            topic=self.topic
        )
        msg = ChatMessage.objects.create(
            conversation=conv,
            role='user',
            content='Bonjour!'
        )
        self.assertEqual(msg.role, 'user')
        self.assertEqual(msg.content, 'Bonjour!')
    
    def test_conversation_get_messages_count(self):
        """Test le comptage des messages"""
        conv = Conversation.objects.create(user=self.user)
        ChatMessage.objects.create(conversation=conv, role='user', content='Test')
        ChatMessage.objects.create(conversation=conv, role='assistant', content='Réponse')
        self.assertEqual(conv.get_messages_count(), 2)


class ChatServicesTestCase(TestCase):
    """Tests des services RAG"""
    
    def test_rag_service_initialization(self):
        """Test l'initialisation du service RAG"""
        from .services import get_rag_service, RAGService
        
        service = get_rag_service()
        self.assertIsInstance(service, RAGService)
        
        # Singleton pattern
        service2 = get_rag_service()
        self.assertIs(service, service2)


class ChatViewsTestCase(TestCase):
    """Tests des vues du chat"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.topic = Topic.objects.create(
            name='Test Topic'
        )
    
    def test_chat_home_requires_login(self):
        """Test que la page d'accueil requiert une authentification"""
        response = self.client.get(reverse('chat:home'))
        # Doit rediriger vers login
        self.assertEqual(response.status_code, 302)
    
    def test_chat_home_authenticated(self):
        """Test la page d'accueil pour un utilisateur authentifié"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/chat_interface.html')
    
    def test_create_conversation(self):
        """Test la création de conversation via API"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('chat:create_conversation'),
            data=json.dumps({
                'topic_id': self.topic.id,
                'title': 'Test Conversation'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('conversation_id', data)


class ChatIntegrationTestCase(TestCase):
    """Tests d'intégration du pipeline RAG"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.topic = Topic.objects.create(
            name='Test Topic'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_full_chat_flow(self):
        """Test le flux complet: création conversation -> envoi message -> réponse"""
        # 1. Crée une conversation
        conv = Conversation.objects.create(
            user=self.user,
            topic=self.topic,
            title='Test Flow'
        )
        
        # 2. Envoie un message
        response = self.client.post(
            reverse('chat:send_message', args=[conv.id]),
            data=json.dumps({
                'message': 'Quelle est la capitale de la France?'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # 3. Vérifie la réponse
        self.assertTrue(data['success'])
        self.assertIn('assistant_message', data)
        self.assertIn('content', data['assistant_message'])
        self.assertIn('metrics', data['assistant_message'])
        
        # 4. Vérifie que les messages sont sauvegardés
        self.assertEqual(conv.messages.count(), 2)  # User + Assistant


class ChatFeedbackTestCase(TestCase):
    """Tests du système de feedback"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.conv = Conversation.objects.create(user=self.user)
        self.msg = ChatMessage.objects.create(
            conversation=self.conv,
            role='assistant',
            content='Réponse test'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_submit_helpful_feedback(self):
        """Test l'envoi d'un feedback positif"""
        response = self.client.post(
            reverse('chat:submit_feedback', args=[self.msg.id]),
            data=json.dumps({
                'is_helpful': True
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Vérifie que le feedback est sauvegardé
        self.msg.refresh_from_db()
        self.assertTrue(self.msg.is_helpful)


# ============================================
# Test Utilities
# ============================================



if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['noxa.base.chat.tests'])
