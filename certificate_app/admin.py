from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AppSettings, Certificate


# ═══════════════════════════════════════════════════════════════
# Certificate Admin
# ═══════════════════════════════════════════════════════════════

@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    """Admin configuration for Certificate model with Unfold theme."""

    list_display = (
        "student_name",
        "certificate_code_1",
        "certificate_code_2",
        "certificate_code_3",
        "created_at",
    )

    list_filter = ("created_at",)

    search_fields = (
        "student_name",
        "certificate_code_1",
        "certificate_code_2",
        "certificate_code_3",
    )

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "بيانات الطالب",
            {
                "fields": ("student_name",),
                "description": "أدخل اسم الطالب رباعياً كما سيظهر في صفحة التحقق من الشهادة.",
            },
        ),
        (
            "الشهادة الأولى",
            {
                "fields": ("certificate_code_1", "certificate_pdf_1"),
            },
        ),
        (
            "الشهادة الثانية",
            {
                "fields": ("certificate_code_2", "certificate_pdf_2"),
                "classes": ("collapse",),
                "description": "اختياري. اترك الحقول فارغة إذا كان الطالب لديه شهادة واحدة فقط.",
            },
        ),
        (
            "الشهادة الثالثة",
            {
                "fields": ("certificate_code_3", "certificate_pdf_3"),
                "classes": ("collapse",),
                "description": "اختياري. اترك الحقول فارغة إذا كان الطالب ليس لديه شهادة ثالثة.",
            },
        ),
        (
            "معلومات النظام",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# ═══════════════════════════════════════════════════════════════
# AppSettings Admin (Singleton)
# ═══════════════════════════════════════════════════════════════

@admin.register(AppSettings)
class AppSettingsAdmin(ModelAdmin):
    """Admin configuration for AppSettings singleton with Unfold theme."""

    list_display = ("__str__",)

    fieldsets = (
        (
            "هوية الأكاديمية",
            {
                "fields": ("logo", "academy_name_ar", "academy_name_en"),
            },
        ),
        (
            "الألوان الأساسية",
            {
                "fields": ("primary_color", "secondary_color"),
                "description": "أكواد الألوان المستخدمة في الموقع. اتركها فارغة لاستخدام الألوان الافتراضية.",
            },
        ),
        (
            "تذييل الموقع (الفوتر)",
            {
                "fields": ("footer_text_ar", "footer_text_en"),
            },
        ),
    )

    def has_add_permission(self, request):
        """Only allow adding if no settings record exists."""
        return not AppSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton."""
        return False
