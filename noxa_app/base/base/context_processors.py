# context_processors.py

# System wide values (for the entire website, not just a view)


def notifications_context(request):
    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(
            is_read=False, 
            is_deleted=False
        ).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}


def recentSearches(request):
    if request.user.is_authenticated:
        recent_searches = request.user.search_history.all()
        return {'recent_searches': recent_searches}
    return {'recent_searches': None}









