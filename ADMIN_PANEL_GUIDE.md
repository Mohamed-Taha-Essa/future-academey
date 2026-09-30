# Admin Panel User Guide

This guide explains every model available in the Django admin, how to fill it in, and **exactly where that content appears on the public website**.

It is written for the academy administrator/content editor. You do not need to know how the code works — you only need to know which box to fill and which page changes as a result.

---

## Table of Contents

1. [How to open the admin panel](#1-how-to-open-the-admin-panel)
2. [The three rules that control everything](#2-the-three-rules-that-control-everything)
3. [Why a section disappears from the website](#3-why-a-section-disappears-from-the-website)
4. [Content models — where each one shows up](#4-content-models--where-each-one-shows-up)
5. [`AcademySettings` — the singleton](#5-academysettings--the-singleton)
6. [`HeroSlide` — the homepage banner](#6-heroslide--the-homepage-banner)
7. [`Service` — the services grid](#7-service--the-services-grid)
8. [`Course` — the courses grid](#8-course--the-courses-grid)
9. [`CourseVideo` — videos inside a course](#9-coursevideo--videos-inside-a-course)
10. [`Review` — student testimonials](#10-review--student-testimonials)
11. [`ContactMessage` — the message inbox](#11-contactmessage--the-message-inbox)
12. [Certificate app models](#12-certificate-app-models)
13. [Quick reference table](#13-quick-reference-table)
14. [Recommended first-time setup order](#14-recommended-first-time-setup-order)
15. [Image sizing guide](#15-image-sizing-guide)
16. [Validation rules and limits](#16-validation-rules-and-limits)
17. [Arabic / English rules](#17-arabic--english-rules)
18. [Troubleshooting](#18-troubleshooting)
19. [Do's and don'ts](#19-dos-and-donts)

---

## 1. How to open the admin panel

The admin panel is Django's built-in administration area, restyled with the **Unfold** theme (a modern dark/light interface).

Start the project, then open:

```
http://127.0.0.1:8000/admin/
```

Log in with a **superuser** account. If you do not have one, create it from the terminal:

```bash
venv/bin/python manage.py createsuperuser
```

The sidebar is split into two domains:

| Admin section | What it manages | What it affects on the website |
|---|---|---|
| `ACADEMY` | Homepage content, courses, reviews, messages, WhatsApp | The whole public website |
| `CERTIFICATES` | Student certificates, academy logo/colors/footer | `/certificate/` verification page + header/footer branding |

There are two completely separate groups of settings. They look similar but do different jobs — see section 12.

---

## 2. The three rules that control everything

Almost every content model in `academy_app` has the same three fields. Learn these once and you understand the entire admin.

### Rule 1 — `is_active` (نشط) decides if it is visible

Only records with **`is_active` ticked** are ever sent to the public website.

- Ticked → visible on the site
- Untick it → instantly disappears from the site
- Unticking is **not deletion**. The record and its uploaded files stay in the admin, and you can re-activate it any time by ticking the box again.

This is the recommended way to remove a course or review for a short time without losing it. Use real deletion only for things you will never publish again (for example a typo, or a spam review).

### Rule 2 — `display_order` (ترتيب العرض) decides the position

A whole number. **Lower number = higher on the page.** The website always sorts by `display_order` first, then by creation ID as a tiebreaker.

- `1, 2, 3, 4` → the natural reading order
- `0` on everything → falls back to oldest-first, which is usually not what you want
- All three demo courses use `1, 2, 3`

Tip: use gaps of 10 (`10, 20, 30`) so you can slot a new item between two existing ones later without renumbering everything.

### Rule 3 — every text field comes in an Arabic and an English pair

Fields appear as `الاسم (عربي)` and `الاسم (إنجليزي)` — for example `name_ar` and `name_en`.

- The visitor sees **Arabic** when the site is in Arabic.
- The visitor sees **English** when the site is in English.
- **Fallback rule:** if the Arabic value is empty, the site shows the English value instead. So a fully English entry still displays correctly in Arabic mode.

Only `name_ar`/`name_en` (and for courses, `duration_ar`/`duration_en`) are mandatory. Descriptions, alt text, and button labels are optional and can be left blank.

---

## 3. Why a section disappears from the website

This is the single most common reason for "the UI is missing", so read this before changing anything.

The public website is **completely database-driven**. Nothing about the layout is hardcoded. Each homepage section only renders when there is at least one **active** record to show it:

| Website section | Requires | If none are active |
|---|---|---|
| Hero carousel | 1 active `HeroSlide` | A branded **fallback banner** is shown instead |
| Our Services | 1 active `Service` | The whole section is **omitted** |
| Our Courses | 1 active `Course` | The whole section is **omitted** |
| What Our Students Say | 1 active `Review` | The whole section is **omitted** |
| Contact Us | Nothing — always renders | Always visible |
| Header / Footer / WhatsApp button | — | Always visible (WhatsApp needs a number) |

**The result:** a brand-new installation with an empty database shows only the header, a fallback hero, the contact form, and the footer. That is correct behaviour, not a bug.

To make the page look complete, add at least one active record to each of the four models above. See section 14 for the recommended order.

**A note on carousel controls:** the previous/next arrows and the dot indicators are only rendered when there is **more than one** active slide. With exactly one active slide they are intentionally hidden, because there would be nothing to slide to.

---

## 4. Content models — where each one shows up

| Model | Admin label | Where it appears on the site | Public URL |
|---|---|---|---|
| `AcademySettings` | إعدادات الأكاديمية | Floating WhatsApp button (all pages) + the "Enroll on WhatsApp" button on course pages | — |
| `HeroSlide` | شرائح العرض الرئيسي | Top homepage carousel (banner) | `/` |
| `Service` | الخدمات | "Our Services" card grid + full service page | `/` and `/services/<slug>/` |
| `Course` | الدورات التدريبية | "Our Courses" card grid + full course page | `/` and `/courses/<slug>/` |
| `CourseVideo` | فيديوهات الدورات | Video player list on the course page | `/courses/<slug>/` |
| `Review` | تقييمات الطلاب | "What Our Students Say" carousel | `/` |
| `ContactMessage` | رسائل الاتصال | Nowhere — this is your **inbox** | — |
| `Certificate` | الشهادات | Certificate verification page | `/certificate/<code>/` |
| `AppSettings` | إعدادات التطبيق | Logo, brand colors, footer text (site-wide) | all pages |

---

## 5. `AcademySettings` — the singleton

**Admin:** `Academy` → `إعدادات الأكاديمية` (Academy Settings)

This model has exactly **one field**, and the record is a **singleton** — it always saves to row ID 1. You can never have a second one, and the admin hides the delete button so it cannot be removed. This is intentional: the templates look up this one record to build the WhatsApp link.

### Fields

| Field | Arabic label | Required | Notes |
|---|---|---|---|
| `whatsapp_number` | رقم الواتساب | No | International format, **digits only, no `+`** |

Example: `201001234567` → correct. `+20 100 123 4567` → spaces and `+` are stripped automatically.

**Leave it empty and every WhatsApp button disappears from the website** — both the floating button and the course enrollment button. This is the correct setting if you do not want WhatsApp contact at all.

### Where it shows in the UI

1. **Floating WhatsApp button** — bottom corner of *every* page (homepage, service pages, course pages, even the certificate page). It is green, round, and always visible. In Arabic it sits on the **left**; in English on the **right**.
2. **"Enroll on WhatsApp" button** — on each course page (`/courses/<slug>/`). The message is pre-filled with the course name, for example *"I would like to enroll in OSHA General Industry"*.

### Validation

- Between 5 and 20 digits.
- Anything else is rejected with *"رقم الواتساب غير صالح"*.
- The number is normalized to digits only before it is saved, so `+20 (100) 123-4567` and `201001234567` end up identical.

### Caution

A number that is set but not a real WhatsApp account means the buttons are visible but every tap opens a chat that fails. Verify the number by opening one of the buttons after saving.

---

## 6. `HeroSlide` — the homepage banner

**Admin:** `Academy` → `شرائح العرض الرئيسي` (Hero Slides)

The rotating banner at the very top of the homepage. Slides rotate automatically on a timer, and you can also click the arrows or dots.

### Fields

| Field | Arabic label | Required | Used for |
|---|---|---|---|
| `image` | صورة العرض | **Yes** | The banner photo. 16:7 landscape works best |
| `image_alt_ar` / `image_alt_en` | النص البديل للصورة | No | Screen-reader text. Describe the photo |
| `title_ar` / `title_en` | العنوان | No | The big headline. First slide renders as the page `<h1>` |
| `description_ar` / `description_en` | الوصف | No | Supporting sentence under the headline |
| `button_text_ar` / `button_text_en` | نص الزر | No | Call-to-action label. Blank hides the button |
| `button_url` | رابط الزر | No | Where the button goes, e.g. `/courses/` or `/#contact` |
| `display_order` | ترتيب العرض | No | Slide order |
| `is_active` | نشط | No | Visible or not |

### Where it shows in the UI

The `#hero` section at the top of `/`, **above** the fold on every screen size.

- The image is cropped to 16:7 (16:9 on phones) and darkened by a gradient at the bottom so white text stays readable.
- Text sits in the lower-left (lower-right in Arabic).
- If you fill **both** title fields, the **first active slide** supplies the page `<h1>`. Keep your most important message on the slide with `display_order = 1`.
- If you leave a slide's title *and* description empty, the image shows on its own with no text block.

### Empty state

With **zero** active slides, the carousel is replaced by a branded fallback banner (so the page never looks broken). With **one** active slide there are no arrows or dots. With **two or more**, the full carousel controls appear.

---

## 7. `Service` — the services grid

**Admin:** `Academy` → `الخدمات` (Services)

The "Our Services" section on the homepage. Each service also gets its own detail page.

### Fields

| Field | Arabic label | Required | Used for |
|---|---|---|---|
| `name_ar` / `name_en` | اسم الخدمة | **Yes** | Card heading and page `<h1>` |
| `slug` | الرابط المختصر | **Yes** | The page address, e.g. `safety-consulting` |
| `image` | صورة الخدمة | **Yes** | Card photo, cropped 16:10 |
| `image_alt_ar` / `image_alt_en` | النص البديل | No | Screen-reader text |
| `short_description_ar` / `short_description_en` | الوصف المختصر | No | 1–3 lines on the card. Keep it short |
| `content_ar` / `content_en` | المحتوى | No | The full body on the detail page |
| `external_url` | رابط خارجي | No | Optional outbound link |
| `display_order` | ترتيب العرض | No | Card order left-to-right |
| `is_active` | نشط | No | Visible or not |

### `slug` — read this before saving

- The slug is the URL. `name = "Safety Consulting"` with slug `safety-consulting` gives `/services/safety-consulting/`.
- It is **auto-filled from `name_en`** as you type, thanks to Django's prepopulated field. You rarely need to touch it.
- It must be **unique**. If you reuse a slug you will get *"The slug with value X is already in use"* and the save will fail.
- **It is not a required-safe decision to change later.** Changing the slug changes the public URL and breaks any links people already shared. If you must change it, you are responsible for setting up a redirect.

### Where it shows in the UI

1. **Homepage** `/` → the `#services` section, 3 cards per row on desktop, 1 per row on phones. The card shows the image, name, short description, and a **"View Details"** button.
2. **Detail page** `/services/<slug>/` → shows the large image, full `content`, breadcrumb, and SEO tags.
3. Untick `is_active` and the card and its page both return **404** (Not Found) to visitors. The nav item stays, because the nav links to the `#services` anchor, not to a specific service.

---

## 8. `Course` — the courses grid

**Admin:** `Academy` → `الدورات التدريبية` (Courses)

The "Our Courses" section, plus a detail page that carries the price, duration, videos, and the WhatsApp enrollment button.

### Fields

| Field | Arabic label | Required | Used for |
|---|---|---|---|
| `name_ar` / `name_en` | اسم الدورة | **Yes** | Card heading and page `<h1>` |
| `slug` | الرابط المختصر | **Yes** | The page address, e.g. `osha-general-industry` |
| `image` | صورة الدورة | **Yes** | Card photo, cropped 16:10 |
| `image_alt_ar` / `image_alt_en` | النص البديل | No | Screen-reader text |
| `short_description_ar` / `short_description_en` | الوصف المختصر | No | Card text — keep to 1–2 lines |
| `description_ar` / `description_en` | الوصف الكامل | No | Full body on the detail page |
| `duration_ar` / `duration_en` | المدة | **Yes** | Free text badge, e.g. `30 يومًا` / `30 Days` |
| `price` | السعر | **Yes** | Price badge. Numbers only, **0 or greater** |
| `display_order` | ترتيب العرض | No | Card order |
| `is_active` | نشط | No | Visible or not |

`duration` is a **text** field, not a number — write "30 يومًا" in Arabic and "30 Days" in English.

`price` is a real decimal: enter `350`, not `"350 EGP"`. Two things follow from this:

- **No currency is printed.** The badge shows the bare number. If you need "EGP" or "$" visible, that has to come from the surrounding design, not this field.
- **It always shows two decimals.** Enter `350` and visitors see `350.00`.

### Extra admin columns

The course list view shows two computed columns:

- **معاينة (Preview)** — a small thumbnail, so you can spot the wrong image at a glance.
- **عدد الفيديوهات (Video count)** — how many videos are attached.

### Adding videos

**Course videos are edited inline, inside the course page itself.** Scroll to the **فيديوهات الدورة (Course Videos)** panel at the bottom of the course form and use the stacked rows. You do not need to visit a separate "videos" page.

There is one empty row ready to go (`extra = 1`). To add more, use the **+** button at the bottom of the panel. Set `display_order` on each row to control the playback order.

For a full standalone view of all videos across all courses, use `Academy → فيديوهات الدورات`.

### Where it shows in the UI

1. **Homepage** `/` → the `#courses` section. Each card shows image, name, short description, a **price badge**, a **duration badge**, and a **"View Course"** button.
2. **Detail page** `/courses/<slug>/` → breadcrumb, `<h1>`, duration and price chips, full description, the video list, and the WhatsApp enrollment button.
3. **SEO** — the course page outputs its own `<title>`, meta description, canonical link, and Open Graph image automatically from the name/description/image you entered. Nothing extra to configure.
4. Untick `is_active` and the card disappears and the page 404s.

---

## 9. `CourseVideo` — videos inside a course

**Admin:** `Academy` → `فيديوهات الدورات` (Course Videos), or the inline panel inside each course.

### Fields

| Field | Arabic label | Required | Notes |
|---|---|---|---|
| `course` | الدورة | **Yes** | Which course this video belongs to |
| `title_ar` / `title_en` | العنوان | No | Heading above the player |
| `description_ar` / `description_en` | الوصف | No | Notes below the player |
| `video_file` | ملف الفيديو | **Yes** | **mp4 or webm, 15 MB maximum** |
| `thumbnail` | صورة مصغرة | No | Optional preview still |
| `display_order` | ترتيب العرض | No | Playback order within the course |
| `is_active` | نشط | No | Visible or not |

### File rules — these are enforced

- **Format:** `.mp4` or `.webm` only. Anything else is rejected with *"اسم الملف ليس مدعومًا"*.
- **Size:** 15 MB hard limit. Over it and you get *"حجم الفيديو كبير جدًا (X م.ب)"* naming the actual size.
- Keep files under the limit by encoding at a modest bitrate rather than uploading a raw camera file.

### Where it shows in the UI

The video list on `/courses/<slug>/`, below the description and above the footer. Each video sits in a 16:9 player with native browser controls. Videos are ordered by `display_order` and only **active** videos are shown — the page query filters them for you.

Videos load with `preload="metadata"`, so the page does not download every video the moment it opens. The first video is prefetched to make it start faster.

**Videos never appear on the homepage.** They exist only on the course detail page. A course with no videos is completely normal and still publishes fine — it simply has no video section.

### Caution

Deleting a video deletes its uploaded file from storage permanently. Untick `is_active` instead if you might want it back.

---

## 10. `Review` — student testimonials

**Admin:** `Academy` → `تقييمات الطلاب` (Reviews)

The "What Our Students Say" carousel on the homepage.

### Fields

| Field | Arabic label | Required | Used for |
|---|---|---|---|
| `image` | صورة التقييم | **Yes** | The testimonial screenshot |
| `image_alt_ar` / `image_alt_en` | النص البديل | No | Screen-reader text |
| `student_name_ar` / `student_name_en` | اسم الطالب | No | Caption under the image |
| `description_ar` / `description_en` | الوصف | No | Quote text under the name |
| `display_order` | ترتيب العرض | No | Carousel order |
| `is_active` | نشط | No | Visible or not |

**There is no slug and no separate detail page.** A review is homepage-only.

### Where it shows in the UI

The `#reviews` section of `/`. Each review is one carousel slide: the screenshot inside a white padded frame, with the student name and description in a caption below.

Images are displayed with `object-fit: contain` and capped at 420px tall, so **screenshots are never cropped**. That is deliberate — a certificate or result screenshot must stay fully readable. Upload the full screenshot as-is; do not pre-crop it.

Same carousel rule as the hero: arrows and dots appear only with 2+ active reviews.

**Tip:** get written permission before publishing a student's name, photo, or result screenshot.

---

## 11. `ContactMessage` — the message inbox

**Admin:** `Academy` → `رسائل الاتصال` (Contact Messages)

Every submission from the contact form on the homepage lands here. This is your inbox, not website content — it has no `is_active` and no `display_order`.

### Fields

| Field | Arabic label | Auto? | Notes |
|---|---|---|---|
| `name` | الاسم | From visitor | Max 150 characters |
| `email` | البريد الإلكتروني | From visitor | Validated — must look like an email |
| `phone` | رقم الهاتف | From visitor | Max 32 characters |
| `message` | الرسالة | From visitor | The message body |
| `is_read` | مقروء | Set to `False` | Tick to mark handled |
| `created_at` | تاريخ الإنشاء | Automatic | Read-only |

### Working with the inbox

- **Newest first** by default, with a date drill-down in the sidebar for jumping to a particular day.
- **Filter** by `مقروء` (read/unread) or by date.
- **Search** across name, email, phone, and the message body.
- **Bulk actions** — select rows with the checkboxes, then choose from the action dropdown:
  - **Mark as read**
  - **Mark as unread**
- Every field is read-only after submission, including the timestamps. Messages cannot be edited, only marked and deleted.

### Where it shows in the UI

Nowhere on the website. It is the record of what visitors sent through the **Contact Us** form.

The form re-renders with inline error messages under each bad field, so a visitor with a typo in their email address never creates a broken record. On success the visitor is redirected back to `/#contact` and sees a confirmation message. **No email is sent** — this admin list is the only place messages appear, so check it regularly.

---

## 12. Certificate app models

These live under the separate `CERTIFICATES` admin section and serve the **certificate verification page**, not the academy marketing pages.

### `AppSettings` — branding (singleton)

**Admin:** `Certificates` → `إعدادات التطبيق` (App Settings)

Also a singleton: one record, no delete button.

| Field | Arabic label | Used for |
|---|---|---|
| `logo` | الشعار | The logo in the header **and** footer of every page |
| `academy_name_ar` / `academy_name_en` | اسم الأكاديمية | Brand name in header/footer and SEO |
| `primary_color` / `secondary_color` | الألوان الأساسية | Brand colors as hex codes, e.g. `#0B2D4A` |
| `footer_text_ar` / `footer_text_en` | نص التذييل | Footer copyright line |

### Built-in fallbacks

Nothing here is required — the site works with this model completely empty. Each field has a sensible default:

| Field left blank | Falls back to |
|---|---|
| `logo` | The bundled `static/images/logo.jpg` |
| `academy_name_ar` | `أكاديمية Future HSE` |
| `academy_name_en` | `Future HSE Academy` |
| `primary_color` | `#0B2D4A` (dark navy) |
| `secondary_color` | `#4C9F24` (green) |
| `footer_text_ar` | `© أكاديمية Future HSE — جميع الحقوق محفوظة.` |
| `footer_text_en` | `© Future HSE Academy - All rights reserved.` |

Colors are passed through a `safe_color` filter before being written into the page, so **a malformed hex value is silently ignored** and the default is used instead. You cannot break the site's styling from this panel.

> **Do not confuse these with `AcademySettings`.** `AppSettings` controls **appearance** (logo, colors, footer). `AcademySettings` controls **contact** (the WhatsApp number only). Both are singletons; they are edited in different admin sections and do different jobs.

### `Certificate` — student certificates

**Admin:** `Certificates` → `الشهادات` (Certificates)

| Field | Arabic label | Required | Notes |
|---|---|---|---|
| `student_name` | اسم الطالب | **Yes** | Enter the **full four-part name** exactly as it should print on the certificate |
| `certificate_code_1` + `certificate_pdf_1` | الشهادة الأولى | **Yes** | Verification code and the PDF |
| `certificate_code_2` + `certificate_pdf_2` | الشهادة الثانية | No | Collapse this section if unused |
| `certificate_code_3` + `certificate_pdf_3` | الشهادة الثالثة | No | Collapse this section if unused |
| `created_at` / `updated_at` | — | Auto | Read-only |

### Where it shows in the UI

`/certificate/<code>/` — the public verification page a holder uses to prove a certificate is genuine. It shows the student's name, the certificate, and a **QR code** encoding the verification URL.

Codes must be **unique**. If you enter a code that already exists, the save is rejected.

The second and third certificate fieldsets are **collapsed by default** — expand them only when a student holds more than one certificate. One student can hold up to three.

This model is entered by hand; there is no code generator yet. See `CERTIFICATE_CODE_GENERATION_FEATURE.md` for the proposed automated version.

---

## 13. Quick reference table

Print this. It answers "I changed X — where did it go?"

| I edited... | Check this page to see the change |
|---|---|
| `AcademySettings.whatsapp_number` | Every page — the floating button; `/courses/<slug>/` for the enroll button |
| `AppSettings.logo` | The header on every page |
| `AppSettings.primary_color` / `secondary_color` | Buttons, links, section accents site-wide |
| `AppSettings.footer_text_*` | The footer on every page |
| `HeroSlide` | `/` — the top carousel |
| `Service` | `/` — `#services` grid, and `/services/<slug>/` |
| `Course` | `/` — `#courses` grid, and `/courses/<slug>/` |
| `CourseVideo` | `/courses/<slug>/` — the video list only |
| `Review` | `/` — `#reviews` carousel |
| `ContactMessage` | Nowhere — it is the inbox |
| `Certificate` | `/certificate/<code>/` |

---

## 14. Recommended first-time setup order

Follow this order on a new, empty database. Doing settings and hero first means the page is presentable even while you are still adding courses.

1. **`Certificates → App Settings`** — set the logo, academy name, colors, and footer text. This affects the header on every page, so do it first.
2. **`Academy → Academy Settings`** — add the WhatsApp number. The floating button appears immediately.
3. **`Academy → Hero Slides`** — add 2–3 banners. The page immediately stops showing the fallback banner.
4. **`Academy → Services`** — add at least one, `display_order` 1, 2, 3.
5. **`Academy → Courses`** — add at least one with name, duration, price, and image.
6. **Inside each course** — add its videos in the inline panel at the bottom.
7. **`Academy → Reviews`** — add at least one screenshot.
8. **Check `/`** in both Arabic and English. Every section should now be present.
9. **`Academy → Contact Messages`** — send yourself a test message from the form to confirm the inbox works.

Steps 1–3 alone turn the page from "almost empty" into a complete-looking site.

---

## 15. Image sizing guide

The site crops and scales images for you. Upload the dimensions below to get the best result with no surprises.

| Where | Cropped to | Recommended size | Notes |
|---|---|---|---|
| `HeroSlide.image` | 16:7 desktop, 16:9 mobile | **1920 × 840 px** | Landscape. Keep important text away from the bottom-left/right, the gradient darkens it |
| `Service.image` | 16:10 | **1280 × 800 px** | Cropped to fill, so keep faces away from edges |
| `Course.image` | 16:10 | **1280 × 800 px** | Same |
| `Review.image` | **Never cropped** | ~1000 × 620 px | Shown whole with `contain` |
| `CourseVideo.thumbnail` | — | 1280 × 720 px | Optional |
| `AppSettings.logo` | — | ~200 × 60 px | Transparent PNG looks best |

Formats: **JPG or PNG**. Keep each file under ~500 KB so pages stay fast — the site lazy-loads card images, but the hero image loads eagerly because it is above the fold.

**Always fill in the alt-text fields.** They are what a screen reader announces, and they are the only description a visitor gets if an image fails to load.

---

## 16. Validation rules and limits

| Rule | Limit | Message if broken |
|---|---|---|
| WhatsApp number | 5–20 digits | رقم الواتساب غير صالح |
| Video format | `.mp4`, `.webm` | اسم الملف ليس مدعومًا. استخدم mp4 أو webm |
| Video size | 15 MB | حجم الفيديو كبير جدًا (X م.ب) |
| Course price | 0 or greater | Cannot be negative |
| Service / Course slug | unique, max 180 chars | The slug with value X is already in use |
| Contact name | 150 characters | Form re-renders with the error |
| Contact email | must be a valid email | Form re-renders with the error |
| Contact phone | 32 characters | Form re-renders with the error |
| Certificate code | unique | Duplicate rejected on save |

Storage note: uploaded files go to **Cloudflare R2** when the R2 environment variables are configured, and to local `media/` otherwise. In R2 mode `MEDIA_ROOT` is intentionally unset, so **running the test suite leaves small `test_*.gif` files in the project root** — they are harmless test leftovers, not content. Do not commit them.

---

## 17. Arabic / English rules

1. **Pair everything.** If you write an Arabic title, write the English one too. It is the same amount of work and keeps both audiences served.
2. **English fallback protects you.** An empty Arabic field shows the English value instead of nothing. So a missing translation degrades gracefully — it never renders an empty heading.
3. **Test both.** Use the language switcher in the header. It posts to `/set-language/` and the whole page re-renders, flipping `dir` to `rtl` in Arabic and `ltr` in English. Bootstrap's RTL stylesheet swaps in automatically.
4. **Watch the flip.** In Arabic the layout mirrors: the logo goes right, text aligns right, and the WhatsApp button moves to the **left**. This is expected, not a bug.
5. **`display_order` is shared** between languages. It is a single ordering, not one per language.
6. **Plain text only.** These fields are rendered as text, not rich text. Paste plain paragraphs; `<b>` or `<div>` tags will appear literally. Use blank lines to separate paragraphs.

---

## 18. Troubleshooting

**"The services/courses/reviews section is missing entirely."**
Expected. There are no **active** records for that model. Add one with `is_active` ticked.

**"Only the header, a banner, and the contact form show."**
The database is empty. Work through section 14 in order.

**"The floating WhatsApp button is missing."**
`AcademySettings.whatsapp_number` is empty, or has fewer than 5 digits. Re-check section 5.

**"The WhatsApp button is there but the chat does not open."**
The number is wrong or is not a WhatsApp account. Test it by tapping the button.

**"There are no arrows or dots on the carousel."**
You have exactly one active slide. The controls only appear with two or more. Not a bug.

**"My course page returns 404."**
Either the `slug` in the URL is wrong, or `is_active` is unticked.

**"The URL of my course/service changed."**
You edited the `slug`. Restore the old value, or accept that the old links are dead and set up a redirect.

**"I saved a video but it is not on the page."**
Check three things: the video is inside the **right course**, its `is_active` is ticked, and the file is mp4/webm under 15 MB.

**"My uploaded image does not appear."**
Confirm the file finished uploading and is not still a placeholder name. If the file is genuinely absent the card falls back to a neutral background rather than a broken icon.

**"I cannot delete `AcademySettings` or `AppSettings`."**
Correct behaviour. They are singletons, and the templates require exactly one.

**"I cannot add a second `AppSettings` row."**
Same reason. Edit the existing row.

**"My changes are not visible on the live site."**
Check `is_active` first, then confirm the content is deployed. Browsers and servers cache pages — hard-refresh.

**"Where did my contact messages go?"**
`Academy → Contact Messages`, newest first. Note that no email is sent anywhere.

---

## 19. Do's and don'ts

### Do

- Tick `is_active` only when the content is ready — a half-finished draft is one checkbox away from going live.
- Use `display_order` deliberately; the site always honours it.
- Fill in both languages and both alt-text fields.
- Upload a full, uncropped screenshot for reviews.
- Keep video files under 15 MB.
- Use `is_active` to hide content temporarily, and real deletion only when you are certain.
- Preview every change in both Arabic and English before you finish.
- Back up the database before bulk edits.

### Don't

- Don't reuse a `slug` — it is rejected, and it breaks existing links.
- Don't change a published `slug` without a redirect plan.
- Don't put currency symbols or HTML inside the `price` field.
- Don't crop review screenshots yourself — the layout already fits them whole.
- Don't delete uploaded files by unticking `is_active`; that is the safe reversible option.
- Don't assume deleting a `CourseVideo` is recoverable — the file is gone from storage.
- Don't commit the stray `test_*.gif` files or upload folders in the project root.
- Don't edit models or run `migrate` from the admin; schema changes are a developer task.

---

*This guide documents the admin panel only. For system architecture see `STRUCTURE.md`, and for the current codebase state see `CURRENT_PROJECT_ANALYSIS.md`.*
