"""Stamp a vector QR code onto a certificate PDF.

Placement is stored as fractions of the *displayed* page (what the admin
sees in the preview), with a top-left origin:

* ``x``, ``y``: top-left corner of the QR (0..1 of page width / height)
* ``size``: QR side length (0..1 of page width)

The original PDF is never modified; callers always stamp from the
original so re-stamping never produces two QR codes.
"""

import io

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


MIN_QR_SIZE = 0.05
MAX_QR_SIZE = 0.5
# White margin around the code, in QR modules. 3 matches the hand-made
# certificates (QR image with ~2.6 modules of margin) and still scans well.
QR_QUIET_ZONE_MODULES = 3

# Certificate code printed next to the QR, proportional to the QR side
# (hand-made certificates: 11pt text, 7.7pt gap for a 63.5pt QR).
LABEL_FONT = "Helvetica-Bold"
LABEL_CAP_HEIGHT = 0.718  # Helvetica cap height, fraction of font size
LABEL_SIZE_RATIO = 11 / 63.5
LABEL_GAP_RATIO = 7.7 / 63.5


class StampError(Exception):
    """The PDF cannot be read or stamped (encrypted, broken, bad page)."""


def _open_reader(pdf_file) -> PdfReader:
    if hasattr(pdf_file, "seek"):
        pdf_file.seek(0)
    try:
        reader = PdfReader(pdf_file)
        if reader.is_encrypted and not reader.decrypt(""):
            raise StampError("ملف الـ PDF محمي بكلمة مرور ولا يمكن تعديله.")
        if len(reader.pages) == 0:
            raise StampError("ملف الـ PDF لا يحتوي على صفحات.")
    except StampError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise StampError("ملف الـ PDF تالف أو غير صالح.") from exc
    return reader


def inspect_pdf(pdf_file) -> int:
    """Validate a PDF can be stamped; return its page count."""
    reader = _open_reader(pdf_file)
    count = len(reader.pages)
    if hasattr(pdf_file, "seek"):
        pdf_file.seek(0)
    return count


def compute_rect(box, x, y, size):
    """Convert top-left page fractions into PDF points.

    ``box`` is ``(left, bottom, width, height)`` of the visible page area
    (CropBox). Returns ``(left, bottom, side)`` in PDF user space
    (bottom-left origin). The square is clamped to stay inside the page.
    """
    box_left, box_bottom, width, height = box
    size = min(max(float(size), MIN_QR_SIZE), MAX_QR_SIZE)
    side = min(size * width, width, height)
    left = box_left + min(max(float(x), 0.0), 1.0) * width
    top = box_bottom + height - min(max(float(y), 0.0), 1.0) * height
    left = min(left, box_left + width - side)
    bottom = max(top - side, box_bottom)
    return left, bottom, side


def _draw_label(c, label, box, left, bottom, side):
    """Code text vertically centred on the QR: to its right, or to its left
    when there is no room before the page edge."""
    font_size = side * LABEL_SIZE_RATIO
    gap = side * LABEL_GAP_RATIO
    width = pdfmetrics.stringWidth(label, LABEL_FONT, font_size)
    box_left, _, box_width, _ = box
    text_x = left + side + gap
    if text_x + width > box_left + box_width:
        text_x = max(box_left, left - gap - width)
    cap_height = LABEL_CAP_HEIGHT * font_size
    baseline = bottom + side / 2 - cap_height / 2
    c.setFillColorRGB(0, 0, 0)
    c.setFont(LABEL_FONT, font_size)
    c.drawString(text_x, baseline, label)


def _qr_overlay(url, page_width, page_height, left, bottom, side, label, box) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))
    # White background so the QR stays scannable on any design.
    c.setFillColorRGB(1, 1, 1)
    c.rect(left, bottom, side, side, stroke=0, fill=1)

    widget = QrCodeWidget(url, barLevel="H", barBorder=QR_QUIET_ZONE_MODULES)
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(
        side,
        side,
        transform=[side / (x1 - x0), 0, 0, side / (y1 - y0), 0, 0],
    )
    drawing.add(widget)
    renderPDF.draw(drawing, c, left, bottom)
    if label:
        _draw_label(c, label, box, left, bottom, side)
    c.save()
    return buf.getvalue()


def stamp_qr(
    pdf_file, url, page_index=0, x=0.8, y=0.75, size=0.12, label=""
) -> bytes:
    """Return a new PDF (bytes) with a QR for ``url`` stamped on one page.

    ``label`` (the certificate code) is printed next to the QR when given.
    """
    reader = _open_reader(pdf_file)
    if not 0 <= int(page_index) < len(reader.pages):
        raise StampError("رقم الصفحة المحدد غير موجود في ملف الـ PDF.")

    try:
        writer = PdfWriter(clone_from=reader)
        page = writer.pages[int(page_index)]
        # Bake /Rotate into the content so page coordinates match what the
        # admin sees in the preview.
        if page.rotation:
            page.transfer_rotation_to_content()

        crop = page.cropbox
        box = (
            float(crop.left),
            float(crop.bottom),
            float(crop.width),
            float(crop.height),
        )
        left, bottom, side = compute_rect(box, x, y, size)
        media = page.mediabox
        overlay = PdfReader(
            io.BytesIO(
                _qr_overlay(
                    url,
                    float(media.right),
                    float(media.top),
                    left,
                    bottom,
                    side,
                    label,
                    box,
                )
            )
        )
        page.merge_page(overlay.pages[0])

        out = io.BytesIO()
        writer.write(out)
    except StampError:
        raise
    except Exception as exc:  # pypdf raises many internal error types
        raise StampError("تعذّر إضافة رمز QR إلى ملف الـ PDF.") from exc
    return out.getvalue()
