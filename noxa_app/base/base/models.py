from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from . import utils
from PyPDF2 import PdfReader


class CustomUser(AbstractUser):
    """Modèle User custom avec champs supplémentaires"""
    bio = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='profils/', blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    school = models.CharField(max_length=50, default='ENSAE Dakar', blank=True, null=True)

    def __str__(self):
        return self.username


class Topic(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Publication(models.Model):
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL, 
        null=True)
    authors = models.ManyToManyField(
        get_user_model(), 
        related_name="pub_authored", 
        blank=True)
    theme = models.CharField(max_length=400)
    topic = models.ForeignKey(Topic, 
                              on_delete=models.SET_NULL, 
                              null=True
                              )
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name="publications"
    )
    affiliations = models.TextField(
        blank=True,
        null=True,
        help_text="Enter affiliations separated by commas (,)"
    )
    file = models.FileField(
        upload_to=utils.pdfUploadPath, 
        validators=[utils.validatePdf], 
        help_text="Upload a PDF file",
        blank=True, 
        null=True
    )
    file_url = models.URLField(blank=True, null=True)
    file_basename = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated', '-created']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # sauvegarde d'abord l'objet
        if self.user and self.user not in self.authors.all():
            self.authors.add(self.user)

    def get_affiliations_list(self):
        """Return affiliations as a list."""
        return [aff.strip() for aff in self.affiliations.split(",") if aff.strip()]
    
    def page_count(self):
        try:
            self.file.open('rb')
            reader = PdfReader(self.file)
            return len(reader.pages)
        except:
            return None
        finally:
            self.file.close()

    def __str__(self):
        return self.theme
    

class Collection(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    publications = models.ManyToManyField(
        'Publication',
        through='CollectionPublication',
        related_name='collections',
        blank=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class CollectionPublication(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('collection', 'publication')  # prevent duplicates
        ordering = ['-added']

    def __str__(self):
        return f"{self.publication} in {self.collection} (added {self.added})"


class Notification(models.Model):
    """
    Notification class: inherits from django.db.models.Model \n
    Properties:\n
    recipient: who receives the notification \n
    actor: who triggered the notification \n
    type: type of notification (follow, discussion in publication, ...). Default value set in NOTIFICATION_TYPES \n
    target: the object this notification is about, depends on the notification's type. 
    For follow notification, the target is the follower, for discussion in publication notification, the target is the discussion itself\n
    title: notification title\n
    message: the body of the notification\n
    is_read: read status\n
    is_deleted: deleted status, when deleted stays in database but doesn't show up in notification ever again\n
    created: date of creation\n
    read_at: read date\n
    action_url: for redirecting to the target object page
    Methods:\n
    mark_as_read: marks the notification as read
    """

    NOTIFICATION_TYPES = [
        ('follow', 'New Follower'),
        ('discussion_in_publication', 'New discussion in publication'),
        # ('follow_accepted', 'Follow Request Accepted'),
        ('publication_like', 'Publication Liked'),
        ('publication_comment', 'New Comment on Publication'),
        ('collection_shared', 'Collection Shared'),
        ('discussion_reply', 'Discussion Reply'),
        ('discussion_mention', 'Mentioned in Discussion'),
        ('publication_added', 'New Publication from Followed User'),
        ('topic_follow', 'Someone Followed Your Topic'),
        ('system', 'System Notification'),
        ('achievement', 'Achievement Unlocked'),
    ] # not exhaustive list, just built it up quickly like that

    # Who receives the notification
    recipient = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    # Who triggered the notification
    actor = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='sent_notifications',
        null=True, 
        blank=True
    )
    
    # Type of notification
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    
    # The object this notification is about (publication, comment, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional: Action URL for clicking the notification
    action_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['recipient', '-created']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} for {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def time_since(self):
        from django.utils.timesince import timesince
        return timesince(self.created)

# class Notification(models.Model):
#     user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
#     type = models.CharField(max_length=50)
#     body = models.TextField()
#     created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['-created']

#     def __str__(self):
#         return f"{self.type} - {self.body} (added {self.created})"


class Discussion(models.Model):
    """
    Discussion class: inherits from django.db.models.Model \n
    Properties:\n
    creator: the user which created the room (automatically filled in, current logged in user)\n
    publication: which publication is this room about ? (automatically filled in)\n
    title: Discussion room name\n
    description: Small description of the discussion room, what point will this discussion talk about specifically or something else\n
    participants: people who wrote a message in this at least one time (will be incrementedly increased as people participate in it)\n
    updated: date of the last message (automatically filled in)\n
    created: date of creation (automatically filled in)
    """
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    participants = models.ManyToManyField(get_user_model(), related_name="participants", blank=True)
    updated = models.DateTimeField(auto_now=True) 
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.title
    

class Message(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE)
    body = models.TextField()
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    updated = models.DateTimeField(auto_now=True) 
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.body[0:50]
    
    @property
    def is_reply(self):
        """Check if this message is a reply to another message"""
        return self.reply_to is not None
    
    def get_replies(self):
        """Get all replies to this message"""
        return self.replies.all().order_by('created')
    

class SearchHistory(models.Model):
    """
    Store user search history for better UX.
    Only stores successful searches (when user clicks on a result).
    """
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE,
        related_name='search_history'
    )
    query = models.CharField(max_length=200)
    
    # Store what they clicked on using generic foreign key
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    clicked_object = GenericForeignKey('content_type', 'object_id')
    
    # Track search context
    search_type = models.CharField(
        max_length=50, 
        choices=[
            ('general', 'General Search'),
            ('publication', 'Publication Search'),
            ('author', 'Author Search'),
            ('collection', 'Collection Search'),
            ('profile', 'Profile Search'),
            ('discussion', 'Discussion Search'),
            ('tag', 'Tag Search'),
        ],
        default='general'
    )
    
    # Timestamps
    searched_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)  # Updated when query is reused
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['-last_used']
        #unique_together = ('user', 'query', 'search_type', 'content_type', 'object_id')  # Prevent duplicates
        indexes = [
            models.Index(fields=['user', '-last_used']),
            #models.Index(fields=['user', 'query']),
        ]
        verbose_name_plural = "Search histories"
    
    def __str__(self):
        return f"{self.user.username}: '{self.query}'"
    
    @classmethod
    def add_search(cls, user, query, search_type='general', clicked_object=None):
        """
        Add or update search history entry.
        """
        if not user.is_authenticated or not query.strip():
            return None
            
        query = query.strip().lower()
        
        # Get content type for the clicked object
        content_type = None
        object_id = None
        if clicked_object:
            content_type = ContentType.objects.get_for_model(clicked_object)
            object_id = clicked_object.id
        
        # Get or create the search entry
        search_entry, created = cls.objects.update_or_create(
            user=user,
            query=query,
            search_type=search_type,
            content_type=content_type,
            object_id=object_id,
            defaults={
                'last_used': timezone.now()
            }
        )
        
        if not created:
            # Update existing entry
            search_entry.usage_count += 1
            search_entry.last_used = timezone.now()
            if clicked_object:
                search_entry.content_type = content_type
                search_entry.object_id = object_id
            search_entry.save(update_fields=['usage_count', 'last_used', 'content_type', 'object_id'])
        
        # Keep only last 20 searches per user
        cls.cleanup_old_searches(user)
        
        return search_entry
    
    @classmethod
    def get_recent_searches(cls, user, limit=20):
        """
        Get user's recent searches.
        """
        if not user.is_authenticated:
            return cls.objects.none()
            
        return cls.objects.filter(user=user).order_by('-last_used')[:limit]
    
    @classmethod
    def cleanup_old_searches(cls, user, keep_count=20):
        """
        Keep only the most recent searches for a user.
        """
        if not user.is_authenticated:
            return
            
        # Get IDs of searches to keep
        keep_ids = list(
            cls.objects.filter(user=user)
            .order_by('-last_used')
            .values_list('id', flat=True)[:keep_count]
        )
        
        # Delete the rest
        cls.objects.filter(user=user).exclude(id__in=keep_ids).delete()
    
    @classmethod
    def get_popular_searches(cls, user, limit=10):
        """
        Get user's most frequently used searches.
        """
        if not user.is_authenticated:
            return cls.objects.none()
            
        return cls.objects.filter(user=user).order_by('-usage_count', '-last_used')[:limit]


class SearchSuggestion(models.Model):
    """
    Store popular search terms for autocomplete suggestions.
    This is system-wide, not user-specific.
    """
    query = models.CharField(max_length=200, unique=True)
    search_count = models.PositiveIntegerField(default=1)
    last_searched = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-search_count', '-last_searched']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['-search_count']),
        ]
    
    def __str__(self):
        return f"'{self.query}' ({self.search_count} searches)"
    
    @classmethod
    def increment_search(cls, query):
        """
        Increment search count for a query.
        """
        if not query.strip():
            return None
            
        query = query.strip().lower()
        suggestion, created = cls.objects.get_or_create(
            query=query,
            defaults={'search_count': 1}
        )
        
        if not created:
            suggestion.search_count += 1
            suggestion.save(update_fields=['search_count', 'last_searched'])
        
        return suggestion
    
    @classmethod
    def get_suggestions(cls, query_prefix, limit=10):
        """
        Get search suggestions based on query prefix.
        """
        return cls.objects.filter(
            query__istartswith=query_prefix,
            is_active=True
        ).order_by('-search_count')[:limit]
    

########################################################################
################# SUBJECTS / EXAMS #####################################
########################################################################

class Specialization(models.Model):
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label
    
class Classes(models.Model):
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    
    def __str__(self):
        return self.label

class Courses(models.Model):
    """Courses / disciplines in a class/specialization"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, null=True, blank=True)
    classe = models.ForeignKey(Classes, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    
    # add a constraint to ensure that we will not have two courses with the same name in the same specialization/class and the same semester
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'specialization', 'classe', 'semester'], name='unique_course')
        ]

    def __str__(self):
        return self.label
    
class Corrections(models.Model):
    """ Corrections for baki subjects """
    id = models.AutoField(primary_key=True)
    subject = models.ForeignKey('Subjects', on_delete=models.CASCADE)
    aws_url = models.URLField(max_length=500, null=True, blank=True)
  #  file = models.FileField(upload_to=utils.correctionUploadPath, validators=[utils.validatePdf])
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    nb_likes = models.IntegerField(default=0)
    users_liked = models.ManyToManyField(get_user_model(), related_name="liked_corrections", blank=True)

    def __str__(self):
        return f"Correction for {self.subject}"
    
class Comments(models.Model):
    """ Comments for a correction """
    id = models.AutoField(primary_key=True)
    correction = models.ForeignKey(Corrections, on_delete=models.CASCADE, related_name="comments")
    subject = models.ForeignKey('Subjects', on_delete=models.CASCADE)
    body = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
   
    def __str__(self):
        return f"Comment for {self.subject}"
    
class Subjects(models.Model):
    """" Subject / baki """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    formated_name = models.CharField(max_length=200)
    aws_url = models.URLField(max_length=500, null=True, blank=True)
    class_field = models.ForeignKey(Classes, on_delete=models.CASCADE, null=True, blank=True)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=7, null=True, blank=True)
    author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    source = models.CharField(max_length=200, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-createdAt']
        verbose_name_plural = "Subjects"
        constraints = [
            models.UniqueConstraint(fields=['course', 'academic_year'], name='unique_subject')
        ]
    
    def __str__(self):
        return f"{self.course} - {self.academic_year}"
    

    




##############################################################################################
################################## Utility functions #########################################
############################## We need to find a way to better manage this ###################
##############################################################################################



def track_search_click(request, clicked_object):
    """
    Tracks when a user clicks on a search result.
    We call this on the clicked object view
    """
    # Check if this came from a search

    if request.GET.get('from') == 'search':
        query = request.GET.get('q')
        search_tab = request.GET.get('tab', 'all')
        
        if query and request.user.is_authenticated:
            # Map tab to search_type
            search_type_map = {
                'all': 'general',
                'publications': 'publication',
                'authors': 'author',
                'profiles': 'profile',
                'collections': 'collection',
                'discussions': 'discussion',
                'tags': 'tag'
            }
            
            search_type = search_type_map.get(search_tab, 'general')
            
            SearchHistory.add_search(
                user=request.user,
                query=query,
                search_type=search_type,
                clicked_object=clicked_object
            )
            
            return True
    return False


def get_search_context_from_request(request):
    """
    Extract search context from request parameters.
    """
    return {
        'from_search': request.GET.get('from') == 'search',
        'search_query': request.GET.get('q', ''),
        'search_tab': request.GET.get('tab', 'all')
    }


##########################################################################
### MODELES POUR LE RAG ##################################################

class DocumentChunk(models.Model):
    publication = models.ForeignKey(
        Publication, 
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    chunk_index = models.IntegerField()  # Index du chunk dans le document
    page_number = models.IntegerField(null=True, blank=True)
    content = models.TextField()  # Le texte extrait du chunk
    token_count = models.IntegerField(null=True, blank=True)
    
    # IDs pour Pinecone
    pinecone_id = models.CharField(max_length=255, unique=True)
    embedding_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'), 
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['publication', 'chunk_index']
        unique_together = ['publication', 'chunk_index']
    
    def __str__(self):
        return f"{self.publication.theme} - Chunk {self.chunk_index}"













##############################################################################################








