from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import ContactForm
from .models import (
    AcademySettings,
    Course,
    CourseVideo,
    HeroSlide,
    Review,
    Service,
)
from .utils import build_whatsapp_url


def _active_ordered(model):
    """Public homepage queryset: active records in configured order."""
    return model.objects.filter(is_active=True).order_by("display_order", "pk")


def _home_context(form=None):
    """Shared homepage context used for GET and invalid-POST rendering."""
    return {
        "hero_slides": _active_ordered(HeroSlide),
        "services": _active_ordered(Service),
        "courses": _active_ordered(Course),
        "reviews": _active_ordered(Review),
        "contact_form": form if form is not None else ContactForm(),
    }


def home_view(request):
    """Render the public academy homepage; handle the contact-form POST."""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            message_obj = form.save(commit=False)
            message_obj.is_read = False
            message_obj.save()
            messages.success(
                request,
                _("Thank you! Your message has been received. We will contact you soon."),
            )
            return redirect("{}#contact".format(reverse("home")))
        return render(request, "home.html", _home_context(form))
    return render(request, "home.html", _home_context())


def service_detail_view(request, slug):
    """Render an active service detail page; 404 for missing/inactive."""
    service = get_object_or_404(
        Service.objects.filter(is_active=True),
        slug=slug,
    )
    return render(
        request,
        "academy_app/service_detail.html",
        {"service": service},
    )


def course_detail_view(request, slug):
    """Render an active course detail page with videos and WhatsApp CTA."""
    active_videos = CourseVideo.objects.filter(is_active=True).order_by(
        "display_order", "pk"
    )
    course = get_object_or_404(
        Course.objects.filter(is_active=True).prefetch_related(
            Prefetch("videos", queryset=active_videos)
        ),
        slug=slug,
    )

    videos = list(course.videos.all())

    whatsapp_enrollment_url = ""
    academy_settings = AcademySettings.load()
    if academy_settings and academy_settings.whatsapp_number:
        message = _("I would like to enroll in {course}").format(
            course=course.localized_name()
        )
        whatsapp_enrollment_url = build_whatsapp_url(
            academy_settings.whatsapp_number,
            message,
        )

    return render(
        request,
        "academy_app/course_detail.html",
        {
            "course": course,
            "videos": videos,
            "whatsapp_enrollment_url": whatsapp_enrollment_url,
        },
    )
