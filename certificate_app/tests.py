import io
import shutil
import tempfile

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from .models import AppSettings, Certificate, CertificateSource
from .pdf_stamp import StampError, compute_rect, inspect_pdf, stamp_qr
from .qr_utils import build_certificate_url, certificate_slug

BASE_URL = "https://www.futureacademey.com"
TEMP_MEDIA = tempfile.mkdtemp()

# Never touch the real bucket: a developer .env may configure R2 storage.
LOCAL_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": TEMP_MEDIA, "base_url": "/media/"},
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


def make_pdf(pages=1, pagesize=landscape(A4), rotate=0):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)
    for i in range(pages):
        c.drawString(100, 100, f"design page {i}")
        c.showPage()
    c.save()
    if not rotate:
        return buf.getvalue()
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(buf.getvalue())).pages:
        page.rotate(rotate)
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def pdf_upload(name="design.pdf", **kwargs):
    return SimpleUploadedFile(name, make_pdf(**kwargs), content_type="application/pdf")


# ═══════════════════════════════════════════════════════════════
# Stamping engine
# ═══════════════════════════════════════════════════════════════

class PdfStampTests(TestCase):
    def test_compute_rect_converts_top_left_fractions(self):
        left, bottom, side = compute_rect((0, 0, 1000, 500), 0.1, 0.2, 0.1)
        self.assertEqual((left, side), (100, 100))
        # top = 500 - 0.2 * 500 = 400 → bottom = 300
        self.assertEqual(bottom, 300)

    def test_compute_rect_respects_cropbox_origin(self):
        left, bottom, side = compute_rect((50, 20, 1000, 500), 0, 0, 0.1)
        self.assertEqual((left, bottom, side), (50, 420, 100))

    def test_compute_rect_clamps_inside_page(self):
        left, bottom, side = compute_rect((0, 0, 1000, 500), 0.99, 0.99, 0.2)
        self.assertLessEqual(left + side, 1000)
        self.assertGreaterEqual(bottom, 0)

    def test_stamp_keeps_pages_and_changes_target_page(self):
        original = make_pdf(pages=2)
        out = stamp_qr(io.BytesIO(original), f"{BASE_URL}/certificate/a-fa1", 1)
        reader = PdfReader(io.BytesIO(out))
        self.assertEqual(len(reader.pages), 2)
        source = PdfReader(io.BytesIO(original))
        self.assertEqual(
            reader.pages[0].get_contents().get_data(),
            source.pages[0].get_contents().get_data(),
        )
        self.assertNotEqual(
            reader.pages[1].get_contents().get_data(),
            source.pages[1].get_contents().get_data(),
        )

    def test_restamping_from_original_is_idempotent(self):
        original = make_pdf()
        url = f"{BASE_URL}/certificate/a-fa1"
        first = stamp_qr(io.BytesIO(original), url, 0, 0.1, 0.1, 0.1)
        second = stamp_qr(io.BytesIO(original), url, 0, 0.1, 0.1, 0.1)
        self.assertEqual(len(first), len(second))

    def test_rotated_page_is_stamped(self):
        out = stamp_qr(io.BytesIO(make_pdf(rotate=90)), f"{BASE_URL}/x", 0)
        self.assertEqual(PdfReader(io.BytesIO(out)).pages[0].rotation, 0)

    def test_broken_pdf_raises_stamp_error(self):
        with self.assertRaises(StampError):
            inspect_pdf(io.BytesIO(b"not a pdf"))

    def test_encrypted_pdf_raises_stamp_error(self):
        writer = PdfWriter(clone_from=PdfReader(io.BytesIO(make_pdf())))
        writer.encrypt(user_password="secret", owner_password="secret")
        buf = io.BytesIO()
        writer.write(buf)
        with self.assertRaises(StampError):
            stamp_qr(io.BytesIO(buf.getvalue()), "u")

    def test_missing_page_raises_stamp_error(self):
        with self.assertRaises(StampError):
            stamp_qr(io.BytesIO(make_pdf()), "u", page_index=3)


# ═══════════════════════════════════════════════════════════════
# URLs and model validation
# ═══════════════════════════════════════════════════════════════

@override_settings(CERTIFICATE_PUBLIC_BASE_URL=BASE_URL + "/")
class CertificateUrlTests(TestCase):
    def test_url_uses_configured_base_not_request_host(self):
        self.assertEqual(
            build_certificate_url("Karim Abbas", "FA0088"),
            f"{BASE_URL}/certificate/karim-abbas-fa0088",
        )

    def test_arabic_name_slug_falls_back(self):
        self.assertEqual(certificate_slug("محمد علي", "FA1"), "certificate-fa1")

    def test_model_slug_matches_qr_slug(self):
        cert = Certificate(student_name="محمد علي")
        self.assertEqual(cert.generate_url_slug("FA1"), "certificate-fa1")


@override_settings(STORAGES=LOCAL_STORAGES)
class CertificateValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.existing = Certificate.objects.create(
            student_name="Existing Student",
            certificate_code_1="FA0082",
            certificate_code_2="FA0083",
        )

    def test_code_used_in_another_column_of_another_row_is_rejected(self):
        cert = Certificate(student_name="Other", certificate_code_1="fa0083")
        with self.assertRaises(ValidationError) as ctx:
            cert.full_clean()
        self.assertIn("certificate_code_1", ctx.exception.message_dict)

    def test_hyphen_in_code_is_rejected(self):
        cert = Certificate(student_name="Other", certificate_code_1="FA-1")
        with self.assertRaises(ValidationError) as ctx:
            cert.full_clean()
        self.assertIn("certificate_code_1", ctx.exception.message_dict)

    def test_legacy_and_lowercase_codes_are_accepted_and_uppercased(self):
        cert = Certificate(student_name="Other", certificate_code_1="sr206")
        cert.full_clean()
        self.assertEqual(cert.certificate_code_1, "SR206")

    def test_editing_own_codes_is_not_a_duplicate(self):
        self.existing.full_clean()


# ═══════════════════════════════════════════════════════════════
# Admin workflow
# ═══════════════════════════════════════════════════════════════

@override_settings(STORAGES=LOCAL_STORAGES, CERTIFICATE_PUBLIC_BASE_URL=BASE_URL)
class CertificateAdminStampingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "a@example.com", "pw")

    def setUp(self):
        self.client.force_login(self.admin)

    def post_form(self, url, **overrides):
        data = {"student_name": "Karim Abbas"}
        for slot in (1, 2, 3):
            data[f"certificate_code_{slot}"] = ""
        data.update(overrides)
        return self.client.post(url, data)

    def add(self, **overrides):
        return self.post_form(
            reverse("admin:certificate_app_certificate_add"), **overrides
        )

    def change(self, cert, **overrides):
        return self.post_form(
            reverse("admin:certificate_app_certificate_change", args=[cert.pk]),
            **overrides,
        )

    def test_upload_original_stamps_qr(self):
        response = self.add(certificate_code_1="fa0100", upload_pdf_1=pdf_upload())
        self.assertEqual(response.status_code, 302)
        cert = Certificate.objects.get()
        source = cert.sources.get()
        self.assertTrue(cert.certificate_pdf_1.name.startswith("certificates/stamped/"))
        self.assertEqual(source.stamped_code, "FA0100")
        self.assertEqual(source.stamped_url, f"{BASE_URL}/certificate/karim-abbas-fa0100")
        defaults = AppSettings.load()
        self.assertEqual((source.x, source.y), (defaults.qr_default_x, defaults.qr_default_y))
        # Public verification works with the stamped PDF.
        page = self.client.get("/certificate/karim-abbas-fa0100")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "/media/certificates/stamped/karim-abbas_FA0100")

    def test_same_upload_filename_never_shares_storage(self):
        self.add(certificate_code_1="FA0120", upload_pdf_1=pdf_upload("design.pdf"))
        self.post_form(
            reverse("admin:certificate_app_certificate_add"),
            student_name="Second Student",
            certificate_code_1="FA0121",
            upload_pdf_1=pdf_upload("design.pdf"),
        )
        names = set(CertificateSource.objects.values_list("original_pdf", flat=True))
        self.assertEqual(len(names), 2)

    def test_code_without_any_pdf_is_rejected(self):
        response = self.add(certificate_code_1="FA0101")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Certificate.objects.exists())

    def test_has_qr_upload_is_stored_without_stamping(self):
        response = self.add(
            certificate_code_1="FA0102",
            upload_pdf_1=pdf_upload("final.pdf"),
            has_qr_1="on",
        )
        self.assertEqual(response.status_code, 302)
        cert = Certificate.objects.get()
        self.assertFalse(cert.sources.exists())
        self.assertIn("final", cert.certificate_pdf_1.name)
        self.assertFalse(cert.certificate_pdf_1.name.startswith("certificates/stamped/"))

    def test_change_page_shows_place_button_for_pdf_without_system_qr(self):
        self.add(certificate_code_1="FA0130", upload_pdf_1=pdf_upload(), has_qr_1="on")
        cert = Certificate.objects.get()
        page = self.client.get(
            reverse("admin:certificate_app_certificate_change", args=[cert.pk])
        )
        self.assertContains(
            page, reverse("admin:certificate_app_certificate_qr_place", args=[cert.pk, 1])
        )
        self.assertContains(page, "إضافة / تعديل مكان QR")

    def test_placing_qr_on_pdf_without_system_qr_creates_source(self):
        self.add(certificate_code_1="FA0131", upload_pdf_1=pdf_upload(), has_qr_1="on")
        cert = Certificate.objects.get()
        manual_name = cert.certificate_pdf_1.name
        url = reverse("admin:certificate_app_certificate_qr_place", args=[cert.pk, 1])
        page = self.client.get(url)
        self.assertContains(page, "لم يُضف رمز QR على هذا الملف بعد")
        response = self.client.post(url, {"page": 0, "x": 0.5, "y": 0.5, "size": 0.1})
        self.assertEqual(response.status_code, 302)
        cert.refresh_from_db()
        source = cert.sources.get()
        self.assertEqual(source.stamped_code, "FA0131")
        self.assertTrue(cert.certificate_pdf_1.name.startswith("certificates/stamped/"))
        # The manual file is kept in storage, never deleted.
        self.assertTrue(cert.certificate_pdf_1.storage.exists(manual_name))

    def test_broken_original_shows_form_error(self):
        broken = SimpleUploadedFile("x.pdf", b"broken", content_type="application/pdf")
        response = self.add(certificate_code_1="FA0103", upload_pdf_1=broken)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Certificate.objects.exists())

    def test_code_change_restamps_and_deletes_old_output(self):
        self.add(certificate_code_1="FA0104", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        old_name = cert.certificate_pdf_1.name
        response = self.change(cert, certificate_code_1="FA0105")
        self.assertEqual(response.status_code, 302)
        cert.refresh_from_db()
        self.assertEqual(cert.sources.get().stamped_code, "FA0105")
        self.assertNotEqual(cert.certificate_pdf_1.name, old_name)
        self.assertFalse(cert.certificate_pdf_1.storage.exists(old_name))

    def test_manual_final_upload_switches_slot_to_manual(self):
        self.add(certificate_code_1="FA0106", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        self.change(
            cert,
            certificate_code_1="FA0106",
            upload_pdf_1=pdf_upload("final.pdf"),
            has_qr_1="on",
        )
        cert.refresh_from_db()
        self.assertFalse(cert.sources.exists())
        self.assertFalse(cert.certificate_pdf_1.name.startswith("certificates/stamped/"))

    def test_clearing_code_removes_original_and_stamped_pdf(self):
        self.add(
            certificate_code_1="FA0107",
            certificate_code_2="FA0108",
            upload_pdf_1=pdf_upload(),
            upload_pdf_2=pdf_upload(),
        )
        cert = Certificate.objects.get()
        response = self.change(cert, certificate_code_1="FA0107")
        self.assertEqual(response.status_code, 302)
        cert.refresh_from_db()
        self.assertFalse(cert.certificate_pdf_2)
        self.assertEqual(list(cert.sources.values_list("slot", flat=True)), [1])

    def test_placement_post_restamps_and_can_set_default(self):
        self.add(certificate_code_1="FA0109", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        url = reverse("admin:certificate_app_certificate_qr_place", args=[cert.pk, 1])
        page = self.client.get(url)
        self.assertContains(page, 'id="qrp-data"')
        self.assertContains(
            page,
            reverse("admin:certificate_app_certificate_qr_source", args=[cert.pk, 1]),
        )
        response = self.client.post(
            url, {"page": 0, "x": 0.1, "y": 0.2, "size": 0.15, "make_default": "on"}
        )
        self.assertRedirects(
            response,
            reverse("admin:certificate_app_certificate_change", args=[cert.pk]),
        )
        source = cert.sources.get()
        self.assertEqual((source.x, source.y, source.size), (0.1, 0.2, 0.15))
        self.assertEqual(AppSettings.load().qr_default_size, 0.15)

    def test_placement_rejects_missing_page(self):
        self.add(certificate_code_1="FA0110", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        url = reverse("admin:certificate_app_certificate_qr_place", args=[cert.pk, 1])
        response = self.client.post(url, {"page": 5, "x": 0.1, "y": 0.1, "size": 0.1})
        self.assertEqual(response.status_code, 200)

    def test_source_view_streams_original(self):
        self.add(certificate_code_1="FA0111", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        response = self.client.get(
            reverse("admin:certificate_app_certificate_qr_source", args=[cert.pk, 1])
        )
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_png_download(self):
        self.add(certificate_code_1="FA0112", upload_pdf_1=pdf_upload())
        cert = Certificate.objects.get()
        response = self.client.get(
            reverse("admin:certificate_app_certificate_qr_slot", args=[cert.pk, 1])
        )
        self.assertEqual(response["Content-Type"], "image/png")


@override_settings(STORAGES=LOCAL_STORAGES)
class CertificateAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cert = Certificate.objects.create(
            student_name="Perm Student", certificate_code_1="FA0200"
        )
        CertificateSource.objects.create(
            certificate=cls.cert,
            slot=1,
            original_pdf=SimpleUploadedFile("o.pdf", make_pdf()),
            x=0.1,
            y=0.1,
            size=0.1,
        )
        cls.place_url = reverse(
            "admin:certificate_app_certificate_qr_place", args=[cls.cert.pk, 1]
        )

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.place_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_staff_without_change_permission_is_denied(self):
        staff = User.objects.create_user("staff", password="pw", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="view_certificate"))
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.place_url).status_code, 403)
        source_url = reverse(
            "admin:certificate_app_certificate_qr_source", args=[self.cert.pk, 1]
        )
        self.assertEqual(self.client.get(source_url).status_code, 403)
        png_url = reverse(
            "admin:certificate_app_certificate_qr_slot", args=[self.cert.pk, 1]
        )
        self.assertEqual(self.client.get(png_url).status_code, 200)


class QrDefaultPlacementTests(TestCase):
    def test_default_box_matches_hand_made_certificates(self):
        from .models import QR_DEFAULT_SIZE, QR_DEFAULT_X, QR_DEFAULT_Y

        settings_obj = AppSettings.load()
        self.assertEqual(
            (settings_obj.qr_default_x, settings_obj.qr_default_y, settings_obj.qr_default_size),
            (QR_DEFAULT_X, QR_DEFAULT_Y, QR_DEFAULT_SIZE),
        )
        # A4 landscape: 63.5pt square, 42pt from the left, 19pt from the bottom.
        left, bottom, side = compute_rect(
            (0, 0, 841.92, 595.32), QR_DEFAULT_X, QR_DEFAULT_Y, QR_DEFAULT_SIZE
        )
        self.assertAlmostEqual(left, 42.0, delta=0.5)
        self.assertAlmostEqual(bottom, 19.0, delta=0.5)
        self.assertAlmostEqual(side, 63.5, delta=0.5)


class QrCodeLabelTests(TestCase):
    def _label_positions(self, pdf_bytes, label):
        found = []

        def visitor(text, cm, tm, font, size):
            if label in (text or ""):
                found.append(cm[4] + tm[4] * cm[0])

        PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text(visitor_text=visitor)
        return found

    def test_code_printed_right_of_qr(self):
        out = stamp_qr(io.BytesIO(make_pdf()), "u", 0, 0.0499, 0.8614, 0.0754, "FA0080")
        xs = self._label_positions(out, "FA0080")
        self.assertEqual(len(xs), 1)
        # Hand-made certificates: code starts at 113.2pt (QR right edge + 7.7pt).
        self.assertAlmostEqual(xs[0], 113.2, delta=0.5)

    def test_code_moves_left_of_qr_near_right_edge(self):
        out = stamp_qr(io.BytesIO(make_pdf()), "u", 0, 0.92, 0.5, 0.0754, "FA0080")
        left, _, _ = compute_rect((0, 0, 841.89, 595.28), 0.92, 0.5, 0.0754)
        xs = self._label_positions(out, "FA0080")
        self.assertLess(xs[0], left)

    def test_no_label_without_code(self):
        out = stamp_qr(io.BytesIO(make_pdf()), "u", 0, 0.1, 0.1, 0.1)
        self.assertEqual(self._label_positions(out, "FA"), [])


@override_settings(STORAGES=LOCAL_STORAGES, CERTIFICATE_PUBLIC_BASE_URL=BASE_URL)
class QrCodeLabelSettingTests(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser("admin2", "b@example.com", "pw")
        )

    def _stamped_text(self):
        cert = Certificate.objects.get()
        with cert.certificate_pdf_1.open("rb") as handle:
            return PdfReader(handle).pages[0].extract_text()

    def _add(self):
        self.client.post(
            reverse("admin:certificate_app_certificate_add"),
            {
                "student_name": "Label Student",
                "certificate_code_1": "FA0300",
                "certificate_code_2": "",
                "certificate_code_3": "",
                "upload_pdf_1": pdf_upload(),
            },
        )

    def test_code_is_stamped_by_default(self):
        self._add()
        self.assertIn("FA0300", self._stamped_text())

    def test_code_can_be_turned_off(self):
        settings_obj = AppSettings.load()
        settings_obj.qr_show_code = False
        settings_obj.save()
        self._add()
        self.assertNotIn("FA0300", self._stamped_text())
