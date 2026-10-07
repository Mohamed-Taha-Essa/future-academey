from urllib.parse import quote


def normalize_whatsapp_number(raw_number):
    """Return only the digits of a WhatsApp number, or empty string if invalid."""
    if not raw_number:
        return ""
    digits = "".join(filter(str.isdigit, raw_number))
    if 5 <= len(digits) <= 20:
        return digits
    return ""


def build_whatsapp_url(raw_number, message=None):
    """Build a safe wa.me URL. Returns empty string when no valid number exists."""
    number = normalize_whatsapp_number(raw_number)
    if not number:
        return ""
    base = f"https://wa.me/{number}"
    if message:
        base += f"?text={quote(message)}"
    return base


def build_enrollment_message(course_name, template):
    """Compose the enrollment message using a localized format string."""
    return template.format(course=course_name) if template else ""
