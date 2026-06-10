from django.contrib import admin
from .models import Email, EmailOpen

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'user', 'tracking_id', 'sent_at', 'open_count')
    list_filter = ('sent_at', 'user')
    search_fields = ('recipient', 'subject', 'tracking_id')
    readonly_fields = ('tracking_id', 'sent_at')

@admin.register(EmailOpen)
class EmailOpenAdmin(admin.ModelAdmin):
    list_display = ('email', 'ip_address', 'opened_at')
    list_filter = ('opened_at',)
    search_fields = ('email__recipient', 'email__subject', 'ip_address')
    readonly_fields = ('opened_at',)
