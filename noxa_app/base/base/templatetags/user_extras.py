from django import template # templating system so that parameter call work in Django jinja structure
# i.e. user.is_following(follower) for example (not supporter in django by default)

register = template.Library()

@register.filter
def is_following(user, target_user):
    """Check if user is following target_user"""
    if not user.is_authenticated:
        return False
    return user.is_following(target_user)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)








