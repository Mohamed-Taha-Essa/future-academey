from django.conf import settings
from django.utils.translation import get_language


def site_settings_processor(request):
    """
    Context processor that injects site settings into every template.
    Provides fallback values when AppSettings has not been configured.
    """
    from .models import AppSettings

    try:
        site_settings = AppSettings.load()
    except Exception:
        # If database is not yet migrated, provide a dummy object
        site_settings = None

    current_language = get_language() or "ar"
    is_rtl = current_language == "ar"

    # Determine logo URL
    logo_url = None
    if site_settings and site_settings.logo:
        try:
            logo_url = site_settings.logo.url
        except ValueError:
            logo_url = None

    # Fallback to static logo if no admin-uploaded logo
    if not logo_url:
        from django.templatetags.static import static
        logo_url = static("images/logo.jpg")

    # Academy name based on language
    if site_settings:
        if current_language == "ar":
            academy_name = site_settings.get_academy_name_ar
            footer_text = site_settings.get_footer_text_ar
        else:
            academy_name = site_settings.get_academy_name_en
            footer_text = site_settings.get_footer_text_en

        primary_color = site_settings.get_primary_color
        secondary_color = site_settings.get_secondary_color
    else:
        # Defaults when no settings exist
        if current_language == "ar":
            academy_name = "أكاديمية Future HSE"
            footer_text = "© أكاديمية Future HSE — جميع الحقوق محفوظة."
        else:
            academy_name = "Future HSE Academy"
            footer_text = "© Future HSE Academy — All rights reserved."

        primary_color = "#0B2D4A"
        secondary_color = "#4C9F24"

    return {
        "site_settings": site_settings,
        "logo_url": logo_url,
        "academy_name": academy_name,
        "footer_text": footer_text,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "current_language": current_language,
        "is_rtl": is_rtl,
        "LANGUAGES": settings.LANGUAGES,
    }
