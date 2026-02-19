# utils.py

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse


def pdfUploadPath(instance, filename):
    return f"pdf/{filename}"

def validatePdf(file):
    if not file.name.lower().endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed...")
    
# Notification manager (all helper functions for the task)
class NotificationManager:
    @staticmethod
    def create_notification(recipient, actor, notification_type, target_object, title, message, action_url=None):
        """
        Create a notification
        """
        from .models import Notification
        content_type = ContentType.objects.get_for_model(target_object)
        
        notification = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            type=notification_type,
            content_type=content_type,
            object_id=target_object.pk,
            title=title,
            message=message,
            action_url=action_url
        )
        return notification
    
    @staticmethod
    def new_follower(follower, followed):
        """Create follow notification"""
        return NotificationManager.create_notification(
            recipient=followed,
            actor=follower,
            notification_type='follow',
            target_object=follower,
            title="New Follower",
            message=f"@{follower.username} started following you",
            action_url=reverse('base:user-profile', kwargs={'pk': follower.id})
        )
    
    @staticmethod
    def new_discussion_in_publication(creator, author, discussion):
        """Create new discussion in publication notification"""
        return NotificationManager.create_notification(
            recipient=author,
            actor=creator,
            notification_type='discussion_in_publication',
            target_object=discussion,
            title="New discussion opened in your publication",
            message=f'@{creator.username} created new discussion: "{discussion.title}" in your publication "{discussion.publication.theme}"',
            action_url=reverse('base:discussion', kwargs={'pk': discussion.id})
        )
    
    @staticmethod
    def publication_comment(commenter, publication_owner, publication, comment):
        """Create comment notification"""
        return NotificationManager.create_notification(
            recipient=publication_owner,
            actor=commenter,
            notification_type='publication_comment',
            target_object=comment,
            title="New Comment on Your Publication",
            message=f"{commenter.username} commented on '{publication.theme}'",
            action_url=reverse('base:publication', kwargs={'pk': publication.id})
        )
    
    @staticmethod
    def discussion_reply(replier, original_poster, discussion, reply):
        """Create discussion reply notification"""
        return NotificationManager.create_notification(
            recipient=original_poster,
            actor=replier,
            notification_type='discussion_reply',
            target_object=reply,
            title="New Reply in Discussion",
            message=f'@{replier.username} replied in discussion "{discussion.title}"',
            action_url=reverse('base:discussion', kwargs={'pk': discussion.id}) # doesn't exist yet
        )
    
    @staticmethod
    def new_publication_from_followed(follower, publisher, publication):
        """Notify followers of new publication"""
        return NotificationManager.create_notification(
            recipient=follower,
            actor=publisher,
            notification_type='publication_added',
            target_object=publication,
            title="New Publication",
            message=f"{publisher.username} published '{publication.theme}'",
            action_url=reverse('base:publication', kwargs={'pk': publication.id})
        )
    



































