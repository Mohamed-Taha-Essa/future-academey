import os
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


def validate_pdf_extension(value):
    """Validate that the uploaded file has a .pdf extension."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError(
            f'يسمح فقط بملفات PDF. تم العثور على: {ext}'
        )


class Certificate(models.Model):
    """
    Stores a student's certificate data.
    Each student can have up to 3 certificate code/PDF pairs.
    Certificate codes are globally unique identifiers.
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
        help_text="الكود الفريد للشهادة الأولى (مثال: FA0064).",
    )
    certificate_pdf_1 = models.FileField(
        "ملف الشهادة 1 (PDF)",
        upload_to="certificates/",
        validators=[validate_pdf_extension],
        help_text="ملف الـ PDF للشهادة الأولى.",
    )

    # ── Certificate 2 ──────────────────────────────────────────
    certificate_code_2 = models.CharField(
        "كود الشهادة 2",
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="الكود الفريد للشهادة الثانية (اختياري).",
    )
    certificate_pdf_2 = models.FileField(
        "ملف الشهادة 2 (PDF)",
        upload_to="certificates/",
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
        help_text="الكود الفريد للشهادة الثالثة (اختياري).",
    )
    certificate_pdf_3 = models.FileField(
        "ملف الشهادة 3 (PDF)",
        upload_to="certificates/",
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

            if code and not pdf:
                errors[f"certificate_pdf_{i}"] = "مطلوب إرفاق ملف الـ PDF عند إدخال كود الشهادة."
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

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def get_certificate_by_code(code):
        from django.db.models import Q
        code_upper = code.strip().upper()
        try:
            cert = Certificate.objects.get(
                Q(certificate_code_1__iexact=code_upper)
                | Q(certificate_code_2__iexact=code_upper)
                | Q(certificate_code_3__iexact=code_upper)
            )
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
        name_slug = slugify(self.student_name, allow_unicode=False)
        return f"{name_slug}-{code.lower()}"


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
