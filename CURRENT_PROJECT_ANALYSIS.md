# Current Project Analysis

## 1. Scope

This document describes the current state of the `future-academey` Django project after the academy website implementation. It is an analysis document only. It does not change the project architecture and does not replace `STRUCTURE.md`.

Analysis date: 2026-09-25

## 2. Executive Summary

The project is a Django 5.2 academy website with two clear domains:

- `certificate_app`: certificate verification, certificate PDF storage, certificate branding settings, and the existing certificate admin workflow.
- `academy_app`: the public academy website, including homepage content, services, courses, course videos, reviews, contact messages, WhatsApp settings, and public templates.

The architecture is appropriately separated. Certificate verification remains under `/certificate/`, while the public academy website owns the root homepage and catalog pages.

The current certificate model already supports three certificate code/PDF pairs for one student. Codes are manually entered in the admin panel and are globally unique at the database-field level. There is currently no code-generation service, code-generation admin control, code reservation mechanism, issuance audit log, or public code-creation page.

## 3. Repository Structure

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
  tests.py
  migrations/
  templates/certificate_app/

academy_app/
  models.py
  views.py
  urls.py
  admin.py
  forms.py
  context_processors.py
  utils.py
  tests.py
  templatetags/
  migrations/
  templates/academy_app/

templates/
  base.html
  home.html
  404.html
  partials/
  components/

static/
  css/style.css
  js/main.js
  images/logo.jpg
  unfold/css/rtl.css

locale/
  ar/LC_MESSAGES/
  en/LC_MESSAGES/

media/
  certificates/
  settings/
```

## 4. Django Configuration

`project/settings.py` currently provides:

- Django 5.2 configuration.
- Unfold before `django.contrib.admin`.
- `certificate_app` and `academy_app` in `INSTALLED_APPS`.
- Security, WhiteNoise, sessions, locale, CSRF, authentication, messages, and clickjacking middleware.
- Arabic as the default language.
- Arabic and English language support.
- A root template directory and app template discovery.
- The existing certificate context processor.
- The academy context processor for WhatsApp settings.
- SQLite by default with `DATABASE_URL` support.
- Local filesystem storage when R2 is unavailable.
- Cloudflare R2/S3-compatible default storage when R2 credentials are configured.
- A 15 MB request upload limit.
- Production HTTPS and cookie security options when `DEBUG` is false.

The project uses Django's default storage abstraction correctly for uploaded certificate PDFs, images, and course videos. New feature work must not hardcode local media paths.

## 5. URL Architecture

Current public routes:

| URL | Name | Responsibility |
|---|---|---|
| `/` | `home` | Database-driven academy homepage |
| `/services/<slug>/` | `service_detail` | Active service detail page |
| `/courses/<slug>/` | `course_detail` | Active course detail page |
| `/certificate/<certificate_id>` | `certificate_app:certificate` | Certificate verification without trailing slash |
| `/certificate/<certificate_id>/` | `certificate_app:certificate` | Certificate verification with trailing slash |
| `/set-language/` | `set_language` | Existing custom language switch view |
| `/i18n/` | Django i18n URLs | Required by Django and Unfold |
| `/admin/` | Django admin | Unfold administration |

The two certificate URL forms must remain unchanged because QR codes and external links may use either form.

## 6. Certificate Domain

### Certificate model

`certificate_app.models.Certificate` currently stores:

- One student name.
- `certificate_code_1` and `certificate_pdf_1` as the required first certificate pair.
- Optional `certificate_code_2` and `certificate_pdf_2`.
- Optional `certificate_code_3` and `certificate_pdf_3`.
- Creation and update timestamps.

Each code field is a unique `CharField` with a maximum length of 50. The second and third code fields are optional and nullable.

### Existing validation

`Certificate.clean()` currently:

- Trims certificate codes.
- Converts entered codes to uppercase.
- Requires a PDF when a code is entered.
- Requires a code when a PDF is uploaded.
- Detects duplicate codes between slots on the same record.

PDF extension validation accepts only `.pdf` files.

### Existing lookup

`Certificate.get_certificate_by_code()`:

- Normalizes the lookup value to uppercase.
- Searches all three code columns case-insensitively.
- Returns the matching certificate, code, and PDF.
- Returns `None` when no match exists or a duplicate match is detected.

### Existing verification URL behavior

`certificate_app.views.certificate_view` extracts the final URL segment after the last hyphen and uses it as the certificate code. This means generated codes should not contain hyphens. A generated code should remain compatible with:

```python
Certificate.generate_url_slug(code)
```

### Existing admin

`certificate_app.admin.CertificateAdmin` already provides:

- Student and certificate-code search.
- Created-date filtering.
- Three certificate fieldsets.
- PDF upload fields.
- Read-only timestamps.
- Unfold styling.

The certificate admin is a good location for a code-generation control because it is already the trusted issuance workflow.

### Existing certificate data

The current local database contains:

- One `AppSettings` row.
- Two `Certificate` rows.
- Certificate codes currently include `SR206` and `FA0064`.
- One empty `AcademySettings` row is present for the academy feature.
- No active hero slides, services, courses, course videos, reviews, or contact messages are currently stored.

## 7. Academy Domain

`academy_app` owns the public academy workflow:

- `AcademySettings`: singleton WhatsApp setting.
- `HeroSlide`: localized hero content and images.
- `Service`: localized service cards and detail pages.
- `Course`: localized course information, price, duration, and image.
- `CourseVideo`: ordered active/inactive direct-upload video records.
- `Review`: localized student review screenshots.
- `ContactMessage`: public contact submissions with read/unread state.

The homepage uses four ordered, active querysets. Course details use `Prefetch` to load active videos without N+1 queries.

## 8. Frontend Architecture

The project uses Django templates and Bootstrap 5.3.3. Shared templates include:

- Responsive header and navigation.
- Arabic RTL and English LTR support.
- Hero carousel.
- Service cards.
- Course cards.
- Review carousel.
- Contact form.
- Floating WhatsApp action.
- Shared footer.

`static/css/style.css` contains the project design system, academy components, certificate styles, focus states, responsive rules, and reduced-motion behavior. `static/js/main.js` provides the navbar scroll effect.

## 9. Internationalization

The current i18n architecture uses:

- `LocaleMiddleware`.
- `LANGUAGE_CODE = "ar"`.
- Arabic and English catalogs.
- Explicit bilingual database fields.
- A custom `/set-language/` endpoint that stores the selected language in the session and cookie.

New certificate-code generation labels should use Django translation helpers in admin forms, templates, and messages. No new translation framework is needed.

## 10. Storage and Deployment

The project supports:

- Local filesystem media storage in development when R2 is not configured.
- Cloudflare R2/S3-compatible storage when R2 credentials exist.
- WhiteNoise static files.
- Gunicorn deployment.
- Migration, static collection, and translation compilation through `build.sh`.

Any code-generation feature should avoid writing temporary generated files. A certificate code is text data and should not require a new storage dependency.

## 11. Testing State

`academy_app/tests.py` currently covers:

- Academy models and validation.
- Video extension and size validation.
- WhatsApp helpers.
- Contact forms and CSRF behavior.
- Homepage, detail pages, empty states, and query behavior.
- Reviews.
- Admin registration and actions.
- Arabic/English rendering.
- Existing certificate routes and PDF links.

The existing `certificate_app/tests.py` remains minimal. Certificate regression coverage currently lives in `academy_app/tests.py` so the certificate app itself remains stable.

## 12. Strengths

- Clear separation between certificate verification and public academy content.
- Existing certificate URLs and PDF behavior are stable.
- Admin is already the trusted certificate issuance interface.
- Code fields are already unique and normalized during model validation.
- Storage abstraction supports local and R2 deployments.
- The public UI already supports Arabic RTL and English LTR.
- The project has a working Unfold admin foundation.
- The current test suite covers the public website and certificate regressions.

## 13. Current Gaps Relevant to Code Generation

The project does not currently have:

- A reusable certificate-code generator.
- A standard code format policy.
- A server-side code reservation or issuance service.
- An admin button for generating a code.
- A copy-to-clipboard control for generated codes.
- A generated verification URL display in the admin.
- A code-generation audit log.
- Bulk code generation.
- A certificate status such as draft, issued, revoked, or expired.

The three code fields are also a denormalized structure. This should not be redesigned as part of the first generation feature because changing it could affect existing certificate records, lookup behavior, URLs, and QR links.

## 14. Known Risks

1. Certificate codes are searched case-insensitively, while database uniqueness behavior can vary by database engine. A generator must always produce uppercase codes and perform case-insensitive collision checks.
2. Generated codes must not contain hyphens because the certificate view extracts the final hyphen-delimited URL segment as the code.
3. A public generation page would allow visitors to mint untrusted verification codes and would expose an internal issuance operation.
4. A client-side-only generator could produce duplicate codes. Generation must be server-side and collision checked.
5. Automatic generation during every save could unexpectedly replace or fill manually managed values. Generation should be explicit unless a future issuance workflow requires automation.
6. The existing custom language switch view accepts a user-supplied `next` URL and should be hardened separately with safe URL validation. This is not required for the code-generation feature.
7. A future audit requirement may require a separate code-generation or certificate-issuance log rather than adding more fields to the current `Certificate` model.

## 15. Recommended Next Feature

Implement certificate-code generation inside the existing authenticated Unfold certificate admin. Do not create a public UI page for code generation.

The detailed feature proposal is documented in:

```text
CERTIFICATE_CODE_GENERATION_FEATURE.md
```
