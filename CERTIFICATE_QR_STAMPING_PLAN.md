# Certificate QR Stamping — Implementation Plan

Status: implemented (2026-10-07) — see §11 for changes made during implementation
Date: 2026-10-07
Supersedes the "QR-first / download & merge outside the admin" flow in
`CERTIFICATE_QR_WORKFLOW.md` and the random code generator in
`CERTIFICATE_CODE_GENERATION_FEATURE.md`.

## 1. Goal

Staff do everything inside the admin:

1. Write the student name and the code for each certificate (manual codes,
   e.g. `FA0082`; no automatic code generator).
2. Upload the certificate design PDF **without** a QR.
3. The server generates the QR for that code and stamps it on the PDF.
4. Staff control where the QR sits (drag/resize on a PDF preview), and the
   server re-stamps.

The public verification page, its URLs, and every existing certificate
remain unchanged.

## 2. Target flow

```
Certificate add/change (admin)
  name
  slot N: code  +  "PDF without QR" (original)   [+ legacy "final PDF" upload]
        │ Save
        ▼
  server: validate code → store original (CertificateSource)
          → stamp QR at default position → write certificate_pdf_N
        │
        ▼
  "Place QR (N)" page: PDF.js preview + draggable square → Apply
          → re-stamp from the ORIGINAL → overwrite certificate_pdf_N
```

Re-stamp also happens automatically when the code or student name of a
slot that has an original changes (the URL inside the QR depends on both).

Legacy / fallback: staff can still upload a final PDF that already contains
a QR directly in `certificate_pdf_N` (manual mode). Existing rows stay in
manual mode until someone uploads an original for them.

## 3. Data model (one additive migration)

### 3.1 `Certificate` (existing table, no data change)

- `certificate_pdf_1`: add `blank=True` (state-only change; no SQL on the
  live DB). Required because the stamped file is produced after form
  validation.
- Code fields: add a format validator — `^[A-Z0-9]+$` after uppercasing
  (no hyphen, because the verify view splits on the last `-`). Existing
  codes such as `FA0064`, `SR206`, `FA0082` pass.

### 3.2 New `CertificateSource`

One row per stamped slot. Keeps the original so we never stamp on top of
an already-stamped file.

| Field | Type | Notes |
|---|---|---|
| certificate | FK → Certificate, CASCADE | `related_name="sources"` |
| slot | PositiveSmallInteger (1/2/3) | unique together with certificate |
| original_pdf | FileField `certificates/originals/` | PDF validator |
| page | PositiveSmallInteger, default 0 | page index for the QR |
| x, y | Float 0..1 | top-left of the QR, as fraction of page width/height |
| size | Float 0..1 | QR side as fraction of page width |
| stamped_code | Char | code encoded in the current stamped file |
| stamped_url | Char | URL encoded in the current stamped file |
| stamped_at | DateTime null | |

### 3.3 `AppSettings` (existing singleton) — default QR position

`qr_default_page`, `qr_default_x`, `qr_default_y`, `qr_default_size`
(defaults e.g. bottom-right corner). New uploads use these, so most
certificates need zero clicks.

## 4. Server components (`certificate_app`)

| File | Responsibility |
|---|---|
| `qr_utils.py` | Single URL builder: `CERTIFICATE_PUBLIC_BASE_URL` + `reverse()` + one slug function shared with `Certificate.generate_url_slug()`; PNG download helper (kept as fallback). |
| `pdf_stamp.py` (new) | `stamp_qr(original_file, url, page, x, y, size) -> bytes` using **pypdf + ReportLab vector QR** (`barLevel="H"`, white quiet zone). Handles CropBox origin and page `/Rotate`; raises a clean `StampError` for encrypted/broken PDFs or out-of-range page. |
| `services.py` (new) | `apply_source(certificate, slot)` : read original via storage → stamp → save to `certificate_pdf_N` (deletes the previous stamped file) → update `stamped_*`. Storage-agnostic (local or R2), no temp files. |
| `forms.py` | `CertificateAdminForm`: extra non-model fields `source_pdf_1..3` (PDF without QR); validation rules in §5. `QRPlacementForm` (page/x/y/size with range checks). Remove `QRGeneratorForm`. |
| `admin.py` | Uses the form; `save_related` calls the service; per-slot status + "Place QR" + "View PDF" + PNG download links; custom URLs in §6. Remove the stateless generator/download views. |
| `templates/admin/certificate_app/qr_place.html` | PDF.js (cdnjs) canvas + square drag/resize box, page selector, Apply. |

Settings: `CERTIFICATE_PUBLIC_BASE_URL` from env, default
`https://www.futureacademey.com` (same host used by the QRs already printed).

Requirements: add `pypdf`, `reportlab` (pinned).

## 5. Validation rules

Per slot N:

- Code format `^[A-Z0-9]+$` (auto-uppercased), max 50.
- Code unique **across all three columns of all rows** (case-insensitive,
  excluding the current record). The DB `unique=True` is per column only,
  so today `FA0082` in slot 1 of student A and slot 2 of student B is
  accepted and both verification pages then return 404.
- Code ≠ other codes on the same record (existing rule).
- Code requires a final PDF **or** an original (no public "verified"
  page without a PDF).
- Original or final PDF requires a code (existing rule).
- Uploading both an original and a final PDF for the same slot in one save
  → error (ambiguous).
- Clearing a code removes the slot's source row and stamped file.
- Placement: `0 ≤ x, y < 1`, `size` between a print-safe minimum (≈2 cm on
  A4 ≈ 0.10 of width) and 0.5, box must stay inside the page, `page` must
  exist in the PDF.

## 6. Admin URLs (all via `get_urls()` + `admin_view` + model permission)

| URL | Method | Permission | Purpose |
|---|---|---|---|
| `<id>/qr-place/<slot>/` | GET/POST | change_certificate | Placement page; POST re-stamps |
| `<id>/qr-source/<slot>/` | GET | change_certificate | Streams the original PDF same-origin (PDF.js on an R2 URL would need bucket CORS) |
| `<id>/qr/<slot>/` | GET | view_certificate | QR PNG download (fallback) |
| `<id>/qr-zip/` | GET | view_certificate | All QR PNGs + `urls.txt` (fallback) |

Changelist action "download QR ZIP" kept; `pdf_status` column shows
`مكتمل` / `بدون PDF` / `QR مطبوع آلياً` per slot.

Removed: `qr-generator/`, `qr-download/` (stateless flow no longer needed;
smaller attack surface).

## 7. Old bugs fixed in this work

| # | Bug | Fix |
|---|---|---|
| 1 | `certificate_pdf_1` not `blank=True` → draft for slot 1 impossible | migration (state-only) |
| 2 | QR URL built from request host (localhost / railway / http could be printed forever) | fixed `CERTIFICATE_PUBLIC_BASE_URL` |
| 3 | Same code allowed in different columns of different rows → both verify pages 404 | cross-column iexact check in form/model clean |
| 4 | Generator didn't check DB for existing codes | generator removed; check in #3 covers the admin form |
| 5 | Relative link `qr-generator/` broken on change page | removed with generator; all links use `reverse()` |
| 6 | `format_html()` called without args on f-string HTML (deprecated, unescaped) | `format_html_join` |
| 7 | Code without PDF showed a public "verified" page with no PDF | code requires final or original PDF |
| 8 | Custom admin views only checked `is_staff` | explicit `has_view/change_permission` checks |
| 9 | No code format validation (hyphen breaks URL parsing) | `^[A-Z0-9]+$` validator |
| 10 | Two slug functions (`generate_url_slug` gives `-fa0082` for Arabic names, `qr_utils` gives `certificate-fa0082`) | one shared function |
| 11 | `CERTIFICATE_QR_WORKFLOW.md` claims `futureacademey.com` is a typo | doc rewritten for the new flow |

## 8. Tests (`certificate_app/tests.py`)

- Stamping: output is a valid PDF, same page count, original untouched;
  stamping twice from original ≠ double QR; rotated page and non-A4 page;
  encrypted/broken PDF → form error, not 500.
- Coordinate conversion (top-left fractions → PDF points) for A4 portrait,
  landscape, and offset CropBox.
- Encoded URL equals `CERTIFICATE_PUBLIC_BASE_URL/certificate/<slug>-<code>/`.
- Form: cross-row/cross-column duplicate rejected, hyphen rejected, legacy
  codes accepted, code without any PDF rejected, both PDFs for a slot
  rejected.
- Re-stamp on code change and on name change; placement POST re-stamps.
- Permissions: anonymous → login redirect; staff without change permission
  → 403 on placement/source views.
- Regression: existing tests in `academy_app/tests.py` for both verify URL
  forms and PDF links still pass.

## 9. Rollout on the live site

1. `pip install -r requirements.txt` (adds `pypdf`, `reportlab`).
2. Set `CERTIFICATE_PUBLIC_BASE_URL=https://www.futureacademey.com`.
3. `python manage.py migrate` (additive: new table, new AppSettings
   columns with defaults, `blank=True` state change).
4. Existing certificates: untouched, remain in manual mode.
5. Acceptance: stamp one real certificate → print → scan with a phone →
   verification page + PDF open on the production domain.

## 10. Out of scope (later)

- Automatic code generation / random codes (sequential codes remain
  enumerable; revisit if that becomes a concern).
- Stamping student name text (Arabic shaping in ReportLab).
- Bulk CSV import, `Student → CertificateItem` normalization, audit log.

## 11. Implementation notes (deviations from the plan)

- **Unique storage keys.** `django-storages` S3/R2 overwrites files with
  the same name by default, so two students' `certificate.pdf` uploads
  replaced each other (existing live bug). All certificate PDFs, originals
  and stamped outputs now get a random prefix/suffix
  (`certificate_pdf_upload_to`, `original_pdf_upload_to`, `apply_source`).
- **Tests use local temp storage** (`LOCAL_STORAGES` in
  `certificate_app/tests.py`). A developer shell with `R2_*` variables
  would otherwise write test files to the real bucket.
- Migration `0004_certificate_qr_stamping` only adds `AppSettings` columns
  and the `CertificateSource` table; the `Certificate` alterations
  (validators, `blank`, `upload_to`) produce no SQL.
- **Single upload field per slot** (`upload_pdf_N` + `has_qr_N`) after
  UI testing: two upload fields led staff to upload the design into the
  "final" field, so nothing was stamped. The placement page also works on
  a slot with a manual PDF (first «تطبيق» turns it into the original).
- `.env` contains the production R2 keys and `settings.py` loads it, so
  every local `runserver` writes uploads to the real bucket.
  `.claude/launch.json` sets `R2_ACCESS_KEY_ID=` (empty; `load_dotenv`
  does not override existing variables) to force local storage.
