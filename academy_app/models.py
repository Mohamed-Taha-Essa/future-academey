import os

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

# ═══════════════════════════════════════════════════════════════
# Validators
# ═══════════════════════════════════════════════════════════════

VIDEO_MAX_BYTES = 15 * 1024 * 1024  # 15 MB: matches project upload limit


def validate_video_size(value):
    """Reject video files larger than the configured upload limit."""
    if value.size > VIDEO_MAX_BYTES:
        megabytes = value.size / (1024 * 1024)
        raise ValidationError(
            _("حجم الفيديو كبير جدًا (%(size)s م.ب). الحد الأقصى 15 م.ب") % {
                "size": round(megabytes, 1)
            }
        )


VIDEO_VALIDATORS = [
    FileExtensionValidator(
        allowed_extensions=["mp4", "webm"],
        message=_("اسم الملف ليس مدعومًا. استخدم mp4 أو webm."),
    ),
    validate_video_size,
]


# ═══════════════════════════════════════════════════════════════
# AcademySettings singleton
# ═══════════════════════════════════════════════════════════════

class AcademySettings(models.Model):
    """Singleton settings model owned by the public academy app."""

    whatsapp_number = models.CharField(
        "رقم الواتساب",
        max_length=32,
        blank=True,
        default="",
        help_text="رقم الواتساب بالصيغة الدولية بدون "+" مثل: 201001234567. اتركه فارغًا لإخفاء أزرار الواتساب.",
    )

    class Meta:
        verbose_name = "إعدادات الأكاديمية"
        verbose_name_plural = "إعدادات الأكاديمية"

    def __str__(self):
        return "إعدادات الأكاديمية"

    def clean(self):
        super().clean()
        if self.whatsapp_number:
            digits = "".join(filter(str.isdigit, self.whatsapp_number))
            if not 5 <= len(digits) <= 20:
                raise ValidationError(
                    {"whatsapp_number": _("رقم الواتساب غير صالح.")}
                )
            self.whatsapp_number = digits

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return None


# ═══════════════════════════════════════════════════════════════
# Helper mixin for bilingual fields
# ═══════════════════════════════════════════════════════════════

class LocalizedMixin:
    """Provide *localized_* accessors that pick AR/EN by current language."""

    def _localized(self, base_name):
        lang = get_language()
        if lang == "ar":
            value = getattr(self, f"{base_name}_ar", "")
        else:
            value = getattr(self, f"{base_name}_en", "")
        return value or getattr(self, f"{base_name}_en", "")

    def localized_name(self):
        return self._localized("name")

    def localized_title(self):
        return self._localized("title")

    def localized_description(self):
        return self._localized("description")

    def localized_short_description(self):
        return self._localized("short_description")

    def localized_content(self):
        return self._localized("content")

    def localized_button_text(self):
        return self._localized("button_text")

    def localized_image_alt(self, fallback=""):
        return self._localized("image_alt") or fallback

    def localized_duration(self):
        return self._localized("duration")

    def localized_student_name(self):
        return self._localized("student_name")


# ═══════════════════════════════════════════════════════════════
# HeroSlide
# ═══════════════════════════════════════════════════════════════

class HeroSlide(LocalizedMixin, models.Model):
    image = models.ImageField("صورة العرض", upload_to="hero/")
    image_alt_ar = models.CharField("النص البديل للصورة (عربي)", max_length=255, blank=True)
    image_alt_en = models.CharField("النص البديل للصورة (إنجليزي)", max_length=255, blank=True)
    title_ar = models.CharField("العنوان (عربي)", max_length=255, blank=True)
    title_en = models.CharField("العنوان (إنجليزي)", max_length=255, blank=True)
    description_ar = models.TextField("الوصف (عربي)", blank=True)
    description_en = models.TextField("الوصف (إنجليزي)", blank=True)
    button_text_ar = models.CharField("نص الزر (عربي)", max_length=100, blank=True)
    button_text_en = models.CharField("نص الزر (إنجليزي)", max_length=100, blank=True)
    button_url = models.URLField("رابط الزر", blank=True)
    display_order = models.PositiveIntegerField("ترتيب العرض", default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "شريحة العرض الرئيسي"
        verbose_name_plural = "شرائح العرض الرئيسي"
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return self.title_en or self.title_ar or f"Slide {self.pk}"


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class Service(LocalizedMixin, models.Model):
    name_ar = models.CharField("اسم الخدمة (عربي)", max_length=255)
    name_en = models.CharField("اسم الخدمة (إنجليزي)", max_length=255)
    slug = models.SlugField("الرابط المختصر", max_length=180, unique=True)
    image = models.ImageField("صورة الخدمة", upload_to="services/")
    image_alt_ar = models.CharField("النص البديل (عربي)", max_length=255, blank=True)
    image_alt_en = models.CharField("النص البديل (إنجليزي)", max_length=255, blank=True)
    short_description_ar = models.TextField("الوصف المختصر (عربي)", blank=True)
    short_description_en = models.TextField("الوصف المختصر (إنجليزي)", blank=True)
    content_ar = models.TextField("المحتوى (عربي)", blank=True)
    content_en = models.TextField("المحتوى (إنجليزي)", blank=True)
    external_url = models.URLField("رابط خارجي", blank=True)
    display_order = models.PositiveIntegerField("ترتيب العرض", default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "خدمة"
        verbose_name_plural = "الخدمات"
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return self.name_en or self.name_ar


# ═══════════════════════════════════════════════════════════════
# Course + CourseVideo
# ═══════════════════════════════════════════════════════════════

class Course(LocalizedMixin, models.Model):
    name_ar = models.CharField("اسم الدورة (عربي)", max_length=255)
    name_en = models.CharField("اسم الدورة (إنجليزي)", max_length=255)
    slug = models.SlugField("الرابط المختصر", max_length=180, unique=True)
    image = models.ImageField("صورة الدورة", upload_to="courses/")
    image_alt_ar = models.CharField("النص البديل (عربي)", max_length=255, blank=True)
    image_alt_en = models.CharField("النص البديل (إنجليزي)", max_length=255, blank=True)
    short_description_ar = models.TextField("الوصف المختصر (عربي)", blank=True)
    short_description_en = models.TextField("الوصف المختصر (إنجليزي)", blank=True)
    description_ar = models.TextField("الوصف الكامل (عربي)", blank=True)
    description_en = models.TextField("الوصف الكامل (إنجليزي)", blank=True)
    duration_ar = models.CharField("المدة (عربي)", max_length=100)
    duration_en = models.CharField("المدة (إنجليزي)", max_length=100)
    price = models.DecimalField(
        "السعر",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    display_order = models.PositiveIntegerField("ترتيب العرض", default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "دورة تدريبية"
        verbose_name_plural = "الدورات التدريبية"
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return self.name_en or self.name_ar


class CourseVideo(LocalizedMixin, models.Model):
    course = models.ForeignKey(
        Course,
        related_name="videos",
        on_delete=models.CASCADE,
        verbose_name="الدورة",
    )
    title_ar = models.CharField("العنوان (عربي)", max_length=255, blank=True)
    title_en = models.CharField("العنوان (إنجليزي)", max_length=255, blank=True)
    description_ar = models.TextField("الوصف (عربي)", blank=True)
    description_en = models.TextField("الوصف (إنجليزي)", blank=True)
    video_file = models.FileField(
        "ملف الفيديو",
        upload_to="courses/videos/",
        validators=VIDEO_VALIDATORS,
        help_text="يدعم mp4 أو webm بحجم أقصاه 15 م.ب",
    )
    thumbnail = models.ImageField(
        "صورة مصغرة",
        upload_to="courses/video_thumbnails/",
        blank=True,
    )
    display_order = models.PositiveIntegerField("ترتيب العرض", default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "فيديو الدورة"
        verbose_name_plural = "فيديوهات الدورات"
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["course", "is_active", "display_order"]),
        ]

    def __str__(self):
        return f"{self.course} - {self.title_en or self.title_ar or self.pk}"


# ═══════════════════════════════════════════════════════════════
# Review
# ═══════════════════════════════════════════════════════════════

class Review(LocalizedMixin, models.Model):
    image = models.ImageField("صورة التقييم", upload_to="reviews/")
    image_alt_ar = models.CharField("النص البديل (عربي)", max_length=255, blank=True)
    image_alt_en = models.CharField("النص البديل (إنجليزي)", max_length=255, blank=True)
    student_name_ar = models.CharField("اسم الطالب (عربي)", max_length=255, blank=True)
    student_name_en = models.CharField("اسم الطالب (إنجليزي)", max_length=255, blank=True)
    description_ar = models.TextField("الوصف (عربي)", blank=True)
    description_en = models.TextField("الوصف (إنجليزي)", blank=True)
    display_order = models.PositiveIntegerField("ترتيب العرض", default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "تقييم الطالب"
        verbose_name_plural = "تقييمات الطلاب"
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return self.student_name_en or self.student_name_ar or f"Review {self.pk}"


# ═══════════════════════════════════════════════════════════════
# ContactMessage
# ═══════════════════════════════════════════════════════════════

class ContactMessage(models.Model):
    name = models.CharField("الاسم", max_length=150)
    email = models.EmailField("البريد الإلكتروني")
    phone = models.CharField("رقم الهاتف", max_length=32)
    message = models.TextField("الرسالة")
    is_read = models.BooleanField("مقروء", default=False)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التعديل", auto_now=True)

    class Meta:
        verbose_name = "رسالة اتصال"
        verbose_name_plural = "رسائل الاتصال"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_read", "created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.email}"
