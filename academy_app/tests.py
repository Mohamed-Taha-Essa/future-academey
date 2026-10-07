import tempfile
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import translation

EN = {"HTTP_ACCEPT_LANGUAGE": "en"}

from .forms import ContactForm
from .models import (
    AcademySettings,
    ContactMessage,
    Course,
    CourseVideo,
    HeroSlide,
    Review,
    Service,
)
from .utils import build_enrollment_message, build_whatsapp_url, normalize_whatsapp_number

# Minimal valid GIF (1x1) accepted by Pillow for ImageField tests.
SMALL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)



TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": tempfile.mkdtemp(prefix="academy-tests-")},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

test_settings = override_settings(ALLOWED_HOSTS=["*"], STORAGES=TEST_STORAGES)

def make_image(name="test.gif"):
    return SimpleUploadedFile(name, SMALL_GIF, content_type="image/gif")


def make_video(name="clip.mp4"):
    return SimpleUploadedFile(name, b"\x00" * 128, content_type="video/mp4")


def make_service(**kwargs):
    defaults = {
        "name_ar": "خدمة السلامة",
        "name_en": "Safety Service",
        "slug": "safety-service",
        "image": make_image(),
        "short_description_en": "Short service text",
        "content_en": "Full service content",
    }
    defaults.update(kwargs)
    return Service.objects.create(**defaults)


def make_course(**kwargs):
    defaults = {
        "name_ar": "دورة السلامة",
        "name_en": "Safety Course",
        "slug": "safety-course",
        "image": make_image(),
        "short_description_en": "Short course text",
        "description_en": "Full course description",
        "duration_ar": "٣ أيام",
        "duration_en": "3 days",
        "price": Decimal("1500.00"),
    }
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


def make_hero(**kwargs):
    defaults = {
        "image": make_image(),
        "title_en": "Welcome",
        "title_ar": "أهلاً",
        "description_en": "Hero description",
    }
    defaults.update(kwargs)
    return HeroSlide.objects.create(**defaults)


def make_review(**kwargs):
    defaults = {
        "image": make_image(),
        "student_name_en": "Ahmed",
    }
    defaults.update(kwargs)
    return Review.objects.create(**defaults)


# ═══════════════════════════════════════════════════════════════
# Model tests
# ═══════════════════════════════════════════════════════════════

class AcademySettingsModelTests(TestCase):
    def test_singleton_forces_pk_one(self):
        obj = AcademySettings(whatsapp_number="201001234567")
        obj.save()
        self.assertEqual(obj.pk, 1)
        obj2 = AcademySettings(whatsapp_number="201009999999")
        obj2.save()
        self.assertEqual(obj2.pk, 1)
        self.assertEqual(AcademySettings.objects.count(), 1)

    def test_cannot_be_deleted(self):
        obj = AcademySettings.objects.create(whatsapp_number="")
        obj.delete()
        self.assertEqual(AcademySettings.objects.count(), 1)

    def test_accepts_empty_whatsapp(self):
        obj = AcademySettings.objects.create(whatsapp_number="")
        obj.full_clean()
        self.assertEqual(obj.whatsapp_number, "")

    def test_invalid_whatsapp_rejected(self):
        obj = AcademySettings(whatsapp_number="12")
        with self.assertRaises(ValidationError):
            obj.full_clean()

    def test_whatsapp_normalized_on_clean(self):
        obj = AcademySettings(whatsapp_number="+20 100 123 4567")
        obj.full_clean()
        self.assertEqual(obj.whatsapp_number, "201001234567")


class HeroSlideModelTests(TestCase):
    def test_ordering_by_display_order_then_id(self):
        b = make_hero(display_order=2)
        a = make_hero(display_order=1)
        slides = list(HeroSlide.objects.all())
        self.assertEqual(slides, [a, b])


class ServiceModelTests(TestCase):
    def test_slug_unique(self):
        make_service()
        with self.assertRaises(Exception):
            make_service(name_en="Other")

    def test_str_prefers_english_name(self):
        service = make_service()
        self.assertEqual(str(service), "Safety Service")


class CourseModelTests(TestCase):
    def test_slug_unique(self):
        make_course()
        with self.assertRaises(Exception):
            make_course(name_en="Other")

    def test_negative_price_rejected(self):
        course = make_course(price=Decimal("10.00"))
        course.price = Decimal("-5.00")
        with self.assertRaises(ValidationError):
            course.full_clean()


class CourseVideoModelTests(TestCase):
    def test_course_can_have_multiple_videos(self):
        course = make_course()
        make = lambda i: CourseVideo.objects.create(
            course=course, video_file=make_video(f"v{i}.mp4"), display_order=i
        )
        v1, v2, v3 = make(0), make(1), make(2)
        self.assertEqual(course.videos.count(), 3)

    def test_videos_ordered_by_display_order(self):
        course = make_course()
        v2 = CourseVideo.objects.create(
            course=course, video_file=make_video("b.mp4"), display_order=2
        )
        v1 = CourseVideo.objects.create(
            course=course, video_file=make_video("a.mp4"), display_order=1
        )
        self.assertEqual(list(course.videos.all()), [v1, v2])

    def test_cascade_delete_with_course(self):
        course = make_course()
        CourseVideo.objects.create(course=course, video_file=make_video())
        course.delete()
        self.assertEqual(CourseVideo.objects.count(), 0)

    def test_unsupported_extension_rejected(self):
        course = make_course()
        video = CourseVideo(
            course=course,
            video_file=SimpleUploadedFile("clip.avi", b"\x00" * 64),
        )
        with self.assertRaises(ValidationError):
            video.full_clean()

    def test_oversized_video_rejected(self):
        course = make_course()
        big = SimpleUploadedFile("clip.mp4", b"\x00" * (15 * 1024 * 1024 + 1))
        video = CourseVideo(course=course, video_file=big)
        with self.assertRaises(ValidationError):
            video.full_clean()


class ContactMessageModelTests(TestCase):
    def test_defaults_to_unread(self):
        msg = ContactMessage.objects.create(
            name="Ali", email="a@b.com", phone="123", message="Hello"
        )
        self.assertFalse(msg.is_read)

    def test_newest_first_ordering(self):
        first = ContactMessage.objects.create(
            name="A", email="a@b.com", phone="1", message="x"
        )
        second = ContactMessage.objects.create(
            name="B", email="b@b.com", phone="2", message="y"
        )
        messages = list(ContactMessage.objects.all())
        self.assertEqual(messages, [second, first])


# ═══════════════════════════════════════════════════════════════
# Utils / WhatsApp tests
# ═══════════════════════════════════════════════════════════════

class WhatsAppUtilsTests(TestCase):
    def test_normalize_removes_formatting(self):
        self.assertEqual(
            normalize_whatsapp_number("+20 (100) 123-4567"), "201001234567"
        )

    def test_normalize_rejects_empty_and_short(self):
        self.assertEqual(normalize_whatsapp_number(""), "")
        self.assertEqual(normalize_whatsapp_number(None), "")
        self.assertEqual(normalize_whatsapp_number("123"), "")

    def test_url_contains_number(self):
        url = build_whatsapp_url("+20 100 123 4567")
        self.assertEqual(url, "https://wa.me/201001234567")

    def test_url_encodes_message(self):
        url = build_whatsapp_url("201001234567", "I would like to enroll in X")
        self.assertIn("text=I%20would%20like%20to%20enroll%20in%20X", url)

    def test_url_encodes_arabic_message(self):
        url = build_whatsapp_url("201001234567", "أود التسجيل في دورة السلامة")
        self.assertTrue(url.startswith("https://wa.me/201001234567?text="))
        self.assertNotIn("أود", url)  # must be percent-encoded

    def test_url_empty_when_number_invalid(self):
        self.assertEqual(build_whatsapp_url("12"), "")
        self.assertEqual(build_whatsapp_url(""), "")

    def test_enrollment_message_format(self):
        msg = build_enrollment_message("Safety 101", "I would like to enroll in {course}")
        self.assertEqual(msg, "I would like to enroll in Safety 101")


# ═══════════════════════════════════════════════════════════════
# Form tests
# ═══════════════════════════════════════════════════════════════

class ContactFormTests(TestCase):
    def test_required_fields(self):
        form = ContactForm(data={})
        self.assertFalse(form.is_valid())
        for field in ("name", "email", "phone", "message"):
            self.assertIn(field, form.errors)

    def test_invalid_email_rejected(self):
        form = ContactForm(
            data={"name": "Ali", "email": "not-an-email", "phone": "123", "message": "Hi"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_valid_form_strips_whitespace(self):
        form = ContactForm(
            data={
                "name": "  Ali  ",
                "email": " a@b.com ",
                "phone": " 123 ",
                "message": "  Hello  ",
            }
        )
        self.assertTrue(form.is_valid())
        obj = form.save()
        self.assertEqual(obj.name, "Ali")
        self.assertEqual(obj.message, "Hello")

    def test_max_lengths(self):
        form = ContactForm(
            data={
                "name": "x" * 151,
                "email": "a@b.com",
                "phone": "1" * 33,
                "message": "hi",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("phone", form.errors)


# ═══════════════════════════════════════════════════════════════
# Homepage tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class HomepageTests(TestCase):
    def test_url_reverses_and_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_active_hero_slides_appear(self):
        make_hero(title_en="Visible Slide")
        response = self.client.get(reverse("home"), **EN)
        self.assertContains(response, "Visible Slide")

    def test_inactive_hero_slides_hidden(self):
        make_hero(title_en="Hidden Slide", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Hidden Slide")

    def test_services_appear_in_order(self):
        s2 = make_service(name_en="Second", slug="second", display_order=2)
        s1 = make_service(name_en="First", slug="first", display_order=1)
        response = self.client.get(reverse("home"), **EN)
        content = response.content.decode()
        self.assertLess(content.index("First"), content.index("Second"))

    def test_inactive_service_hidden(self):
        make_service(name_en="Ghost Service", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Ghost Service")

    def test_courses_appear_with_price_and_duration(self):
        make_course(price=Decimal("2500.00"), duration_en="5 days")
        response = self.client.get(reverse("home"), **EN)
        self.assertContains(response, "2500.00")
        self.assertContains(response, "5 days")

    def test_inactive_course_hidden(self):
        make_course(name_en="Ghost Course", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Ghost Course")

    def test_active_reviews_appear(self):
        make_review(student_name_en="Happy Student")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Happy Student")

    def test_inactive_review_hidden(self):
        make_review(student_name_en="Hidden Student", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Hidden Student")

    def test_empty_database_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hero-fallback")

    def test_contact_form_present(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="phone"')
        self.assertContains(response, 'name="message"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_homepage_query_count_constant(self):
        make_hero()
        make_service()
        make_course()
        make_review()
        self.client.get(reverse("home"))  # warm-up: creates AppSettings row
        with CaptureQueriesContext(connection) as baseline:
            self.client.get(reverse("home"))
        # Add more records — query count must not increase (no N+1)
        for i in range(3):
            make_service(name_en=f"Svc{i}", slug=f"svc-{i}")
            make_course(name_en=f"Crs{i}", slug=f"crs-{i}")
            make_review()
            make_hero()
        with CaptureQueriesContext(connection) as grown:
            self.client.get(reverse("home"))
        self.assertEqual(len(grown), len(baseline))


# ═══════════════════════════════════════════════════════════════
# Contact submission tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class ContactSubmissionTests(TestCase):
    def _valid_data(self):
        return {
            "name": "Ali Hassan",
            "email": "ali@example.com",
            "phone": "201001234567",
            "message": "I want more information.",
        }

    def test_valid_post_creates_one_message(self):
        response = self.client.post(reverse("home"), self._valid_data())
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertRedirects(
            response, reverse("home") + "#contact", fetch_redirect_response=False
        )

    def test_new_message_is_unread(self):
        self.client.post(reverse("home"), self._valid_data())
        self.assertFalse(ContactMessage.objects.first().is_read)

    def test_invalid_post_rerenders_homepage_with_errors(self):
        data = self._valid_data()
        data["email"] = "broken"
        response = self.client.post(reverse("home"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "invalid-feedback")

    def test_invalid_post_keeps_homepage_sections(self):
        make_hero(title_en="Keep Me")
        make_service()
        data = self._valid_data()
        data["name"] = ""
        response = self.client.post(reverse("home"), data, **EN)
        self.assertContains(response, "Keep Me")
        self.assertContains(response, "Safety Service")

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("home"), self._valid_data())
        self.assertEqual(response.status_code, 403)

    def test_submitted_content_is_escaped(self):
        data = self._valid_data()
        data["name"] = "<script>alert(1)</script>"
        data["message"] = "hello"
        self.client.post(reverse("home"), data)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "<script>alert(1)</script>")


# ═══════════════════════════════════════════════════════════════
# Service detail tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class ServiceDetailTests(TestCase):
    def test_url_reverses(self):
        self.assertEqual(
            reverse("service_detail", kwargs={"slug": "safety-service"}),
            "/services/safety-service/",
        )

    def test_active_service_returns_200(self):
        make_service()
        response = self.client.get(
            reverse("service_detail", kwargs={"slug": "safety-service"}), **EN
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Safety Service")

    def test_missing_service_404(self):
        response = self.client.get(reverse("service_detail", kwargs={"slug": "nope"}))
        self.assertEqual(response.status_code, 404)

    def test_inactive_service_404(self):
        make_service(is_active=False)
        response = self.client.get(
            reverse("service_detail", kwargs={"slug": "safety-service"})
        )
        self.assertEqual(response.status_code, 404)

    def test_external_url_only_when_configured(self):
        service = make_service(external_url="https://example.com")
        response = self.client.get(
            reverse("service_detail", kwargs={"slug": "safety-service"})
        )
        self.assertContains(response, "https://example.com")

    def test_external_url_hidden_when_empty(self):
        make_service()
        response = self.client.get(
            reverse("service_detail", kwargs={"slug": "safety-service"})
        )
        self.assertNotContains(response, "Visit External Link")

    def test_english_content_selected(self):
        make_service(name_en="English Name", name_ar="اسم عربي")
        response = self.client.get(
            reverse("service_detail", kwargs={"slug": "safety-service"}),
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertContains(response, "English Name")

    def test_arabic_content_selected(self):
        make_service(name_en="English Name", name_ar="اسم عربي")
        with translation.override("ar"):
            response = self.client.get(
                reverse("service_detail", kwargs={"slug": "safety-service"})
            )
        self.assertContains(response, "اسم عربي")


# ═══════════════════════════════════════════════════════════════
# Course detail tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class CourseDetailTests(TestCase):
    def test_url_reverses(self):
        self.assertEqual(
            reverse("course_detail", kwargs={"slug": "safety-course"}),
            "/courses/safety-course/",
        )

    def test_active_course_returns_200_with_details(self):
        make_course()
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"}), **EN
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Safety Course")
        self.assertContains(response, "1500.00")
        self.assertContains(response, "3 days")
        self.assertContains(response, "Full course description")

    def test_missing_course_404(self):
        response = self.client.get(reverse("course_detail", kwargs={"slug": "nope"}))
        self.assertEqual(response.status_code, 404)

    def test_inactive_course_404(self):
        make_course(is_active=False)
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"})
        )
        self.assertEqual(response.status_code, 404)

    def test_active_videos_render_in_order(self):
        course = make_course()
        CourseVideo.objects.create(
            course=course, video_file=make_video("b.mp4"),
            title_en="Second Video", display_order=2,
        )
        CourseVideo.objects.create(
            course=course, video_file=make_video("a.mp4"),
            title_en="First Video", display_order=1,
        )
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"})
        )
        content = response.content.decode()
        self.assertLess(content.index("First Video"), content.index("Second Video"))
        self.assertContains(response, "<video")
        self.assertContains(response, 'preload="metadata"')
        self.assertContains(response, "controls")

    def test_inactive_videos_hidden(self):
        course = make_course()
        CourseVideo.objects.create(
            course=course, video_file=make_video(),
            title_en="Hidden Video", is_active=False,
        )
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"})
        )
        self.assertNotContains(response, "Hidden Video")

    def test_no_videos_shows_empty_state(self):
        make_course()
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"}), **EN
        )
        self.assertContains(response, "Course videos will be available soon.")
        self.assertNotContains(response, "<video")

    def test_video_uses_configured_storage_url(self):
        course = make_course()
        CourseVideo.objects.create(course=course, video_file=make_video("x.mp4"))
        video = CourseVideo.objects.first()
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"})
        )
        self.assertContains(response, video.video_file.url)

    def test_whatsapp_enrollment_url_rendered(self):
        AcademySettings.objects.create(whatsapp_number="+20 100 123 4567")
        make_course()
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"}),
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertContains(response, "https://wa.me/201001234567")
        self.assertContains(response, "text=I%20would%20like%20to%20enroll")

    def test_enrollment_button_hidden_without_number(self):
        AcademySettings.objects.create(whatsapp_number="")
        make_course()
        response = self.client.get(
            reverse("course_detail", kwargs={"slug": "safety-course"}), **EN
        )
        self.assertNotContains(response, "wa.me")
        self.assertContains(response, "Contact Us to Enroll")

    def test_course_detail_query_count_constant(self):
        course = make_course()
        for i in range(2):
            CourseVideo.objects.create(
                course=course, video_file=make_video(f"a{i}.mp4")
            )
        self.client.get(reverse("course_detail", kwargs={"slug": "safety-course"}))  # warm-up
        with CaptureQueriesContext(connection) as baseline:
            self.client.get(reverse("course_detail", kwargs={"slug": "safety-course"}))
        for i in range(5):
            CourseVideo.objects.create(
                course=course, video_file=make_video(f"b{i}.mp4")
            )
        with CaptureQueriesContext(connection) as grown:
            self.client.get(reverse("course_detail", kwargs={"slug": "safety-course"}))
        self.assertEqual(len(grown), len(baseline))


# ═══════════════════════════════════════════════════════════════
# Context processor tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class ContextProcessorTests(TestCase):
    def test_whatsapp_url_exposed_globally(self):
        AcademySettings.objects.create(whatsapp_number="201001234567")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "https://wa.me/201001234567")
        self.assertContains(response, "whatsapp-float")

    def test_whatsapp_button_hidden_without_number(self):
        AcademySettings.objects.create(whatsapp_number="")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "whatsapp-float")

    def test_invalid_number_hides_button(self):
        AcademySettings.objects.create(whatsapp_number="12")
        # Bypass model clean (simulating legacy bad data)
        AcademySettings.objects.filter(pk=1).update(whatsapp_number="12")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "whatsapp-float")


# ═══════════════════════════════════════════════════════════════
# Reviews component tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class ReviewComponentTests(TestCase):
    def test_single_review_hides_controls(self):
        make_review()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "reviewsCarousel")
        self.assertNotContains(response, "carousel-control-prev")

    def test_multiple_reviews_show_controls(self):
        make_review()
        make_review(student_name_en="Second")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "carousel-control-prev")
        self.assertContains(response, "carousel-indicators")


# ═══════════════════════════════════════════════════════════════
# Admin tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            "admin", "admin@example.com", "pass1234"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_all_models_registered(self):
        for model in (
            AcademySettings, HeroSlide, Service, Course,
            CourseVideo, Review, ContactMessage,
        ):
            self.assertIn(model, admin.site._registry)

    def test_changelists_render(self):
        for model_name in (
            "academysettings", "heroslide", "service", "course",
            "coursevideo", "review", "contactmessage",
        ):
            url = reverse(f"admin:academy_app_{model_name}_changelist")
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_academysettings_no_add_when_exists(self):
        AcademySettings.objects.create(whatsapp_number="")
        response = self.client.get(
            reverse("admin:academy_app_academysettings_add")
        )
        self.assertEqual(response.status_code, 403)

    def test_academysettings_no_delete(self):
        obj = AcademySettings.objects.create(whatsapp_number="")
        response = self.client.get(
            reverse("admin:academy_app_academysettings_delete", args=(obj.pk,))
        )
        self.assertEqual(response.status_code, 403)

    def test_mark_read_unread_actions(self):
        msg = ContactMessage.objects.create(
            name="Ali", email="a@b.com", phone="1", message="hi"
        )
        model_admin = admin.site._registry[ContactMessage]
        model_admin.mark_as_read(None, ContactMessage.objects.all())
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
        model_admin.mark_as_unread(None, ContactMessage.objects.all())
        msg.refresh_from_db()
        self.assertFalse(msg.is_read)

    def test_preview_safe_when_image_missing(self):
        from academy_app.admin import image_preview

        service = Service(name_en="No Img", name_ar="x", slug="no-img")
        self.assertEqual(image_preview(service), "")

    def test_contact_message_search(self):
        ContactMessage.objects.create(
            name="FindMePlease", email="a@b.com", phone="1", message="hi"
        )
        response = self.client.get(
            reverse("admin:academy_app_contactmessage_changelist"),
            {"q": "FindMePlease"},
        )
        self.assertContains(response, "FindMePlease")


# ═══════════════════════════════════════════════════════════════
# Internationalization tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class I18nTests(TestCase):
    def test_arabic_is_default_and_rtl(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "bootstrap.rtl.min.css")

    def test_english_switch_renders_ltr(self):
        self.client.post(
            reverse("set_language"), {"language": "en", "next": "/"}
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'dir="ltr"')
        self.assertContains(response, "bootstrap.min.css")

    def test_language_cookie_set(self):
        response = self.client.post(
            reverse("set_language"), {"language": "en", "next": "/"}
        )
        self.assertIn("django_language", response.cookies)

    def test_next_url_preserved(self):
        response = self.client.post(
            reverse("set_language"), {"language": "en", "next": "/courses/x/"}
        )
        self.assertEqual(response.url, "/courses/x/")

    def test_new_ui_labels_translated(self):
        with translation.override("ar"):
            response = self.client.get(reverse("home"))
        self.assertContains(response, "تواصل معنا")

    def test_invalid_language_falls_back(self):
        response = self.client.post(
            reverse("set_language"), {"language": "xx", "next": "/"}
        )
        self.assertEqual(response.status_code, 302)


# ═══════════════════════════════════════════════════════════════
# Existing certificate functionality (regression)
# ═══════════════════════════════════════════════════════════════

@test_settings
class CertificateRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from certificate_app.models import Certificate

        cls.certificate = Certificate.objects.create(
            student_name="Test Student",
            certificate_code_1="FA9999",
            certificate_pdf_1=SimpleUploadedFile(
                "cert.pdf", b"%PDF-1.4 test", content_type="application/pdf"
            ),
        )

    def test_certificate_url_without_slash(self):
        response = self.client.get("/certificate/test-student-fa9999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Student")

    def test_certificate_url_with_slash(self):
        response = self.client.get("/certificate/test-student-fa9999/")
        self.assertEqual(response.status_code, 200)

    def test_certificate_pdf_link_rendered(self):
        response = self.client.get("/certificate/test-student-fa9999/")
        self.assertContains(response, ".pdf")

    def test_certificate_not_found(self):
        response = self.client.get("/certificate/unknown-zz0000/")
        self.assertEqual(response.status_code, 404)

    def test_404_template_renders(self):
        response = self.client.get("/certificate/unknown-zz0000/", **EN)
        self.assertContains(
            response, "Certificate Not Found", status_code=404
        )

    def test_certificate_page_has_shared_layout(self):
        response = self.client.get("/certificate/test-student-fa9999/")
        self.assertContains(response, 'id="main-navbar"')
        self.assertContains(response, "footer-custom")


# ═══════════════════════════════════════════════════════════════
# Shared layout tests
# ═══════════════════════════════════════════════════════════════

@test_settings
class SharedLayoutTests(TestCase):
    def test_navbar_has_expected_id_and_links(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="main-navbar"')
        for anchor in ("#services", "#courses", "#reviews", "#contact"):
            self.assertContains(response, anchor)

    def test_static_assets_loaded(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "css/style.css")
        self.assertContains(response, "js/main.js")

    def test_whatsapp_button_on_detail_and_certificate_pages(self):
        AcademySettings.objects.create(whatsapp_number="201001234567")
        make_service()
        make_course()
        for url in (
            reverse("home"),
            reverse("service_detail", kwargs={"slug": "safety-service"}),
            reverse("course_detail", kwargs={"slug": "safety-course"}),
        ):
            response = self.client.get(url)
            self.assertContains(response, "whatsapp-float")

    def test_seo_meta_on_detail_pages(self):
        make_service(short_description_en="Unique service description")
        make_course(short_description_en="Unique course description")
        r1 = self.client.get(reverse("service_detail", kwargs={"slug": "safety-service"}))
        self.assertContains(r1, "Unique service description")
        self.assertContains(r1, 'rel="canonical"')
        self.assertContains(r1, "og:image")
        r2 = self.client.get(reverse("course_detail", kwargs={"slug": "safety-course"}))
        self.assertContains(r2, 'rel="canonical"')


# ═══════════════════════════════════════════════════════════════
# load_demo_content management command
# ═══════════════════════════════════════════════════════════════

@test_settings
class LoadDemoContentTests(TestCase):
    def run_command(self, *args):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("load_demo_content", *args, stdout=out)
        return out.getvalue()

    def test_fills_empty_sections_as_inactive_with_files(self):
        from django.core.files.storage import default_storage

        self.run_command()
        self.assertEqual(HeroSlide.objects.count(), 2)
        self.assertEqual(Service.objects.count(), 3)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseVideo.objects.count(), 2)
        self.assertEqual(Review.objects.count(), 3)
        self.assertFalse(Course.objects.filter(is_active=True).exists())
        video = CourseVideo.objects.first()
        self.assertEqual(video.course.slug, "osha-general-industry")
        self.assertTrue(default_storage.exists(video.video_file.name))
        self.assertTrue(default_storage.exists(Service.objects.first().image.name))

    def test_running_twice_does_not_duplicate(self):
        self.run_command()
        out = self.run_command()
        self.assertEqual(Course.objects.count(), 3)
        self.assertIn("skipped", out)

    def test_existing_content_is_never_touched(self):
        real = Service.objects.create(
            name_ar="خدمة", name_en="Real", slug="real", image=make_image()
        )
        self.run_command()
        self.assertEqual(list(Service.objects.all()), [real])
        self.assertEqual(Course.objects.count(), 3)

    def test_active_flag_publishes(self):
        self.run_command("--active")
        self.assertEqual(Review.objects.filter(is_active=True).count(), 3)

    def test_dry_run_writes_nothing(self):
        out = self.run_command("--dry-run")
        self.assertEqual(HeroSlide.objects.count(), 0)
        self.assertIn("coursevideo: 2 created", out)

    def test_certificates_are_not_created(self):
        from certificate_app.models import Certificate

        self.run_command()
        self.assertFalse(Certificate.objects.exists())
