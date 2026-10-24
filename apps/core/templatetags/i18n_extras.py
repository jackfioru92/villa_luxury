"""Template tag di supporto per il multilingua."""
from django import template
from django.urls import translate_url as django_translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def translate_current_url(context, language_code):
    """
    Restituisce l'URL della pagina corrente nella lingua indicata.

    Usato per i link alternate hreflang. Se l'URL non e' risolvibile nella
    lingua richiesta, django_translate_url torna l'URL originale.
    """
    request = context.get('request')
    if request is None:
        return ''
    return request.build_absolute_uri(
        django_translate_url(request.get_full_path(), language_code)
    )
