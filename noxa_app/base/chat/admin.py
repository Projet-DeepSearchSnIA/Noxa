from django.contrib import admin
from .models import Conversation, ChatMessage, ChatSource, ChatFeedback


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'created_at', 'total_time')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'topic', 'created_at', 'updated_at', 'is_active')
    list_filter = ('is_active', 'topic', 'created_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('get_preview', 'role', 'conversation', 'created_at', 'is_helpful')
    list_filter = ('role', 'is_helpful', 'created_at')
    search_fields = ('content', 'conversation__title')
    readonly_fields = ('created_at', 'query_embedding_time', 'retrieval_time', 'generation_time', 'total_time')

    def get_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_preview.short_description = 'Message'


@admin.register(ChatSource)
class ChatSourceAdmin(admin.ModelAdmin):
    list_display = ('publication', 'message', 'chunk_index', 'relevance_score', 'page_number')
    list_filter = ('relevance_score',)
    search_fields = ('publication__theme', 'excerpt')


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'rating', 'issue_type', 'created_at')
    list_filter = ('rating', 'issue_type', 'created_at')
    search_fields = ('comment', 'user__username')
    readonly_fields = ('created_at',)
