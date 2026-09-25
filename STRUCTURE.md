# Project Analysis

This document is an implementation plan for the existing repository. It describes what already exists, what should be reused, and what the next implementation agent should create or modify.

This document does not implement the requested public website. No Python code, models, templates, CSS, JavaScript, settings, or migrations should be changed as part of the planning phase.

The repository is a small Django 5.2 project named `future-academey`. It currently contains one project package and one existing Django application. The planned public academy website should be introduced as a separate `academy_app` domain app, while `certificate_app` remains dedicated to certificate verification and is not modified by the homepage work.

The local SQLite database currently contains one `AppSettings` record and two `Certificate` records. The existing settings record has no uploaded logo and no configured text values. Existing local media contains certificate PDFs. The existing static fallback logo is `static/images/logo.jpg`.

# Current Architecture

## Repository Structure

Important existing paths:

```text
project/
  settings.py
  urls.py
  asgi.py
  wsgi.py

certificate_app/
  models.py
  views.py
  urls.py
  admin.py
  context_processors.py
  apps.py
  tests.py
  migrations/
  templates/certificate_app/

academy_app/                         # planned new public website app
  models.py
  views.py
  urls.py
  admin.py
  forms.py
  context_processors.py
  utils.py
  apps.py
  tests.py
  migrations/
  templates/academy_app/

templates/
  base.html
  home.html
  404.html

static/
  css/style.css
  js/main.js
  images/logo.jpg
  unfold/css/rtl.css

locale/
  ar/LC_MESSAGES/django.po
  en/LC_MESSAGES/django.po

media/
  certificates/
```

## Django Configuration

`project/settings.py` currently provides:

- Django 5.2 configuration.
- `unfold` before `django.contrib.admin`.
- `certificate_app` as the existing certificate application.
- `academy_app` as the planned public academy website application.
- `WhiteNoiseMiddleware` for static files.
- `LocaleMiddleware` between session and common middleware.
- A root `templates/` directory and app template discovery.
- `certificate_app.context_processors.site_settings_processor` in every public template context.
- A planned `academy_app.context_processors.academy_settings_processor` for academy-specific settings such as WhatsApp.
- SQLite by default, with `DATABASE_URL` support through `dj-database-url`.
- Arabic as the default language.
- Arabic and English as supported languages.
- Static files under `static/` and `staticfiles/` as the collection directory.
- Local filesystem media when R2 is not configured.
- Cloudflare R2/S3-compatible default storage when `R2_ACCESS_KEY_ID` exists.
- A 15 MB upload limit.
- Production HTTPS and cookie security settings when `DEBUG` is false.

## Authentication and Middleware

The public website has no authentication requirement. Django authentication is used for admin access only.

Existing middleware includes security, WhiteNoise, sessions, locale switching, common middleware, CSRF, authentication, messages, and clickjacking protection. The contact form must use the existing CSRF and messages middleware.

## Existing Models

`certificate_app.models.Certificate` stores up to three certificate code/PDF pairs for one student. It includes PDF extension validation, uniqueness constraints, timestamps, certificate lookup logic, and descending creation-date ordering.

`certificate_app.models.AppSettings` is a singleton. Its `save()` forces primary key `1`, its `delete()` does nothing, and its `load()` uses `get_or_create(pk=1)`. It currently stores the logo, Arabic/English academy names, brand colors, and Arabic/English footer text.

There are no existing service, course, review, hero, or contact-message models.

## Existing Views and URLs

`certificate_app.views.home_view` currently renders `templates/home.html` and performs no content queries. It is legacy homepage behavior and must remain unchanged because `certificate_app` is being kept stable. The root URL should be reassigned to the new `academy_app.views.home_view` when the public website is implemented.

`certificate_app.views.certificate_view` extracts the certificate code from the final URL segment, uses `Certificate.get_certificate_by_code()`, and renders either the certificate page or the not-found page.

`certificate_app.views.set_language_view` accepts a POST request, validates the language against `settings.LANGUAGES`, updates the session and language cookie, and redirects to the supplied `next` URL.

`project/urls.py` currently defines:

| URL | Name | Existing behavior |
|---|---|---|
| `/` | `home` | Coming-soon homepage |
| `/certificate/<certificate_id>` | `certificate_app:certificate` | Certificate verification |
| `/certificate/<certificate_id>/` | `certificate_app:certificate` | Certificate verification with trailing slash |
| `/set-language/` | `set_language` | Custom language switching |
| `/i18n/` | Django i18n URLs | Used by Django and Unfold |
| `/admin/` | Django admin | Unfold admin interface |

The certificate URLs must remain compatible with existing QR codes and links.

The implementation should add `academy_app.urls` for the root homepage, service pages, and course pages. It must not add public website routes to `certificate_app.urls`.

## Existing Templates

`templates/base.html` provides:

- HTML language and direction attributes.
- Meta description and title blocks.
- Google Fonts using Cairo and Inter.
- Bootstrap 5.3.3 RTL or LTR CSS from CDN.
- Bootstrap Icons from CDN.
- A logo and academy name.
- The existing language switcher.
- A simple sticky Bootstrap navbar.
- A footer with logo, academy name, and footer text.
- Bootstrap JavaScript bundle.

`templates/home.html` is currently a coming-soon page. The certificate templates extend the base template and should continue to work after the base template is expanded.

There is no existing partial or component convention. The implementation should introduce one consistently rather than duplicate all markup in `home.html`.

## Existing Static Assets

`static/css/style.css` contains the current brand variables, navbar styles, coming-soon styles, certificate styles, footer styles, responsive rules, and RTL overrides. It is currently not linked from `base.html`.

`static/js/main.js` contains a navbar scroll-shadow behavior. It looks for `#main-navbar`, but the current navbar has no such ID. It is currently not loaded by `base.html`.

`static/unfold/css/rtl.css` contains RTL rules for the Unfold admin and should be preserved.

`static/images/logo.jpg` is a 1254x1254 JPEG used as the context-processor fallback logo.

## Existing Admin and Unfold Configuration

`certificate_app/admin.py` registers `Certificate` and `AppSettings` using `unfold.admin.ModelAdmin`. It must remain unchanged. New public-content admin classes belong in `academy_app/admin.py`.

The existing Unfold configuration in `project/settings.py` sets the admin title, header, URL, symbol, language display, and custom RTL stylesheet. New admins should use the same Unfold `ModelAdmin` base class. No new admin package is required.

# Existing Functionality to Preserve

The implementation must preserve:

- Certificate model data and lookup behavior.
- Certificate PDF validation and storage paths.
- Existing certificate URLs, including the no-slash and slash forms.
- Existing generated QR-code links.
- Existing `AppSettings` singleton behavior and fields must remain unchanged.
- Existing uploaded-logo fallback behavior.
- Existing brand color and academy-name fallback behavior.
- Existing Arabic/English language configuration.
- Existing custom language-switch endpoint.
- Existing `/i18n/` route.
- Existing admin access and Unfold theme.
- Existing certificate templates and PDF viewer.
- Existing local-storage and R2-storage compatibility.
- Existing Bootstrap and Bootstrap Icons CDN usage.
- Existing static fallback files, including the logo and QR-code assets.

The new public home page must not replace or break certificate verification.

# Current Home Page Analysis

The current homepage is `templates/home.html`, rendered by `home_view` at `/` with URL name `home`.

Current context is provided only by the global context processor. It includes the configured or fallback logo, academy name, footer text, colors, current language, RTL state, and supported languages.

Current visual content:

- Academy logo.
- Academy name.
- Coming-soon badge.
- Coming-soon description.
- Health, Safety, and Environment icons.
- Existing tagline.

The current page has no database-driven content, no hero carousel, no services, no courses, no reviews, no contact form, and no WhatsApp action.

The existing Bootstrap layout and brand colors can be reused. The coming-soon-specific page markup should be replaced, but the certificate pages should continue using the same base template.

# Proposed Architecture

Create one new domain app named `academy_app` for the public academy website. Do not split every homepage section into a separate Django app. Hero slides, services, courses, course videos, reviews, contact messages, academy-specific settings, and their public views belong to one cohesive public-academy domain.

Keep `certificate_app` unchanged. It remains responsible for certificate verification, its existing `Certificate` and `AppSettings` models, its certificate views and URLs, its existing admin registrations, its context processor, and its certificate templates.

This boundary is better than either adding homepage models to `certificate_app` or creating one app per homepage section:

- `certificate_app` stays stable while future certificate features can be added independently.
- `academy_app` owns the complete public marketing/catalog workflow.
- Hero, services, courses, videos, reviews, and contact messages share ordering, publishing, localization, admin, and homepage concerns.
- One public app avoids excessive cross-app imports and fragmented migrations.
- A future large catalog can later be extracted into a separate app only if course management becomes an independent business domain.

The new app may import `certificate_app.models.AppSettings` read-only for existing branding values, but it must not add fields, methods, models, admin registrations, context-processor logic, or views to `certificate_app`.

The public website should consist of:

```text
base.html
  header partial
  main page content
  footer partial
  WhatsApp partial

home.html
  hero slider
  services section
  courses section
  reviews slider
  contact form

service_detail.html
course_detail.html
certificate.html
certificate_not_found.html
404.html
```

The homepage should use `academy_app.views.home_view`, which performs the four public content queries and handles the contact form. Detail pages should use one reusable template per content type, not one template per record.

# Database Design

## Existing Models To Reuse

### `Certificate`

No changes are required for the requested public website. Preserve all fields, validation, relationships, ordering, and file paths.

### `AppSettings`

Reuse this existing model without changing it. It remains owned and administered by `certificate_app`.

Existing responsibilities preserved:

- Uploaded logo.
- Arabic and English academy names.
- Primary and secondary brand colors.
- Arabic and English footer text.
- Singleton primary-key behavior.
- Existing fallback properties.

Do not add `whatsapp_number` to this model. Academy-specific public settings belong to the new app below.

## New Models Required

### `AcademySettings`

This is a new singleton owned by `academy_app`. It must not replace or modify `certificate_app.models.AppSettings`.

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `whatsapp_number` | `CharField` | No | `""` | `max_length=32`; store international digits |

Singleton behavior:

- Force primary key `1` on save.
- Prevent deletion.
- Provide a `load()` helper or a read-only lookup with safe fallback.
- Keep the WhatsApp value optional so a new database can render the site without a configured number.
- Validate or normalize international digits without changing the original certificate settings model.

### `HeroSlide`

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `image` | `ImageField` | Yes | None | `upload_to="hero/"` |
| `image_alt_ar` | `CharField` | No | `""` | `max_length=255` |
| `image_alt_en` | `CharField` | No | `""` | `max_length=255` |
| `title_ar` | `CharField` | No | `""` | `max_length=255` |
| `title_en` | `CharField` | No | `""` | `max_length=255` |
| `description_ar` | `TextField` | No | `""` | Optional localized description |
| `description_en` | `TextField` | No | `""` | Optional localized description |
| `button_text_ar` | `CharField` | No | `""` | `max_length=100` |
| `button_text_en` | `CharField` | No | `""` | `max_length=100` |
| `button_url` | `URLField` | No | `""` | Optional action URL |
| `display_order` | `PositiveIntegerField` | Yes | `0` | Lower values display first |
| `is_active` | `BooleanField` | Yes | `True` | Public visibility flag |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["display_order", "id"]`
- Index `is_active` and `display_order`, preferably with a composite index for the public query.
- No relationships.
- No delete behavior involving other models.

### `Service`

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `name_ar` | `CharField` | Yes | N/A | `max_length=255` |
| `name_en` | `CharField` | Yes | N/A | `max_length=255` |
| `slug` | `SlugField` | Yes | N/A | `max_length=180`, unique |
| `image` | `ImageField` | Yes | N/A | `upload_to="services/"` |
| `image_alt_ar` | `CharField` | No | `""` | `max_length=255` |
| `image_alt_en` | `CharField` | No | `""` | `max_length=255` |
| `short_description_ar` | `TextField` | No | `""` | Card description |
| `short_description_en` | `TextField` | No | `""` | Card description |
| `content_ar` | `TextField` | No | `""` | Detail content |
| `content_en` | `TextField` | No | `""` | Detail content |
| `external_url` | `URLField` | No | `""` | Optional external link |
| `display_order` | `PositiveIntegerField` | Yes | `0` | Lower values display first |
| `is_active` | `BooleanField` | Yes | `True` | Public visibility flag |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["display_order", "id"]`
- Unique index from `slug=True`.
- Index active/order for the homepage query.
- No relationships.

The slug should be a stable ASCII slug managed by the administrator. Do not generate an Arabic slug that may not work with the existing Django `<slug:slug>` converter. Use the English name when generating a suggestion, but allow the administrator to correct it before saving.

### `Course`

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `name_ar` | `CharField` | Yes | N/A | `max_length=255` |
| `name_en` | `CharField` | Yes | N/A | `max_length=255` |
| `slug` | `SlugField` | Yes | N/A | `max_length=180`, unique |
| `image` | `ImageField` | Yes | N/A | `upload_to="courses/"` |
| `image_alt_ar` | `CharField` | No | `""` | `max_length=255` |
| `image_alt_en` | `CharField` | No | `""` | `max_length=255` |
| `short_description_ar` | `TextField` | No | `""` | Card description |
| `short_description_en` | `TextField` | No | `""` | Card description |
| `description_ar` | `TextField` | No | `""` | Full detail description |
| `description_en` | `TextField` | No | `""` | Full detail description |
| `duration_ar` | `CharField` | Yes | N/A | `max_length=100` |
| `duration_en` | `CharField` | Yes | N/A | `max_length=100` |
| `price` | `DecimalField` | Yes | `0` | `max_digits=10`, `decimal_places=2` |
| `display_order` | `PositiveIntegerField` | Yes | `0` | Lower values display first |
| `is_active` | `BooleanField` | Yes | `True` | Public visibility flag |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["display_order", "id"]`
- Unique index from `slug=True`.
- Index active/order for the homepage query.
- Add a non-negative price validator.
- `CourseVideo` has a foreign-key relationship to this model.

The previous single `video_url` design is intentionally removed. A course can have multiple uploaded short videos through the related `CourseVideo` model below.

### `CourseVideo`

`CourseVideo` represents one short video belonging to one course. This is a one-to-many relationship: one course can have zero or more videos.

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `course` | `ForeignKey` | Yes | N/A | Related `Course`, `related_name="videos"`, `on_delete=models.CASCADE` |
| `title_ar` | `CharField` | No | `""` | `max_length=255` |
| `title_en` | `CharField` | No | `""` | `max_length=255` |
| `description_ar` | `TextField` | No | `""` | Optional localized description |
| `description_en` | `TextField` | No | `""` | Optional localized description |
| `video_file` | `FileField` | Yes | N/A | `upload_to="courses/videos/"` |
| `thumbnail` | `ImageField` | No | `""` | `upload_to="courses/video_thumbnails/"` |
| `display_order` | `PositiveIntegerField` | Yes | `0` | Lower values display first |
| `is_active` | `BooleanField` | Yes | `True` | Public visibility flag |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["display_order", "id"]`
- Index `course`, `is_active`, and `display_order` for the detail-page query.
- Use `on_delete=models.CASCADE` so videos cannot remain orphaned after a course is deleted.
- Add a file-extension validator for supported direct-upload formats such as MP4 and WebM.
- Add a maximum file-size validator consistent with the project upload limit.
- Validate that the uploaded file is a video by extension and content type where practical; do not rely on the browser-supplied content type alone.

The file is uploaded through Django admin and stored using the project’s existing default storage backend. No video URL is stored.

### `Review`

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `image` | `ImageField` | Yes | N/A | `upload_to="reviews/"` |
| `image_alt_ar` | `CharField` | No | `""` | `max_length=255` |
| `image_alt_en` | `CharField` | No | `""` | `max_length=255` |
| `student_name_ar` | `CharField` | No | `""` | `max_length=255` |
| `student_name_en` | `CharField` | No | `""` | `max_length=255` |
| `description_ar` | `TextField` | No | `""` | Optional description |
| `description_en` | `TextField` | No | `""` | Optional description |
| `display_order` | `PositiveIntegerField` | Yes | `0` | Lower values display first |
| `is_active` | `BooleanField` | Yes | `True` | Public visibility flag |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["display_order", "id"]`
- Index active/order for the homepage query.
- No relationships.

### `ContactMessage`

Fields:

| Field | Type | Required | Default | Details |
|---|---|---:|---|---|
| `name` | `CharField` | Yes | N/A | `max_length=150` |
| `email` | `EmailField` | Yes | N/A | Django email validation |
| `phone` | `CharField` | Yes | N/A | `max_length=32` |
| `message` | `TextField` | Yes | N/A | Visitor message |
| `is_read` | `BooleanField` | Yes | `False` | Admin read status |
| `created_at` | `DateTimeField` | Yes | N/A | `auto_now_add=True` |
| `updated_at` | `DateTimeField` | Yes | N/A | `auto_now=True` |

Meta configuration:

- `ordering = ["-created_at"]`
- Index `is_read` and `created_at`.
- No relationships.

# Site Settings

There are two intentionally separate settings owners:

`certificate_app.models.AppSettings` remains unchanged and continues to provide the existing logo, academy name, colors, and footer text through `certificate_app.context_processors.site_settings_processor`.

`academy_app.models.AcademySettings` is a new singleton owned by the public academy app. It stores the WhatsApp number required by the homepage, course enrollment, and global button.

Do not add homepage fields to `AppSettings`, and do not modify `certificate_app.context_processors.site_settings_processor`.

Add `academy_app.context_processors.academy_settings_processor` to the template context processors in `project/settings.py`. It should expose:

- `academy_settings`.
- `whatsapp_number`.
- `whatsapp_url`.

The existing certificate context processor continues exposing:

- `site_settings`.
- `logo_url`.
- `academy_name`.
- `footer_text`.
- `primary_color`.
- `secondary_color`.
- `current_language`.
- `is_rtl`.
- `LANGUAGES`.

This preserves existing branding behavior while keeping public academy settings isolated. The global WhatsApp URL has no message. Course-specific URLs must be generated in `academy_app` backend code because they contain dynamic text.

# Header

Modify the shared header in `templates/base.html`, preferably moving it to `templates/partials/header.html`.

Desktop layout:

- Left group contains the logo, academy name, and language switcher.
- Center group contains navigation links.
- Bootstrap `navbar-expand-lg` controls the responsive breakpoint.

Navigation links:

- Home
- Services
- Courses
- Reviews
- Contact

The links should use named URL reversing and section fragments. On detail pages they should link back to the homepage with the same fragments.

Mobile behavior:

- Use the existing Bootstrap navbar collapse behavior.
- Keep the logo visible.
- Keep the language switcher accessible.
- Give the toggler an accessible label.
- Ensure links have visible focus states.

The language switcher must continue using `set_language_view`, not a new translation mechanism.

# Hero / Slider

Create a database-driven `HeroSlide` model and admin interface.

Use Bootstrap 5 Carousel because Bootstrap is already loaded and no additional frontend framework is needed.

Behavior:

- Query only active slides.
- Order by `display_order` and primary key.
- Mark only the first slide as active.
- Render controls and indicators only if more than one slide exists.
- Render optional title, description, and button only when values exist.
- Use the current language’s text fields.
- Use the current language’s alt field with an academy-name fallback.
- Load the first hero image eagerly.
- Lazy-load subsequent images.
- Render a safe empty-state or omit the section when no slides exist.

Recommended image ratio is 16:7 or 16:9. The admin help text should explain the expected ratio.

# Services

Create a database-driven `Service` section.

Homepage cards should contain:

- Responsive image.
- Localized service name.
- Localized short description.
- View Details button.

Cards should use a responsive Bootstrap grid with one column on small screens, two on medium screens, and three on large screens.

Create one detail view and one detail template:

```text
/services/<slug>/
```

Only active services should be accessible publicly. Inactive or missing services should return 404.

The internal detail page is the default link. If `external_url` exists, display it as an optional secondary action.

# Courses

Create a database-driven `Course` section.

Each course can have multiple related `CourseVideo` records. Videos are uploaded directly through the admin and are not represented by a URL field on `Course`.

Homepage cards should contain:

- Image.
- Localized course name.
- Localized short description.
- Localized duration.
- Price.
- View Course button.

Only active courses should be queried for the homepage.

Do not create one template per course. Use one reusable course card and one reusable detail template.

# Course Detail

Create:

```text
/courses/<slug>/
```

The detail template should show all relevant course information:

- Name.
- Image.
- Short description.
- Full description.
- Duration.
- Price.
- Video section.
- Enroll Now button.

Descriptions should be rendered as escaped text with line breaks. Do not mark database content as safe HTML because the project has no rich-text sanitization package.

## Video Decision

Use a related `CourseVideo` model with direct file uploads. Do not keep a single `video_url` field on `Course`.

Reason:

- One course needs to support multiple short videos.
- The administrator should upload the video files directly through Django admin.
- The project already supports local filesystem storage and Cloudflare R2 through Django’s default storage backend.
- A foreign key keeps videos organized under their course and allows independent ordering and publication status.
- HTML5 video can play uploaded MP4/WebM files without an iframe or external hosting dependency.
- No new frontend framework or video package is required.

The implementation should use `FileField`, not `URLField`, with `upload_to="courses/videos/"`. Restrict uploads to browser-friendly formats such as MP4 and WebM and validate a maximum file size consistent with the existing 15 MB upload limit. If the project later needs larger files, update the Django, reverse-proxy, and storage upload limits together instead of silently allowing oversized uploads.

The course detail view should retrieve active videos with `prefetch_related()` and order them by `display_order` and primary key. The template should render each file using an HTML5 `<video controls preload="metadata">` element with an optional thumbnail poster and a download/open fallback link.

If a course has no active videos, show a translated fallback instead of an empty video area.

# WhatsApp Enrollment

Store the WhatsApp number in `AcademySettings.whatsapp_number`.

Create reusable logic in `academy_app/utils.py`:

- Normalize the number to international digits.
- Remove formatting characters.
- Reject empty or invalid values.
- Build a `wa.me` URL.
- Encode the optional message with `urllib.parse.quote`.

Course enrollment message:

```text
I would like to enroll in [Course Name]
```

The course detail view should pass a final `whatsapp_enrollment_url` to the template. Templates should not build the number or dynamic message themselves.

If the number is missing or invalid, the enrollment button should be hidden or replaced with a translated contact fallback.

# Reviews

Create a database-driven `Review` model for admin-uploaded student review screenshots.

Display active reviews in a Bootstrap Carousel.

Each slide may include:

- Screenshot image.
- Optional localized student name.
- Optional localized description.

Use `display_order` for ordering. Hide controls and indicators when only one review exists. Use localized alt text and an accessible carousel label.

The admin should receive image preview help and recommended screenshot dimensions. The original uploaded screenshot should use the existing default storage backend.

# Contact

Create `academy_app/forms.py` containing a `ContactForm` based on `ContactMessage`.

The form fields are:

- Name.
- Email.
- Phone.
- Message.

Validation requirements:

- All fields are required.
- Email uses Django validation.
- Name, phone, and message have reasonable maximum lengths.
- Values are stripped before save.
- Submitted text is escaped in templates.
- CSRF token is included.

The form should submit to the homepage because the contact form is a homepage section and the current project has only a homepage public workflow.

`home_view` should handle:

- GET with an unbound form.
- POST with a bound form.
- Save valid messages with `is_read=False`.
- Add a translated success message.
- Redirect to `home#contact` after success.
- Re-render the complete homepage context with validation errors after failure.

A shared homepage context helper should be used for both GET and invalid POST so the form does not lose the sliders or cards.

# Global WhatsApp Button

Create `templates/partials/whatsapp_button.html` and include it from `base.html`.

The button must appear on:

- Homepage.
- Service detail pages.
- Course detail pages.
- Certificate pages.
- Certificate-not-found page.
- 404 page.

Use the globally exposed `whatsapp_url`. Hide the button when no valid number is configured.

Accessibility and behavior:

- Add an accessible `aria-label`.
- Use `target="_blank"` and `rel="noopener noreferrer"`.
- Keep it visible above the footer.
- Prevent it from covering form controls on small screens.
- Support RTL positioning with logical CSS properties where possible.

# Internationalization

Preserve the existing system:

- `LANGUAGE_CODE = "ar"`.
- `LANGUAGES = [("ar", ...), ("en", ...)]`.
- `LocaleMiddleware`.
- Custom `/set-language/` endpoint.
- `LANGUAGE_COOKIE_NAME = "django_language"`.
- Existing `/i18n/` route.

Do not add `django-modeltranslation` or another translation dependency.

Use bilingual database fields because `AppSettings` already follows this pattern and no model translation package exists.

All new static interface labels must use `{% trans %}` or `gettext_lazy`.

Update the existing Arabic and English `.po` files for new UI strings and admin labels. The current `.po` files contain many empty translations, so the implementation should add real translations for the new public content labels and form messages. Run the existing `compilemessages` step afterward.

Use `is_rtl` and the existing RTL Bootstrap CSS selection. Do not add a second direction system.

# URL Architecture

Existing routes must remain unchanged.

New routes:

| URL | Name | View | Template |
|---|---|---|---|
| `/services/<slug>/` | `service_detail` | `academy_app.views.service_detail_view` | `academy_app/service_detail.html` |
| `/courses/<slug>/` | `course_detail` | `academy_app.views.course_detail_view` | `academy_app/course_detail.html` |

The homepage remains `/` with name `home`. It will support both GET and contact-form POST.

The contact form does not need a dedicated URL. Its form action should be the homepage with the `#contact` fragment.

Add service and course routes directly in `project/urls.py` or expose them through a carefully designed public URL include. Do not accidentally place them under `/certificate/` because the existing certificate include is reserved for certificate verification.

# View Architecture

## `academy_app.views.home_view`

File: `academy_app/views.py`

Type: Function-based view.

Context:

- `hero_slides`.
- `services`.
- `courses`.
- `reviews`.
- `contact_form`.

Querysets:

```python
HeroSlide.objects.filter(is_active=True).order_by("display_order", "pk")
Service.objects.filter(is_active=True).order_by("display_order", "pk")
Course.objects.filter(is_active=True).order_by("display_order", "pk")
Review.objects.filter(is_active=True).order_by("display_order", "pk")
```

The homepage models have no relationships requiring joins. `Course` does have related `CourseVideo` records, so the course detail view must use `prefetch_related()` to load active videos without N+1 queries. Avoid querying the same queryset again from templates or context processors.

## `academy_app.views.service_detail_view`

File: `academy_app/views.py`

Type: Function-based view.

URL: `/services/<slug>/`.

Query only an active service by slug. Return 404 for inactive or missing services. Pass the service, localized title, description, and metadata context to one reusable detail template.

## `academy_app.views.course_detail_view`

File: `academy_app/views.py`

Type: Function-based view.

URL: `/courses/<slug>/`.

Query only an active course by slug and prefetch its active, ordered `CourseVideo` records. Generate the WhatsApp enrollment URL in backend code. Return 404 for inactive or missing courses.

## `certificate_app.views.certificate_view`

Preserve current behavior. Only add shared base-template functionality such as the global header, footer, and WhatsApp button.

## `certificate_app.views.set_language_view`

Preserve current session and cookie behavior. Validate the redirect target with Django’s safe URL validation to prevent an external open redirect through the `next` POST parameter.

# Template Architecture

Recommended structure:

```text
templates/
  base.html
  home.html
  404.html
  partials/
    header.html
    footer.html
    whatsapp_button.html
  components/
    hero_slider.html
    service_card.html
    course_card.html
    review_slider.html
    contact_form.html

certificate_app/templates/certificate_app/
  certificate.html
  certificate_not_found.html

academy_app/templates/academy_app/
  service_detail.html
  course_detail.html
```

Responsibilities:

- `base.html`: document shell, SEO blocks, static assets, partial inclusion, main block.
- `header.html`: logo, language switcher, responsive navigation.
- `footer.html`: logo, academy name, footer text, optional contact information if added later.
- `whatsapp_button.html`: global floating action.
- `hero_slider.html`: Bootstrap hero carousel.
- `service_card.html`: one service card.
- `course_card.html`: one course card.
- `review_slider.html`: Bootstrap review carousel.
- `contact_form.html`: accessible contact form and messages.
- `home.html`: section order and component inclusion only.
- Detail templates: one reusable page per model type.

Existing certificate templates should continue extending `base.html` without duplicated header/footer markup.

# Bootstrap/UI Architecture

Continue using Bootstrap 5.3.3 and Bootstrap Icons from the existing CDN links. Do not add React, Vue, jQuery, Swiper, or another frontend framework.

Recommended page order:

```text
Header
Hero / image slider
Services
Courses
Reviews
Contact
Footer
Floating WhatsApp button
```

Use:

- `container` or `container-xl` for page width.
- `py-5` or equivalent section spacing.
- Responsive `row` and `col-*` grids.
- Consistent card heights where possible.
- `object-fit: cover` for card images.
- `object-fit: contain` for logos and review screenshots where cropping would be harmful.
- 16:9 or 16:7 hero media.
- 16:9 course video ratio using Bootstrap `.ratio .ratio-16x9`.
- Rounded cards and existing brand shadows.
- Existing Cairo font for Arabic and Inter for English.

Responsive breakpoints:

- Small screens: one-column cards and collapsed navigation.
- Medium screens: two-column service/course cards.
- Large screens: three-column service/course cards and centered navigation.

Sliders must include:

- Indicators when there are multiple items.
- Previous and next controls when there are multiple items.
- Accessible labels.
- Keyboard-friendly controls.
- Sensible autoplay intervals.
- Reduced-motion consideration in CSS.

The existing CSS variables and brand palette should be reused. Dynamic colors from `AppSettings` should only be inserted after validating that they are safe color values.

# Admin / Unfold

All new admin classes should inherit from `unfold.admin.ModelAdmin`.

## `HeroSlideAdmin`

Recommended configuration:

- `list_display`: image preview, localized title, display order, active status.
- `list_filter`: active status, created date if available.
- `search_fields`: Arabic title, English title, descriptions.
- `ordering`: display order and ID.
- `readonly_fields`: timestamps and image preview.
- `fieldsets`: image, localized content, action button, publishing metadata.
- Show an image preview using `format_html`, not unsafe string concatenation.

## `ServiceAdmin`

Recommended configuration:

- `list_display`: image preview, English name, Arabic name, display order, active status.
- `list_filter`: active status.
- `search_fields`: both names, both descriptions, slug.
- `ordering`: display order and ID.
- `readonly_fields`: timestamps and image preview.
- `prepopulated_fields`: slug from the English name only if it does not interfere with bilingual data entry.
- Fieldsets for identity, images, localized card content, localized detail content, optional external URL, and publishing.

## `CourseAdmin`

Recommended configuration:

- `list_display`: image preview, English name, price, duration, video count, display order, active status.
- `list_filter`: active status.
- `search_fields`: both names, both descriptions, slug.
- `ordering`: display order and ID.
- `readonly_fields`: timestamps and image preview.
- Fieldsets for identity, image, localized content, duration/price, and publishing.
- Add a `CourseVideoInline` so administrators can upload and order multiple short videos from the course page.
- Register `CourseVideoAdmin` separately so videos can also be filtered by course and active status.
- Add help text explaining that uploaded videos should be short MP4/WebM files within the configured size limit.
- Show uploaded video file links and optional thumbnail previews where practical.

## `ReviewAdmin`

Recommended configuration:

- `list_display`: screenshot preview, student name, display order, active status.
- `list_filter`: active status.
- `search_fields`: student names and descriptions.
- `ordering`: display order and ID.
- `readonly_fields`: timestamps and image preview.
- Fieldsets for screenshot, student information, description, and publishing.

## `ContactMessageAdmin`

Recommended configuration:

- `list_display`: name, email, phone, read status, created date.
- `list_filter`: read status and created date.
- `search_fields`: name, email, phone, message.
- `ordering`: newest first.
- `readonly_fields`: created and updated timestamps.
- `date_hierarchy`: created date.
- Add admin actions to mark selected messages as read or unread.
- Put the full message in a clear detail fieldset.

## `certificate_app.admin.AppSettingsAdmin`

Reuse the existing admin unchanged. Do not extend its fieldsets or change its permissions.

It continues to manage only the existing certificate/application branding settings:

- Logo.
- Academy names.
- Brand colors.
- Footer text.

## `AcademySettingsAdmin`

Create this admin in `academy_app/admin.py` for the new `AcademySettings` singleton.

Recommended configuration:

- Show the WhatsApp number.
- Use a clear fieldset describing international number format.
- Do not allow adding a second settings record.
- Do not allow deleting the singleton.

No new Unfold dependency is required. The current global Unfold configuration and RTL stylesheet should be preserved.

# Media Handling

The existing settings support two storage modes.

Local mode:

- `MEDIA_URL = "/media/"`.
- `MEDIA_ROOT = BASE_DIR / "media"`.
- `FileSystemStorage`.

R2 mode:

- Enabled when `R2_ACCESS_KEY_ID` exists.
- Uses `storages.backends.s3boto3.S3Boto3Storage`.
- Uses R2 credentials and endpoint settings from environment variables.

All new `ImageField` and `FileField` values should use Django’s default storage. Do not hardcode local media paths in templates.

Recommended upload paths:

- Logo: existing `settings/`.
- Hero images: `hero/`.
- Service images: `services/`.
- Course images: `courses/`.
- Course video files: `courses/videos/`.
- Course video thumbnails: `courses/video_thumbnails/`.
- Review screenshots: `reviews/`.

Images must be validated by `ImageField` and Pillow. Admin help text should recommend dimensions and aspect ratios.

Course videos are uploaded directly by administrators through Django admin. Use browser-friendly MP4/WebM files and validate the extension and maximum size. The current project-wide upload limit is 15 MB, so the first implementation should either enforce that limit for short clips or explicitly update the application and reverse-proxy limits together before allowing larger files. R2 storage can store the uploaded files without changing the model field definitions.

Potential existing issue to verify during implementation: `MEDIA_URL` and `MEDIA_ROOT` are only defined in the local-storage branch, while `project/urls.py` accesses them whenever `DEBUG` is true. Ensure the development media-serving condition does not fail when R2 is configured.

Do not change the storage architecture or install a new image-processing package.

# Performance

Homepage query plan:

- One query for active hero slides.
- One query for active services.
- One query for active courses.
- One query for active reviews.
- One branding settings lookup through the existing certificate context processor.
- One academy settings lookup through the new academy context processor.

The homepage queries do not require relationship joins. The course detail query must use `prefetch_related()` for active `CourseVideo` records because one course can have multiple uploaded videos.

Additional measures:

- Filter `is_active=True` in the database.
- Order in the database.
- Do not query content from templates.
- Do not create one database query per card.
- Use lazy loading for non-hero images.
- Load the first hero image eagerly.
- Use `loading="lazy"` for course, service, and review images.
- Use `preload="metadata"` for HTML5 course videos and avoid loading all video data before playback.
- Use optional thumbnail posters for course videos.
- Provide width/height or stable aspect-ratio containers to reduce layout shift.
- Avoid caching `AppSettings` or `AcademySettings` permanently because administrators need changes to appear without a restart.

Do not add pagination to the homepage initially. If content volume becomes large, add a separate catalog route later rather than overcomplicating the first implementation.

# SEO

Extend the existing `title` and `meta_description` blocks.

Homepage:

- Use the academy name and a translated training-focused description.
- Use one clear `h1`.
- Use `h2` for Services, Courses, Reviews, and Contact.

Service detail pages:

- Localized title using the service name.
- Description based on the service short description.
- Stable slug URL.

Course detail pages:

- Localized title using the course name.
- Description based on the course short description.
- Stable slug URL.
- Optional Open Graph image from the course image.

Base template additions should include:

- `meta description` block.
- Optional canonical URL block.
- Optional Open Graph title, description, and image blocks.
- Semantic `lang` and `dir` attributes, already present.

All uploaded images must have meaningful localized alt text or a safe fallback.

# Accessibility

Implement:

- Semantic `header`, `nav`, `main`, `section`, and `footer` elements.
- One logical `h1` per page.
- Proper heading hierarchy.
- Visible form labels.
- CSRF token.
- Accessible error messages.
- Keyboard-operable navbar and carousel controls.
- `aria-label` values for carousel controls and the WhatsApp button.
- Meaningful image alt text.
- `aria-current` or equivalent active navigation state where practical.
- Visible focus styles.
- Sufficient text/background contrast.
- `rel="noopener noreferrer"` for external new-tab links.
- No information conveyed only by color.
- Mobile controls with sufficiently large tap targets.
- Reduced-motion CSS behavior for users who request it.

Review screenshots should not be cropped in a way that makes text unreadable.

# Testing Plan

Add tests to `academy_app/tests.py` or split them into focused `academy_app` test modules if the file becomes too large. Do not add public-website tests to `certificate_app/tests.py`.

## Models

- `AppSettings` remains unchanged and its existing singleton behavior still works.
- `AcademySettings` is singleton and cannot be deleted.
- `AcademySettings` accepts an empty WhatsApp number.
- Invalid WhatsApp numbers are rejected or safely omitted.
- Hero slide ordering works.
- Service and course slugs are unique.
- Course prices cannot be negative.
- A course can have multiple related `CourseVideo` records.
- Course videos are ordered correctly and inactive videos are excluded publicly.
- Unsupported video extensions and oversized video files are rejected.
- Active flags control public visibility.
- Contact messages default to unread.
- Contact message ordering is newest first.

## Homepage

- Homepage resolves using `home`.
- Homepage returns HTTP 200.
- Active hero slides appear.
- Inactive hero slides do not appear.
- Active services appear in configured order.
- Active courses appear in configured order.
- Active reviews appear in configured order.
- Empty sections do not produce broken markup.
- Homepage contains the contact form.
- Homepage does not create N+1 queries as content records increase.

Use query-capture testing where practical. Avoid brittle exact query counts if the global context processor makes the baseline dependent on settings lookup; instead verify that query counts stay constant when the number of cards increases.

## Services

- Service detail URL reverses correctly.
- Active service detail returns 200.
- Missing service returns 404.
- Inactive service returns 404.
- Localized service content is selected correctly.
- Optional external URL renders only when configured.

## Courses

- Course detail URL reverses correctly.
- Active course detail returns 200.
- Missing course returns 404.
- Inactive course returns 404.
- Duration, price, description, and image render.
- Multiple active uploaded videos render in display order.
- Inactive course videos do not render.
- Missing videos do not render a broken video element.
- Uploaded video files use the configured storage backend.
- Video sources render with HTML5 controls and metadata preload.

## WhatsApp

- Number normalization removes formatting safely.
- Enrollment URL contains the configured number.
- Course name is URL encoded.
- Arabic course names are encoded correctly.
- Missing number hides or disables enrollment action.
- Global WhatsApp URL is available on shared templates.

## Reviews

- Active reviews render.
- Inactive reviews do not render.
- Review ordering works.
- One review hides unnecessary controls.
- Multiple reviews render carousel controls.

## Contact

- Required fields reject empty submissions.
- Invalid email is rejected.
- Valid POST creates exactly one `ContactMessage`.
- New messages are unread.
- Successful POST redirects to `home#contact`.
- Invalid POST re-renders the homepage with errors and all content sections.
- CSRF protection is active.
- Submitted content is escaped.

## Admin

- All new models appear in Unfold admin.
- Search fields work.
- Active/read filters work.
- Ordering is correct.
- Image previews do not fail when images are missing.
- Contact messages can be marked read/unread.
- AcademySettings cannot be duplicated or deleted.
- Existing AppSettings admin behavior remains unchanged.

## Internationalization

- Arabic is the default language.
- English switches correctly.
- Language selection persists through the cookie.
- The current URL is preserved after switching.
- New UI labels are translated.
- Arabic pages use RTL Bootstrap CSS.
- English pages use LTR Bootstrap CSS.

## Existing Features

- Existing certificate URL without trailing slash still works.
- Existing certificate URL with trailing slash still works.
- Existing certificate PDF links still work.
- Certificate not-found behavior remains unchanged.
- Existing 404 template still renders.

# Implementation Order

1. Back up or verify existing database and media data.
2. Add the new `academy_app` to `INSTALLED_APPS`.
3. Add `AcademySettings`, `HeroSlide`, `Service`, `Course`, `CourseVideo`, `Review`, and `ContactMessage` models to `academy_app`.
4. Add model validation, ordering, indexes, and localized field labels.
5. Create the migration; do not alter existing certificate migrations.
6. Update Unfold admin registrations and fieldsets.
7. Create `ContactForm`.
8. Create WhatsApp utilities and direct-video upload validators.
9. Add the academy context processor without changing the existing certificate context processor.
10. Add service and course views to `academy_app`.
11. Update the root URL to use `academy_app.views.home_view`.
12. Add public service and course URL patterns to `academy_app.urls`.
13. Verify the local/R2 media URL behavior.
14. Split the shared base header/footer/WhatsApp markup into partials.
15. Load the existing project CSS and JavaScript correctly.
16. Replace the coming-soon homepage with dynamic sections.
17. Add service and course detail templates.
18. Add hero, card, review, and contact components.
19. Add the responsive Bootstrap styling.
20. Add SEO metadata blocks.
21. Update Arabic and English translations.
22. Compile translations.
23. Add automated tests.
24. Run migrations and collectstatic in the implementation environment.
25. Test local storage and R2-compatible storage paths.
26. Test homepage, detail pages, certificate pages, language switching, admin, and mobile layout.

# File-by-File Changes

## `certificate_app/models.py`

Action: REUSE

Purpose: Preserve certificate and existing branding data without adding homepage functionality.

Changes:

- Do not add fields, models, validators, or relationships.
- Do not add `whatsapp_number` to `AppSettings`.
- Do not move public models into this file.
- Preserve all current `Certificate` and `AppSettings` behavior.

Dependencies:

- Existing certificate migrations and database records.

## `certificate_app/admin.py`

Action: REUSE

Purpose: Preserve the existing certificate and branding administration.

Changes:

- Do not register public homepage models here.
- Do not change AppSettings fieldsets or permissions.
- Do not add WhatsApp settings here.
- Preserve current CertificateAdmin and AppSettingsAdmin exactly.

Dependencies:

- Existing models in `certificate_app.models`.
- Existing `unfold.admin.ModelAdmin` configuration.

## `academy_app/models.py`

Action: CREATE

Purpose: Own all public academy content and academy-specific settings.

Changes:

- Add `AcademySettings`.
- Add `HeroSlide`.
- Add `Service`.
- Add `Course`.
- Add `CourseVideo` with a foreign key to `Course`.
- Add `Review`.
- Add `ContactMessage`.
- Add image and direct-video upload paths.
- Add bilingual fields.
- Add ordering, indexes, publishing flags, and validation.
- Add course price validation.
- Add WhatsApp number validation.

Dependencies:

- Django models.
- Pillow through existing `ImageField` support.
- `certificate_app.models.AppSettings` is not a model dependency; existing branding is read through its unchanged context processor.

## `academy_app/admin.py`

Action: CREATE

Purpose: Provide administrator-friendly Unfold management for public academy content.

Changes:

- Register `AcademySettings`.
- Register HeroSlide, Service, Course, CourseVideo, Review, and ContactMessage.
- Add list displays, filters, searches, ordering, fieldsets, and previews.
- Add a course-video inline and a dedicated CourseVideo admin.
- Add read/unread actions for contact messages.
- Preserve `certificate_app.admin` without changes.

Dependencies:

- Models in `academy_app.models`.
- `unfold.admin.ModelAdmin` and appropriate Unfold inline classes.

## `academy_app/forms.py`

Action: CREATE

Purpose: Define the public contact form.

Changes:

- Add `ContactForm(ModelForm)`.
- Expose name, email, phone, and message.
- Add translated labels and help text.
- Add validation and whitespace normalization.

Dependencies:

- `ContactMessage`.
- Django forms and validators.

## `academy_app/utils.py`

Action: CREATE

Purpose: Hold reusable safe URL helpers.

Changes:

- Add WhatsApp number normalization.
- Add WhatsApp URL generation.
- Add course-message URL encoding.
- Keep direct-video file validation with the model or a dedicated validator module.
- Do not add external video-host parsing because course videos are uploaded files.

Dependencies:

- Python `urllib.parse`.
- Python URL parsing utilities.

## `academy_app/views.py`

Action: MODIFY

Purpose: Replace the coming-soon homepage workflow and add detail views.

Changes:

- Import new models and `ContactForm`.
- Add a shared homepage context builder.
- Update `home_view` to query active ordered content.
- Add valid/invalid contact POST handling.
- Add success messages and redirect to `home#contact`.
- Add `service_detail_view`.
- Add `course_detail_view`.
- Prefetch active ordered `CourseVideo` records for the course detail page.
- Generate enrollment context and expose uploaded video files.
- Do not contain certificate verification views.
- Reuse the existing certificate language-switch route without modifying `certificate_app.views`.

Dependencies:

- New models.
- `ContactForm`.
- `academy_app.utils`.
- Existing messages and translation middleware.

## `academy_app/context_processors.py`

Action: CREATE

Purpose: Expose academy-specific settings and WhatsApp values without modifying the certificate context processor.

Changes:

- Add `academy_settings`.
- Add normalized `whatsapp_number`.
- Add message-free `whatsapp_url`.
- Preserve safe fallbacks when the settings record is missing.

Dependencies:

- `AcademySettings`.
- `academy_app.utils`.

## `academy_app/urls.py`

Action: CREATE

Purpose: Own all public academy URLs.

Changes:

- Add the homepage route named `home`.
- Add `/services/<slug>/` named `service_detail`.
- Add `/courses/<slug>/` named `course_detail`.
- Keep certificate URL patterns out of this module.

Dependencies:

- `academy_app.views`.

## `certificate_app/context_processors.py`

Action: REUSE

Purpose: Preserve existing branding context for all public and certificate templates.

Changes:

- Do not modify this file.
- Continue exposing `logo_url`, `academy_name`, `footer_text`, colors, language, and RTL state.
- Do not add WhatsApp or homepage content here.

## `certificate_app/views.py`

Action: REUSE

Purpose: Preserve certificate verification and the existing language switcher.

Changes:

- Do not modify this file.
- Leave the legacy `home_view` implementation in place even though the root URL will use `academy_app.views.home_view`.
- Leave `certificate_view` unchanged.
- Leave `set_language_view` unchanged.

## `certificate_app/apps.py`

Action: REUSE

Purpose: Preserve the existing certificate app registration.

Changes:

- Do not modify this file.

## `certificate_app/tests.py`

Action: REUSE

Purpose: Keep the existing certificate test module isolated from public academy tests.

Changes:

- Do not add homepage tests here.

## `certificate_app/migrations/`

Action: REUSE

Purpose: Preserve certificate and existing settings schema history.

Changes:

- Do not create or edit certificate-app migrations for the public website.
- Create all new public migrations under `academy_app/migrations/`.

## `certificate_app/urls.py`

Action: REUSE

Purpose: Preserve certificate routes.

Changes:

- No required change unless the implementation deliberately separates public routes from certificate routes.
- Preserve both certificate URL forms.

## `project/urls.py`

Action: MODIFY

Purpose: Mount the new public academy app while preserving certificate routes.

Changes:

- Include `academy_app.urls` at the root path.
- Keep certificate routes under `/certificate/` through unchanged `certificate_app.urls`.
- Keep `/set-language/` pointing to the existing `certificate_app.views.set_language_view`.
- Preserve i18n and admin routes.
- Verify the development media-serving branch does not access undefined `MEDIA_URL` when R2 storage is configured.

Dependencies:

- `academy_app.urls`.
- Existing Django URL configuration.

## `project/settings.py`

Action: MODIFY

Purpose: Register the new public app and its context processor while preserving the existing certificate configuration.

Changes:

- Add `academy_app` to `INSTALLED_APPS`.
- Add `academy_app.context_processors.academy_settings_processor` after the existing certificate context processor.
- Do not add packages or a new storage system.
- Ensure local/R2 media behavior is valid.
- Ensure development media serving is conditional when local media settings exist.
- Preserve existing Unfold, i18n, static, middleware, and certificate context-processor configuration.

Dependencies:

- Existing environment variables.
- `django-storages` and R2 configuration already present in requirements.

## `academy_app/apps.py`

Action: CREATE

Purpose: Register the new public academy Django application.

Changes:

- Set the app name to `academy_app`.
- Use the existing default BigAutoField configuration.
- Give the app a clear admin label such as Public Academy.

## `academy_app/tests.py`

Action: CREATE

Purpose: Test all public academy functionality without changing certificate tests.

Changes:

- Add model tests for AcademySettings and public content models.
- Add view, URL, form, WhatsApp, video upload, i18n, admin, and query-behavior tests.
- Keep `certificate_app/tests.py` unchanged.

## `templates/base.html`

Action: MODIFY

Purpose: Create the shared public shell for the new website and existing certificate pages.

Changes:

- Include `static/css/style.css`.
- Include `static/js/main.js`.
- Add the correct `main-navbar` ID.
- Include the header partial.
- Add SEO blocks for title, description, canonical URL, and Open Graph metadata.
- Include footer and WhatsApp partials.
- Preserve Bootstrap CDN and RTL/LTR selection.
- Preserve existing blocks used by certificate pages.

Dependencies:

- Partials.
- Global context processor.
- Existing Bootstrap assets.

## `templates/home.html`

Action: MODIFY

Purpose: Replace the coming-soon page with the database-driven public homepage.

Changes:

- Render hero section.
- Render services section when data exists.
- Render courses section when data exists.
- Render reviews section when data exists.
- Render contact form.
- Use named section IDs: `hero`, `services`, `courses`, `reviews`, and `contact`.
- Use translated labels and localized model fields.
- Preserve the base template inheritance.

Dependencies:

- Homepage view context.
- Components.

## `templates/partials/header.html`

Action: CREATE

Purpose: Reusable responsive header.

Changes:

- Render database/static fallback logo.
- Render academy name.
- Render current language and language switch form.
- Render centered section links.
- Render responsive Bootstrap toggler.

Dependencies:

- Existing language endpoint.
- Global context processor.

## `templates/partials/footer.html`

Action: CREATE

Purpose: Reusable footer.

Changes:

- Render logo.
- Render academy name.
- Render localized footer text.
- Keep layout responsive.

Dependencies:

- Global context processor.

## `templates/partials/whatsapp_button.html`

Action: CREATE

Purpose: Render the global floating WhatsApp action.

Changes:

- Render only when `whatsapp_url` exists.
- Add accessible label.
- Open WhatsApp in a safe new tab.
- Use RTL-safe positioning classes.

Dependencies:

- Context processor.
- Bootstrap Icons or equivalent existing icon asset.

## `templates/components/hero_slider.html`

Action: CREATE

Purpose: Render the Bootstrap hero carousel.

Changes:

- Render ordered active slides.
- Handle optional text and buttons.
- Add accessible controls and indicators.
- Apply eager/lazy image loading rules.

Dependencies:

- `HeroSlide` queryset.
- Bootstrap JavaScript bundle.

## `templates/components/service_card.html`

Action: CREATE

Purpose: Render one localized service card.

Changes:

- Render image, name, short description, and detail link.
- Use localized alt text.
- Use responsive card markup.

Dependencies:

- One `Service` instance.
- `service_detail` URL.

## `templates/components/course_card.html`

Action: CREATE

Purpose: Render one localized course card.

Changes:

- Render image, name, duration, price, short description, and detail link.
- Use localized alt text.
- Use responsive card markup.

Dependencies:

- One `Course` instance.
- `course_detail` URL.

## `templates/components/review_slider.html`

Action: CREATE

Purpose: Render the review screenshot carousel.

Changes:

- Render active reviews in order.
- Render optional student name and description.
- Add accessible controls and image alt values.

Dependencies:

- `Review` queryset.
- Bootstrap JavaScript bundle.

## `templates/components/contact_form.html`

Action: CREATE

Purpose: Render the contact form and validation messages.

Changes:

- Render labels and fields.
- Render field-level errors.
- Render non-field errors.
- Include CSRF token.
- Submit to the homepage contact section.

Dependencies:

- `ContactForm`.
- Django messages.

## `academy_app/templates/academy_app/service_detail.html`

Action: CREATE

Purpose: Render one service detail page.

Changes:

- Extend `base.html`.
- Render localized title, image, content, and optional external URL.
- Add title and meta-description blocks.
- Preserve global navigation and WhatsApp button.

Dependencies:

- `service_detail_view`.

## `academy_app/templates/academy_app/course_detail.html`

Action: CREATE

Purpose: Render one course detail page.

Changes:

- Extend `base.html`.
- Render localized course information.
- Render all active related `CourseVideo` records in display order.
- Render uploaded files with HTML5 `<video controls preload="metadata">`.
- Use an optional thumbnail as the `poster` attribute.
- Provide a fallback link to open or download the uploaded file.
- Render a translated empty state when the course has no active videos.
- Render enrollment WhatsApp action.
- Add SEO metadata.

Dependencies:

- `course_detail_view`.
- WhatsApp utilities.
- `CourseVideo` relation and default storage backend.

## `certificate_app/templates/certificate_app/certificate.html`

Action: REUSE

Purpose: Preserve certificate verification page.

Changes:

- No direct feature changes required.
- Verify compatibility with expanded base template.

## `certificate_app/templates/certificate_app/certificate_not_found.html`

Action: REUSE

Purpose: Preserve certificate error page.

Changes:

- No direct feature changes required.
- Verify compatibility with expanded base template.

## `templates/404.html`

Action: REUSE or MODIFY only for SEO/accessibility consistency

Purpose: Preserve the existing 404 page while receiving the shared header/footer/WhatsApp button.

## `static/css/style.css`

Action: MODIFY

Purpose: Style the new public homepage while preserving certificate styles.

Changes:

- Preserve current brand variables.
- Add hero carousel styles.
- Add service and course card styles.
- Add review slider styles.
- Add contact form styles.
- Add floating WhatsApp button styles.
- Add detail-page styles.
- Add mobile breakpoints.
- Add focus states and reduced-motion behavior.
- Preserve existing certificate and RTL rules.

## `static/js/main.js`

Action: REUSE, with optional MODIFY

Purpose: Restore the existing navbar scroll-shadow behavior.

Changes:

- Existing code can be reused once `base.html` loads it and adds `id="main-navbar"`.
- Do not add custom slider code because Bootstrap already supplies carousel behavior.
- Modify only if smooth-scroll or reduced-motion behavior requires it.

## `static/unfold/css/rtl.css`

Action: REUSE

Purpose: Preserve existing Unfold RTL behavior.

## `locale/ar/LC_MESSAGES/django.po`

Action: MODIFY

Purpose: Add Arabic translations for new interface labels, form messages, admin labels, carousel controls, and empty states.

## `locale/en/LC_MESSAGES/django.po`

Action: MODIFY

Purpose: Add English translations for new interface labels, form messages, admin labels, carousel controls, and empty states.

## `locale/*/LC_MESSAGES/django.mo`

Action: REGENERATE during implementation

Purpose: Compile updated translation catalogs using the existing `build.sh` process.

## `academy_app/migrations/0001_initial.py`

Action: CREATE

Purpose: Create all new public academy tables without changing certificate migrations.

Changes:

- Create `AcademySettings` with an optional WhatsApp number.
- Create `HeroSlide`.
- Create `Service`.
- Create `Course`.
- Create `CourseVideo` with a foreign key to `Course`.
- Create `Review`.
- Create `ContactMessage`.

The exact migration filename may be generated by Django. It belongs under `academy_app/migrations/` and must not modify or depend on a new migration in `certificate_app`.

## `requirements.txt`

Action: REUSE

Purpose: No new package is required. Existing Django, Pillow, Unfold, django-storages, boto3, and deployment packages are sufficient.

# Migration Plan

Create the initial migration for `academy_app`. Do not create a new migration in `certificate_app`.

Migration operations:

- Add nullable-compatible or empty-default `whatsapp_number` to `AcademySettings`.
- Create `HeroSlide`.
- Create `Service`.
- Create `Course`.
- Create `CourseVideo` with a foreign key to `Course`.
- Create `Review`.
- Create `ContactMessage`.
- Add unique constraints and indexes.

Existing-data compatibility:

- The existing AppSettings row and schema must remain untouched.
- The new AcademySettings WhatsApp field must default to an empty value.
- Existing Certificate records and files must not be altered.
- No data migration is required for the new empty tables.
- If an implementation branch already contains `Course.video_url`, remove that field while creating `CourseVideo`. The current repository has not implemented `Course` yet, so a fresh implementation should not create `video_url` at all.
- Existing media paths must remain unchanged.
- Slugs are required only for newly created service and course records.

Before migration in production, back up the database and media storage.

# Risks and Edge Cases

## Existing Database Data

Risk: A new required academy setting could fail migration, or a developer could accidentally alter the existing certificate settings table.

Solution: Create `AcademySettings` with an optional empty-default WhatsApp field and keep `certificate_app` migrations and models untouched.

## Existing URLs

Risk: Moving or replacing certificate routes could invalidate existing QR codes.

Solution: Preserve both certificate URL patterns exactly.

## Duplicate Models

Risk: Mixing public academy models into `certificate_app` or creating one app per section would couple unrelated domains or fragment the project.

Solution: Keep `certificate_app` unchanged and place the six public-content/message models plus `AcademySettings` in one cohesive `academy_app`.

## Translation Conflicts

Risk: The project has no modeltranslation package, and current PO files contain many empty translations.

Solution: Use explicit Arabic/English database fields and update PO files for static UI text.

## Slug Collisions

Risk: Two services or courses may use the same slug, or Arabic slug generation may produce an empty value.

Solution: Use unique admin-managed ASCII slugs and validate them before save.

## Missing Images

Risk: Deleted or missing media can produce broken image markup.

Solution: Add safe template fallbacks, admin previews that handle missing files, and meaningful image alt values.

## Empty Sections

Risk: A carousel with no items or only one item can render broken controls.

Solution: Hide empty sections and hide controls/indicators when there is only one item.

## Invalid WhatsApp Number

Risk: A formatted or invalid number creates a broken external link.

Solution: Normalize and validate the number in backend code. Hide WhatsApp actions when invalid.

## Course Without Video

Risk: A course may have no active uploaded videos, or an uploaded file may exceed the allowed size or use an unsupported format.

Solution: Make the `CourseVideo` relation optional, validate MP4/WebM extensions and file size, prefetch only active videos, and render a translated fallback when no videos exist.

## Contact Spam

Risk: Public contact forms can receive spam.

Solution: Use CSRF, strict validation, a honeypot if needed, and monitor admin messages. Do not add a third-party package in this implementation unless spam volume requires it.

## Contact Error Rendering

Risk: Re-rendering only the contact form after invalid POST loses homepage content context.

Solution: Use one shared homepage context builder for GET and invalid POST.

## Media Storage

Risk: R2 and local media settings behave differently, and `MEDIA_URL` may be undefined in the R2 branch during development.

Solution: Verify the development media-serving condition and preserve the default storage abstraction.

## Existing Template Dependencies

Risk: Certificate pages depend on `base.html` classes, blocks, and global context.

Solution: Preserve current blocks and context keys, and test certificate pages after base-template changes.

## Static Asset Loading

Risk: The existing stylesheet and JavaScript are not currently loaded, and JavaScript targets a missing navbar ID.

Solution: Load both assets from the base template and add the expected ID/class.

## External CDN Availability

Risk: Bootstrap, Icons, and Google Fonts rely on external CDNs.

Solution: Preserve current architecture for now, but ensure the page remains usable without icons or fonts. A future hardening task can vendor assets.

## Mobile Layout

Risk: Centered desktop navigation and floating controls may overlap on small screens.

Solution: Use Bootstrap collapse, logical positioning, responsive grids, and mobile viewport testing.

## Open Redirect

Risk: The current language switch accepts a user-supplied `next` URL.

Solution for this feature: Do not modify `certificate_app.views.set_language_view` because `certificate_app` must remain unchanged. Keep the existing endpoint and treat redirect hardening as a separate certificate-app security task. The new header should submit the current same-site request path rather than introducing another redirect mechanism.

# Architecture Decisions

## Decision: Keep `certificate_app` unchanged

Reason: `certificate_app` already contains certificate data, verification views, existing branding settings, and routes that may gain more certificate features later.

Alternative considered: Add homepage models and views to the existing app.

Why the selected approach fits: It prevents unrelated public marketing changes from coupling to certificate functionality and preserves a stable extension point for future certificate features.

## Decision: Create one `academy_app` for the homepage domain

Reason: Hero slides, services, courses, course videos, reviews, contact messages, and WhatsApp settings form one public academy domain.

Alternative considered: Create one Django app for every homepage section.

Why the selected approach fits: One domain app keeps shared ordering, publishing, bilingual content, admin, and homepage queries together without fragmenting the project into small apps with unnecessary cross-app dependencies.

## Decision: Create `AcademySettings` instead of modifying `AppSettings`

Reason: The requirement is to leave `certificate_app` unchanged, but the public website needs an academy-owned WhatsApp setting.

Alternative considered: Add `whatsapp_number` to `certificate_app.AppSettings`.

Why the selected approach fits: `AcademySettings` keeps ownership clear. The existing `AppSettings` remains responsible for certificate/application branding, while `academy_app` owns public academy configuration.

## Decision: Explicit bilingual fields

Reason: The project supports Arabic and English but does not use a database translation package.

Alternative considered: Install and configure `django-modeltranslation`.

Why the selected approach fits: It requires no dependency and matches the project’s existing bilingual field style without changing `certificate_app`.

## Decision: Related direct-uploaded course videos

Reason: Each course needs multiple short videos uploaded directly by the administrator. A one-to-many model is more appropriate than a single URL field.

Alternative considered: Store one `video_url` on `Course` or use external YouTube/Vimeo embeds.

Why the selected approach fits: `CourseVideo.course` provides clear ownership, ordering, active status, optional localized metadata, and direct storage through the existing local/R2 backend. The videos are explicitly short, so the implementation can enforce the current upload limit or update it deliberately.

## Decision: Homepage contact POST

Reason: Contact is a homepage section and the current site has a single public homepage workflow.

Alternative considered: Add a dedicated `/contact/` endpoint.

Why the selected approach fits: It keeps the public URL structure small and allows invalid form errors to render beside the contact section.

## Decision: Bootstrap Carousel

Reason: Bootstrap 5.3.3 and its JavaScript bundle are already loaded.

Alternative considered: Add Swiper or another slider library.

Why the selected approach fits: It avoids another dependency and supports the required hero/review sliders.

## Decision: Stable ASCII slugs

Reason: Django’s existing slug URL converter is ASCII-oriented, and bilingual names may include Arabic.

Alternative considered: Unicode slugs or ID-based URLs.

Why the selected approach fits: Stable ASCII slugs are readable, portable, and independent of the active language.

# Final Implementation Checklist

- [ ] Confirm the implementation agent is working from this document.
- [ ] Preserve certificate models, files, URLs, and templates.
- [ ] Keep `certificate_app` models, views, URLs, admin, context processor, tests, and migrations unchanged.
- [ ] Create `academy_app` for the public homepage domain.
- [ ] Create AcademySettings instead of modifying AppSettings.
- [ ] Add the academy-owned WhatsApp setting.
- [ ] Add HeroSlide, Service, Course, CourseVideo, Review, and ContactMessage.
- [ ] Add indexes, ordering, validation, and stable slugs.
- [ ] Create and apply the new migration in the implementation phase.
- [ ] Register every new model in Unfold admin.
- [ ] Add ContactForm.
- [ ] Add WhatsApp utilities and direct-video upload validation.
- [ ] Add the `academy_app` context processor.
- [ ] Update homepage and detail views in `academy_app`.
- [ ] Add service/course URL patterns in `academy_app.urls`.
- [ ] Verify local and R2 media behavior.
- [ ] Add responsive header and section navigation.
- [ ] Add reusable templates and components.
- [ ] Load existing CSS and JavaScript correctly.
- [ ] Implement hero and review Bootstrap carousels.
- [ ] Implement service and course cards.
- [ ] Implement service and course detail pages.
- [ ] Implement contact form submission and success/error handling.
- [ ] Implement global WhatsApp button.
- [ ] Implement course enrollment WhatsApp URL.
- [ ] Add SEO metadata.
- [ ] Add accessibility attributes and focus states.
- [ ] Update Arabic and English translations.
- [ ] Compile translation files.
- [ ] Add automated tests.
- [ ] Test existing certificate functionality.
- [ ] Test mobile and RTL/LTR layouts.
- [ ] Run final Django checks and deployment build steps.

# Implementation Checklist

## Phase 1: Data and Migration

- [ ] Back up the database and media storage.
- [ ] Create `AcademySettings` in `academy_app`.
- [ ] Add `HeroSlide`.
- [ ] Add `Service`.
- [ ] Add `Course`.
- [ ] Add `CourseVideo` with a foreign-key relationship to `Course`.
- [ ] Add `Review`.
- [ ] Add `ContactMessage`.
- [ ] Add model validation.
- [ ] Add model ordering.
- [ ] Add database indexes.
- [ ] Generate `academy_app` initial migration.
- [ ] Confirm no `certificate_app` migration is created.
- [ ] Review the generated migration before applying it.

## Phase 2: Admin

- [ ] Register HeroSlide in Unfold.
- [ ] Register Service in Unfold.
- [ ] Register Course in Unfold.
- [ ] Add the CourseVideo inline and dedicated admin.
- [ ] Register Review in Unfold.
- [ ] Register ContactMessage in Unfold.
- [ ] Register AcademySettings in Unfold.
- [ ] Leave AppSettings admin fieldsets unchanged.
- [ ] Add search and filter configuration.
- [ ] Add image previews.
- [ ] Add contact read/unread actions.
- [ ] Verify singleton settings restrictions.

## Phase 3: Backend

- [ ] Create ContactForm.
- [ ] Create WhatsApp helper functions.
- [ ] Create direct-video extension and size validators.
- [ ] Add the academy context processor.
- [ ] Update `academy_app.views.home_view`.
- [ ] Add service detail view in `academy_app`.
- [ ] Add course detail view.
- [ ] Add service and course URL patterns.
- [ ] Verify the existing language-switch flow without modifying `certificate_app.views`.
- [ ] Verify media settings under local storage.
- [ ] Verify media settings under R2 configuration.

## Phase 4: Templates

- [ ] Add header partial.
- [ ] Add footer partial.
- [ ] Add WhatsApp partial.
- [ ] Add hero component.
- [ ] Add service-card component.
- [ ] Add course-card component.
- [ ] Add review-slider component.
- [ ] Add contact-form component.
- [ ] Update base template.
- [ ] Replace coming-soon homepage.
- [ ] Add service detail template.
- [ ] Add course detail template.
- [ ] Verify certificate templates still extend the base correctly.

## Phase 5: Frontend

- [ ] Load `style.css`.
- [ ] Load `main.js`.
- [ ] Add the expected navbar ID.
- [ ] Add responsive navigation.
- [ ] Add responsive cards.
- [ ] Add hero carousel.
- [ ] Add review carousel.
- [ ] Add HTML5 course video controls and 16:9 containers.
- [ ] Add floating WhatsApp styling.
- [ ] Add mobile breakpoints.
- [ ] Add RTL-specific layout checks.
- [ ] Add visible focus states.
- [ ] Add reduced-motion behavior.

## Phase 6: SEO, i18n, and Accessibility

- [ ] Add localized page titles.
- [ ] Add localized meta descriptions.
- [ ] Add canonical and Open Graph blocks where appropriate.
- [ ] Add localized image alt text.
- [ ] Add accessible carousel controls.
- [ ] Add accessible form labels and errors.
- [ ] Update Arabic translations.
- [ ] Update English translations.
- [ ] Compile `.mo` files.

## Phase 7: Verification

- [ ] Run Django system checks.
- [ ] Run migrations in a test environment.
- [ ] Run automated tests.
- [ ] Test homepage with empty content.
- [ ] Test homepage with multiple sliders/cards/reviews.
- [ ] Test service detail pages.
- [ ] Test course detail pages.
- [ ] Test missing and inactive records.
- [ ] Test WhatsApp enrollment URL encoding.
- [ ] Test missing WhatsApp configuration.
- [ ] Test contact success and validation errors.
- [ ] Test admin search and filters.
- [ ] Test Arabic and English switching.
- [ ] Test existing certificate URLs.
- [ ] Test local media uploads.
- [ ] Test R2-compatible media URLs.
- [ ] Test desktop layout.
- [ ] Test mobile layout.
- [ ] Test RTL layout.
- [ ] Run the production build steps without modifying the plan document.
