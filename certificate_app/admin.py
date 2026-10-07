import io
import zipfile

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin

from .forms import CertificateAdminForm, QRPlacementForm
from .models import CODE_SLOTS, AppSettings, Certificate
from .pdf_stamp import StampError, inspect_pdf
from .qr_utils import (
    build_certificate_url,
    build_qr_zip,
    iter_certificate_codes,
    make_qr_png_bytes,
    qr_filename,
    student_slug,
)
from .services import (
    apply_source,
    default_placement,
    remove_source,
    save_original,
    source_from_current_pdf,
)


def _download_response(content: bytes, content_type: str, filename: str):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


SLOT_TITLES = {1: "الشهادة الأولى", 2: "الشهادة الثانية", 3: "الشهادة الثالثة"}


def _slot_fieldset(slot):
    options = {
        "fields": (
            f"certificate_code_{slot}",
            f"upload_pdf_{slot}",
            f"has_qr_{slot}",
            f"qr_status_{slot}",
        ),
        "description": (
            "اكتب الكود ثم ارفع تصميم الشهادة بدون QR واحفظ: سيضيف النظام رمز QR، "
            "ثم اضغط «إضافة / تعديل مكان QR» لاختيار مكانه."
        ),
    }
    if slot > 1:
        options["classes"] = ("collapse",)
    return (SLOT_TITLES[slot], options)


# ═══════════════════════════════════════════════════════════════
# Certificate Admin
# ═══════════════════════════════════════════════════════════════

@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    """Admin configuration for Certificate model with Unfold theme."""

    form = CertificateAdminForm

    list_display = (
        "student_name",
        "certificate_code_1",
        "certificate_code_2",
        "certificate_code_3",
        "pdf_status",
        "created_at",
    )

    list_filter = ("created_at",)

    search_fields = (
        "student_name",
        "certificate_code_1",
        "certificate_code_2",
        "certificate_code_3",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "qr_status_1",
        "qr_status_2",
        "qr_status_3",
    )

    fieldsets = (
        (
            "بيانات الطالب",
            {
                "fields": ("student_name",),
                "description": "أدخل اسم الطالب رباعياً كما سيظهر في صفحة التحقق من الشهادة.",
            },
        ),
        *(_slot_fieldset(slot) for slot in CODE_SLOTS),
        (
            "معلومات النظام",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ("download_qr_zip_bundle",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sources")

    # ── Columns / read-only fields ───────────────────────────────
    @admin.display(description="حالة PDF")
    def pdf_status(self, obj):
        slots = [slot for slot, _ in iter_certificate_codes(obj)]
        if not slots:
            return "—"
        with_pdf = sum(1 for slot in slots if getattr(obj, f"certificate_pdf_{slot}"))
        stamped = {source.slot for source in obj.sources.all()}
        label = "مكتمل" if with_pdf == len(slots) else "ناقص"
        auto = len(stamped & set(slots))
        suffix = f" (QR آلي {auto})" if auto else ""
        return f"{label} {with_pdf}/{len(slots)}{suffix}"

    def _qr_status(self, obj, slot):
        code = getattr(obj, f"certificate_code_{slot}", None) if obj else None
        if not obj or not obj.pk or not code:
            return "احفظ الشهادة بالكود والملف أولاً."
        pdf = getattr(obj, f"certificate_pdf_{slot}")
        source = next((s for s in obj.sources.all() if s.slot == slot), None)
        place_url = reverse(
            "admin:certificate_app_certificate_qr_place", args=[obj.pk, slot]
        )
        png_url = reverse(
            "admin:certificate_app_certificate_qr_slot", args=[obj.pk, slot]
        )
        if source:
            state = format_html(
                "✅ تمت إضافة رمز QR تلقائياً — الرابط: <code>{}</code>",
                source.stamped_url or "—",
            )
        elif pdf:
            state = (
                "⚠️ هذا الملف لم يُضف عليه QR من النظام. إذا كان التصميم بدون QR "
                "اضغط «إضافة / تعديل مكان QR»."
            )
        else:
            state = "لا يوجد ملف PDF."

        buttons = []
        if source or pdf:
            buttons.append(
                format_html(
                    "<a href='{}' style='display:inline-block;padding:.45rem 1rem;"
                    "border-radius:6px;background:#16a34a;color:#fff;font-weight:700;"
                    "text-decoration:none;'>📍 إضافة / تعديل مكان QR</a>",
                    place_url,
                )
            )
        if pdf:
            buttons.append(
                format_html(
                    "<a href='{}' target='_blank' rel='noopener'>عرض الشهادة</a>",
                    pdf.url,
                )
            )
        buttons.append(format_html("<a href='{}'>تحميل QR (PNG)</a>", png_url))
        return format_html(
            "<div>{}</div><div style='margin-top:.5rem;display:flex;gap:1rem;"
            "align-items:center;flex-wrap:wrap;'>{}</div>",
            state,
            format_html_join("", "{}", ((b,) for b in buttons)),
        )

    @admin.display(description="رمز QR")
    def qr_status_1(self, obj):
        return self._qr_status(obj, 1)

    @admin.display(description="رمز QR")
    def qr_status_2(self, obj):
        return self._qr_status(obj, 2)

    @admin.display(description="رمز QR")
    def qr_status_3(self, obj):
        return self._qr_status(obj, 3)

    # ── Saving: store originals and stamp QR codes ───────────────
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        name_changed = "student_name" in form.changed_data
        for slot in CODE_SLOTS:
            self._sync_slot(request, obj, form, slot, change, name_changed)

    def _sync_slot(self, request, obj, form, slot, change, name_changed):
        code = getattr(obj, f"certificate_code_{slot}")
        upload = form.cleaned_data.get(f"upload_pdf_{slot}")
        has_qr = form.cleaned_data.get(f"has_qr_{slot}")
        existing = form.existing_sources.get(slot)
        old_pdf_name = form.initial_pdfs[slot]

        if not code or (upload and has_qr):
            # Code cleared, or a final PDF (QR already inside) was uploaded.
            remove_source(obj, slot, old_pdf_name=old_pdf_name)
            return

        code_changed = f"certificate_code_{slot}" in form.changed_data
        if upload:
            source = save_original(obj, slot, upload)
        elif existing and (code_changed or name_changed):
            source = existing
        else:
            if change and existing is None and getattr(obj, f"certificate_pdf_{slot}") and (
                code_changed or name_changed
            ):
                messages.warning(
                    request,
                    f"الشهادة {slot}: تم تغيير الكود أو الاسم لكن رمز QR داخل الملف "
                    "لم يُضف من النظام، تأكد أنه ما زال صحيحاً.",
                )
            return

        source.certificate = obj
        try:
            apply_source(source)
        except StampError as exc:
            messages.error(request, f"الشهادة {slot}: {exc}")
            return
        messages.success(
            request,
            f"الشهادة {slot}: تمت إضافة رمز QR ({code}). "
            "اضغط «إضافة / تعديل مكان QR» لتغيير مكانه.",
        )

    # ── Custom admin URLs ────────────────────────────────────────
    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/qr-place/<int:slot>/",
                self.admin_site.admin_view(self.qr_place_view),
                name="certificate_app_certificate_qr_place",
            ),
            path(
                "<path:object_id>/qr-source/<int:slot>/",
                self.admin_site.admin_view(self.qr_source_view),
                name="certificate_app_certificate_qr_source",
            ),
            path(
                "<path:object_id>/qr/<int:slot>/",
                self.admin_site.admin_view(self.qr_slot_view),
                name="certificate_app_certificate_qr_slot",
            ),
            path(
                "<path:object_id>/qr-zip/",
                self.admin_site.admin_view(self.qr_zip_view),
                name="certificate_app_certificate_qr_zip",
            ),
        ]
        return custom + super().get_urls()

    def _get_certificate(self, request, object_id, permission):
        if not str(object_id).isdigit():
            raise Http404
        cert = get_object_or_404(Certificate, pk=object_id)
        if not getattr(self, f"has_{permission}_permission")(request, cert):
            raise PermissionDenied
        return cert

    def _get_slot(self, cert, slot):
        """Return ``(source or None, current pdf)`` for a slot with a code."""
        if slot not in CODE_SLOTS or not getattr(cert, f"certificate_code_{slot}"):
            raise Http404
        source = cert.sources.filter(slot=slot).first()
        pdf = getattr(cert, f"certificate_pdf_{slot}")
        if source is None and not pdf:
            raise Http404
        if source is not None:
            source.certificate = cert
        return source, pdf

    # ── Views ────────────────────────────────────────────────────
    def qr_place_view(self, request, object_id, slot):
        """Drag/resize the QR on a preview of the original, then stamp.

        A slot without an original (PDF uploaded as final) uses its current
        PDF as the original on the first "Apply".
        """
        cert = self._get_certificate(request, object_id, "change")
        source, pdf = self._get_slot(cert, slot)
        change_url = reverse("admin:certificate_app_certificate_change", args=[cert.pk])

        preview_file = source.original_pdf if source else pdf
        try:
            with preview_file.open("rb") as handle:
                page_count = inspect_pdf(handle)
        except StampError as exc:
            messages.error(request, str(exc))
            return redirect(change_url)

        form = QRPlacementForm(request.POST or None, page_count=page_count)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            if source is None:
                source = source_from_current_pdf(cert, slot)
            source.certificate = cert
            source.page = data["page"]
            source.x = data["x"]
            source.y = data["y"]
            source.size = data["size"]
            source.save(update_fields=["page", "x", "y", "size"])
            if data["make_default"]:
                settings_obj = AppSettings.load()
                settings_obj.qr_default_page = data["page"]
                settings_obj.qr_default_x = data["x"]
                settings_obj.qr_default_y = data["y"]
                settings_obj.qr_default_size = data["size"]
                settings_obj.save()
            try:
                apply_source(source)
            except StampError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"الشهادة {slot}: تم وضع رمز QR في الشهادة.")
            # Back to the certificate so staff can continue with other slots.
            return redirect(change_url)

        placement = (
            {"page": source.page, "x": source.x, "y": source.y, "size": source.size}
            if source
            else default_placement()
        )
        placement["page"] = min(placement["page"], page_count - 1)
        size_field = QRPlacementForm.base_fields["size"]
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": cert,
            "title": f"مكان رمز QR — {cert.student_name} — الشهادة {slot}",
            "form": form,
            "source": source,
            "code": getattr(cert, f"certificate_code_{slot}"),
            "page_range": range(page_count),
            "min_size": size_field.min_value,
            "max_size": size_field.max_value,
            "stamped_url": pdf.url if (pdf and source) else "",
            "change_url": change_url,
            "placement": {
                **placement,
                "defaults": default_placement(),
                "page_count": page_count,
                "min_size": size_field.min_value,
                "max_size": size_field.max_value,
                "source_url": reverse(
                    "admin:certificate_app_certificate_qr_source",
                    args=[cert.pk, slot],
                ),
            },
        }
        return render(request, "admin/certificate_app/qr_place.html", context)

    def qr_source_view(self, request, object_id, slot):
        """Stream the PDF to place the QR on (same-origin, for PDF.js)."""
        cert = self._get_certificate(request, object_id, "change")
        source, pdf = self._get_slot(cert, slot)
        preview_file = source.original_pdf if source else pdf
        return FileResponse(preview_file.open("rb"), content_type="application/pdf")

    def qr_slot_view(self, request, object_id, slot):
        cert = self._get_certificate(request, object_id, "view")
        code = (getattr(cert, f"certificate_code_{slot}", "") or "").strip() if slot in CODE_SLOTS else ""
        if not code:
            raise Http404
        url = build_certificate_url(cert.student_name, code)
        return _download_response(
            make_qr_png_bytes(url), "image/png", qr_filename(cert.student_name, code)
        )

    def qr_zip_view(self, request, object_id):
        cert = self._get_certificate(request, object_id, "view")
        codes = [code for _, code in iter_certificate_codes(cert)]
        if not codes:
            raise Http404
        return _download_response(
            build_qr_zip(cert.student_name, codes),
            "application/zip",
            f"{student_slug(cert.student_name)}_qrcodes.zip",
        )

    @admin.action(description="تحميل رموز QR (ZIP لكل طالب)", permissions=["view"])
    def download_qr_zip_bundle(self, request, queryset):
        """Batch action: one ZIP containing a folder per student."""
        buf = io.BytesIO()
        count = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for cert in queryset:
                folder = student_slug(cert.student_name)
                for _, code in iter_certificate_codes(cert):
                    url = build_certificate_url(cert.student_name, code)
                    zf.writestr(
                        f"{folder}/{qr_filename(cert.student_name, code)}",
                        make_qr_png_bytes(url),
                    )
                    count += 1
        if count == 0:
            messages.error(request, "الشهادات المحددة لا تحتوي على أكواد.")
            return None
        return _download_response(
            buf.getvalue(), "application/zip", "certificates_qrcodes.zip"
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
            "روابط التواصل الاجتماعي",
            {
                "fields": ("facebook_url", "instagram_url", "linkedin_url", "youtube_url"),
            },
        ),
        (
            "تذييل الموقع (الفوتر)",
            {
                "fields": ("footer_text_ar", "footer_text_en"),
            },
        ),
        (
            "الموضع الافتراضي لرمز QR في الشهادات",
            {
                "fields": (
                    "qr_default_page",
                    "qr_default_x",
                    "qr_default_y",
                    "qr_default_size",
                ),
                "description": (
                    "يُستخدم عند رفع شهادة جديدة بدون QR. الأسهل ضبطه من صفحة "
                    "«تعديل مكان QR» لأي شهادة واختيار «اجعله الموضع الافتراضي»."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        """Only allow adding if no settings record exists."""
        return not AppSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton."""
        return False
