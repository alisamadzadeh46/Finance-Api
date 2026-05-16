from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import User, KYC


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'is_active', 'is_staff', 'has_pin', 'kyc_status', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'username']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username',)}),
        (_('Transaction PIN'), {'fields': ('transaction_pin',), 'classes': ('collapse',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']

    def has_pin(self, obj):
        if obj.transaction_pin:
            return mark_safe('<span style="color:green">✔ Set</span>')
        return mark_safe('<span style="color:red">✘ Not Set</span>')
    has_pin.short_description = 'PIN'

    def kyc_status(self, obj):
        try:
            s = obj.kyc_profile.verification_status
        except Exception:
            return 'N/A'
        colors = {
            'UNVERIFIED': 'gray',
            'PENDING': 'orange',
            'VERIFIED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(s, 'black')
        return mark_safe('<b style="color:%s">%s</b>' % (color, s))
    kyc_status.short_description = 'KYC'


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'full_name', 'id_type', 'colored_status', 'created_at']
    list_filter = ['verification_status', 'id_type']
    search_fields = ['user__email', 'full_name']
    readonly_fields = ['user', 'full_name', 'date_of_birth', 'id_type', 'id_image', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('User Info', {'fields': ('user', 'full_name', 'date_of_birth')}),
        ('Identity Document', {'fields': ('id_type', 'id_image')}),
        ('Verification', {'fields': ('verification_status', 'rejection_reason')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    actions = ['approve_kyc', 'reject_kyc']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def colored_status(self, obj):
        colors = {
            'UNVERIFIED': 'gray',
            'PENDING': 'orange',
            'VERIFIED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.verification_status, 'black')
        return mark_safe('<b style="color:%s">%s</b>' % (color, obj.get_verification_status_display()))
    colored_status.short_description = 'Status'

    @admin.action(description='Approve selected KYC submissions')
    def approve_kyc(self, request, queryset):
        updated = queryset.exclude(
            verification_status=KYC.VerificationStatus.VERIFIED
        ).update(
            verification_status=KYC.VerificationStatus.VERIFIED,
            rejection_reason=''
        )
        self.message_user(request, f'{updated} KYC submission(s) approved.')

    @admin.action(description='Reject selected KYC submissions')
    def reject_kyc(self, request, queryset):
        updated = queryset.exclude(
            verification_status=KYC.VerificationStatus.REJECTED
        ).update(
            verification_status=KYC.VerificationStatus.REJECTED,
            rejection_reason='Rejected by admin.'
        )
        self.message_user(request, f'{updated} KYC submission(s) rejected.')