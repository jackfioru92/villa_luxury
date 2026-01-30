from django.contrib import admin
from .models import (
    Villa, BookableUnit, SeasonPrice, Amenity,
    VillaAmenity, UnitAmenity, GalleryImage
)


class VillaAmenityInline(admin.TabularInline):
    model = VillaAmenity
    extra = 1


class UnitAmenityInline(admin.TabularInline):
    model = UnitAmenity
    extra = 1


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1
    fields = ('image', 'alt_text', 'is_hero', 'sort_order')


class BookableUnitInline(admin.TabularInline):
    model = BookableUnit
    extra = 0
    fields = ('name', 'unit_type', 'base_price', 'max_guests', 'is_active', 'sort_order')
    show_change_link = True


class SeasonPriceInline(admin.TabularInline):
    model = SeasonPrice
    extra = 1


@admin.register(Villa)
class VillaAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'total_guests', 'total_bedrooms', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BookableUnitInline, VillaAmenityInline, GalleryImageInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'tagline', 'description', 'description_short')
        }),
        ('Posizione', {
            'fields': ('address', 'city', 'province', 'postal_code', 'country', 'latitude', 'longitude')
        }),
        ('Caratteristiche', {
            'fields': ('total_guests', 'total_bedrooms', 'total_bathrooms', 'total_sqm')
        }),
        ('Media', {
            'fields': ('hero_image', 'hero_video_url')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Stato', {
            'fields': ('is_active',)
        }),
    )


@admin.register(BookableUnit)
class BookableUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'villa', 'unit_type', 'base_price', 'max_guests', 'min_nights', 'is_active')
    list_filter = ('villa', 'unit_type', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SeasonPriceInline, UnitAmenityInline, GalleryImageInline]
    fieldsets = (
        (None, {
            'fields': ('villa', 'name', 'slug', 'unit_type', 'description', 'description_short')
        }),
        ('Capacità', {
            'fields': ('max_guests', 'bedrooms', 'bathrooms', 'beds_description')
        }),
        ('Prezzi', {
            'fields': ('base_price', 'cleaning_fee')
        }),
        ('Regole prenotazione', {
            'fields': ('min_nights', 'max_nights')
        }),
        ('Media', {
            'fields': ('main_image',)
        }),
        ('Stato', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_highlighted')
    list_filter = ('category', 'is_highlighted')
    search_fields = ('name',)
    list_editable = ('is_highlighted',)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('alt_text', 'villa', 'unit', 'is_hero', 'sort_order')
    list_filter = ('is_hero', 'villa', 'unit')
    list_editable = ('is_hero', 'sort_order')
