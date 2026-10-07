"""Certificate QR stamping workflow (storage-agnostic: local or R2)."""

import uuid

import os

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .models import AppSettings, CertificateSource
from .pdf_stamp import stamp_qr
from .qr_utils import build_certificate_url, student_slug

STAMPED_PREFIX = "certificates/stamped/"


def default_placement():
    settings_obj = AppSettings.load()
    return {
        "page": settings_obj.qr_default_page,
        "x": settings_obj.qr_default_x,
        "y": settings_obj.qr_default_y,
        "size": settings_obj.qr_default_size,
    }


def _delete_if_stamped(name):
    """Delete a previous stamped output; never touch manual uploads."""
    if name and name.startswith(STAMPED_PREFIX):
        default_storage.delete(name)


def apply_source(source: CertificateSource) -> None:
    """Stamp the slot's QR on the original and store it as the public PDF.

    Raises ``pdf_stamp.StampError`` if the original cannot be stamped.
    """
    certificate = source.certificate
    slot = source.slot
    code = getattr(certificate, f"certificate_code_{slot}")
    url = build_certificate_url(certificate.student_name, code)

    with source.original_pdf.open("rb") as original:
        pdf_bytes = stamp_qr(
            original, url, source.page, source.x, source.y, source.size
        )

    field_name = f"certificate_pdf_{slot}"
    previous = getattr(certificate, field_name)
    previous_name = previous.name if previous else ""

    # Fresh key per stamp: never overwrite a file a browser may have cached.
    key = (
        f"{STAMPED_PREFIX}{student_slug(certificate.student_name)}_{code}_"
        f"{uuid.uuid4().hex[:8]}.pdf"
    )
    stored_name = previous.storage.save(key, ContentFile(pdf_bytes))
    setattr(certificate, field_name, stored_name)
    certificate.save(update_fields=[field_name, "updated_at"])

    if previous_name.startswith(STAMPED_PREFIX) and previous_name != stored_name:
        previous.storage.delete(previous_name)

    source.stamped_code = code
    source.stamped_url = url
    source.stamped_at = timezone.now()
    source.save(update_fields=["stamped_code", "stamped_url", "stamped_at"])


def save_original(certificate, slot, uploaded_file) -> CertificateSource:
    """Create/replace the slot's original PDF, keeping any custom position."""
    source = CertificateSource.objects.filter(
        certificate=certificate, slot=slot
    ).first()
    if source is None:
        source = CertificateSource(
            certificate=certificate, slot=slot, **default_placement()
        )
    else:
        source.original_pdf.delete(save=False)
    source.original_pdf.save(uploaded_file.name, uploaded_file, save=False)
    source.save()
    return source


def source_from_current_pdf(certificate, slot) -> CertificateSource:
    """Use the slot's current (manual) PDF as the original to stamp on.

    The manual file itself is left untouched in storage.
    """
    current = getattr(certificate, f"certificate_pdf_{slot}")
    with current.open("rb") as handle:
        content = ContentFile(handle.read(), name=os.path.basename(current.name))
    return save_original(certificate, slot, content)


def remove_source(certificate, slot, old_pdf_name="") -> None:
    """Drop a slot's original and its stamped output.

    ``old_pdf_name`` is the slot's public file before this save.
    """
    _delete_if_stamped(old_pdf_name)
    source = CertificateSource.objects.filter(
        certificate=certificate, slot=slot
    ).first()
    if source is None:
        return
    source.original_pdf.delete(save=False)
    source.delete()
