from django.contrib import admin
from .models import SiteSettings, Page, FAQ, Testimonial, NewsletterSubscription


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Generale', {
            'fields': ('site_name', 'site_description', 'site_keywords')
        }),
        ('Contatti', {
            'fields': ('email', 'phone', 'whatsapp', 'address')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url')
        }),
        ('Orari', {
            'fields': ('check_in_time', 'check_out_time')
        }),
        ('Legale', {
            'fields': ('privacy_policy', 'terms_conditions'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'show_in_menu', 'menu_order')
    list_filter = ('is_published', 'show_in_menu')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'show_in_menu', 'menu_order')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
    list_filter = ('is_active',)
    list_editable = ('order', 'is_active')
    search_fields = ('question', 'answer')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('guest_name', 'guest_country', 'rating', 'is_featured', 'is_active')
    list_filter = ('is_featured', 'is_active', 'rating')
    list_editable = ('is_featured', 'is_active')
    search_fields = ('guest_name', 'content')


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('email',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
