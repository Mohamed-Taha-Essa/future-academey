import os
import re
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.text import get_valid_filename

from .qr_utils import certificate_slug

CODE_SLOTS = (1, 2, 3)

# Default QR box measured from the hand-made certificates (A4 landscape):
# 63.5pt square, 42pt from the left edge, 19pt from the bottom edge.
QR_DEFAULT_X = 0.0499
QR_DEFAULT_Y = 0.8614
QR_DEFAULT_SIZE = 0.0754
CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


def validate_pdf_extension(value):
    """Validate that the uploaded file has a .pdf extension."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError(
            f'يسمح فقط بملفات PDF. تم العثور على: {ext}'
        )


def _unique_name(folder, filename):
    """Unique storage key: R2/S3 storage overwrites files with equal names."""
    base = get_valid_filename(os.path.basename(filename)) or "certificate.pdf"
    return f"{folder}/{uuid.uuid4().hex[:12]}_{base}"


def certificate_pdf_upload_to(instance, filename):
    return _unique_name("certificates", filename)


def original_pdf_upload_to(instance, filename):
    return _unique_name("certificates/originals", filename)


def validate_certificate_code(value):
    """Letters and digits only: the verify view splits the URL on '-'."""
    if value and not CODE_PATTERN.match(value.strip()):
        raise ValidationError(
            "الكود يجب أن يحتوي على حروف إنجليزية وأرقام فقط (بدون مسافات أو شرطة -)."
        )


class Certificate(models.Model):
    """
    Stores a student's certificate data.
    Each student can have up to 3 certificate code/PDF pairs.
    Certificate codes are globally unique identifiers.

    A certificate PDF is either uploaded final (manual mode, QR already in
    the design) or produced by stamping a QR on an original uploaded through
    ``CertificateSource`` (stamped mode).
    """

    student_name = models.CharField(
        "اسم الطالب",
        max_length=255,
        help_text="الاسم الثلاثي أو الرباعي للطالب.",
    )

    # ── Certificate 1 ──────────────────────────────────────────
    certificate_code_1 = models.CharField(
        "كود الشهادة 1",
        max_length=50,
        unique=True,
        validators=[validate_certificate_code],
        help_text="الكود الفريد للشهادة الأولى (مثال: FA0064).",
    )
    certificate_pdf_1 = models.FileField(
        "ملف الشهادة 1 (PDF)",
        upload_to=certificate_pdf_upload_to,
        validators=[validate_pdf_extension],
        blank=True,
        help_text="ملف الـ PDF النهائي للشهادة الأولى.",
    )

    # ── Certificate 2 ──────────────────────────────────────────
    certificate_code_2 = models.CharField(
        "كود الشهادة 2",
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        validators=[validate_certificate_code],
        help_text="الكود الفريد للشهادة الثانية (اختياري).",
    )
    certificate_pdf_2 = models.FileField(
        "ملف الشهادة 2 (PDF)",
        upload_to=certificate_pdf_upload_to,
        validators=[validate_pdf_extension],
        blank=True,
        null=True,
        help_text="ملف الـ PDF للشهادة الثانية (اختياري).",
    )

    # ── Certificate 3 ──────────────────────────────────────────
    certificate_code_3 = models.CharField(
        "كود الشهادة 3",
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        validators=[validate_certificate_code],
        help_text="الكود الفريد للشهادة الثالثة (اختياري).",
    )
    certificate_pdf_3 = models.FileField(
        "ملف الشهادة 3 (PDF)",
        upload_to=certificate_pdf_upload_to,
        validators=[validate_pdf_extension],
        blank=True,
        null=True,
        help_text="ملف الـ PDF للشهادة الثالثة (اختياري).",
    )

    # ── Timestamps ─────────────────────────────────────────────
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "شهادة المتدرب"
        verbose_name_plural = "شهادات المتدربين"
        ordering = ["-created_at"]

    def __str__(self):
        return self.student_name

    def clean(self):
        super().clean()
        errors = {}

        codes = []
        for i in range(1, 4):
            code = getattr(self, f"certificate_code_{i}")
            pdf = getattr(self, f"certificate_pdf_{i}")

            if code:
                code_upper = code.strip().upper()
                setattr(self, f"certificate_code_{i}", code_upper)
                codes.append((i, code_upper))

            # "Code requires a PDF" is enforced by the admin form, which
            # also knows about an uploaded original to stamp.
            if pdf and not code:
                errors[f"certificate_code_{i}"] = "مطلوب إدخال الكود عند إرفاق ملف الشهادة."

        seen = {}
        for idx, code in codes:
            if code in seen:
                errors[f"certificate_code_{idx}"] = (
                    f"هذا الكود مكرر مع الشهادة رقم {seen[code]}. "
                    "يجب أن يكون لكل شهادة كود مختلف."
                )
            else:
                seen[code] = idx

        # DB unique=True is per column only: the same code in slot 1 of one
        # student and slot 2 of another would make both verify pages 404.
        for idx, code in codes:
            if f"certificate_code_{idx}" in errors:
                continue
            clash = (
                Certificate.objects.exclude(pk=self.pk)
                .filter(code_lookup(code))
                .first()
            )
            if clash:
                errors[f"certificate_code_{idx}"] = (
                    f"الكود {code} مستخدم بالفعل لشهادة الطالب: {clash.student_name}."
                )

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def get_certificate_by_code(code):
        code_upper = code.strip().upper()
        try:
            cert = Certificate.objects.get(code_lookup(code_upper))
        except Certificate.DoesNotExist:
            return None
        except Certificate.MultipleObjectsReturned:
            return None

        if cert.certificate_code_1 and cert.certificate_code_1.upper() == code_upper:
            return {"certificate": cert, "code": cert.certificate_code_1, "pdf": cert.certificate_pdf_1}
        elif cert.certificate_code_2 and cert.certificate_code_2.upper() == code_upper:
            return {"certificate": cert, "code": cert.certificate_code_2, "pdf": cert.certificate_pdf_2}
        elif cert.certificate_code_3 and cert.certificate_code_3.upper() == code_upper:
            return {"certificate": cert, "code": cert.certificate_code_3, "pdf": cert.certificate_pdf_3}

        return None

    def generate_url_slug(self, code):
        return certificate_slug(self.student_name, code)


def code_lookup(code):
    """Case-insensitive match of ``code`` against all three code columns."""
    query = Q()
    for slot in CODE_SLOTS:
        query |= Q(**{f"certificate_code_{slot}__iexact": code})
    return query


class CertificateSource(models.Model):
    """Original certificate PDF (without QR) + where to stamp the QR.

    The stamped result is written to ``Certificate.certificate_pdf_<slot>``;
    stamping always starts from this original, never from a stamped file.
    """

    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name="sources",
        verbose_name="الشهادة",
    )
    slot = models.PositiveSmallIntegerField(
        "رقم الشهادة",
        choices=[(slot, str(slot)) for slot in CODE_SLOTS],
    )
    original_pdf = models.FileField(
        "ملف PDF الأصلي (بدون QR)",
        upload_to=original_pdf_upload_to,
        validators=[validate_pdf_extension],
    )
    page = models.PositiveSmallIntegerField("الصفحة", default=0)
    x = models.FloatField(
        "الموضع الأفقي",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    y = models.FloatField(
        "الموضع الرأسي",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    size = models.FloatField(
        "حجم الـ QR",
        validators=[MinValueValidator(0.05), MaxValueValidator(0.5)],
    )
    stamped_code = models.CharField("الكود المطبوع", max_length=50, blank=True)
    stamped_url = models.URLField("الرابط المطبوع", max_length=500, blank=True)
    stamped_at = models.DateTimeField("تاريخ الطباعة", null=True, blank=True)

    class Meta:
        verbose_name = "ملف شهادة أصلي"
        verbose_name_plural = "ملفات الشهادات الأصلية"
        constraints = [
            models.UniqueConstraint(
                fields=["certificate", "slot"],
                name="unique_certificate_source_slot",
            )
        ]

    def __str__(self):
        return f"{self.certificate} — {self.slot}"


class AppSettings(models.Model):
    """
    Singleton model for site-wide settings.
    """

    logo = models.ImageField(
        "شعار الأكاديمية",
        upload_to="settings/",
        blank=True,
        null=True,
        help_text="الشعار الرسمي للموقع. يفضل أن يكون بحجم 400x400 بكسل.",
    )

    academy_name_ar = models.CharField(
        "اسم الأكاديمية (عربي)",
        max_length=255,
        blank=True,
        null=True,
    )

    academy_name_en = models.CharField(
        "اسم الأكاديمية (إنجليزي)",
        max_length=255,
        blank=True,
        null=True,
    )

    primary_color = models.CharField(
        "اللون الأساسي",
        max_length=20,
        blank=True,
        null=True,
        help_text="رمز اللون الأساسي (مثال: #0B2D4A).",
    )

    secondary_color = models.CharField(
        "اللون الثانوي",
        max_length=20,
        blank=True,
        null=True,
        help_text="رمز اللون الثانوي (مثال: #4C9F24).",
    )

    facebook_url = models.URLField("Facebook", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    linkedin_url = models.URLField("LinkedIn", blank=True)
    youtube_url = models.URLField("YouTube", blank=True)

    footer_text_ar = models.TextField(
        "نص التذييل (عربي)",
        blank=True,
        null=True,
    )

    footer_text_en = models.TextField(
        "نص التذييل (إنجليزي)",
        blank=True,
        null=True,
    )

    # ── Default QR position on stamped certificates ────────────
    qr_default_page = models.PositiveSmallIntegerField(
        "صفحة الـ QR الافتراضية",
        default=0,
        help_text="0 = الصفحة الأولى.",
    )
    qr_default_x = models.FloatField(
        "الموضع الأفقي الافتراضي",
        default=QR_DEFAULT_X,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="نسبة من عرض الصفحة (0 = يسار، 1 = يمين) لأعلى يسار الـ QR.",
    )
    qr_default_y = models.FloatField(
        "الموضع الرأسي الافتراضي",
        default=QR_DEFAULT_Y,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="نسبة من ارتفاع الصفحة (0 = أعلى، 1 = أسفل) لأعلى يسار الـ QR.",
    )
    qr_default_size = models.FloatField(
        "حجم الـ QR الافتراضي",
        default=QR_DEFAULT_SIZE,
        validators=[MinValueValidator(0.05), MaxValueValidator(0.5)],
        help_text="نسبة من عرض الصفحة.",
    )
    qr_show_code = models.BooleanField(
        "طباعة الكود بجانب رمز QR",
        default=True,
        help_text="أوقفه إذا كان تصميم الشهادة يحتوي على الكود مكتوباً بالفعل.",
    )

    class Meta:
        verbose_name = "إعدادات الموقع"
        verbose_name_plural = "إعدادات الموقع"

    def __str__(self):
        return "إعدادات الموقع"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def get_primary_color(self):
        return self.primary_color or "#0B2D4A"

    @property
    def get_secondary_color(self):
        return self.secondary_color or "#4C9F24"

    @property
    def get_academy_name_ar(self):
        return self.academy_name_ar or "أكاديمية Future HSE"

    @property
    def get_academy_name_en(self):
        return self.academy_name_en or "Future HSE Academy"

    @property
    def get_footer_text_ar(self):
        return self.footer_text_ar or "© أكاديمية Future HSE — جميع الحقوق محفوظة."

    @property
    def get_footer_text_en(self):
        return self.footer_text_en or "© Future HSE Academy — All rights reserved."
