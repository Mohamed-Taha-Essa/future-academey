from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, StackedInline

from .models import (
    AcademySettings,
    ContactMessage,
    Course,
    CourseVideo,
    HeroSlide,
    Review,
    Service,
)


def image_preview(obj, field_name="image", max_height="60px"):
    """Safe small preview helper used in list/detail views."""
    image = getattr(obj, field_name, None)
    if not image:
        return ""
    try:
        url = image.url
    except (ValueError, AttributeError):
        return ""
    return format_html(
        '<img src="{}" style="max-height:{};border-radius:6px;object-fit:cover;"></img>',
        url,
        max_height,
    )


# ═══════════════════════════════════════════════════════════════
# AcademySettings (singleton)
# ═══════════════════════════════════════════════════════════════

@admin.register(AcademySettings)
class AcademySettingsAdmin(ModelAdmin):
    list_display = ("__str__", "whatsapp_number")

    fieldsets = (
        (
            "الاتصال العام",
            {
                "fields": ("whatsapp_number",),
                "description": "يستخدم هذا الرقم في زر الواتساب العائم وزر التسجيل في الدورات. اتركه فارغًا لإخفاء الأزرار.",
            },
        ),
    )

    def has_add_permission(self, request):
        return not AcademySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════
# HeroSlide
# ═══════════════════════════════════════════════════════════════

@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    list_display = (
        "preview",
        "title_en",
        "title_ar",
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("title_ar", "title_en", "description_ar", "description_en")
    ordering = ("display_order", "pk")
    readonly_fields = ("preview", "created_at", "updated_at")

    fieldsets = (
        ("صورة الشريحة", {"fields": ("image", "preview", "image_alt_ar", "image_alt_en")}),
        (
            "المحتوى",
            {
                "fields": (
                    "title_ar",
                    "title_en",
                    "description_ar",
                    "description_en",
                    "button_text_ar",
                    "button_text_en",
                    "button_url",
                )
            },
        ),
        (
            "النشر",
            {
                "fields": ("display_order", "is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def preview(self, obj):
        return image_preview(obj)

    preview.short_description = "معاينة"


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = (
        "preview",
        "name_en",
        "name_ar",
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_ar", "short_description_en", "short_description_ar", "slug")
    ordering = ("display_order", "pk")
    prepopulated_fields = {"slug": ("name_en",)}
    readonly_fields = ("preview", "created_at", "updated_at")

    fieldsets = (
        ("الهوية", {"fields": ("name_ar", "name_en", "slug")}),
        ("الصورة", {"fields": ("image", "preview", "image_alt_ar", "image_alt_en")}),
        (
            "محتوى البطاقة",
            {"fields": ("short_description_ar", "short_description_en")},
        ),
        (
            "صفحة التفاصيل",
            {
                "fields": ("content_ar", "content_en", "external_url"),
            },
        ),
        (
            "النشر",
            {
                "fields": ("display_order", "is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def preview(self, obj):
        return image_preview(obj)

    preview.short_description = "معاينة"


# ═══════════════════════════════════════════════════════════════
# Course + CourseVideoInline
# ═══════════════════════════════════════════════════════════════

class CourseVideoInline(StackedInline):
    model = CourseVideo
    extra = 1
    verbose_name = "فيديو الدورة"
    verbose_name_plural = "فيديوهات الدورة"
    fields = (
        "title_ar",
        "title_en",
        "description_ar",
        "description_en",
        "video_file",
        "thumbnail",
        "display_order",
        "is_active",
    )


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = (
        "preview",
        "name_en",
        "name_ar",
        "price",
        "duration_en",
        "video_count",
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_ar", "short_description_en", "short_description_ar", "slug")
    ordering = ("display_order", "pk")
    prepopulated_fields = {"slug": ("name_en",)}
    readonly_fields = ("preview", "video_count", "created_at", "updated_at")
    inlines = (CourseVideoInline,)

    fieldsets = (
        ("الهوية", {"fields": ("name_ar", "name_en", "slug")}),
        ("الصورة", {"fields": ("image", "preview", "image_alt_ar", "image_alt_en")}),
        (
            "محتوى البطاقة",
            {"fields": ("short_description_ar", "short_description_en")},
        ),
        (
            "تفاصيل الدورة",
            {"fields": ("description_ar", "description_en", "duration_ar", "duration_en", "price")},
        ),
        (
            "النشر",
            {
                "fields": ("display_order", "is_active", "video_count", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def preview(self, obj):
        return image_preview(obj)

    preview.short_description = "معاينة"

    def video_count(self, obj):
        return obj.videos.count()

    video_count.short_description = "عدد الفيديوهات"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("videos")


@admin.register(CourseVideo)
class CourseVideoAdmin(ModelAdmin):
    list_display = ("__str__", "course", "is_active", "display_order")
    list_filter = ("course", "is_active")
    search_fields = ("title_ar", "title_en", "course__name_en", "course__name_ar")
    ordering = ("course", "display_order", "pk")

    fieldsets = (
        ("الدورة", {"fields": ("course",)}),
        ("المعلومات", {"fields": ("title_ar", "title_en", "description_ar", "description_en")}),
        ("الملفات", {"fields": ("video_file", "thumbnail")}),
        (
            "النشر",
            {
                "fields": ("display_order", "is_active"),
                "classes": ("collapse",),
            },
        ),
    )


# ═══════════════════════════════════════════════════════════════
# Review
# ═══════════════════════════════════════════════════════════════

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = (
        "preview",
        "student_name_en",
        "student_name_ar",
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("student_name_ar", "student_name_en", "description_ar", "description_en")
    ordering = ("display_order", "pk")
    readonly_fields = ("preview", "created_at", "updated_at")

    fieldsets = (
        ("الصورة", {"fields": ("image", "preview", "image_alt_ar", "image_alt_en")}),
        ("اسم الطالب", {"fields": ("student_name_ar", "student_name_en")}),
        ("الوصف", {"fields": ("description_ar", "description_en")}),
        (
            "النشر",
            {
                "fields": ("display_order", "is_active", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def preview(self, obj):
        return image_preview(obj)

    preview.short_description = "معاينة"


# ═══════════════════════════════════════════════════════════════
# ContactMessage
# ═══════════════════════════════════════════════════════════════

@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ("name", "email", "phone", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "phone", "message")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_as_read", "mark_as_unread"]

    fieldsets = (
        ("المرسل", {"fields": ("name", "email", "phone")}),
        ("الرسالة", {"fields": ("message",)}),
        (
            "الحالة",
            {
                "fields": ("is_read", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
