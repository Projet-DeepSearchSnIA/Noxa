from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Topic)
admin.site.register(Tag)
@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('theme', 'user', 'topic', 'created', 'updated')
    list_filter = ('topic', 'created')
    search_fields = ('theme', 'description')
    readonly_fields = ('created', 'updated')
    actions = ['sync_from_gdrive']

    def sync_from_gdrive(self, request, queryset):
        from chat.gdrive_sync import sync_noxa_docs
        result = sync_noxa_docs()
        if result.get("status") == "success":
            self.message_user(request, f"Succès: {result.get('processed')} documents traités")
        else:
            self.message_user(request, f"Erreur: {result.get('message')}", level='ERROR')
    sync_from_gdrive.short_description = "Synchroniser depuis le Google Drive NOXA"

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('publication', 'chunk_index', 'page_number', 'short_content', 'embedding_status', 'created')
    list_filter = ('embedding_status', 'created')
    search_fields = ('content', 'publication__theme')
    readonly_fields = ('created',)

    def short_content(self, obj):
        return obj.content[:50] + "..." if obj.content else ""
    short_content.short_description = "Aperçu du contenu"
admin.site.register(Collection)
admin.site.register(CollectionPublication)
admin.site.register(Message)
admin.site.register(Notification)
admin.site.register(Discussion)
admin.site.register(SearchHistory)
admin.site.register(SearchSuggestion)
admin.site.register(Specialization)
admin.site.register(Classes)
admin.site.register(Courses)
admin.site.register(Subjects)
