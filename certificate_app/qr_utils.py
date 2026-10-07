"""QR-code helpers for certificates.

Single source of truth for the verification URL encoded in every QR
(stamped into PDFs or downloaded as PNG).
"""

import io
import zipfile

import qrcode
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


QR_BOX_SIZE = 10
QR_BORDER = 4


def student_slug(student_name: str) -> str:
    """URL-safe slug for a student name.

    Arabic-only names slugify to an empty string (allow_unicode=False),
    so fall back to a neutral token — the verify view only uses the code
    part after the last hyphen anyway.
    """
    slug = slugify(student_name or "", allow_unicode=False)
    return slug.strip("-") or "certificate"


def certificate_slug(student_name: str, code: str) -> str:
    """Path segment encoded in the QR, e.g. ``karim-abbas-fa0088``."""
    return f"{student_slug(student_name)}-{code.strip().lower()}"


def build_certificate_url(student_name: str, code: str) -> str:
    """Absolute public verification URL for a (name, code) pair.

    Always uses ``CERTIFICATE_PUBLIC_BASE_URL`` — never the request host —
    because the URL is printed and can never change afterwards. No trailing
    slash, matching the QR codes already printed (shorter QR, both URL
    forms are routed).
    """
    base = settings.CERTIFICATE_PUBLIC_BASE_URL.rstrip("/")
    path = reverse(
        "certificate_app:certificate",
        args=[certificate_slug(student_name, code)],
    )
    return f"{base}{path.rstrip('/')}"


def make_qr_png_bytes(url: str) -> bytes:
    """Render a print-ready QR PNG for a verification URL."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def qr_filename(student_name: str, code: str) -> str:
    """Stable file name, e.g. ``karim-abbas-abdelghany_FA0088.png``."""
    return f"{student_slug(student_name)}_{code.strip().upper()}.png"


def iter_certificate_codes(certificate):
    """Yield ``(slot, code)`` for every filled code slot (1..3)."""
    for slot in (1, 2, 3):
        code = getattr(certificate, f"certificate_code_{slot}", None)
        if code and str(code).strip():
            yield slot, str(code).strip().upper()


def build_qr_zip(student_name: str, codes) -> bytes:
    """ZIP with one PNG per code plus a ``urls.txt`` manifest."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = []
        for code in codes:
            code = str(code).strip().upper()
            if not code:
                continue
            url = build_certificate_url(student_name, code)
            zf.writestr(qr_filename(student_name, code), make_qr_png_bytes(url))
            manifest.append(f"{code}: {url}")
        zf.writestr("urls.txt", "\n".join(manifest) + ("\n" if manifest else ""))
    return buf.getvalue()
