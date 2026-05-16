from django.contrib import admin
from .models import User, KYC


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'is_active', 'date_joined']
    search_fields = ['email', 'username']


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'id_type', 'verification_status', 'created_at']
    list_filter = ['verification_status', 'id_type']
    search_fields = ['user__email', 'full_name']
    readonly_fields = ['created_at', 'updated_at']
