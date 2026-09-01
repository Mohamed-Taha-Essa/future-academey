from django.http import HttpResponseNotFound
from django.shortcuts import render, redirect
from django.utils.translation import activate, gettext as _
from django.conf import settings

from .models import Certificate


def home_view(request):
    """Render the Coming Soon homepage."""
    return render(request, "home.html")


def certificate_view(request, certificate_id):
    """
    Certificate verification view.

    URL format: /certificate/<student-name>-<code>/
    The code is the last segment after the final hyphen.

    Steps:
    1. Extract the certificate code (last segment after '-').
    2. Look up the certificate in the database.
    3. Determine which PDF belongs to the matched code.
    4. Render the certificate page or 404.
    """
    # Step 1: Extract certificate code from the URL slug
    # The format is: student-name-parts-CODE
    # We take the last segment after the final hyphen
    parts = certificate_id.rsplit("-", 1)
    if len(parts) < 2:
        # No hyphen found — treat the entire string as the code
        code = certificate_id
    else:
        code = parts[-1]

    # Step 2 & 3: Look up certificate and determine the correct PDF
    result = Certificate.get_certificate_by_code(code)

    if result is None:
        # Certificate not found — return HTTP 404
        return HttpResponseNotFound(
            render(request, "certificate_app/certificate_not_found.html", {
                "certificate_id": certificate_id,
            }).content,
            content_type="text/html",
        )

    # Step 4: Render the certificate verification page
    context = {
        "student_name": result["certificate"].student_name,
        "certificate_code": result["code"],
        "pdf_url": result["pdf"].url if result["pdf"] else None,
        "certificate": result["certificate"],
    }

    return render(request, "certificate_app/certificate.html", context)


def set_language_view(request):
    """
    Handle language switching.
    Expects POST with 'language' and 'next' fields.
    Sets the language in the session and redirects back.
    """
    if request.method == "POST":
        language = request.POST.get("language", "ar")

        # Validate the language code against LANGUAGES setting
        valid_languages = [code for code, name in settings.LANGUAGES]
        if language not in valid_languages:
            language = "ar"

        # Activate the language and store in session
        activate(language)
        request.session[settings.LANGUAGE_COOKIE_NAME] = language

        # Redirect to the page the user was on
        next_url = request.POST.get("next", "/")
        response = redirect(next_url)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language,
            max_age=365 * 24 * 60 * 60,  # 1 year
            samesite="Lax",
            httponly=False,
        )
        return response

    return redirect("/")
