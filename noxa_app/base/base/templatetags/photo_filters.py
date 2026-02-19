from django import template

register = template.Library()

@register.filter
def photo_url_safe(user):
    """
    Return the photo URL if it exists and has a file, otherwise return a default avatar
    """
    try:
        if user and hasattr(user, 'photo') and user.photo and user.photo.name:
            return user.photo.url
    except (ValueError, AttributeError):
        pass
    return '/static/images/default-avatar.png'
