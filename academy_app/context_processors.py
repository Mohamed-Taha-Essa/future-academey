from .models import AcademySettings
from .utils import build_whatsapp_url, normalize_whatsapp_number


def academy_settings_processor(request):
    """Expose the academy-specific WhatsApp settings to every template."""
    try:
        academy_settings = AcademySettings.load()
    except Exception:
        academy_settings = None

    raw_number = academy_settings.whatsapp_number if academy_settings else ""
    whatsapp_number = normalize_whatsapp_number(raw_number)
    whatsapp_url = build_whatsapp_url(raw_number) if whatsapp_number else ""

    return {
        "academy_settings": academy_settings,
        "whatsapp_number": whatsapp_number,
        "whatsapp_url": whatsapp_url,
    }
