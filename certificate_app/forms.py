"""Staff forms for the certificate QR stamping workflow."""

from django import forms

from .models import CODE_SLOTS, Certificate, validate_pdf_extension
from .pdf_stamp import MAX_QR_SIZE, MIN_QR_SIZE, StampError, inspect_pdf


class CertificateAdminForm(forms.ModelForm):
    """Certificate form with one PDF upload per slot.

    By default the uploaded PDF is the design *without* a QR: the server
    keeps it as the original and stamps the QR on a copy. Ticking
    ``has_qr_N`` stores the upload as-is (QR already in the design).
    The public file ``certificate_pdf_N`` is never edited directly.
    """

    upload_pdf_1 = forms.FileField(
        label="ملف الشهادة 1 (PDF)",
        required=False,
        validators=[validate_pdf_extension],
        help_text="ارفع التصميم بدون QR وسيضيف النظام رمز QR تلقائياً.",
    )
    has_qr_1 = forms.BooleanField(
        label="الملف يحتوي على QR بالفعل (لا تضف QR)", required=False
    )
    upload_pdf_2 = forms.FileField(
        label="ملف الشهادة 2 (PDF)",
        required=False,
        validators=[validate_pdf_extension],
        help_text="ارفع التصميم بدون QR وسيضيف النظام رمز QR تلقائياً.",
    )
    has_qr_2 = forms.BooleanField(
        label="الملف يحتوي على QR بالفعل (لا تضف QR)", required=False
    )
    upload_pdf_3 = forms.FileField(
        label="ملف الشهادة 3 (PDF)",
        required=False,
        validators=[validate_pdf_extension],
        help_text="ارفع التصميم بدون QR وسيضيف النظام رمز QR تلقائياً.",
    )
    has_qr_3 = forms.BooleanField(
        label="الملف يحتوي على QR بالفعل (لا تضف QR)", required=False
    )

    class Meta:
        model = Certificate
        fields = (
            "student_name",
            "certificate_code_1",
            "certificate_code_2",
            "certificate_code_3",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_sources = {}
        self.initial_pdfs = {}
        for slot in CODE_SLOTS:
            pdf = getattr(self.instance, f"certificate_pdf_{slot}")
            self.initial_pdfs[slot] = pdf.name if pdf else ""
        if self.instance.pk:
            self.existing_sources = {
                source.slot: source for source in self.instance.sources.all()
            }

    def clean(self):
        cleaned = super().clean()
        for slot in CODE_SLOTS:
            code_field = f"certificate_code_{slot}"
            upload_field = f"upload_pdf_{slot}"
            if code_field in self.errors:
                continue

            code = (cleaned.get(code_field) or "").strip()
            upload = cleaned.get(upload_field)
            has_pdf = bool(self.initial_pdfs[slot])

            if upload:
                if not code:
                    self.add_error(upload_field, "أدخل كود الشهادة قبل رفع الملف.")
                    continue
                try:
                    inspect_pdf(upload)
                except StampError as exc:
                    self.add_error(upload_field, str(exc))
                    continue
                if cleaned.get(f"has_qr_{slot}"):
                    # Final PDF with its own QR: store as the public file.
                    setattr(self.instance, f"certificate_pdf_{slot}", upload)
            elif not code and has_pdf:
                # Code removed: detach the PDF (stamped files are deleted
                # by the admin after save; manual files are kept in storage).
                setattr(self.instance, f"certificate_pdf_{slot}", None)
            elif code and not has_pdf:
                self.add_error(upload_field, "ارفع ملف الشهادة (PDF).")
        return cleaned


class QRPlacementForm(forms.Form):
    """Where to stamp the QR, as fractions of the displayed page."""

    page = forms.IntegerField(min_value=0)
    x = forms.FloatField(min_value=0.0, max_value=1.0)
    y = forms.FloatField(min_value=0.0, max_value=1.0)
    size = forms.FloatField(min_value=MIN_QR_SIZE, max_value=MAX_QR_SIZE)
    make_default = forms.BooleanField(required=False)

    def __init__(self, *args, page_count=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = page_count

    def clean_page(self):
        page = self.cleaned_data["page"]
        if page >= self.page_count:
            raise forms.ValidationError("رقم الصفحة غير موجود في الملف.")
        return page
