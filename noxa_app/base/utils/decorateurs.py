import logging
from django.shortcuts import redirect
from functools import wraps

logger = logging.getLogger(__name__)

def log_action(action_name):
    @wraps(action_name)
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            logger.info(f"User {request.user.username} performed action: {action_name}")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator